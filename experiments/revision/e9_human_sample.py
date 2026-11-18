"""
E9 사람 평가 표본 (규칙: results/revision/analysis_plan_addendum_e9_human.md, ca021ba). API 호출 없음.

  python experiments/revision/e9_human_sample.py counts   # e9_eval/sample_counts.md, e9_eval/key/sample_selection.csv

시트는 연구자 승인 후 따로 만든다.
"""
import csv
import json
import os
import random
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import e9_regex_table as tbl    # noqa: E402
from scoring import e9_rules as primary                    # noqa: E402
from scoring import e9_rules_aux as aux                    # noqa: E402

REL = "results/revision"
OUT = f"{ROOT}/{REL}/human_eval/e9_eval"
RUNS = ["e9-main-related-r1", "e9-main-norag-r1"]
STRATA = ["E9-1", "E9-2", "E9-3", "control"]
SEED_PAGE, SEED_ISSUE, N_PAGE, N_MISS, LIMIT = 20261201, 20261202, 15, 2, 150
N_MISS_2, SEED_ISSUE_2 = 1, 20261203      # 부록 2 (c737a9c)


def pages_meta():
    return {p["page_id"]: p for p in json.load(open(f"{ROOT}/testbed_e9/dataset_metadata_e9.json", encoding="utf-8"))["pages"]}


def stratum(p):
    return "control" if p["subtype"] == "control" else p["defect_id"]


def issues_of(run, pid):
    for l in open(f"{ROOT}/{REL}/runs_e9/{run}/reports.jsonl", encoding="utf-8"):
        r = json.loads(l)
        if r["page_id"] == pid:
            return tbl.target_issues(r.get("report") if r["status"] == "ok" else None, pid), r["status"]
    return [], "missing"


def classify(issue, p):
    inj = p["injected_string"] if p["defect_id"] == "E9-1" else None
    m = primary.match_issue(issue, inj)
    s = stratum(p)
    hit = any(m[t] for t in ("E9-1", "E9-2", "E9-3")) if s == "control" else m[s]
    return hit, m, aux.match_issue(issue)


def build(n_miss=N_MISS, seed_issue=SEED_ISSUE):
    meta = pages_meta()
    by = defaultdict(list)
    for pid in sorted(meta):
        if stratum(meta[pid]) in STRATA:
            by[stratum(meta[pid])].append(pid)
    rp = random.Random(SEED_PAGE)
    chosen = {s: sorted(rp.sample(by[s], min(N_PAGE, len(by[s])))) for s in STRATA}
    ri = random.Random(seed_issue)
    pop, sel, status = Counter(), [], Counter()
    for run in RUNS:
        for s in STRATA:
            for pid in by[s]:
                iss, st = issues_of(run, pid)
                p = meta[pid]
                cls = [classify(i, p) for i in iss]
                for (hit, _, _) in cls:
                    pop[(run, s, "걸림" if hit else "안 걸림", "모집단")] += 1
                if pid not in chosen[s]:
                    continue
                status[(run, st)] += 1
                hits = [k for k, c in enumerate(cls) if c[0]]
                miss = [k for k, c in enumerate(cls) if not c[0]]
                take = hits + sorted(ri.sample(miss, min(n_miss, len(miss))))
                for k in sorted(take):
                    hit, m, a = cls[k]
                    pop[(run, s, "걸림" if hit else "안 걸림", "표본")] += 1
                    sel.append({"run_id": run, "page_id": pid, "page_stratum": s, "subtype": p["subtype"],
                                "issue_index": k, "regex_stratum": "hit" if hit else "miss",
                                **{f"primary_{t}": int(m[t]) for t in ("E9-1", "E9-2", "E9-3", "E9-4")},
                                **{f"aux_{t}": int(a[t]) for t in ("E9-1", "E9-2", "E9-3", "E9-4")},
                                "description": iss[k].get("description", ""), "suggestion": iss[k].get("suggestion", "")})
    return chosen, by, pop, sel, status


