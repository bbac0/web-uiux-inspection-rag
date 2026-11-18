"""
고정 질의 임베딩 1회 호출 (연구자 승인 2026-11-12, pending_freeze_v5 9항) → 1,020청크 전체 순위.

  (a) gov_check.pdf 청크의 고정 질의 대비 최상위 거리와 순위
  (b) E9 fixed-long 조건의 청크 선택 (docs/e9_design.md §4.1 사전 지정 규칙 그대로)

- 임베딩: 프로덕션과 같은 GoogleGenerativeAIEmbeddings("models/gemini-embedding-001").embed_query(고정 질의) 1회.
  재시도는 llm_wrapper.call_with_retry 규칙(일시 오류만, 최대 3회)을 따르고 시도 수를 기록한다. 402/429 는 재시도하지 않는다.
- 순위: 같은 벡터로 similarity_search_by_vector_with_relevance_scores(k=전체 청크 수) — 프로덕션 검색과 같은 연산(L2 거리).
  원본 services/chroma_db 는 열지 않고 임시 복사본을 쓴다(복사 전후 해시 확인 후 삭제).
- API 키는 환경변수 GEMINI_API_KEY 에서만 읽고 출력하지 않는다.

출력 (덮어쓰지 않음, 이미 있으면 멈춤):
  results/revision/fixed_query_embedding/call_log.jsonl     호출 기록 (append)
  results/revision/fixed_query_embedding/ranking.csv         1,020청크 전체 순위
  results/revision/fixed_query_embedding/query_vector.json   임베딩 벡터 (재사용·검증용)
  results/revision/fixed_long_selection.json                 fixed-long 선택 기록
"""
import csv
import json
import os
import re
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from services import llm_wrapper as lw          # noqa: E402
from services import exp_config as ec           # noqa: E402

SRC = "services/chroma_db"
OUTDIR = "results/revision/fixed_query_embedding"
SEL = "results/revision/fixed_long_selection.json"
RELATED6 = ["906848de-bb99-4446-adb1-16a2dc61d34e", "574b8c73-13b0-43e7-bbe8-abc31f41bb2c",
            "265eeb6d-3e1a-43bc-99b7-d299c8ff4233", "1fff974d-ca33-444d-a3ac-8b93b5a8aadf",
            "87f08a4d-b8b6-427c-8fd5-2925b07b4d8a", "905711bf-2989-473d-9cf8-47a3ed1dd8f9"]
KEYWORDS = ["공식 배너", "공식 전자정부 누리집", "배너", "헤더", "푸터", "로그인", "회원가입", "작은 화면", "768px"]
T_TARGET, T_LO, T_HI = 4538, 4084, 4992


def fmt(source, page0, content):
    """analyzer._format_context 와 같은 한 청크 형식."""
    return f"[{os.path.basename(source or '정부가이드라인.pdf')} - {(page0 or 0) + 1}페이지]\n{content}"


def kw_hits(text):
    low, nows = text.lower(), re.sub(r"\s+", "", text).lower()
    return [k for k in KEYWORDS if k.lower() in low or re.sub(r"\s+", "", k).lower() in nows]


def kw_hits_raw(text):
    low = text.lower()
    return [k for k in KEYWORDS if k.lower() in low]


def select(ranked, hits_fn):
    """ranked: 순위 순 [(id, source, page0, content, distance, rank)]. 사전 지정 규칙으로 K 를 고른다."""
    excluded, kept = [], []
    for r in ranked:
        cid = r["id"]
        if cid in RELATED6:
            excluded.append({"id": cid, "rank": r["rank"], "reason": "a_related_clause"})
            continue
        h = hits_fn(r["content"])
        if h:
            excluded.append({"id": cid, "rank": r["rank"], "reason": "b_keyword", "keywords": h})
            continue
        kept.append(r)
    lengths, chosen_k = [], None
    for k in range(1, len(kept) + 1):
        L = len("\n\n".join(fmt(x["source"], x["page0"], x["content"]) for x in kept[:k]))
        lengths.append(L)
        if T_LO <= L <= T_HI:
            chosen_k = k
            break
        if L > T_HI:
            break
    rule = "first K within 4,084-4,992"
    if chosen_k is None:
        chosen_k = min(range(1, len(lengths) + 1), key=lambda k: abs(lengths[k - 1] - T_TARGET))
        rule = "no K within range -> argmin |length - 4,538|"
    return excluded, kept, lengths, chosen_k, rule


