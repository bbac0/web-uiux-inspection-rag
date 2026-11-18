import google.generativeai as genai
import streamlit as st
import os
import time
import json
import re
import asyncio
import random
import threading

from datetime import datetime
from PyPDF2 import PdfReader
from playwright.async_api import async_playwright
from urllib.parse import urlparse
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

from services.exp_config import ExperimentConfig, prompt_today, HTML_CHAR_LIMIT
from services import llm_wrapper as lw


RAG_QUERY = "웹 UI/UX 표준 가이드라인 공통 규정"
RAG_K = 4


def calculate_score(total, fault_count):
    if total == 0: return 0
    raw_score = (1 - fault_count / total) * 100
    return int(max(0, round(raw_score)))

_VECTOR_STORE = None
_VECTOR_STORES = {}
_VECTOR_LOCK = threading.RLock()

def get_vector_store(persist_directory="./chroma_db"):
    global _VECTOR_STORE
    with _VECTOR_LOCK:
        if persist_directory == "./chroma_db":
            if _VECTOR_STORE is None:
                embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
                _VECTOR_STORE = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
            return _VECTOR_STORE
        if persist_directory not in _VECTOR_STORES:
            if not os.path.exists(os.path.join(persist_directory, "chroma.sqlite3")):
                # Chroma 는 없는 경로에 빈 DB 를 새로 만든다. 실험에서는 이를 막는다.
                raise FileNotFoundError(f"vector DB not found: {persist_directory}")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
            _VECTOR_STORES[persist_directory] = Chroma(persist_directory=persist_directory,
                                                       embedding_function=embeddings)
        return _VECTOR_STORES[persist_directory]


def _format_context(docs):
    context_list = []
    for doc in docs:
        page_num = doc.metadata.get('page', 0) + 1
        source_file = os.path.basename(doc.metadata.get('source', '정부가이드라인.pdf'))
        context_list.append(f"[{source_file} - {page_num}페이지]\n{doc.page_content}")
    return "\n\n".join(context_list)


def build_page_query(signals):
    """--query-mode page 의 질의 생성 규칙 (results/revision/README.md 에 같은 내용 문서화).

    1. 순서: <title> → h1~h3 헤딩(문서 순서) → 버튼 라벨(문서 순서)
       버튼 라벨 = <button> 의 textContent, input[type=submit|button|reset] 의 value, [role=button] 의 textContent
    2. 각 항목은 앞뒤 공백 제거, 연속 공백을 한 칸으로. 빈 항목 제거, 같은 문자열은 처음 것만 남김.
    3. 공백 한 칸으로 이어 붙인다. 결과가 비면 고정 질의(RAG_QUERY)로 대체하고 fallback=True 로 기록.
    textContent 를 쓰므로 CSS 로 숨겨진(font-size:0 등) 버튼 라벨도 포함된다.
    """
    items = [signals.get("title", "")] + list(signals.get("headings", [])) + list(signals.get("buttons", []))
    seen, parts = set(), []
    for it in items:
        s = re.sub(r"\s+", " ", it or "").strip()
        if s and s not in seen:
            seen.add(s)
            parts.append(s)
    q = " ".join(parts)
    return (q, False) if q else (RAG_QUERY, True)


PAGE_SIGNALS_JS = """() => {
    const t = s => (s || '').replace(/\\s+/g, ' ').trim();
    const headings = Array.from(document.querySelectorAll('h1, h2, h3')).map(e => t(e.textContent));
    const buttons = Array.from(document.querySelectorAll(
        'button, input[type=submit], input[type=button], input[type=reset], [role=button]'))
        .map(e => e.tagName === 'INPUT' ? t(e.value) : t(e.textContent));
    return {title: t(document.title), headings, buttons};
}"""


