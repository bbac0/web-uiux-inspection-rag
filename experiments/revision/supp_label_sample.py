"""
사람 평가 보충 시트 표본 (results/revision/analysis_plan_addendum_supp_label.md 규칙, API 호출 없음).

  python experiments/revision/supp_label_sample.py counts
    → results/revision/human_eval/supp_label/sample_counts.md
      results/revision/human_eval/supp_label/key/sample_selection.csv  (층·run 정보 포함, 평가자에게 주지 않음)

시트·뷰어는 이 스크립트가 만들지 않는다(연구자 승인 후 별도 단계).
"""
import csv
import json
import os
import random
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import make_eval_sheets as mes    # noqa: E402

RUNS = ["E3-oracle", "E3-page", "E2-A1-1", "E2-A1-2", "E2-A1-3", "E4-mobile"]
MERGED = os.path.join(ROOT, "results", "revision", "issue_tables_merged")
RUNS_BASE = os.path.join(ROOT, "results", "revision", "runs")
OUT = os.path.join(ROOT, "results", "revision", "human_eval", "supp_label")
TERM = "Standard Terminology Violation"
SEED_S2, SEED_S3, SEED_SHUFFLE = 20261120, 20261121, 20261122
N_S2, N_S3 = 40, 30


def load_text(run):
    out = {}
    for line in open(os.path.join(RUNS_BASE, run, "reports.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        for idx, issue in enumerate((r.get("report") or {}).get("issues", []) or []):
            if isinstance(issue, dict):
                out[(r["page_id"], idx)] = (mes.clean_text(issue.get("description")), (issue.get("suggestion") or "").strip())
    return out


def stratum(row):
    lab = row["semantic_pass1_merged"]
    if not lab:
        return None
    if lab == TERM:
        return "S1"
    if row["string_match_term"] == "1":
        return "S2"
    return "S3"


def population():
    rows = []
    for ri, run in enumerate(RUNS):
        text = load_text(run)
        for r in csv.DictReader(open(os.path.join(MERGED, f"{run}.csv"), encoding="utf-8-sig")):
            d, s = text[(r["page_id"], int(r["issue_index"]))]
            rows.append(dict(r, _order=(ri, r["page_id"], int(r["issue_index"])), _desc=d, _sug=s, _stratum=stratum(r)))
    rows.sort(key=lambda r: r["_order"])
    groups = defaultdict(list)
    for r in rows:
        groups[(r["_desc"], r["_sug"])].append(r)
    reps = []
    for g in groups.values():
        rep = dict(g[0])
        rep["_dup_n"] = len(g)
        rep["_dup_mixed"] = int(len({(x["semantic_pass1_merged"], x["string_match_term"]) for x in g}) > 1)
        reps.append(rep)
    reps.sort(key=lambda r: r["_order"])
    return rows, reps


def sample(reps):
    by = {s: [r for r in reps if r["_stratum"] == s] for s in ("S1", "S2", "S3")}
    sel = list(by["S1"])
    sel += random.Random(SEED_S2).sample(by["S2"], min(N_S2, len(by["S2"])))
    sel += random.Random(SEED_S3).sample(by["S3"], min(N_S3, len(by["S3"])))
    random.Random(SEED_SHUFFLE).shuffle(sel)
    return by, sel


def counts():
    rows, reps = population()
    by, sel = sample(reps)
    os.makedirs(os.path.join(OUT, "key"), exist_ok=True)
    keyp = os.path.join(OUT, "key", "sample_selection.csv")
    mdp = os.path.join(OUT, "sample_counts.md")
    for p in (keyp, mdp):
        if os.path.exists(p):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {p}")
    cols = ["order", "stratum", "issue_id", "run_id", "page_id", "issue_index", "semantic_pass1_merged",
            "string_match_term", "keyword_types", "dup_n", "dup_mixed"]
    with open(keyp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for i, r in enumerate(sel, 1):
            w.writerow([i, r["_stratum"], r["issue_id"], r["run_id"], r["page_id"], r["issue_index"],
                        r["semantic_pass1_merged"], r["string_match_term"], r["keyword_types"], r["_dup_n"], r["_dup_mixed"]])
    pop_raw = Counter(r["_stratum"] for r in rows)
    pop_rep = Counter(r["_stratum"] for r in reps)
    got = Counter(r["_stratum"] for r in sel)
    L = ["# 보충 시트 표본 건수", "",
         "작성: `experiments/revision/supp_label_sample.py counts` (API 호출 없음).",
         "규칙: `results/revision/analysis_plan_addendum_supp_label.md` (커밋 d594519).",
         f"모집단 이슈 {len(rows)}건, 중복 제거 후 {len(reps)}건 ({len(rows) - len(reps)}건 제거).", "",
         "## 1. 층별 건수", "",
         "| 층 | 모집단(중복 제거 전) | 모집단(중복 제거 후) | 목표 | 표본 |", "|---|---|---|---|---|"]
    for s, tgt in (("S1", "전부"), ("S2", f"최대 {N_S2}"), ("S3", str(N_S3))):
        L.append(f"| {s} | {pop_raw[s]} | {pop_rep[s]} | {tgt} | {got[s]} |")
    L.append(f"| 제외(라벨 없음) | {pop_raw[None]} | {pop_rep[None]} | - | 0 |")
    L.append(f"| 합계 | {len(rows)} | {len(reps)} | | {len(sel)} |")
    L += ["", "출처: `results/revision/issue_tables_merged/{run}.csv`, `results/revision/runs/{run}/reports.jsonl`", "",
          "## 2. 표본의 run 별 건수 (대표 이슈 기준)", "",
          "| run | S1 | S2 | S3 | 합계 |", "|---|---|---|---|---|"]
    for run in RUNS:
        c = Counter(r["_stratum"] for r in sel if r["run_id"] == run)
        L.append(f"| {run} | {c['S1']} | {c['S2']} | {c['S3']} | {sum(c.values())} |")
    L += ["", "출처: `results/revision/human_eval/supp_label/key/sample_selection.csv`", "",
          "## 3. 중복 묶음", "",
          f"- 두 건 이상 묶인 대표 이슈: 모집단 {sum(r['_dup_n'] > 1 for r in reps)}건, 표본 {sum(r['_dup_n'] > 1 for r in sel)}건.",
          f"- 묶음 안에서 의미 라벨이나 string_match 가 다른 대표 이슈: 모집단 {sum(r['_dup_mixed'] for r in reps)}건, "
          f"표본 {sum(r['_dup_mixed'] for r in sel)}건 (층은 대표 이슈 기준).",
          f"- 표본 중 E4-mobile 대표 이슈(스크린샷 390x844): {sum(r['run_id'] == 'E4-mobile' for r in sel)}건.", ""]
    open(mdp, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(mdp)


if __name__ == "__main__":
    if sys.argv[1:] != ["counts"]:
        raise SystemExit("사용법: supp_label_sample.py counts")
    counts()
