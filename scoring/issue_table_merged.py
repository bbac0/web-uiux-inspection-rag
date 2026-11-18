"""
이슈 단위 통합 표 + 재채점 병합 열 (API 호출 없음). 동결된 scoring/issue_table.py 의 열을 그대로 두고 열을 더한다.

  semantic_pass1_merged          원 상태 ok → 원 라벨, 아니면 재채점 상태 ok → 재채점 라벨, 아니면 빈 칸
  semantic_pass1_source          original / retry / unresolved
  semantic_pass1_filled_by_retry 1 = 재채점으로 채운 건
  semantic_retry_status          재채점 상태(ok, parse_error, refusal, api_error), 재채점 대상이 아니면 빈 칸

재채점 폴더 = {semantic_out_id}-retry (없으면 재채점 열은 비고, 원 비성공 건은 unresolved).
주 분석은 merged (results/revision/analysis_plan_addendum_semantic_retry.md).

  python scoring/issue_table_merged.py --run-id E1-R1 [--semantic-out-id E1-R1-sem-p1] [--out PATH]
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import issue_table as it                   # noqa: E402
from scoring import semantic_grader_anthropic as sga    # noqa: E402

EXTRA = ["semantic_pass1_merged", "semantic_pass1_source", "semantic_pass1_filled_by_retry", "semantic_retry_status"]
COLUMNS = it.COLUMNS + EXTRA


def load_retry(out_id, base):
    path = os.path.join(base, out_id + "-retry", "grades.jsonl")
    out = {}
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            r = json.loads(l)
            out[r["issue_id"]] = (r.get("label"), r.get("status"))     # 마지막 기록 우선 (api_error 뒤 재제출)
    return out


def build_rows(run_id, semantic_out_id=None, runs_base=sga.RUNS_BASE, sem_base=sga.OUT_BASE):
    oid = semantic_out_id or f"{run_id}-sem-p1"
    rows = it.build_rows(run_id, oid, runs_base, sem_base)
    retry = load_retry(oid, sem_base)
    for r in rows:
        rl, rs = retry.get(r["issue_id"], (None, None))
        if r["semantic_pass1_status"] == "ok":
            merged, source = r["semantic_pass1"], "original"
        elif rs == "ok":
            merged, source = rl, "retry"
        else:
            merged, source = "", "unresolved"
        r.update(semantic_pass1_merged=merged or "", semantic_pass1_source=source,
                 semantic_pass1_filled_by_retry=int(source == "retry"), semantic_retry_status=rs or "")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--semantic-out-id", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    rows = build_rows(a.run_id, a.semantic_out_id)
    out = a.out or os.path.join(ROOT, "results", "revision", "issue_tables_merged", f"{a.run_id}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS); w.writeheader(); w.writerows(rows)
    print(f"{out}: {len(rows)} issues")


if __name__ == "__main__":
    sys.exit(main())
