"""
E7 보충 표 (2026-11-13 연구자 요청, API 호출 없음).

1. total_checked_count 분포: RAG 켬(E1-R1, R2, R3b), RAG 끔(E2-A1-1~3), 레거시 run2 별 값(30, 60, 기타)과 페이지 수.
   레거시 run2 는 리포트 안 분석 수(rag_status 항목 수: 대상 페이지 + /login)별로 나눠, 60 이 두 분석의 합(30+30)인지 확인한다.
   근거 코드: services/analyzer.py 의 사이트 집계 `total_checked = sum(r.get("total_count", 30) for r in results)`.
2. 이슈 카테고리 비중(exploratory): RAG 켬/끔 3회 합산과 run 별 디자인·운영·기술 비중.

출력: results/revision/e7/total_checked_count_by_condition.csv, exploratory_category_shares_on_off.csv (+ .tex)
"""
import glob
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e7_stats as e7   # noqa: E402


def bucket(v):
    return "30" if v == 30 else "60" if v == 60 else "other"


def main():
    rows = []
    for cond, runs in (("RAG on (E1-R1, R2, R3b)", e7.E1), ("RAG off (E2-A1-1, A1-2, A1-3)", e7.A1)):
        tot = Counter()
        for rid in runs:
            c = Counter(bucket((json.loads(l).get("report") or {}).get("total_count"))
                        for l in open(f"{e7.RUNS}/{rid}/reports.jsonl", encoding="utf-8"))
            tot.update(c)
            rows.append({"group": cond, "run": rid, "analyses_per_report": 1, "pages": sum(c.values()),
                         "30": c["30"], "60": c["60"], "other": c["other"]})
        rows.append({"group": cond, "run": "pooled (3 runs)", "analyses_per_report": 1, "pages": sum(tot.values()),
                     "30": tot["30"], "60": tot["60"], "other": tot["other"]})
    by = {}
    for f in glob.glob("paper_results/run2/report_page_*.json"):
        r = json.load(open(f, encoding="utf-8"))
        n = len(r.get("rag_status") or [])
        by.setdefault(n, Counter())[bucket(r.get("total_count"))] += 1
    allc = Counter()
    for n in sorted(by):
        allc.update(by[n])
        rows.append({"group": "legacy run2", "run": f"reports with {n} analysis(es)", "analyses_per_report": n,
                     "pages": sum(by[n].values()), "30": by[n]["30"], "60": by[n]["60"], "other": by[n]["other"]})
    rows.append({"group": "legacy run2", "run": "all reports", "analyses_per_report": "1 or 2", "pages": sum(allc.values()),
                 "30": allc["30"], "60": allc["60"], "other": allc["other"]})
    e7.wcsv("total_checked_count_by_condition.csv", rows)
    e7.wtex("total_checked_count_by_condition.tex", rows,
            [("Group", "group"), ("Run", "run"), ("Analyses per report", "analyses_per_report"), ("Pages", "pages"),
             ("30", "30"), ("60", "60"), ("Other", "other")],
            "Distribution of total_checked_count (report total_count) by condition.", "tab:e7-tcc-cond",
            "Legacy run2 reports aggregate two analyses (target page + /login) with total_count = sum over analyses "
            "(services/analyzer.py); 60 occurs only in two-analysis reports.")

    cat = []
    for cond, runs in (("on", e7.E1), ("off", e7.A1)):
        tot = Counter()
        for rid in runs:
            c = Counter()
            for l in open(f"{e7.RUNS}/{rid}/reports.jsonl", encoding="utf-8"):
                for i in (json.loads(l).get("report") or {}).get("issues") or []:
                    if isinstance(i, dict):
                        c[i.get("category") if i.get("category") in e7.CATS else "other"] += 1
            tot.update(c)
            n = sum(c.values())
            cat.append({"analysis": "exploratory", "rag": cond, "run": rid, "issues": n,
                        **{f"{k}_share": e7.fmt(c[k] / n) for k in e7.CATS + ["other"]}})
        n = sum(tot.values())
        cat.append({"analysis": "exploratory", "rag": cond, "run": "pooled (3 runs)", "issues": n,
                    **{f"{k}_share": e7.fmt(tot[k] / n) for k in e7.CATS + ["other"]}})
    e7.wcsv("exploratory_category_shares_on_off.csv", cat)
    e7.wtex("exploratory_category_shares_on_off.tex", cat,
            [("RAG", "rag"), ("Run", "run"), ("Issues", "issues"), ("Design", "디자인_share"), ("Operation", "운영_share"),
             ("Technical", "기술_share"), ("Other", "other_share")],
            "EXPLORATORY (not pre-registered): issue category shares, RAG on vs off.", "tab:e7-exp-cat-onoff")
    for r in rows:
        print(r)
    for r in cat:
        print(r)


if __name__ == "__main__":
    main()
