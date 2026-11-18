"""
E9 페이지별 질의 검색 정확도 (2026-11-13 연구자 지시 B5).

- e9-main-page-r1, r2 의 calls.jsonl 에서 서로 다른 질의 문자열(rag.query)을 모은다(질의 생성 규칙은 건드리지 않음).
- 질의마다 프로덕션과 같은 GoogleGenerativeAIEmbeddings("models/gemini-embedding-001").embed_query 1회
  (fixed_long_selection.py 와 같은 방식, 재시도 규칙 llm_wrapper.call_with_retry). 모든 호출을 call_log.jsonl 에 남긴다.
  비용 상한 $0.05: 입력 토큰을 글자 수로 크게 잡아(글자 수 = 토큰 수) $0.15/1M 로 추정해 상한을 넘으면 호출 전에 멈춘다.
- 순위: similarity_search_by_vector_with_relevance_scores(k=전체 1,020청크), 원본 services/chroma_db 는 임시 복사본으로만 연다.
- 검증: 각 질의 순위의 1~4위가 run 에 기록된 rag.chunks(ID 순서)와 같은지 확인한다.
- API 키는 환경변수 GEMINI_API_KEY 에서만 읽고 출력하지 않는다.

출력 (덮어쓰지 않음): results/revision/e9/page_query_embedding/{call_log.jsonl, queries.json, ranks.csv}
보고서는 e9_page_query_rank_report.py 가 만든다(API 없음).
"""
import csv
import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from services import llm_wrapper as lw                     # noqa: E402
from experiments.revision import fixed_long_selection as fls   # noqa: E402  (RELATED6)

SRC = "services/chroma_db"
RUNS = "results/revision/runs_e9"
OUTDIR = "results/revision/e9/page_query_embedding"
PRICE_PER_M = 0.15
CAP_USD = 0.05


def queries():
    q = {}
    for r in (1, 2):
        for l in open(f"{RUNS}/e9-main-page-r{r}/calls.jsonl", encoding="utf-8"):
            x = json.loads(l)
            rag = x.get("rag") or {}
            q.setdefault(rag["query"], {"pages": set(), "recorded": {}})
            q[rag["query"]]["pages"].add(x["page_id"])
            q[rag["query"]]["recorded"].setdefault(f"r{r}", set()).add(tuple(c["id"] for c in rag["chunks"]))
    return q


def main():
    if os.path.exists(OUTDIR):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUTDIR}")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY 없음")
    Q = queries()
    est = sum(len(q) for q in Q) * PRICE_PER_M / 1e6
    if est > CAP_USD:
        raise SystemExit(f"추정 비용 {est:.6f} > 상한 {CAP_USD}")
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_chroma import Chroma

    before = {f: lw.sha256_file(os.path.join(SRC, f)) for f in sorted(os.listdir(SRC)) if os.path.isfile(os.path.join(SRC, f))}
    tmp = tempfile.mkdtemp(prefix="chroma_pageq_")
    dst = os.path.join(tmp, "chroma_db")
    shutil.copytree(SRC, dst)
    os.makedirs(OUTDIR)
    rows, meta = [], []
    try:
        emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        store = Chroma(persist_directory=dst, embedding_function=emb)
        n = store._collection.count()
        for qi, (q, info) in enumerate(sorted(Q.items())):
            log = {"ts_start_utc": lw.utc_now(), "purpose": "E9 page-query retrieval rank (B5)",
                   "model": "models/gemini-embedding-001", "query": q, "query_chars": len(q),
                   "cost_estimate_usd_upper": len(q) * PRICE_PER_M / 1e6, "chroma_source_sha256": before}
            t0 = time.time()
            try:
                vec, attempts, errs = lw.call_with_retry(lambda: emb.embed_query(q), max_retries=3)
                log.update(status="ok", attempts=attempts, errors=errs)
            except Exception as e:
                log.update(status="error", error=f"{type(e).__name__}: {str(e)[:300]}")
                raise
            finally:
                log.update(ts_end_utc=lw.utc_now(), latency_sec=round(time.time() - t0, 4))
                with open(os.path.join(OUTDIR, "call_log.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(log, ensure_ascii=False) + "\n")
            scored = store.similarity_search_by_vector_with_relevance_scores(vec, k=n)
            top4 = tuple(d.id for d, _ in scored[:4])
            rec = {r: sorted(v) for r, v in info["recorded"].items()}
            match = all(len(v) == 1 and next(iter(v)) == top4 for v in info["recorded"].values())
            meta.append({"query": q, "pages": sorted(info["pages"]), "n_chunks": n, "top4": list(top4),
                         "recorded_top4_by_run": {k: [list(t) for t in v] for k, v in rec.items()},
                         "top4_matches_recorded": match})
            for i, (d, s) in enumerate(scored):
                rows.append([q, i + 1, d.id, os.path.basename(d.metadata.get("source", "")), d.metadata.get("page", 0),
                             round(float(s), 6), int(d.id in fls.RELATED6)])
        try:
            store._client.close()
        except Exception:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    after = {f: lw.sha256_file(os.path.join(SRC, f)) for f in sorted(os.listdir(SRC)) if os.path.isfile(os.path.join(SRC, f))}
    assert after == before, "services/chroma_db changed"
    json.dump(meta, open(os.path.join(OUTDIR, "queries.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(OUTDIR, "ranks.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query", "rank", "chunk_id", "source", "page0", "distance", "related_clause"])
        w.writerows(rows)
    print(f"{len(meta)} queries embedded; top4 match recorded: {sum(m['top4_matches_recorded'] for m in meta)}/{len(meta)}")


if __name__ == "__main__":
    main()
