"""
E9 본 실험 분석 준비 (API 호출 없음, 기술 집계만).

1. 조항 문구 인용: 이슈 문구(primary.issue_text)를 공백 제거 후, 관련 조항 6청크 본문(공백 제거)과 15자 이상
   연속 일치하는 이슈 수 (e9_pilot_report.py 6절 (c) 와 같은 방식). 결함 페이지(유형별)와 대조군 별, run 별.
   주 대상은 관련 조항 제공 조건이고, 비교를 위해 다른 4조건에도 같은 검사를 적용한다.
2. 페이지별 질의 조건의 간이 검색 정확도: calls.jsonl 의 rag.chunks(기록된 청크 ID, 거리)만 사용.
   가져온 청크에 관련 조항 6청크가 하나라도 있는 페이지 비율을 결함 유형별로.
출력: results/revision/reports/e9_main_retrieval_check.md
"""
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import e9_rules as primary                      # noqa: E402
from experiments.revision import e9_regex_table as tbl       # noqa: E402
from experiments.revision import e9_pilot_report as pr       # noqa: E402  (RELATED, chunk_texts, norm)

RUNS = "results/revision/runs_e9"
META = "testbed_e9/dataset_metadata_e9.json"
OUT = "results/revision/reports/e9_main_retrieval_check.md"
CONDS = ["related", "norag", "fixed", "page", "fixedlong"]
CNAME = {"norag": "RAG 끔", "fixed": "고정 질의", "page": "페이지별 질의", "related": "관련 조항 제공",
         "fixedlong": "fixed-long"}
GROUPS = ["E9-1", "E9-2", "E9-3", "E9-4", "대조군"]


