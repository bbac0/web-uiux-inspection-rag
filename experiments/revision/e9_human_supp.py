"""
E9 사람 평가 보조 분석: 페이지 단위 검출 하한 (부록 4, 210e56b). API 호출 없음, 검정·신뢰구간 없음.
정규식은 scoring/e9_rules.py 그대로 쓰고 고치지 않는다. 주 결과를 대체하지 않는 보조 분석이다.

  python experiments/revision/e9_human_supp.py --a <평가자 A 52건 CSV 작업 복사본> --out results/revision/reports/e9_human_report_supp.md
"""
import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import e9_human_sample as hs      # noqa: E402
from experiments.revision import e9_human_compare as ec     # noqa: E402
from scoring import e9_rules as primary                     # noqa: E402

KEY = f"{ROOT}/results/revision/human_eval/e9_eval/key/e9_key_hit52.csv"
RUNS = [("e9-main-norag-r1", "RAG 끔"), ("e9-main-related-r1", "관련 조항")]
PG = {"E9-1": "E9-1", "E9-2": "E9-2", "E9-3": "E9-3", "control": "대조군"}
COL = ec.TYPE_COL


def sampled_pages(meta):
    """부록 1 페이지 표본(seed 20261201)을 e9_human_sample.build 와 같은 방식으로 다시 만든다."""
    by = defaultdict(list)
    for pid in sorted(meta):
        if hs.stratum(meta[pid]) in hs.STRATA:
            by[hs.stratum(meta[pid])].append(pid)
    rp = random.Random(hs.SEED_PAGE)
    return {s: sorted(rp.sample(by[s], min(hs.N_PAGE, len(by[s])))) for s in hs.STRATA}, by


def regex_page(run, pid, p):
    iss, _ = hs.issues_of(run, pid)
    d = primary.page_detections(iss, p["injected_string"] if p["defect_id"] == "E9-1" else None)
    s = hs.stratum(p)
    return int(any(d[t] for t in COL)) if s == "control" else d[s]


def analyse(A, K, meta):
    chosen, by = sampled_pages(meta)
    hits = defaultdict(list)
    for i, k in K.items():
        hits[(k["run_id"], k["page_id"])].append(i)
    out = []
    for run, rname in RUNS:
        for s in hs.STRATA:
            pages = chosen[s]
            for (r, pid) in hits:
                if r == run and hs.stratum(meta[pid]) == s and pid not in pages:
                    raise SystemExit(f"{pid}: 표본 밖 페이지의 걸린 이슈")
            row = {"run": run, "name": rname, "stratum": s, "pages": len(pages),
                   "hit_issues": sum(len(hits[(run, p)]) for p in pages),
                   "regex": sum(regex_page(run, p, meta[p]) for p in pages),
                   "regex_all": sum(regex_page(run, p, meta[p]) for p in by[s]), "all_pages": len(by[s])}
            yes_any = lambda i: any(A[i][c] == "예" for c in ec.JUDGE)     # noqa: E731
            if s == "control":
                row["ga"] = None
                row["na"] = sum(any(yes_any(i) for i in hits[(run, p)]) for p in pages)
                iss = [i for p in pages for i in hits[(run, p)]]
                row["ctrl_no"] = sum(not yes_any(i) for i in iss)
                row["ctrl_yes"] = sum(yes_any(i) for i in iss)
            else:
                row["ga"] = sum(any(A[i][COL[s]] == "예" for i in hits[(run, p)]) for p in pages)
                row["na"] = sum(any(yes_any(i) for i in hits[(run, p)]) for p in pages)
            regex_hit_pages = sum(1 for p in pages if hits[(run, p)])
            if regex_hit_pages != row["regex"]:
                raise SystemExit(f"{run} {s}: 걸린 이슈가 있는 페이지 {regex_hit_pages} ≠ 정규식 검출 {row['regex']}")
            out.append(row)
    return out