def _retrieve_experiment(cfg, signals):
    """실험 경로의 검색. 질의 임베딩과 벡터 검색을 분리해 시간을 재고 청크 ID·거리를 남긴다.
    fixed/page: embed_query → similarity_search_by_vector_with_relevance_scores (프로덕션 similarity_search 와 같은 연산)
    oracle: 지정된 청크 ID 를 그대로 가져온다 (임베딩·거리 없음)."""
    detail = {"enabled": cfg.rag and os.getenv("DISABLE_RAG") != "1", "query_mode": cfg.query_mode,
              "query": None, "query_fallback": False, "chroma_path": cfg.chroma_path,
              "n_chunks": 0, "chunks": [], "error": None,
              "latency": {"query_embedding": None, "vector_search": None},
              "embedding_attempts": 0, "embedding_errors": []}
    if not detail["enabled"]:
        return "", detail
    store = get_vector_store(cfg.chroma_path)
    if cfg.query_mode == "oracle":
        ids = list(cfg.oracle_chunks.get(cfg.page_id, []))
        detail["query"] = None
        t0 = time.time()
        got = store.get(ids=ids, include=["documents", "metadatas"]) if ids else {"ids": [], "documents": [], "metadatas": []}
        detail["latency"]["vector_search"] = round(time.time() - t0, 4)
        by_id = {i: (d, m) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])}
        from langchain_core.documents import Document
        docs = [Document(page_content=by_id[i][0], metadata=by_id[i][1] or {}, id=i) for i in ids if i in by_id]
        missing = [i for i in ids if i not in by_id]
        if missing:
            detail["error"] = f"oracle chunk ids not found: {missing}"
        scored = [(d, None) for d in docs]
    else:
        if cfg.query_mode == "page":
            q, fb = build_page_query(signals or {})
        else:
            q, fb = RAG_QUERY, False
        detail["query"], detail["query_fallback"] = q, fb
        t0 = time.time()
        vec, attempts, errs = lw.call_with_retry(lambda: store._embedding_function.embed_query(q),
                                                 max_retries=cfg.max_retries)
        t1 = time.time()
        detail["embedding_attempts"], detail["embedding_errors"] = attempts, errs
        with _VECTOR_LOCK:
            scored = store.similarity_search_by_vector_with_relevance_scores(vec, k=RAG_K)
        t2 = time.time()
        detail["latency"].update(query_embedding=round(t1 - t0, 4), vector_search=round(t2 - t1, 4))
    detail["chunks"] = [{"id": d.id, "distance": (None if s is None else float(s)),
                         "source": os.path.basename(d.metadata.get("source", "")),
                         "page": d.metadata.get("page", 0) + 1} for d, s in scored]
    detail["n_chunks"] = len(scored)
    return _format_context([d for d, _ in scored]), detail


def retrieve_context(config=None, signals=None):
    if config is not None:
        ctx, detail = _retrieve_experiment(config, signals)
        info = {"enabled": detail["enabled"], "ok": detail["error"] is None, "n_chunks": detail["n_chunks"],
                "error": detail["error"]}
        return ctx, info, detail
    info = {"enabled": os.getenv("DISABLE_RAG") != "1", "ok": False, "n_chunks": 0, "error": None}
    if not info["enabled"]:
        return "", info, None
    try:
        with _VECTOR_LOCK:
            vector_store = get_vector_store()
            docs = vector_store.similarity_search(RAG_QUERY, k=RAG_K)
        info.update(ok=True, n_chunks=len(docs))
        return _format_context(docs), info, None
    except Exception as e:
        print(f"베이스 DB 검색 실패: {e}")
        info["error"] = str(e)
        return "", info, None


def generate_with_retry(model, analysis_input, retries=4):
    for attempt in range(1, retries + 1):
        try:
            return model.generate_content(analysis_input)
        except Exception as e:
            msg = str(e).lower()
            transient = any(k in msg for k in ("429", "rate", "quota", "503", "unavailable", "overloaded", "deadline"))
            if not transient or attempt == retries:
                raise
            time.sleep(min(30, 2 ** attempt) + random.uniform(0, 1))


