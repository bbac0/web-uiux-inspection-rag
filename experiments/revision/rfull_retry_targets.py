"""
R-full 잘림 재채점 대상 목록 (API 호출 없음). 기존 규칙(semantic_truncation_report.py)과 같다:
1차 채점 grades.jsonl 에서 truncated 인 이슈. 기존 동결 파일 semantic_truncation_targets.csv 는 고치지 않고 새 파일을 쓴다.

  python experiments/revision/rfull_retry_targets.py
출력(덮어쓰지 않음): results/revision/semantic_truncation_targets_rfull.csv
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "results/revision/semantic_truncation_targets_rfull.csv"
O = "E1-Rfull-r1-sem-p1"


def main():
    if os.path.exists(OUT):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUT}")
    meta = json.load(open(f"results/revision/semantic_scores/{O}/summary.json", encoding="utf-8"))
    rows = []
    for line in open(f"results/revision/semantic_scores/{O}/grades.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r.get("truncated"):
            rows.append([O, O + "-retry", meta["source_run"], r["pass"], "+".join(meta["input_fields"]), r["issue_id"],
                         r.get("input_tokens") or 0])
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["out_id", "retry_out_id", "source_run", "pass", "input_fields", "issue_id", "orig_input_tokens"])
        w.writerows(rows)
    print(f"{OUT}: {len(rows)} targets")


if __name__ == "__main__":
    sys.exit(main())
