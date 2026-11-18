"""
gov_guide 전체(1,181쪽)를 포함한 새 인덱스와 실험 인덱스 비교 (연구자 승인 2026-11-19, 임베딩 비용 상한 $1).

- 실험 DB(services/chroma_db)는 열지 않고 sqlite 를 읽기 전용(mode=ro)으로만 읽는다(청크 본문·ID 대조용).
- 새 인덱스: results/revision/full_index/chroma_db (.gitignore 의 chroma_db/ 로 커밋 제외).
  services/indexer.py 와 같은 로더(PyPDFLoader)·분할(1000/100)·순서(gov_check → gov_guide)·임베딩
  (GoogleGenerativeAIEmbeddings models/gemini-embedding-001, task_type=retrieval_document)·배치 10.
  다른 점: 배치가 실패하면 건너뛰지 않고 llm_wrapper.call_with_retry 로 재시도하고, 끝내 실패하면 멈춘다.
- 질의: 프로덕션과 같은 GoogleGenerativeAIEmbeddings(model) 의 embed_query → similarity_search_by_vector_with_relevance_scores.
  고정 질의 1개 + E3-page 의 서로 다른 질의 + E9 page r1·r2 의 서로 다른 질의.
- 비용: 글자 수를 토큰 수로 크게 잡아 $0.15/1M 로 추정(상한). 호출 전 누적 추정이 $1 를 넘으면 멈춘다.
- API 키는 환경변수 GEMINI_API_KEY 에서만 읽고 출력하지 않는다.

  python experiments/revision/full_index_compare.py build     # 새 인덱스 + call_log
  python experiments/revision/full_index_compare.py compare   # 질의 임베딩 + 비교 결과 JSON
출력(덮어쓰지 않음): results/revision/full_index/{chroma_db/, call_log.jsonl, build_meta.json, compare.json}
"""
import difflib
import json
import os
import re
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from services import llm_wrapper as lw          # noqa: E402

OUT = "results/revision/full_index"
DB = f"{OUT}/chroma_db"
OLD = "services/chroma_db/chroma.sqlite3"
PDFS = ["data/gov_check.pdf", "data/gov_guide.pdf"]
MODEL = "models/gemini-embedding-001"
PRICE_PER_M, CAP = 0.15, 1.0
FIXED = "웹 UI/UX 표준 가이드라인 공통 규정"
RELATED6 = ["906848de-bb99-4446-adb1-16a2dc61d34e", "574b8c73-13b0-43e7-bbe8-abc31f41bb2c",
            "265eeb6d-3e1a-43bc-99b7-d299c8ff4233", "1fff974d-ca33-444d-a3ac-8b93b5a8aadf",
            "87f08a4d-b8b6-427c-8fd5-2925b07b4d8a", "905711bf-2989-473d-9cf8-47a3ed1dd8f9"]
N = lambda t: re.sub(r"\s+", "", t or "")       # noqa: E731