class AnalysisStageError(RuntimeError):
    """실험 경로에서 LLM 호출 전 단계가 실패했을 때 (status 를 로그에 남기기 위함)."""
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def analyze_with_gemini(html_content: str, screenshot_path: str, pdf_paths: list,
                        config=None, page_ctx=None) -> dict:
    """config 가 None 이면 기존 프로덕션 동작 그대로. config 가 있으면 조건을 적용하고 run 로그를 남긴다."""
    if config is None:
        return _analyze_impl(html_content, screenshot_path, pdf_paths, None, None, None)
    page_ctx = page_ctx or {}
    rec = None
    if config.logger is not None:
        rec = lw.empty_record(config.logger.run_id, config.condition, page_ctx.get("url", ""),
                              page_ctx.get("page_id"), page_ctx.get("template_id"))
        rec.update(prompt_date=config.prompt_date, model_name="models/gemini-2.5-flash",
                   modality=config.modality, viewport=list(config.viewport))
        rec["latency_sec"]["acquisition"] = page_ctx.get("acquisition_sec")
    t0 = time.time()
    try:
        return _analyze_impl(html_content, screenshot_path, pdf_paths, config, page_ctx, rec)
    except Exception as e:
        if rec is not None:
            rec["status"] = getattr(e, "status", "api_error")
            errs = getattr(e, "errors", None)
            if errs:
                rec["errors"].extend(errs)
                rec["attempts"] = max(rec["attempts"], getattr(e, "attempts", 0))
                rec["retries"] = max(0, rec["attempts"] - 1)
            else:
                rec["errors"].append({"attempt": None, "type": type(e).__name__, "message": str(e)[:500]})
        raise
    finally:
        if rec is not None:
            rec["ts_end_utc"] = lw.utc_now()
            rec["latency_sec"]["total"] = round((page_ctx.get("acquisition_sec") or 0) + time.time() - t0, 4)
            config.logger.write(rec)


