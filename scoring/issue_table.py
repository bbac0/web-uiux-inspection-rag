"""
이슈 단위 통합 표: 한 run 의 대상 페이지 이슈마다 세 채점기의 판정을 한 행에 모은다 (API 호출 없음).

  keyword_types      키워드 사전(evaluate_performance_v5.CATEGORY_PHRASES, description 만, 다중 라벨) — ';' 로 연결
  semantic_pass1     의미 채점 pass1 라벨 (results/revision/semantic_scores/{out_id}/grades.jsonl), 없으면 빈 칸
  semantic_pass1_status  ok / parse_error / refusal / api_error
  string_match_term  string_match 규칙(description 또는 suggestion 에 '접속하기') 1/0 — 용어 위반만 판정

issue_id 는 의미 채점기와 같은 형식 "{run_id}:{page_id}:{issue_index:02d}" (issue_index = report.issues 안의 원래 순번).

  python scoring/issue_table.py --run-id E1-R1 [--semantic-out-id E1-R1-sem-p1] [--out results/revision/issue_tables/E1-R1.csv]
"""
import argparse
import csv
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import string_match          # noqa: E402
from scoring import semantic_grader_anthropic as sga   # noqa: E402  (iter_run_issues 재사용, API 호출 없음)

_spec = importlib.util.spec_from_file_location("kw", os.path.join(ROOT, "experiments", "evaluate_performance_v5.py"))
kw = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(kw)

COLUMNS = ["issue_id", "run_id", "page_id", "issue_index", "keyword_types", "semantic_pass1", "semantic_pass1_status",
           "string_match_term"]


def load_semantic(out_id, base=sga.OUT_BASE):
    if not out_id:
        return {}
    out = {}
    with open(os.path.join(base, out_id, "grades.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[r["issue_id"]] = (r.get("label"), r.get("status"))
    return out


def build_rows(run_id, semantic_out_id=None, runs_base=sga.RUNS_BASE, sem_base=sga.OUT_BASE):
    sem = load_semantic(semantic_out_id, sem_base)
    rows = []
    for issue_id, src, issue in sga.iter_run_issues(run_id, runs_base):
        k = sorted(kw.match_categories_in_issue(issue.get("description") or ""))
        lab, st = sem.get(issue_id, (None, None))
        rows.append({"issue_id": issue_id, "run_id": run_id, "page_id": src["page_id"], "issue_index": src["issue_index"],
                     "keyword_types": ";".join(k), "semantic_pass1": lab or "", "semantic_pass1_status": st or "",
                     "string_match_term": int(string_match.match(issue))})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--semantic-out-id", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    rows = build_rows(a.run_id, a.semantic_out_id)
    out = a.out or os.path.join(ROOT, "results", "revision", "issue_tables", f"{a.run_id}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS); w.writeheader(); w.writerows(rows)
    print(f"{out}: {len(rows)} issues")


if __name__ == "__main__":
    sys.exit(main())
