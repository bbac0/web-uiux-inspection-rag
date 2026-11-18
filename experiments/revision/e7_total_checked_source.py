"""
total_checked_count 의 출처 구분 (2026-11-13 연구자 요청, API 호출 없음).

리포트의 total_count 는 analyzer 가 `result_dict.get("total_checked_count", 30)` 으로 정한다. 그래서 리포트 값 30 은
(a) 모델이 응답 JSON 에 total_checked_count 를 쓰지 않아 기본값 30 이 쓰인 경우와 (b) 모델이 명시적으로 30 을 쓴 경우가 섞여 있다.

- 이번 run(E1-R1, R2, R3b, E2-A1-1~3)은 calls.jsonl 에 모델 원문(raw_response_text)이 있으므로 원문 JSON 을 다시 읽어 구분한다.
  원문 해석은 코드 펜스(```json)를 벗긴 뒤 json.loads, 실패하면 첫 '{' 부터 마지막 '}' 까지로 다시 시도한다.
- 레거시 run2(paper_results/run2)는 리포트만 남아 있고 모델 원문이 없어서 **구분할 수 없다** (리포트 값만 집계).

출력: results/revision/e7/total_checked_source.csv, .tex
"""
import glob
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e7_stats as e7   # noqa: E402


def parse_raw(t):
    if not t:
        return None
    s = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", t.strip())
    for cand in (s, s[s.find("{"): s.rfind("}") + 1] if "{" in s else ""):
        try:
            v = json.loads(cand)
            if isinstance(v, dict):
                return v
        except Exception:
            pass
    return None


def classify(raw):
    d = parse_raw(raw)
    if d is None:
        return "raw_unparseable"
    if "total_checked_count" not in d:
        return "absent_default_30"
    v = d["total_checked_count"]
    return "explicit_30" if v == 30 else "explicit_60" if v == 60 else "explicit_other"


def main():
    rows = []
    for cond, runs in (("RAG on", e7.E1), ("RAG off", e7.A1)):
        tot = Counter()
        for rid in runs:
            c = Counter()
            for l in open(f"{e7.RUNS}/{rid}/calls.jsonl", encoding="utf-8"):
                r = json.loads(l)
                c[classify(r.get("raw_response_text"))] += 1
            tot.update(c)
            rows.append({"group": cond, "run": rid, "pages": sum(c.values()), "absent_default_30": c["absent_default_30"],
                         "explicit_30": c["explicit_30"], "explicit_60": c["explicit_60"], "explicit_other": c["explicit_other"],
                         "raw_unparseable": c["raw_unparseable"], "distinguishable": "yes"})
        rows.append({"group": cond, "run": "pooled (3 runs)", "pages": sum(tot.values()), "absent_default_30": tot["absent_default_30"],
                     "explicit_30": tot["explicit_30"], "explicit_60": tot["explicit_60"], "explicit_other": tot["explicit_other"],
                     "raw_unparseable": tot["raw_unparseable"], "distinguishable": "yes"})
    leg = Counter()
    for f in glob.glob("paper_results/run2/report_page_*.json"):
        v = json.load(open(f, encoding="utf-8")).get("total_count")
        leg["30" if v == 30 else "60" if v == 60 else "other"] += 1
    rows.append({"group": "legacy run2", "run": "all reports", "pages": sum(leg.values()), "absent_default_30": "n/a",
                 "explicit_30": "n/a", "explicit_60": "n/a", "explicit_other": "n/a", "raw_unparseable": "n/a",
                 "distinguishable": f"no (report only, no raw model output; report total_count: 30={leg['30']}, 60={leg['60']}, other={leg['other']})"})
    e7.wcsv("total_checked_source.csv", rows)
    e7.wtex("total_checked_source.tex", rows,
            [("Group", "group"), ("Run", "run"), ("Pages", "pages"), ("Absent (default 30)", "absent_default_30"),
             ("Explicit 30", "explicit_30"), ("Explicit 60", "explicit_60"), ("Explicit other", "explicit_other"),
             ("Unparseable", "raw_unparseable"), ("Distinguishable", "distinguishable")],
            "Source of total_checked_count: field absent (analyzer default 30) vs explicitly reported by the model.",
            "tab:e7-tcc-source")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