def _analyze_impl(html_content, screenshot_path, pdf_paths, cfg, page_ctx, rec):

    if not html_content or len(html_content) < 100:
        print(f"경고: HTML 내용이 너무 짧거나 비어있습니다. (길이: {len(html_content)})")
    if not os.path.exists(screenshot_path):
        print(f"경고: 스크린샷 파일을 찾을 수 없습니다: {screenshot_path}")

    start_time = time.time()

    # API 세팅
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    os.environ["GOOGLE_API_KEY"] = api_key

    # 베이스 DB 검색 로직
    if cfg is None:
        retrieved_context, rag_info, _ = retrieve_context()
    else:
        try:
            retrieved_context, rag_info, rag_detail = retrieve_context(cfg, (page_ctx or {}).get("signals"))
        except Exception as e:
            raise AnalysisStageError("rag_error", f"RAG retrieval failed: {e}") from e
        if rec is not None:
            rec["rag"] = {k: rag_detail.get(k) for k in lw.RAG_FIELDS}
            rec["rag"].update(query_fallback=rag_detail["query_fallback"], error=rag_detail["error"],
                              embedding_attempts=rag_detail["embedding_attempts"],
                              embedding_errors=rag_detail["embedding_errors"])
            rec["latency_sec"].update(rag_detail["latency"])
        if rag_detail["error"]:
            raise AnalysisStageError("rag_error", rag_detail["error"])
        if cfg.require_rag_chunks and rag_detail["enabled"] and rag_detail["n_chunks"] == 0:
            raise AnalysisStageError("rag_empty", f"RAG enabled but 0 chunks retrieved from {cfg.chroma_path}")

    # 커스텀 PDF 추출 로직
    user_custom_context = ""
    if pdf_paths:
        user_files = [p for p in pdf_paths if "temp" in p or "uploads" in p]
        if user_files:
            for path in user_files:
                try:
                    reader = PdfReader(path)
                    pdf_name = os.path.basename(path)
                    for i, page in enumerate(reader.pages):
                        user_custom_context += f"[{pdf_name} - {i+1}페이지]\n{page.extract_text()}\n"
                except Exception as e:
                    print(f"사용자 PDF 읽기 실패({path}): {e}")

    modality = cfg.modality if cfg is not None else "both"
    image_file = None
    if modality != "html":
        t_up = time.time()
        image_file, up_attempts, up_errs = lw.call_with_retry(
            lambda: genai.upload_file(screenshot_path),
            max_retries=cfg.max_retries if cfg is not None else 0)   # 프로덕션: 업로드 재시도 없음
        if rec is not None:
            rec["latency_sec"]["upload"] = round(time.time() - t_up, 4)
            rec["image_sha256"] = lw.sha256_file(screenshot_path)
            rec["upload_attempts"], rec["upload_errors"] = up_attempts, up_errs

    today = prompt_today(cfg.prompt_date if cfg is not None else None)
    html_block = html_content[:HTML_CHAR_LIMIT] if modality != "screenshot" else ""

    prompt = f"""
    너는 전문적인 UI/UX 및 코드 품질 검수관이야.
    첨부된 '모든' 가이드라인 문서(PDF)를 절대적인 기준으로 삼아, 
    제공된 웹사이트 스크린샷과 HTML 소스 코드를 분석해줘.

    [1. 정부 표준 가이드라인 (기본 지침)]
    {retrieved_context}

    [2. 사용자 지정 추가 가이드라인 (우선 적용)]
    {user_custom_context if user_custom_context else "추가 지침 없음"}

    현재 시점은 **{today}**이고, 모든 최신성 분석은 이 연도를 기준으로 해줘.
    가이드라인보다 더 좋은 방향이 있다면 추가적으로 남겨줘.
    
    ### 카테고리 분류 기준:
    1. **디자인**: 시각적 요소, 레이아웃, 명도 대비, '보이스 앤 톤', 버튼의 텍스트 레이블 등 사용자 경험과 관련된 사항
    2. **운영**: 콘텐츠의 최신성, 오타, 링크 연결 오류, 가이드라인에 명시된 표준 용어 준수 여부
    3. **기술**: HTML 마크업 오류(id 중복 등), 보안 취약점(autocomplete 미설정 등), 반응형 깨짐, 웹 접근성 기술 표준(WAI-ARIA) 위반
    
    결과는 프론트엔드 대시보드에 바로 띄울 수 있도록 반드시 아래 JSON 형식으로만 출력해. 
    다른 설명이나 마크다운 기호(```json)는 절대 쓰지 마.
    만약 위반 사항이 없다면 "issues": [] 빈 리스트를 반환해.
    
    {{
        "status": "success",
        "total_checked_count": 30,
        "summary": "전체적인 분석 요약평을 2~3줄로 작성",
        "issues": [
            {{
                "category": "디자인", 
                "description": "버튼 색상이 가이드라인(p.12)과 다름", 
                "suggestion": "#003366으로 변경하세요.",
                "source_file": "gov_guide.pdf",  
                "page_number": [12]
            }},
            {{
                "category": "운영", 
                "description": "메인 배너 텍스트 가독성 부족", 
                "suggestion": "명도 대비를 4.5:1 이상으로 높이세요.",
                "source_file": "gov_guide.pdf",  
                "page_number": [12]
            }},
            {{
                "category": "기술", 
                "description": "모바일 화면에서 입력창이 영역을 벗어남", 
                "suggestion": "CSS width 속성을 100%로 수정하세요.",
                "source_file": "gov_guide.pdf",  
                "page_number": [12, 13]
            }}
        ]
    }}
    
    [HTML 소스코드 일부]
    {html_block}
    """

    generation_config = genai.types.GenerationConfig(
        temperature=0.0,
        response_mime_type="application/json"
    )

    model = genai.GenerativeModel(
        model_name="models/gemini-2.5-flash",
        generation_config=generation_config
    )

    analysis_input = [image_file, prompt] if image_file is not None else [prompt]
    if rec is not None:
        rec["prompt_sha256"] = lw.sha256_text(prompt)
        rec["html_chars_sent"] = len(html_block)
        rec["_prompt_text"] = prompt          # 러너가 prompts/{sha}.txt 로 따로 저장하고 레코드에서는 뺀다
    t_llm = time.time()
    try:
        response, gen_attempts, gen_errs = lw.call_with_retry(
            lambda: model.generate_content(analysis_input),
            max_retries=cfg.max_retries if cfg is not None else 3)   # 프로덕션 generate_with_retry(retries=4) 와 같음
    except Exception:
        if rec is not None:
            rec["latency_sec"]["llm"] = round(time.time() - t_llm, 4)
        try:
            if image_file is not None:
                genai.delete_file(image_file.name)
        except Exception:
            pass
        raise

    if rec is not None:
        rec["latency_sec"]["llm"] = round(time.time() - t_llm, 4)
        rec["attempts"], rec["retries"] = gen_attempts, gen_attempts - 1
        rec["errors"].extend(gen_errs)
        rec["model_version"] = lw.model_version_of(response)
        rec["usage"] = lw.usage_from_response(response)
        rec["cost_usd"] = lw.cost_from_usage(rec["usage"])

    raw_text = response.text
    clean_json = raw_text.strip()
    if rec is not None:
        rec["raw_response_text"] = raw_text

    try:
        result_dict = json.loads(clean_json)
        if rec is not None:
            rec["parsed"] = json.loads(clean_json) if isinstance(result_dict, dict) else None
        issues = result_dict.get("issues", [])

        for issue in issues:
            if issue.get("category") == "접근성":
                issue["category"] = "기술"

        d_f = len([i for i in issues if i.get("category") == "디자인"])
        o_f = len([i for i in issues if i.get("category") == "운영"])
        t_f = len([i for i in issues if i.get("category") == "기술"])

        result_dict["design_faults"] = d_f
        result_dict["ops_faults"] = o_f
        result_dict["tech_faults"] = t_f
        result_dict["total_faults"] = d_f + o_f + t_f

        result_dict["total_count"] = result_dict.get("total_checked_count", 30)

        result_dict["scores"] = {
            "디자인": calculate_score(result_dict["total_count"], d_f),
            "운영": calculate_score(result_dict["total_count"], o_f),
            "기술": calculate_score(result_dict["total_count"], t_f)
        }
        result_dict["rag"] = rag_info      # [PATCH 2]

        end_time = time.time()
        total_duration = end_time - start_time
        print(f"분석 소요 시간: {total_duration:.2f}초")

        if rec is not None:
            rec["status"] = "ok"
            rec["result"] = json.loads(json.dumps(result_dict, ensure_ascii=False))
        return result_dict

    except Exception as e:
        print(f"JSON 파싱 에러: {e}")
        if rec is not None:
            rec["status"] = "parse_error"
            rec["parse_error"] = f"{type(e).__name__}: {e}"[:500]
            rec["parsed"] = None
        return {
            "status": "error", "message": f"JSON 파싱 에러: {e}", "issues": [],
            "scores": {"디자인": 0, "운영": 0, "기술": 0},
            "design_faults": 0, "ops_faults": 0, "tech_faults": 0, "total_faults": 0, "total_count": 0,
            "rag": rag_info
        }
    finally:
        try:
            if image_file is not None:
                genai.delete_file(image_file.name)
        except:
            pass