def src(*paths):
    return ["", "출처:"] + [f"- `{p}`" for p in paths] + [""]


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    pages = {p["page_id"]: p for p in json.load(open(META, encoding="utf-8"))["pages"]}
    grp = {pid: (m["defect_id"] if m["defect_id"] not in (None, "None") else "대조군") for pid, m in pages.items()}
    npg = Counter(grp.values())
    texts = pr.chunk_texts(pr.RELATED)
    grams = set()
    for t in texts.values():
        n = pr.norm(t)
        grams.update(n[i:i + 15] for i in range(0, max(0, len(n) - 14)))

    L = ["# E9 본 실험: 조항 문구 인용과 페이지별 질의 검색 확인", "",
         "작성: `experiments/revision/e9_main_retrieval_check.py` (API 호출 없음, 기술 집계만, 통계 검정 없음).",
         f"페이지: E9-1 {npg['E9-1']}, E9-2 {npg['E9-2']}, E9-3 {npg['E9-3']}, E9-4 {npg['E9-4']}, 대조군 {npg['대조군']}.",
         "run = e9-main-{조건}-r1, r2 (각 91페이지). 관련 조항 6청크 = e9_pilot_report.RELATED (조건 입력과 같음).", ""]

    # 1
    L += ["## 1. 조항 청크 문구와 15자 이상 일치하는 이슈", "",
          "방식: 대상 페이지 이슈 문구(description + suggestion 등, e9_rules.issue_text)와 6청크 본문을 각각",
          "공백 제거 후 비교, 15자 연속 일치가 하나라도 있으면 그 이슈를 1건으로 센다 (파일럿 보고서 6절 (c)).",
          "칸 = 일치 이슈 / 전체 이슈 (일치 이슈가 1건 이상인 페이지 수).", ""]
    L += ["| 조건 | run | E9-1 | E9-2 | E9-3 | E9-4 | 대조군 |", "|---|---|---|---|---|---|---|"]
    summary = {}
    for c in CONDS:
        for r in (1, 2):
            rid = f"e9-main-{c}-r{r}"
            cnt = defaultdict(lambda: [0, 0, 0])
            for rec in jl(f"{RUNS}/{rid}/reports.jsonl"):
                pid = rec["page_id"]
                iss = tbl.target_issues(rec.get("report") if rec["status"] == "ok" else None, pid)
                hit = 0
                for i in iss:
                    n = pr.norm(primary.issue_text(i))
                    hit += any(n[k:k + 15] in grams for k in range(0, max(0, len(n) - 14)))
                g = grp[pid]
                cnt[g][0] += hit; cnt[g][1] += len(iss); cnt[g][2] += hit > 0
            summary[(c, r)] = cnt
            L.append(f"| {CNAME[c]} | r{r} | " + " | ".join(f"{cnt[g][0]}/{cnt[g][1]} ({cnt[g][2]})" for g in GROUPS) + " |")
    L += src(f"{RUNS}/e9-main-{{조건}}-r{{1,2}}/reports.jsonl", "services/chroma_db/chroma.sqlite3 (읽기 전용, 6청크 본문)",
             "experiments/revision/e9_pilot_report.py")
    L += ["결함 페이지 합계 대 대조군 (관련 조항 제공 조건):", "",
          "| run | 결함 61페이지 일치 이슈/이슈 | 일치 페이지 | 대조군 30페이지 일치 이슈/이슈 | 일치 페이지 |",
          "|---|---|---|---|---|"]
    for r in (1, 2):
        cnt = summary[("related", r)]
        d = [sum(cnt[g][k] for g in GROUPS[:4]) for k in range(3)]
        L.append(f"| r{r} | {d[0]}/{d[1]} | {d[2]} | {cnt['대조군'][0]}/{cnt['대조군'][1]} | {cnt['대조군'][2]} |")
    L += src(f"{RUNS}/e9-main-related-r{{1,2}}/reports.jsonl")

    # 2
    L += ["## 2. 페이지별 질의: 가져온 청크에 관련 조항 6청크가 들어 있는가", "",
          "기록된 rag.chunks 의 청크 ID 와 거리만 사용했다(새 임베딩·검색 없음). 질의 문자열은 calls.jsonl 의 rag.query.",
          "칸 = 6청크 중 하나 이상이 들어 있는 페이지 / 페이지 (비율).", ""]
    L += ["| run | 가져온 청크 수 | E9-1 | E9-2 | E9-3 | E9-4 | 대조군 | 전체 |", "|---|---|---|---|---|---|---|---|"]
    per_run = {}
    for r in (1, 2):
        rid = f"e9-main-page-r{r}"
        calls = {x["page_id"]: x for x in jl(f"{RUNS}/{rid}/calls.jsonl")}
        hits, tot, kset, which, dist, rank = Counter(), Counter(), Counter(), Counter(), [], []
        qs = {}
        for pid, x in calls.items():
            ch = (x.get("rag") or {}).get("chunks") or []
            ids = [c["id"] for c in ch]
            kset[len(ids)] += 1
            g = grp[pid]
            tot[g] += 1
            rel = [(k, c) for k, c in enumerate(ch) if c["id"] in pr.RELATED]
            if rel:
                hits[g] += 1
                for k, c in rel:
                    which[c["id"][:8]] += 1; dist.append(c["distance"]); rank.append(k + 1)
            qs[pid] = ((x.get("rag") or {}).get("query"), tuple(ids))
        per_run[r] = qs
        cells = [f"{hits[g]}/{tot[g]} ({hits[g] / tot[g]:.2f})" if tot[g] else "-" for g in GROUPS]
        a, b = sum(hits.values()), sum(tot.values())
        L.append(f"| r{r} | {', '.join(f'{k}개 {v}' for k, v in sorted(kset.items()))} | " + " | ".join(cells) +
                 f" | {a}/{b} ({a / b:.2f}) |")
        per_run[(r, "detail")] = (which, dist, rank)
    L += src(f"{RUNS}/e9-main-page-r{{1,2}}/calls.jsonl", "experiments/revision/e9_pilot_report.py (RELATED)")
    for r in (1, 2):
        which, dist, rank = per_run[(r, "detail")]
        L += [f"r{r}: 들어온 관련 조항 청크(앞 8자) " + (", ".join(f"{k} {v}" for k, v in which.most_common()) or "없음") + ".",
              (f"   그 청크의 거리 최소/중앙/최대 {min(dist):.3f}/{st.median(dist):.3f}/{max(dist):.3f}, "
               f"순위 분포 {dict(sorted(Counter(rank).items()))}." if dist else "   거리·순위: 해당 없음.")]
    same = sum(per_run[1][p] == per_run[2][p] for p in per_run[1])
    L += ["", f"r1 과 r2 의 질의 문자열과 가져온 청크 ID 목록이 같은 페이지: {same}/{len(per_run[1])}.", ""]
    qc = Counter(per_run[1][p][0] for p in per_run[1])
    L += ["r1 질의 문자열 (페이지 수):", ""] + [f"- `{q}` {n}" for q, n in qc.most_common()]
    L += src(f"{RUNS}/e9-main-page-r1/calls.jsonl", f"{RUNS}/e9-main-page-r2/calls.jsonl")

    freq, info = Counter(), {}
    for x in jl(f"{RUNS}/e9-main-page-r1/calls.jsonl"):
        for c in (x.get("rag") or {}).get("chunks") or []:
            freq[c["id"]] += 1; info[c["id"]] = (c.get("source"), c.get("page"))
    L += ["### 2a. r1 에서 페이지별 질의가 가져온 청크 (자주 나온 순 상위 10, 91페이지 × 4청크 = 364)", "",
          "| 청크 (앞 8자) | 문서 | PDF 쪽 | 페이지 수 |", "|---|---|---|---|"]
    L += [f"| {cid[:8]} | {info[cid][0]} | {info[cid][1]} | {n} |" for cid, n in freq.most_common(10)]
    L += ["", f"서로 다른 청크 {len(freq)}개. 관련 조항 6청크(앞 8자): " + ", ".join(c[:8] for c in pr.RELATED) + "."]
    L += src(f"{RUNS}/e9-main-page-r1/calls.jsonl")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    long = [i + 1 for i, l in enumerate(L) if len(l) > 100]
    print(f"{OUT}: {len(L)} lines; long {long[:10]}")


if __name__ == "__main__":
    main()
