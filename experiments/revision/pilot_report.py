"""
파일럿 run 점검 보고서 (API 호출 없음). run 폴더는 읽기만 한다.
검색 청크 본문은 원본 services/chroma_db 의 sqlite 를 읽기 전용(immutable)으로 열어 가져온다 (Chroma 클라이언트로 열지 않음).

  python experiments/revision/pilot_report.py pilot-02
출력: results/revision/pilot/{run_id}_report.md
"""

import csv
import importlib.util
import json
import os
import re
import sqlite3
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from services import llm_wrapper as lw  # noqa: E402

SECTION_START = "[1. 정부 표준 가이드라인 (기본 지침)]\n    "
SECTION_END = "\n\n    [2. 사용자 지정 추가 가이드라인 (우선 적용)]"


def chunk_texts(ids):
    db = os.path.abspath("services/chroma_db/chroma.sqlite3").replace("\\", "/")
    con = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    out = {}
    for cid in ids:
        rows = con.execute("select m.key, m.string_value, m.int_value from embeddings e join embedding_metadata m "
                           "on e.id = m.id where e.embedding_id = ?", (cid,)).fetchall()
        d = {k: (s if s is not None else i) for k, s, i in rows}
        out[cid] = {"source": os.path.basename(d.get("source", "") or "").split("\\")[-1],
                    "page": (d.get("page") or 0) + 1, "text": d.get("chroma:document", "")}
    con.close()
    return out