def merge_results(results, tree_nodes=None, page_errors=None):
    if not results:
        return {
            "status": "error", "message": "분석 결과 데이터가 없습니다.",
            "scores": {"디자인": 0, "운영": 0, "기술": 0}, "issues": [], "tree_nodes": [],
            "page_errors": page_errors or []
        }

    total_checked = sum(r.get("total_count", 30) for r in results)
    d_faults = sum(r.get("design_faults", 0) for r in results)
    o_faults = sum(r.get("ops_faults", 0) for r in results)
    t_faults = sum(r.get("tech_faults", 0) for r in results)

    d_scores = [r.get("scores", {}).get("디자인", 0) for r in results]
    o_scores = [r.get("scores", {}).get("운영", 0) for r in results]
    t_scores = [r.get("scores", {}).get("기술", 0) for r in results]

    avg_d_score = sum(d_scores) // len(results)
    avg_o_score = sum(o_scores) // len(results)
    avg_t_score = sum(t_scores) // len(results)

    # 트리 노드별 결함 수 매핑
    fault_map = {r.get("url"): r.get("total_faults", 0) for r in results}
    if tree_nodes:
        for node in tree_nodes:
            node["faults"] = fault_map.get(node["id"], 0)

    combined = {
        "status": "success",
        "total_count": total_checked,
        "design_faults": d_faults,
        "ops_faults": o_faults,
        "tech_faults": t_faults,
        "summary": "사이트 전체 분석 결과입니다. " + results[0].get("summary", ""),
        "issues": [],
        "scores": {
            "디자인": avg_d_score,
            "운영": avg_o_score,
            "기술": avg_t_score
        },
        "tree_nodes": tree_nodes or [],  # 트리 시각화 데이터 구조
        "rag_status": [{"url": r.get("url"), **(r.get("rag") or {})} for r in results],
        "page_errors": page_errors or []
    }

    for r in results:
        url_label = r.get("url", "알 수 없는 페이지")
        for issue in r.get("issues", []):
            issue["description"] = f"[{url_label}] {issue.get('description')}"
            combined["issues"].append(issue)

    return combined