def report(rows, a_path):
    L = ["# E9 사람 평가 보조 분석: 페이지 단위 검출 하한 (평가자 A)", "",
         "**보조 분석이다. 주 결과(정규식 기준 검출)를 대체하지 않는다.** 규칙: 부록 4 (210e56b).",
         "작성: `experiments/revision/e9_human_supp.py` (API 호출 없음). 정규식·지표·동결 규칙은 바꾸지 않았다.",
         "이 분석은 A 의 판정을 본 뒤 추가한 사후 보조 분석이다. 신뢰구간과 검정은 만들지 않았다.",
         "사람 평가 결과를 본 뒤 채점 모델, 프롬프트, 키워드 사전, 정규식을 바꾸지 않는다(사전 등록 10절 5항).", "",
         "입력: A 판정 작업 복사본(원본 SHA-256 은 `e9_human_report.md` 1절)",
         f"`{a_path}`,",
         "key `results/revision/human_eval/e9_eval/key/e9_key_hit52.csv`, run `results/revision/runs_e9/`.", "",
         "## 1. 층별 표 (표본 페이지)", "",
         "검출 쪽수는 표본 페이지 중 검출된 페이지 수. 하한 (가) = 유형 일치, (나) = 유형 무시(부록 4 2절).",
         "대조군의 '정규식' 칸은 E9-1~E9-3 중 하나라도 걸린 페이지 수이며 (가)는 없다.", "",
         "| 조건 | 페이지 층 | 표본 쪽 | 걸린 이슈 | 정규식 | 하한 (가) | 하한 (나) |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        ga = "-" if r["ga"] is None else str(r["ga"])
        L.append(f"| {r['name']} | {PG[r['stratum']]} | {r['pages']} | {r['hit_issues']} | {r['regex']} | {ga} | {r['na']} |")
    L += ["", "출처: 위 입력과 `scoring/e9_rules.py` 재계산", "",
          "## 2. 참고: 전체 페이지의 정규식 검출 (같은 규칙, 표본 아님)", "",
          "| 조건 | 페이지 층 | 정규식 검출 / 전체 쪽 |", "|---|---|---|"]
    for r in rows:
        L.append(f"| {r['name']} | {PG[r['stratum']]} | {r['regex_all']}/{r['all_pages']} |")
    L += ["", "출처: `results/revision/runs_e9/{run}/reports.jsonl` 재계산",
          "(`reports/e9_main_report.md` 2절 run 1 과 같은 규칙. 대조군은 세 유형 중 하나라도 걸린 쪽수)",
          "", "## 3. 대조군: 정규식에 걸린 이슈의 A 판정", "",
          "| 조건 | 걸린 이슈 | A 결함 아님(세 열 모두 아니오) | A '예' 하나 이상 |", "|---|---|---|---|"]
    for r in rows:
        if r["stratum"] == "control":
            L.append(f"| {r['name']} | {r['hit_issues']} | {r['ctrl_no']} | {r['ctrl_yes']} |")
    L += ["", "출처: 1절과 같음", ""]
    return L


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if os.path.exists(a.out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {a.out}")
    A, K = ec.read_sheet(a.a), ec.read_key(KEY)
    if set(A) != set(K):
        raise SystemExit("A 시트와 key 의 걸린 이슈가 다르다")
    rows = analyse(A, K, hs.pages_meta())
    return rows, report(rows, os.path.relpath(a.a, ROOT).replace(os.sep, "/"))


def tail(rows):
    diff = [f"{r['name']} {PG[r['stratum']]} ({r['regex']}쪽 → (가) {r['ga']}쪽, (나) {r['na']}쪽)"
            for r in rows if r["stratum"] != "control" and (r["ga"] != r["regex"] or r["na"] != r["regex"])]
    bad = {r["name"] for r in rows if r["stratum"] != "control" and (r["ga"] != r["regex"] or r["na"] != r["regex"])}
    same = [n for _, n in RUNS if n not in bad]
    ga_na = [r for r in rows if r["ga"] is not None and r["ga"] != r["na"]]
    return ["## 4. 요약", "",
            "정규식 기준과 보조 하한의 차이는 " + (", ".join(diff) if diff else "없다") + "에서만 있고,",
            (f"{', '.join(same)} 조건은 모든 결함 층에서 같다." if same else ""), "",
            "- 차이가 난 두 층은 정규식 검출이 각 1쪽뿐이라 건수로만 읽어야 한다.",
            "- 정규식은 배너 문구로 잡았지만 A 는 규격값으로 본 5쌍은 페이지 단위 결과를 바꾸지 않았다",
            f"  ((가)와 (나)가 다른 층 {len(ga_na)}개). 4쌍은 E9-2 페이지라 그 이슈의 spec-values '예'가 페이지 유형과",
            "  같아 (가)로도 검출되고, 1쌍은 E9-1 페이지인데 같은 페이지의 다른 걸린 이슈가 banner-text '예'다.",
            "- 대조군에서 정규식에 걸린 이슈는 두 조건 모두 A 가 전부 결함 아님으로 보았다(3절).", "",
            "## 5. 한계", "",
            "- 하한이다. 정규식이 놓친 이슈를 사람이 검증하지 않아(부록 3) 실제 검출은 이보다 클 수 있다.",
            "- A 의 판정을 본 뒤 추가한 사후 보조 분석이다. 주 결과는 정규식 기준 값이다.",
            "- 평가자 A 1인, 재평가 없음. 층마다 15쪽이고 신뢰구간과 검정은 내지 않았다.", ""]


if __name__ == "__main__":
    rows, L = main()
    out = sys.argv[sys.argv.index("--out") + 1]
    open(out, "w", encoding="utf-8", newline=chr(10)).write(chr(10).join(L + tail(rows)))
    print(out)