def log_call(rec):
    with open(f"{OUT}/call_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def spent():
    if not os.path.exists(f"{OUT}/call_log.jsonl"):
        return 0.0
    return sum(json.loads(l)["cost_estimate_usd_upper"] for l in open(f"{OUT}/call_log.jsonl", encoding="utf-8"))


def key_env():
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY 없음")
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def splits():
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    sp = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    out = []
    for p in PDFS:
        out += [s for s in sp.split_documents(PyPDFLoader(p).load()) if s.page_content.strip()]
    return out


def cmd_build():
    if os.path.exists(OUT):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUT}")
    key_env()
    docs = splits()
    est_total = sum(len(d.page_content) for d in docs) * PRICE_PER_M / 1e6
    if est_total > CAP:
        raise SystemExit(f"추정 비용 상한 {est_total:.4f} > {CAP}")
    os.makedirs(OUT)
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_chroma import Chroma
    emb = GoogleGenerativeAIEmbeddings(model=MODEL, task_type="retrieval_document")
    store = Chroma(embedding_function=emb, persist_directory=DB)
    t_start = lw.utc_now()
    for i in range(0, len(docs), 10):
        batch = docs[i:i + 10]
        chars = sum(len(d.page_content) for d in batch)
        cost = chars * PRICE_PER_M / 1e6
        if spent() + cost > CAP:
            raise SystemExit("비용 상한 도달 → 멈춤")
        rec = {"ts_start_utc": lw.utc_now(), "kind": "index_batch", "batch": i // 10, "n_texts": len(batch),
               "chars": chars, "model": MODEL, "task_type": "retrieval_document", "cost_estimate_usd_upper": cost}
        try:
            _, attempts, errs = lw.call_with_retry(lambda: store.add_documents(batch), max_retries=3)
            rec.update(status="ok", attempts=attempts, errors=errs)
        except Exception as e:
            rec.update(status="error", error=f"{type(e).__name__}: {str(e)[:300]}")
            log_call(rec)
            raise SystemExit(f"배치 {i // 10} 실패 → 멈춤")
        rec["ts_end_utc"] = lw.utc_now()
        log_call(rec)
        time.sleep(2)
    meta = {"started_utc": t_start, "finished_utc": lw.utc_now(), "n_chunks": store._collection.count(),
            "expected_chunks": len(docs), "pdfs": PDFS, "splitter": "RecursiveCharacterTextSplitter(1000, 100)",
            "model": MODEL, "batch_size": 10}
    json.dump(meta, open(f"{OUT}/build_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))


def old_chunks():
    con = sqlite3.connect(f"file:{OLD}?mode=ro", uri=True)
    q = ("select e.embedding_id, d.string_value, s.string_value, p.int_value from embeddings e "
         "join embedding_metadata d on d.id=e.id and d.key='chroma:document' "
         "join embedding_metadata s on s.id=e.id and s.key='source' "
         "join embedding_metadata p on p.id=e.id and p.key='page'")
    return {i: {"text": t, "source": os.path.basename(s.replace("\\", "/")), "page": p} for i, t, s, p in con.execute(q)}


def recorded_queries():
    """(실험, page_id) → (질의, 기록된 상위 4 청크 ID)."""
    out = {}
    for exp, path in (("E3", "results/revision/runs/E3-page/calls.jsonl"),
                      ("E9-r1", "results/revision/runs_e9/e9-main-page-r1/calls.jsonl"),
                      ("E9-r2", "results/revision/runs_e9/e9-main-page-r2/calls.jsonl")):
        for l in open(path, encoding="utf-8"):
            c = json.loads(l)
            out[(exp, c["page_id"])] = (c["rag"]["query"], [x["id"] for x in c["rag"]["chunks"]])
    return out


def cmd_compare():
    if not os.path.exists(f"{OUT}/build_meta.json"):
        raise SystemExit("build 먼저")
    if os.path.exists(f"{OUT}/compare.json"):
        raise SystemExit("이미 있음(덮어쓰지 않음): compare.json")
    key_env()
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_chroma import Chroma
    emb = GoogleGenerativeAIEmbeddings(model=MODEL)              # analyzer.get_vector_store 와 같은 생성
    store = Chroma(persist_directory=DB, embedding_function=emb)
    got = store._collection.get(include=["documents", "metadatas"])
    new = {i: {"text": d, "source": os.path.basename((m.get("source") or "").replace("\\", "/")), "page": m.get("page")}
           for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])}
    newkey = {}
    for i, c in new.items():
        newkey.setdefault((c["source"], N(c["text"])), i)
    old = old_chunks()
    o2n, how = {}, {}
    for oid, c in old.items():
        k = (c["source"], N(c["text"]))
        if k in newkey:
            o2n[oid], how[oid] = newkey[k], "text"
        else:
            cand = [(difflib.SequenceMatcher(None, N(c["text"]), N(n["text"])).ratio(), nid) for nid, n in new.items()
                    if n["source"] == c["source"] and n["page"] == c["page"]]
            r, nid = max(cand) if cand else (0, None)
            o2n[oid], how[oid] = nid, f"same page, ratio {r:.3f}"
    rec = recorded_queries()
    qs = sorted({FIXED} | {q for q, _ in rec.values()})
    est = sum(len(q) for q in qs) * PRICE_PER_M / 1e6
    if spent() + est > CAP:
        raise SystemExit("비용 상한 도달 → 멈춤")
    n_all = store._collection.count()
    res = {}
    for q in qs:
        r = {"ts_start_utc": lw.utc_now(), "kind": "query", "query": q, "chars": len(q), "model": MODEL,
             "cost_estimate_usd_upper": len(q) * PRICE_PER_M / 1e6}
        try:
            vec, attempts, errs = lw.call_with_retry(lambda: emb.embed_query(q), max_retries=3)
            r.update(status="ok", attempts=attempts, errors=errs)
        except Exception as e:
            r.update(status="error", error=f"{type(e).__name__}: {str(e)[:300]}")
            log_call(r)
            raise SystemExit("질의 임베딩 실패 → 멈춤")
        log_call(r)
        ranked = store.similarity_search_by_vector_with_relevance_scores(vec, k=n_all)
        res[q] = [d.id for d, _ in ranked]
    # 1) 고정 질의
    fixed_old = [x["id"] for x in json.loads(open("results/revision/runs/E1-R1/calls.jsonl", encoding="utf-8")
                                             .readline())["rag"]["chunks"]]
    def desc(nid):
        c = new[nid]
        return {"id": nid, "source": c["source"], "page": c["page"] + 1}
    fixed = {"old_top4": [{"id": o, "source": old[o]["source"], "page": old[o]["page"] + 1, "new_id": o2n[o],
                           "match": how[o]} for o in fixed_old],
             "new_top4": [desc(n) for n in res[FIXED][:4]]}
    fixed["same_set"] = set(o2n[o] for o in fixed_old) == set(res[FIXED][:4])
    fixed["same_order"] = [o2n[o] for o in fixed_old] == res[FIXED][:4]
    # 2) 페이지별 질의
    pages = {}
    for (exp, pid), (q, top_old) in sorted(rec.items()):
        new4 = res[q][:4]
        old4 = [o2n.get(o) for o in top_old]
        added = [n for n in new4 if n not in old4]
        pages[f"{exp}|{pid}"] = {"query": q, "same_set": set(old4) == set(new4), "same_order": old4 == new4,
                                 "new_in_top4": [desc(n) for n in added],
                                 "new_from_unindexed_pages": sum(1 for n in added if new[n]["source"] == "gov_guide.pdf"
                                                                 and n not in set(o2n.values()))}
    # 3) E9 지정 조항 6청크 recall@4
    rel_new = [o2n[o] for o in RELATED6]
    recall = {}
    for q in sorted({q for (e, _), (q, _) in rec.items() if e.startswith("E9")} | {FIXED}):
        ranks = [res[q].index(n) + 1 for n in rel_new]
        recall[q] = {"recall_at_4": sum(r <= 4 for r in ranks) / 6, "ranks": ranks, "best": min(ranks)}
    out = {"n_new_chunks": n_all, "n_old_chunks": len(old),
           "old_to_new_match": {"text": sum(1 for h in how.values() if h == "text"),
                                "same_page_fallback": {o: h for o, h in how.items() if h != "text"}},
           "related6_match": {o: how[o] for o in RELATED6}, "fixed": fixed, "pages": pages, "recall": recall,
           "spent_usd_upper": spent(), "n_calls": sum(1 for _ in open(f"{OUT}/call_log.jsonl", encoding="utf-8"))}
    json.dump(out, open(f"{OUT}/compare.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"fixed_same_set": fixed["same_set"], "fixed_same_order": fixed["same_order"],
                      "spent": out["spent_usd_upper"], "calls": out["n_calls"]}))


if __name__ == "__main__":
    {"build": cmd_build, "compare": cmd_compare}.get(sys.argv[1] if len(sys.argv) > 1 else "",
                                                     lambda: sys.exit(__doc__))()