async def run_analysis_flow(target_url, is_any_checked, upload_file, config=None):
    """config=None 이면 기존 동작 그대로 (1280x800, 링크 포함 최대 5페이지, 동시 분석 제한 없음)."""
    if config is not None:
        config.validate()
    viewport_w, viewport_h = config.viewport if config is not None else (1280, 800)
    max_pages = config.max_pages if config is not None else 5
    page_sem = asyncio.Semaphore(config.concurrency) if (config is not None and config.concurrency) else None
    all_page_results = []
    page_errors = []   
    tree_nodes = []  # 트리 구조 수집 리스트

    print("\n" + "="*50)
    print(f"사이트 분석 시작")
    print(f"대상 URL: {target_url}")
    print("="*50)

    async with async_playwright() as p:
        print("브라우저 실행 중")
        browser = await p.chromium.launch(headless=True)
        # 브라우저 차단 방지를 위한 User-Agent 설정
        context = await browser.new_context(
            viewport={'width': viewport_w, 'height': viewport_h},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        try:
            if max_pages == 1:
                # --max-pages 1: 시작 페이지만 분석. 링크 수집용 사전 접속을 하지 않는다.
                clean_target_url = target_url.split("#")[0].rstrip("/")
                targets = [clean_target_url]
                tree_nodes.append({"id": clean_target_url, "label": "메인 페이지", "parent": None})
                yield {"progress": 15, "text": "1개 페이지 분석 시작..."}
            else:
                print("메인 페이지 접속 및 하위 링크 수집 시작...")
                yield {"progress": 5, "text": "링크 수집 중..."}
                main_page = await context.new_page()
                await main_page.goto(target_url, wait_until="networkidle", timeout=30000)

                # 페이지 하단까지 스크롤하여 동적 로딩 메뉴/푸터 링크 활성화
                await main_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

                # 입력 URL 정규화
                clean_target_url = target_url.split("#")[0].rstrip("/")
                parsed_url = urlparse(clean_target_url)

                # 루트 도메인 추출 함수
                def get_root_domain(netloc):
                    parts = netloc.split(".")
                    return ".".join(parts[-2:]) if len(parts) >= 2 else netloc

                base_root_domain = get_root_domain(parsed_url.netloc)

                # href뿐만 아니라 onclick, data-url 등 다양한 속성에서 URL을 파싱하는 JS
                extracted_urls = await main_page.evaluate("""() => {
                    const urls = new Set();
                
                    document.querySelectorAll('a').forEach(el => {
                        // 1. 일반 href
                        if (el.href) urls.add(el.href);
                    
                        // 2. onclick 속성 내부 URL/경로 파싱
                        const onclickAttr = el.getAttribute('onclick') || '';
                        const match = onclickAttr.match(/['"](\\/[^'"]+|https?:\\/\\/[^'"]+)['"]/);
                        if (match) {
                            try {
                                const fullUrl = new URL(match[1], window.location.href).href;
                                urls.add(fullUrl);
                            } catch(e) {}
                        }

                        // 3. data-href, data-url 속성
                        const dataUrl = el.getAttribute('data-href') || el.getAttribute('data-url');
                        if (dataUrl) {
                            try {
                                urls.add(new URL(dataUrl, window.location.href).href);
                            } catch(e) {}
                        }
                    });
                
                    return Array.from(urls);
                }""")

                targets = [clean_target_url]
                # Root 노드 등록
                tree_nodes.append({
                    "id": clean_target_url,
                    "label": "메인 페이지",
                    "parent": None
                })

                print(f"메인 페이지에서 수집된 총 원본 URL 개수: {len(extracted_urls)}")

                for href in extracted_urls:
                    if not href or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:"):
                        continue

                    clean_url = href.split("#")[0].rstrip("/")
                    href_netloc = urlparse(clean_url).netloc

                    # 동일 루트 도메인 검사 및 중복 제외
                    if href_netloc and get_root_domain(href_netloc) == base_root_domain and clean_url not in targets:
                        if len(targets) >= max_pages:
                            break
                        targets.append(clean_url)
                        path_label = urlparse(clean_url).path or clean_url
                        tree_nodes.append({
                            "id": clean_url,
                            "label": path_label,
                            "parent": clean_target_url
                        })

                print(f"수집 완료. 총 {len(targets)}개 페이지 분석 예정")
                yield {"progress": 15, "text": f"{len(targets)}개 페이지 분석 시작..."}
                for t in targets: print(f"   > {t}")
                await main_page.close()

            # 페이지별 분석 로직
            async def analyze_single_page(idx, url):
                if page_sem is not None:
                    async with page_sem:
                        return await _analyze_single_page(idx, url)
                return await _analyze_single_page(idx, url)

            async def _analyze_single_page(idx, url):
                page = await context.new_page()
                if config is None:
                    shot_path = os.path.abspath(f"temp_shot_{idx}.png")
                else:
                    # 여러 run/페이지가 동시에 돌 때 파일명이 겹치지 않도록
                    shot_path = os.path.abspath(f"temp_shot_{config.run_id or 'x'}_{config.page_id or 'p'}_{idx}.png")
                page_ctx = None
                if config is not None:
                    is_target = (idx == 0)
                    pid = config.page_id if is_target else f"{config.page_id}#linked:{urlparse(url).path}"
                    page_ctx = {"url": url, "page_id": pid, "template_id": config.template_id,
                                "acquisition_sec": None, "signals": None}
                llm_started = False
                try:
                    print(f"\n [{idx+1}/{len(targets)}] 페이지 분석 시작: {url}")
                    t_acq = time.time()
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(3)

                    await page.screenshot(path=shot_path)
                    html_data = await page.content()

                    retry = 0
                    while not os.path.exists(shot_path) and retry < 10:
                        await asyncio.sleep(0.1)
                        retry += 1

                    if config is not None:
                        page_ctx["acquisition_sec"] = round(time.time() - t_acq, 4)
                        if config.query_mode == "page":
                            page_ctx["signals"] = await page.evaluate(PAGE_SIGNALS_JS)
                        if config.shots_dir:
                            import shutil
                            os.makedirs(config.shots_dir, exist_ok=True)
                            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", page_ctx["page_id"] or f"p{idx}")
                            shutil.copyfile(shot_path, os.path.join(config.shots_dir, f"{safe}.png"))

                    llm_started = True
                    if config is None:
                        res = await asyncio.to_thread(
                            analyze_with_gemini, html_data, shot_path, upload_file
                        )
                    else:
                        res = await asyncio.to_thread(
                            analyze_with_gemini, html_data, shot_path, upload_file,
                            config=config, page_ctx=page_ctx
                        )

                    print(f"해당 페이지 분석 완료. 점수: {res.get('scores')}")
                    res['url'] = url
                    return res
                except Exception as e:
                    print(f" {url} 분석 중 에러 발생: {e}")
                    if config is not None and config.logger is not None and not llm_started:
                        rec = lw.empty_record(config.logger.run_id, config.condition, url,
                                              page_ctx["page_id"], config.template_id)
                        rec.update(status="acquisition_error", prompt_date=config.prompt_date,
                                   model_name="models/gemini-2.5-flash", modality=config.modality,
                                   viewport=list(config.viewport), ts_end_utc=lw.utc_now())
                        rec["errors"].append({"attempt": None, "type": type(e).__name__, "message": str(e)[:500]})
                        config.logger.write(rec)
                    return {"status": "error", "url": url, "message": str(e), "issues": []}   # [PATCH 3]
                finally:
                    if os.path.exists(shot_path):
                        try: os.remove(shot_path)
                        except: pass
                    await page.close()

            print("\n수집된 모든 페이지의 AI 추론 시작")

            tasks = [asyncio.create_task(analyze_single_page(idx, url)) for idx, url in enumerate(targets)]

            complete_count = 0
            for future in asyncio.as_completed(tasks):
                result = await future
                if result.get("status") != "error":
                    all_page_results.append(result)
                else:   # [PATCH 3]
                    page_errors.append({"url": result.get("url"), "message": result.get("message", "")})
                complete_count += 1
                progress_count = 15 + int((complete_count / len(targets)) * 75)
                yield {"progress": min(progress_count, 90), "text": f"{complete_count}/{len(targets)} 완료..."}

            print("\n" + "="*50)
            print("모든 페이지 병렬 분석 프로세스 종료")
            print("="*50 + "\n")

            if all_page_results:
                yield {"progress": 95, "text": "페이지 분석 완료, 결과 통합 중..."}
                final_report = merge_results(all_page_results, tree_nodes, page_errors)
                await asyncio.sleep(0.5)
                yield {"progress": 100, "text": "분석 완료", "result": final_report}
            else:
                yield {"progress": -1, "text": "분석 실패: 유효한 결과가 없습니다."}

        except Exception as e:
            print(f"분석 도중 에러 발생: {e}")
            yield {"progress": -1, "text": f"오류 발생: {str(e)}"}
        finally:
            print("잔여 비동기 태스크 셧다운 시작...")
            if 'tasks' in locals():
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            await browser.close()
            print("비동기 태스크 및 브라우저 정리 완료.")