def load_kw():
    spec = importlib.util.spec_from_file_location("kw", "experiments/evaluate_performance_v5.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main(run_id):
    d = os.path.join("results", "revision", "runs", run_id)
    recs = [json.loads(l) for l in open(os.path.join(d, "calls.jsonl"), encoding="utf-8")]
    meta = json.load(open(os.path.join(d, "run_meta.json"), encoding="utf-8"))
    summ = json.load(open(os.path.join(d, "summary.json"), encoding="utf-8"))
    kw = load_kw()
    gt = {}
    for r in csv.DictReader(open("results/revision/ground_truth.csv", encoding="utf-8")):
        gt.setdefault(r["page_id"], {})[r["defect_type"]] = (int(r["nominal_injected"]), int(r["effective_1280"]))
    L = [f"# 파일럿 점검: {run_id}", ""]

    # 기본 상태
    L += ["## 1. 실행 상태", "",
          f"- 상태: {summ['status_counts']}, 파싱 실패 {len(summ['parse_error_pages'])}, 재시도 합계 {summ['retries_total']}",
          f"- model_version: {summ['model_versions']}, 프롬프트 날짜 {meta['args']['prompt_date']}, git {meta['env']['git_describe']}",
          f"- 실제 실행 시각(UTC): {summ['started_utc']} → {summ['finished_utc']}",
          f"- 로그 스키마 문제 레코드: {sum(bool(lw.validate_record(r)) for r in recs)}/{len(recs)}",
          f"- SHA256SUMS 대조 불일치: {lw.verify_run(d) or '없음'}", ""]
    try:
        open(os.path.join(d, "calls.jsonl"), "a")
        L.append("- 잠금: **쓰기 가능 (문제)**")
    except PermissionError:
        L.append("- 잠금: 쓰기 거부됨 (정상)")
    ch = meta.get("chroma") or {}
    L += [f"- chroma 원본 복사 시점 해시(파일 {len(ch.get('source_sha256', {}))}개 결합): `{ch.get('source_combined_sha256')}`; "
          f"복사본 정리: {(summ.get('chroma') or {}).get('cleanup')}", ""]

    # 토큰/비용/지연
    u = lambda k: [r["usage"][k] for r in recs if r["usage"].get(k) is not None]
    mean = lambda xs: sum(xs) / len(xs) if xs else None
    L += ["## 2. 토큰, 비용, 지연시간 (호출 평균)", "",
          "| 항목 | 평균 | 최소 | 최대 |", "|---|---:|---:|---:|"]
    for k in ("prompt_token_count", "candidates_token_count", "thoughts_token_count_derived",
              "thoughts_check_without_cached_subtraction", "cached_content_token_count", "total_token_count"):
        xs = u(k)
        L.append(f"| {k} | {mean(xs):.1f} | {min(xs)} | {max(xs)} |")
    costs = [r["cost_usd"]["total"] for r in recs]
    L += [f"| 비용 (USD) | {mean(costs):.5f} | {min(costs):.5f} | {max(costs):.5f} |"]
    for k in lw.LATENCY_FIELDS:
        xs = [r["latency_sec"][k] for r in recs if r["latency_sec"].get(k) is not None]
        L.append(f"| 지연 {k} (초) | {mean(xs):.3f} | {min(xs):.3f} | {max(xs):.3f} |")
    neg = [r["page_id"] for r in recs if r["usage"]["thoughts_token_count_derived"] < 0]
    mism = [r["page_id"] for r in recs if r["usage"]["thoughts_token_count_derived"] != r["usage"]["thoughts_check_without_cached_subtraction"]]
    ratio = [r["usage"]["thoughts_token_count_derived"] / max(1, r["usage"]["candidates_token_count"]) for r in recs]
    L += ["", f"- derived 사고 토큰 음수: {neg or '없음'}; cached>0: {summ['cached_tokens_positive'] or '없음'}; "
          f"계산식 두 가지 불일치: {mism or '없음'}",
          f"- 사고/출력 토큰 비: {min(ratio):.2f} ~ {max(ratio):.2f} (평균 {mean(ratio):.2f})",
          f"- run 총비용 ${summ['cost_usd_total']:.4f} (입력 비캐시 ${summ['cost_usd_breakdown']['input_uncached']:.4f}, "
          f"cached ${summ['cost_usd_breakdown']['input_cached']:.4f}, 출력+사고 ${summ['cost_usd_breakdown']['output']:.4f})", ""]

    # RAG
    idsets = Counter(tuple(c["id"] for c in r["rag"]["chunks"]) for r in recs)
    nch = Counter(r["rag"]["n_chunks"] for r in recs)
    all_ids = sorted({c["id"] for r in recs for c in r["rag"]["chunks"]})
    texts = chunk_texts(all_ids)
    L += ["## 3. RAG 검색", "",
          f"- n_chunks 분포: {dict(nch)}; 질의: `{recs[0]['rag']['query']}`",
          f"- 페이지별 청크 ID 순서 조합 종류: {len(idsets)} (1 이면 모든 페이지가 같은 4개를 같은 순서로 받음)", "",
          "| 순위 | 청크 ID | 파일 | 쪽 | L2 거리 (페이지 간 범위) | 첫 100자 |", "|---:|---|---|---:|---|---|"]
    first = recs[0]["rag"]["chunks"]
    for i, c in enumerate(first, 1):
        ds = [x["distance"] for r in recs for x in r["rag"]["chunks"] if x["id"] == c["id"]]
        t = texts[c["id"]]
        L.append(f"| {i} | `{c['id']}` | {c['source']} | {c['page']} | {min(ds):.4f}~{max(ds):.4f} | "
                 f"{t['text'][:100].replace(chr(10), ' ').replace('|', '/')} |")
    # 프롬프트 길이
    ctx_lens, prompt_lens = [], []
    for r in recs:
        pt = open(os.path.join(d, "prompts", r["prompt_sha256"] + ".txt"), encoding="utf-8").read()
        a = pt.index(SECTION_START) + len(SECTION_START)
        b = pt.index(SECTION_END)
        ctx_lens.append(b - a)
        prompt_lens.append(len(pt))
    L += ["", "### 프롬프트 길이 (RAG 켬 vs run2 와 같은 빈 컨텍스트)", "",
          f"- 검색 컨텍스트 길이: {min(ctx_lens)}~{max(ctx_lens)}자 (모든 페이지 같은 내용)",
          f"- 프롬프트 텍스트 길이: RAG 켬 평균 {mean(prompt_lens):.0f}자 → 컨텍스트를 비우면 평균 {mean(prompt_lens) - mean(ctx_lens):.0f}자",
          f"- 프롬프트 텍스트 중 컨텍스트 비율(문자 기준): {mean([c / p for c, p in zip(ctx_lens, prompt_lens)]):.1%}",
          f"- 입력 토큰 평균 {mean(u('prompt_token_count')):.0f} (스크린샷 이미지 토큰 포함). 토크나이저를 따로 부르지 않았으므로 청크 4개의 정확한 토큰 수는 "
          "E2-A1(--no-rag)과 E1-R1 의 같은 페이지 입력 토큰 차이로 확정한다.", ""]

    # 근거 필드 일치
    chunk_pairs = {(c["source"], c["page"]) for c in first}
    chunk_files = {c["source"] for c in first}
    issues = [(r["page_id"], i) for r in recs for i in (r["parsed"] or {}).get("issues", []) if isinstance(i, dict)]
    n = len(issues)
    def pages_of(i):
        pn = i.get("page_number")
        return pn if isinstance(pn, list) else ([pn] if isinstance(pn, int) else [])
    f_ok = sum(i.get("source_file") in chunk_files for _, i in issues)
    fp_ok = sum(any((i.get("source_file"), p) in chunk_pairs for p in pages_of(i)) for _, i in issues)
    all_ok = sum(bool(pages_of(i)) and all((i.get("source_file"), p) in chunk_pairs for p in pages_of(i)) for _, i in issues)
    ex = sum(i.get("source_file") == "gov_guide.pdf" and pages_of(i) in ([12], [12, 13]) for _, i in issues)
    sf = Counter(str(i.get("source_file")) for _, i in issues)
    pn = Counter(json.dumps(i.get("page_number")) for _, i in issues)
    pct = lambda x: f"{x}/{n} ({x / n:.1%})" if n else "-"
    L += ["## 4. 모델이 보고한 근거와 검색 청크의 일치", "",
          f"- 이슈 {n}건. 검색 청크 (파일, 쪽): {sorted(chunk_pairs)}",
          f"- source_file 이 검색 청크 파일 중 하나: {pct(f_ok)}",
          f"- (파일, 쪽) 쌍이 검색 청크와 하나 이상 일치: {pct(fp_ok)}; 모든 쪽이 일치: {pct(all_ok)}",
          f"- 프롬프트 예시값(gov_guide.pdf, [12] 또는 [12, 13]) 그대로: {pct(ex)}",
          f"- source_file 분포: {dict(sf.most_common())}",
          f"- page_number 분포: {dict(pn.most_common())}", ""]

    # 페이지별 키워드 결과와 주목 페이지
    L += ["## 5. 페이지별 결과 (키워드 채점, 참고용)", "",
          "| page_id | nominal 결함 | effective 결함 | 이슈 수 | 키워드 매칭 유형 |", "|---|---|---|---:|---|"]
    for r in recs:
        p = r["page_id"]
        nom = [t for t, v in gt[p].items() if v[0]]
        eff = [t for t, v in gt[p].items() if v[1]]
        iss = (r["parsed"] or {}).get("issues", [])
        m = sorted({t for i in iss for t in kw.match_categories_in_issue(i.get("description") or "")})
        short = lambda xs: ", ".join(x.split()[0] + ("(" + x.split()[1] + ")" if len(x.split()) > 1 else "") for x in xs) or "-"
        L.append(f"| {p} | {short(nom)} | {short(eff)} | {len(iss)} | {short(m)} |")
    for p, label in (("page_135", "효과 없는 버튼 잘림 (dashboard, 버튼 없음)"), ("page_028", "미주입 용어 위반 (form_page) + 중복 ID")):
        r = next(x for x in recs if x["page_id"] == p)
        iss = (r["parsed"] or {}).get("issues", [])
        L += ["", f"### {p}: {label}", "", f"요약: {(r['parsed'] or {}).get('summary', '')}", "",
              "| # | category | 키워드 매칭 | description (앞 220자) | source_file / page |", "|---:|---|---|---|---|"]
        for k, i in enumerate(iss, 1):
            m = ", ".join(sorted(kw.match_categories_in_issue(i.get("description") or ""))) or "-"
            L.append(f"| {k} | {i.get('category')} | {m} | {(i.get('description') or '')[:220].replace('|', '/')} | "
                     f"{i.get('source_file')} / {i.get('page_number')} |")
    out = os.path.join("results", "revision", "pilot")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{run_id}_report.md")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])
