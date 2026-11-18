"""
E1 과 E2-A1 실행 순서 (analysis_plan.md 9절 사전 수정).

  E1-R1 (순차, 지연시간 측정) → [관문] → E2-A1-1 → E1-R2 → E2-A1-2 → E1-R3 → E2-A1-3   (각 run 동시 4건)

관문: R1 의 오류율(api/rag/acquisition 오류 페이지 / 요청 페이지) ≤ 5% 이고 파싱 실패 ≤ 2% 일 때만 이어서 실행한다.
어느 run 이든 러너가 중단(종료 코드 ≠ 0: 402/429 즉시 중단, 오류율 20% 초과 등)하면 그 자리에서 멈춘다.
이미 끝난 run_id 는 건너뛴다(같은 run_id 는 러너가 거부하므로 재실행되지 않음).

  python experiments/revision/run_e1_a1_sequence.py [--from RUN_ID]
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
RUNS = os.path.join("results", "revision", "runs")
COMMON = ["--pages", "all", "--max-pages", "1", "--chroma-path", "services/chroma_db", "--prompt-date", "2026-11-11"]
SEQUENCE = [
    ("E1-R1", "E1", ["--concurrency", "1"]),
    ("E2-A1-1", "E2-A1", ["--concurrency", "4", "--no-rag"]),
    ("E1-R2", "E1", ["--concurrency", "4"]),
    ("E2-A1-2", "E2-A1", ["--concurrency", "4", "--no-rag"]),
    ("E1-R3", "E1", ["--concurrency", "4"]),
    ("E2-A1-3", "E2-A1", ["--concurrency", "4", "--no-rag"]),
]
GATE_ERROR = 0.05
GATE_PARSE = 0.02


def run_summary(run_id):
    d = os.path.join(RUNS, run_id)
    s = json.load(open(os.path.join(d, "summary.json"), encoding="utf-8"))
    n_issues = []
    for line in open(os.path.join(d, "reports.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        n_issues.append(len((r.get("report") or {}).get("issues", []) or []) if r["status"] == "ok" else None)
    ok_counts = [x for x in n_issues if x is not None]
    req = s["pages_requested"]
    out = {
        "run_id": run_id, "aborted": s["aborted"], "abort_reason": s["abort_reason"], "pages": req,
        "status_counts": s["status_counts"],
        "error_rate": len(s["failed_pages"]) / req, "parse_rate": len(s["parse_error_pages"]) / req,
        "failed_pages": s["failed_pages"], "parse_error_pages": s["parse_error_pages"],
        "issues_per_page": {"mean": round(statistics.mean(ok_counts), 2) if ok_counts else None,
                            "median": statistics.median(ok_counts) if ok_counts else None,
                            "min": min(ok_counts) if ok_counts else None, "max": max(ok_counts) if ok_counts else None,
                            "hist": dict(sorted(Counter(ok_counts).items()))},
        "cost_usd_total": s["cost_usd_total"], "model_versions": s["model_versions"],
        "rag_n_chunks_counts": s["rag_n_chunks_counts"],
    }
    print(f"\n===== {run_id} 요약 =====\n" + json.dumps(out, ensure_ascii=False, indent=1), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default=None)
    a = ap.parse_args()
    seq = SEQUENCE
    if a.start:
        seq = SEQUENCE[[r for r, _, _ in SEQUENCE].index(a.start):]
    for run_id, cond, extra in seq:
        if os.path.exists(os.path.join(RUNS, run_id)):
            print(f"[건너뜀] {run_id} 이미 있음", flush=True)
            s = run_summary(run_id)
        else:
            cmd = [sys.executable, "-W", "ignore", "experiments/revision/run_experiment.py",
                   "--run-id", run_id, "--condition", cond] + COMMON + extra
            print(f"\n>>> 시작 {run_id}: {' '.join(cmd[3:])}", flush=True)
            rc = subprocess.call(cmd)
            s = run_summary(run_id)
            if rc != 0 or s["aborted"]:
                print(f"!!! {run_id} 중단 (rc={rc}): {s['abort_reason']} → 순서 실행 멈춤", flush=True)
                return 2
        if run_id == "E1-R1":
            if s["error_rate"] > GATE_ERROR or s["parse_rate"] > GATE_PARSE:
                print(f"!!! R1 관문 불통과: 오류율 {s['error_rate']:.1%} (≤{GATE_ERROR:.0%}), "
                      f"파싱 실패 {s['parse_rate']:.1%} (≤{GATE_PARSE:.0%}) → 멈춤", flush=True)
                return 3
            print(f"R1 관문 통과: 오류율 {s['error_rate']:.1%}, 파싱 실패 {s['parse_rate']:.1%} → 계속", flush=True)
    print("\n전체 순서 완료 (E1-R1~R3, E2-A1-1~3). A2, A3, E3, E4 는 승인 후 진행.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