def cmd_counts(v2=False):
    os.makedirs(f"{OUT}/key", exist_ok=True)
    out_md = f"{OUT}/sample_counts_2.md" if v2 else f"{OUT}/sample_counts.md"
    out_csv = f"{OUT}/key/sample_selection.csv"
    for p in ((out_md,) if v2 else (out_md, out_csv)):   # v2: 연구자 지시로 sample_selection.csv 를 갱신한다(이전 판은 09d6e91)
        if os.path.exists(p):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {p}")
    chosen, by, pop, sel, status = build(*((N_MISS_2, SEED_ISSUE_2) if v2 else ()))
    text = Counter((primary.issue_text({"description": r["description"], "suggestion": r["suggestion"]})) for r in sel)
    for r in sel:
        r["dup_n_in_sample"] = text[primary.issue_text({"description": r["description"], "suggestion": r["suggestion"]})]
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sel[0]))
        w.writeheader()
        w.writerows(sel)
    L = ["# E9 사람 평가 표본 건수" + (" (부록 2: 안 걸린 이슈 (페이지, 조건)당 최대 1건)" if v2 else " (시트 생성 전)"), "",
         f"작성: `experiments/revision/e9_human_sample.py {'counts2' if v2 else 'counts'}` (API 호출 없음). 2026-11-18.",
         "규칙: `results/revision/analysis_plan_addendum_e9_human.md` (ca021ba)"
         + (", `analysis_plan_addendum_e9_human_2.md` (c737a9c). 시드 페이지 20261201, 이슈 20261203." if v2 else
            ". 시드 페이지 20261201, 이슈 20261202."), "",
         "## 1. 페이지 표본", "", "| 페이지 층 | 전체 페이지 | 표본 페이지 |", "|---|---|---|"]
    L += [f"| {s} | {len(by[s])} | {len(chosen[s])} |" for s in STRATA]
    L += ["", "출처: `testbed_e9/dataset_metadata_e9.json`. 두 조건에 같은 페이지 표본을 쓴다.", "",
          "## 2. 이슈 건수 (모집단 = 그 층의 모든 페이지, 표본 = 표본 페이지에서 뽑은 이슈)", "",
          "| 조건 run | 페이지 층 | 정규식 | 모집단 이슈 | 표본 이슈 |", "|---|---|---|---|---|"]
    tot = Counter()
    for run in RUNS:
        for s in STRATA:
            for h in ("걸림", "안 걸림"):
                a, b = pop[(run, s, h, "모집단")], pop[(run, s, h, "표본")]
                tot["pop"] += a
                tot["smp"] += b
                L.append(f"| {run} | {s} | {h} | {a} | {b} |")
    L += [f"| 합계 | | | {tot['pop']} | {tot['smp']} |", "",
          "출처: `results/revision/runs_e9/{run}/reports.jsonl` (대상 페이지 이슈), `scoring/e9_rules.py`;",
          f"표본 목록 `{REL}/human_eval/e9_eval/key/sample_selection.csv`", "",
          "## 3. 표본 페이지 상태", "", "| 조건 run | 상태 | 페이지 |", "|---|---|---|"]
    L += [f"| {r} | {st} | {n} |" for (r, st), n in sorted(status.items())]
    dups = sum(1 for r in sel if r["dup_n_in_sample"] > 1)
    L += ["", "출처: 위 reports.jsonl", "",
          f"- 표본 안에서 같은 문장(설명 + 제안)이 2번 이상 나온 이슈: {dups}건(합치지 않음).",
          f"- **총 표본 이슈 {tot['smp']}건" + (f": 150건을 넘는다. 시트를 만들기 전에 지시를 받는다.**"
                                          if tot["smp"] > LIMIT else ": 150건 이하.**"), ""]
    open(out_md, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"{out_md}: sample {tot['smp']} (population {tot['pop']}), dups {dups}")


if __name__ == "__main__":
    {"counts": cmd_counts, "counts2": lambda: cmd_counts(True)}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
