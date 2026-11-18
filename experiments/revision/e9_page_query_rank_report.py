"""
E9 페이지별 질의 검색 순위 보고서 (API 호출 없음). 입력: results/revision/e9/page_query_embedding/ (e9_page_query_rank.py),
고정 질의 순위 results/revision/fixed_query_embedding/ranking.csv (v5, 동결).
출력: results/revision/reports/e9_page_query_retrieval_rank.md
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import fixed_long_selection as fls   # noqa: E402

D = "results/revision/e9/page_query_embedding"
FAILED = "results/revision/e9/page_query_embedding_attempt1_failed"
FIXED = "results/revision/fixed_query_embedding/ranking.csv"
META = "testbed_e9/dataset_metadata_e9.json"
OUT = "results/revision/reports/e9_page_query_retrieval_rank.md"
KS = (4, 10, 20, 50)
GROUPS = ["E9-1", "E9-2", "E9-3", "E9-4", "대조군"]
FIXED_QUERY = "웹 UI/UX 표준 가이드라인 공통 규정"


def src(*p):
    return ["", "출처:"] + [f"- `{x}`" for x in p] + [""]


def main():
    pages = {p["page_id"]: p for p in json.load(open(META, encoding="utf-8"))["pages"]}
    grp = {pid: (m["defect_id"] if m["defect_id"] not in (None, "None") else "대조군") for pid, m in pages.items()}
    tmpl = {pid: m["body_template"] for pid, m in pages.items()}
    qmeta = json.load(open(f"{D}/queries.json", encoding="utf-8"))
    ranks = defaultdict(dict)
    n_chunks = None
    for r in csv.DictReader(open(f"{D}/ranks.csv", encoding="utf-8")):
        if r["related_clause"] == "1":
            ranks[r["query"]][r["chunk_id"]] = int(r["rank"])
    for r in csv.DictReader(open(FIXED, encoding="utf-8")):
        if r["chunk_id"] in fls.RELATED6:
            ranks[FIXED_QUERY][r["chunk_id"]] = int(r["rank"])
    n_chunks = qmeta[0]["n_chunks"]
    rel = fls.RELATED6
    recall = lambda q, k: sum(ranks[q][c] <= k for c in rel) / len(rel)

    logs = [json.loads(l) for l in open(f"{D}/call_log.jsonl", encoding="utf-8")]
    flogs = [json.loads(l) for l in open(f"{FAILED}/call_log.jsonl", encoding="utf-8")] if os.path.exists(FAILED) else []
    cost = sum(x["cost_estimate_usd_upper"] for x in logs + flogs)

    L = ["# E9 페이지별 질의: 관련 조항 6청크의 전체 순위와 Recall@k", "",
         "작성: `experiments/revision/e9_page_query_rank.py` (임베딩), `e9_page_query_rank_report.py` (이 보고서).",
         f"질의 = e9-main-page-r1, r2 의 rag.query 중 서로 다른 것 {len(qmeta)}개 (질의 생성 규칙은 그대로).",
         f"질의마다 gemini-embedding-001 embed_query 1회, 전체 {n_chunks}청크 L2 순위(프로덕션 검색과 같은 연산).",
         f"검증: 각 질의 순위의 1~4위가 run 에 기록된 가져온 청크와 같음 "
         f"{sum(m['top4_matches_recorded'] for m in qmeta)}/{len(qmeta)}.",
         f"호출: 성공 {len(logs)}회 + 첫 시도 {len(flogs)}회(스크립트 비교 코드 오류로 첫 질의 뒤 멈춤,",
         f"폴더 `{FAILED}` 에 보존).",
         f"비용 추정 상한(글자 수 = 토큰, $0.15/1M) ${cost:.6f} (상한 $0.05).",
         "Recall@k = 6청크 중 k위 안에 든 비율. 통계 검정 없음.", ""]

    L += ["## 1. 질의별 순위와 Recall@k (고정 질의와 나란히)", "",
          "| 질의 | 페이지 | 템플릿 | 6청크 최고 순위 | R@4 | R@10 | R@20 | R@50 |", "|---|---|---|---|---|---|---|---|"]
    qorder = [m["query"] for m in sorted(qmeta, key=lambda m: min(ranks[m["query"]].values()))]
    for q in qorder:
        m = next(x for x in qmeta if x["query"] == q)
        t = ", ".join(sorted({tmpl[p] for p in m["pages"]}))
        L.append(f"| {q} | {len(m['pages'])} | {t} | {min(ranks[q].values())} | "
                 + " | ".join(f"{recall(q, k):.2f}" for k in KS) + " |")
    L.append(f"| (고정 질의) {FIXED_QUERY} | 91 | 전체 | {min(ranks[FIXED_QUERY].values())} | "
             + " | ".join(f"{recall(FIXED_QUERY, k):.2f}" for k in KS) + " |")
    L += src(f"{D}/ranks.csv", f"{D}/queries.json", FIXED, META)

    L += ["## 2. 관련 조항 6청크 각각의 순위", "",
          "| 질의 | " + " | ".join(c[:8] for c in rel) + " |", "|---|" + "---|" * len(rel)]
    for q in qorder + [FIXED_QUERY]:
        name = q if q != FIXED_QUERY else f"(고정) {q}"
        L.append(f"| {name} | " + " | ".join(str(ranks[q][c]) for c in rel) + " |")
    L += ["", "열 = 청크 ID 앞 8자 (e9_related_clause_chunks.csv 의 6청크)."]
    L += src(f"{D}/ranks.csv", FIXED)

    L += ["## 3. 질의와 페이지 유형의 대응", "",
          "| 질의 | E9-1 | E9-2 | E9-3 | E9-4 | 대조군 |", "|---|---|---|---|---|---|"]
    for q in qorder:
        m = next(x for x in qmeta if x["query"] == q)
        c = Counter(grp[p] for p in m["pages"])
        L.append(f"| {q} | " + " | ".join(str(c[g]) for g in GROUPS) + " |")
    L += ["", "질의는 본문 템플릿(body_template)에서 정해지며 결함 유형과는 무관하다. 템플릿마다 E9-1~4 와 대조군이 섞여 있다."]
    L += src(f"{D}/queries.json", META)

    L += ["## 4. 결함 유형별 평균 Recall@k (페이지 단위 평균) 과 '6청크 중 하나라도 k위 안' 페이지 비율", "",
          "| 유형 | 페이지 | R@4 | R@10 | R@20 | R@50 | 하나라도 @4 | @10 | @20 | @50 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    pq = {p: m["query"] for m in qmeta for p in m["pages"]}
    for g in GROUPS:
        ps = [p for p in pages if grp[p] == g]
        mr = [sum(recall(pq[p], k) for p in ps) / len(ps) for k in KS]
        hit = [sum(min(ranks[pq[p]].values()) <= k for p in ps) / len(ps) for k in KS]
        L.append(f"| {g} | {len(ps)} | " + " | ".join(f"{x:.3f}" for x in mr) + " | "
                 + " | ".join(f"{x:.2f}" for x in hit) + " |")
    L.append("| (고정 질의, 모든 페이지) | 91 | " + " | ".join(f"{recall(FIXED_QUERY, k):.3f}" for k in KS) + " | "
             + " | ".join(f"{float(min(ranks[FIXED_QUERY].values()) <= k):.2f}" for k in KS) + " |")
    L += src(f"{D}/ranks.csv", f"{D}/queries.json", FIXED, META)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print(OUT, "long:", [i + 1 for i, l in enumerate(L) if len(l) > 100])


if __name__ == "__main__":
    main()