def main():
    for p in (OUTDIR, SEL):
        if os.path.exists(p):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {p}")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY 없음")
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]   # analyzer.py 와 같은 처리 (값은 출력하지 않음)

    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_chroma import Chroma

    before = {f: lw.sha256_file(os.path.join(SRC, f)) for f in sorted(os.listdir(SRC)) if os.path.isfile(os.path.join(SRC, f))}
    tmp = tempfile.mkdtemp(prefix="chroma_fixedq_")
    dst = os.path.join(tmp, "chroma_db")
    shutil.copytree(SRC, dst)
    os.makedirs(OUTDIR)
    log = {"ts_start_utc": lw.utc_now(), "purpose": "fixed-query ranking (gov_check top rank; E9 fixed-long selection)",
           "model": "models/gemini-embedding-001", "query": ec.RAG_QUERY, "chroma_source": SRC,
           "chroma_source_sha256": before}
    try:
        emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        store = Chroma(persist_directory=dst, embedding_function=emb)
        n = store._collection.count()
        t0 = time.time()
        try:
            vec, attempts, errs = lw.call_with_retry(lambda: emb.embed_query(ec.RAG_QUERY), max_retries=3)
            log.update(status="ok", attempts=attempts, errors=errs)
        except Exception as e:
            log.update(status="error", error=f"{type(e).__name__}: {str(e)[:300]}")
            raise
        finally:
            log.update(ts_end_utc=lw.utc_now(), latency_sec=round(time.time() - t0, 4))
            with open(os.path.join(OUTDIR, "call_log.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        scored = store.similarity_search_by_vector_with_relevance_scores(vec, k=n)
        try:
            store._client.close()
        except Exception:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    after = {f: lw.sha256_file(os.path.join(SRC, f)) for f in sorted(os.listdir(SRC)) if os.path.isfile(os.path.join(SRC, f))}
    assert after == before, "services/chroma_db changed"

    ranked = [{"rank": i + 1, "id": d.id, "source": os.path.basename(d.metadata.get("source", "")),
               "page0": d.metadata.get("page", 0), "content": d.page_content, "distance": float(s)}
              for i, (d, s) in enumerate(scored)]
    json.dump({"model": log["model"], "query": ec.RAG_QUERY, "dim": len(vec), "vector": vec},
              open(os.path.join(OUTDIR, "query_vector.json"), "w", encoding="utf-8"))
    with open(os.path.join(OUTDIR, "ranking.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "chunk_id", "source", "page", "distance", "chars", "prompt_form_chars"])
        for r in ranked:
            w.writerow([r["rank"], r["id"], r["source"], r["page0"] + 1, f"{r['distance']:.6f}", len(r["content"]),
                        len(fmt(r["source"], r["page0"], r["content"]))])

    # (a) gov_check 최상위
    gc = [r for r in ranked if r["source"] == "gov_check.pdf"]
    gov_check = {"n_chunks": len(gc), "top": {"rank": gc[0]["rank"], "chunk_id": gc[0]["id"], "page": gc[0]["page0"] + 1,
                                               "distance": gc[0]["distance"]},
                 "top5": [{"rank": r["rank"], "chunk_id": r["id"], "page": r["page0"] + 1, "distance": r["distance"]} for r in gc[:5]],
                 "fixed_top4": [{"rank": r["rank"], "chunk_id": r["id"], "source": r["source"], "page": r["page0"] + 1,
                                 "distance": r["distance"]} for r in ranked[:4]]}

    # (b) fixed-long (사전 지정: 원문 + 공백 제거 검사)
    excl, kept, lengths, k, rule = select(ranked, kw_hits)
    chosen = kept[:k]
    ctx = "\n\n".join(fmt(x["source"], x["page0"], x["content"]) for x in chosen)
    per_kw = {kw: sum(1 for e in excl if kw in e.get("keywords", [])) for kw in KEYWORDS}
    # 참고: 원문 부분 문자열 검사만 했을 때 (사전 지정 아님, 보고용)
    excl_r, kept_r, lengths_r, k_r, rule_r = select(ranked, kw_hits_raw)
    sel = {
        "created_utc": lw.utc_now(), "rule_source": "docs/e9_design.md §4.1 (사전 지정, 결과를 본 뒤 바꾸지 않음)",
        "condition_name": "E9 결함 주제 키워드를 제외한 컨텍스트, 길이 맞춤 (fixed-long)",
        "embedding_call": log, "query": ec.RAG_QUERY, "n_ranked": len(ranked),
        "target_chars": T_TARGET, "range_chars": [T_LO, T_HI], "keywords": KEYWORDS,
        "keyword_check": "case-insensitive substring on raw text OR on whitespace-removed text",
        "excluded_n": len(excl), "excluded_by_reason": {"a_related_clause": sum(e["reason"] == "a_related_clause" for e in excl),
                                                         "b_keyword": sum(e["reason"] == "b_keyword" for e in excl)},
        "excluded_per_keyword": per_kw, "excluded": excl,
        "K": k, "k_rule_applied": rule, "cumulative_lengths": lengths, "final_context_chars": len(ctx),
        "selected": [{"filtered_rank": i + 1, "original_rank": x["rank"], "chunk_id": x["id"], "source": x["source"],
                      "page": x["page0"] + 1, "distance": x["distance"], "chars": len(x["content"]),
                      "prompt_form_chars": len(fmt(x["source"], x["page0"], x["content"]))} for i, x in enumerate(chosen)],
        "fixed_top4_excluded": [r["id"] for r in ranked[:4] if r["id"] in {e["id"] for e in excl}],
        "reference_raw_substring_only (not pre-registered)": {
            "excluded_n": len(excl_r), "K": k_r, "final_context_chars": len("\n\n".join(fmt(x["source"], x["page0"], x["content"]) for x in kept_r[:k_r])),
            "selected_ids": [x["id"] for x in kept_r[:k_r]],
            "same_selection_as_preregistered": [x["id"] for x in kept_r[:k_r]] == [x["id"] for x in chosen]},
        "gov_check": gov_check,
    }
    json.dump(sel, open(SEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    show = {k2: sel[k2] for k2 in ("excluded_n", "excluded_by_reason", "excluded_per_keyword", "K", "k_rule_applied",
                                    "cumulative_lengths", "final_context_chars", "selected", "fixed_top4_excluded")}
    show["raw_only_ref"] = sel["reference_raw_substring_only (not pre-registered)"]
    show["gov_check"] = gov_check
    show["call"] = {k2: log[k2] for k2 in ("status", "attempts", "latency_sec", "ts_start_utc")}
    print(json.dumps(show, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
