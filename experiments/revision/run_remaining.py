"""
A2 → A3 → E3-page → E3-oracle(related-clause) → E4-mobile 순서 실행 (2026-11-13 연구자 승인).

- run_id·플래그는 results/revision/README.md 실행 표 그대로. E3-fixed 는 E1-R1 재사용(실행 안 함).
- 각 run 시작 전 남은 메모리: 5GB 이상이면 동시 2건, 4.0~5.0GB 이면 동시 1건(memory_logs/concurrency_deviations.jsonl 에 기록,
  README 계획 이탈 기록 대상), 4.0GB 미만이면 실행하지 않고 멈춘다(종료 코드 4). (2026-11-13 연구자 결정)
- 실행 중 기록 5건마다 남은 메모리를 results/revision/memory_logs/{run_id}.jsonl 에 남긴다. 4GB 미만이면 러너를 멈추고
  상태를 보존한다(종료 코드 6, 잠금·aborted 표시 안 함).
- **오류율 5% 초과 즉시 중단:** 실패 페이지(api/rag/acquisition 오류) 수가 요청 페이지의 5% 를 넘는 순간(최종 오류율이 5% 를
  넘을 수밖에 없는 시점) 러너를 멈추고 상태를 보존한다(종료 코드 7). 402/429 는 러너가 즉시 중단한다(종료 코드 2).
- E3-oracle 은 results/revision/oracle_chunks.csv 와 fixed_long_selection.json 이 있어야 시작한다.

  python experiments/revision/run_remaining.py [--dry-run] [--mock-test DIR]
"""
import argparse
import json
import os
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from services import llm_wrapper as lw                         # noqa: E402
from experiments.revision import run_e1_r3b_a1_3 as d0         # noqa: E402  (memory, memlog, kill_tree, ensure_server, frozen_changed)
from experiments.revision import run_e1_a1_sequence as seq0    # noqa: E402  (run_summary)

RUNS = os.path.join("results", "revision", "runs")
BASE = ["--max-pages", "1", "--chroma-path", "services/chroma_db", "--prompt-date", "2026-11-11"]
LOW_FREE_GB = 4.0     # 2026-11-13 연구자 결정: 5GB 이상 동시 2건, 4.0~5.0GB 동시 1건(계획 이탈 기록), 4.0GB 미만 실행 안 함
DEVIATIONS = os.path.join("results", "revision", "memory_logs", "concurrency_deviations.jsonl")
SEQUENCE = [
    ("E2-A2", "E2-A2", ["--pages", "all", "--modality", "html"]),
    ("E2-A3", "E2-A3", ["--pages", "all", "--modality", "screenshot"]),
    ("E3-page", "E3-page", ["--pages", "terminology+controls", "--query-mode", "page"]),
    ("E3-oracle", "E3-oracle", ["--pages", "terminology+controls", "--query-mode", "oracle",
                                "--oracle-chunks", "results/revision/oracle_chunks.csv"]),
    ("E4-mobile", "E4-mobile", ["--pages", "mobile+controls", "--viewport-extra", "mobile"]),
]
MAX_ERR = 0.05
FAIL = ("api_error", "rag_empty", "rag_error", "acquisition_error")


def watch(run_dir, path, stop, proc, flags, n_req):
    calls = os.path.join(run_dir, "calls.jsonl")
    nxt = d0.LOG_EVERY
    while True:
        last = stop.is_set()
        recs = [json.loads(l) for l in open(calls, encoding="utf-8")] if os.path.exists(calls) else []
        n = len(recs)
        while n >= nxt:
            r = d0.memlog(path, "progress", records=n, mark=nxt)
            if r["avail_gb"] < d0.MIN_FREE_GB:
                d0.memlog(path, "warning_below_threshold", records=n, threshold_gb=d0.MIN_FREE_GB)
            if r["avail_gb"] < d0.STOP_BELOW_GB and not flags["mem"].is_set():
                d0.memlog(path, "stop_below_threshold", records=n, threshold_gb=d0.STOP_BELOW_GB)
                flags["mem"].set(); d0.kill_tree(proc.pid)
            nxt += d0.LOG_EVERY
        failed = len({r["page_id"] for r in recs if r["status"] in FAIL})
        if n_req and failed / n_req > MAX_ERR and not flags["err"].is_set():
            d0.memlog(path, "stop_error_rate", records=n, failed_pages=failed, requested=n_req)
            flags["err"].set(); d0.kill_tree(proc.pid)
        if last:
            return
        stop.wait(2.0)


PROGRESS = os.path.join("results", "revision", "reports", "a2_e4_progress.md")


def progress_append(rid, conc, run_dir, note):
    """run 이 끝날 때마다 요약 한 덩어리를 a2_e4_progress.md 에 덧붙이고 run 결과와 함께 커밋한다."""
    calls = [json.loads(l) for l in open(os.path.join(run_dir, "calls.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(run_dir, "calls.jsonl")) else []
    reps = [json.loads(l) for l in open(os.path.join(run_dir, "reports.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(run_dir, "reports.jsonl")) else []
    meta = json.load(open(os.path.join(run_dir, "run_meta.json"), encoding="utf-8"))
    summ_p = os.path.join(run_dir, "summary.json")
    summ = json.load(open(summ_p, encoding="utf-8")) if os.path.exists(summ_p) else {}
    st = {}
    for c in calls:
        st[c["status"]] = st.get(c["status"], 0) + 1
    fail = sum(v for k, v in st.items() if k in FAIL)
    n_iss = [len((r.get("report") or {}).get("issues") or []) for r in reps]
    state = "aborted" if summ.get("aborted") else ("complete" if summ else "stopped (no summary)")
    new = not os.path.exists(PROGRESS)
    L = []
    if new:
        L += ["# A2~E4 진행 기록", "", "run 이 끝날 때마다 덧붙인다. 기술 집계만(통계 검정 없음). 동시 실행이 계획(2건)과 다르면 표시한다.", ""]
    L += [f"## {rid} ({lw.utc_now()[:19]} UTC 기록)", "",
          "| 항목 | 값 |", "|---|---|",
          f"| 상태 | {state} ({note}) |",
          f"| 동시 실행 | {conc}{' (계획 2건과 다름: 시작 전 메모리 4.0~5.0GB)' if conc != '2' else ''} |",
          f"| 요청 페이지 | {len(meta['pages'])} |",
          f"| 기록 | {len(calls)} |",
          f"| 상태별 | {', '.join(f'{k} {v}' for k, v in sorted(st.items()))} |",
          f"| 오류율 | {100 * fail / max(1, len(calls)):.1f}% |",
          f"| 이슈 합계 | {sum(n_iss)} |",
          f"| 이슈/페이지 평균 (범위) | {(sum(n_iss) / len(n_iss)) if n_iss else 0:.2f} "
          f"({min(n_iss) if n_iss else 0}~{max(n_iss) if n_iss else 0}) |",
          f"| 비용 (USD) | {sum(c['cost_usd']['total'] for c in calls):.4f} |",
          f"| RAG 청크 | {', '.join(sorted({str(c['rag']['n_chunks']) for c in calls}))} |", "",
          f"출처: `{run_dir.replace(os.sep, '/')}/calls.jsonl`, `reports.jsonl`, `run_meta.json`, `summary.json`", ""]
    with open(PROGRESS, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    subprocess.call(["git", "add", PROGRESS, run_dir, d0.MEMLOG_DIR])
    subprocess.call(["git", "commit", "-q", "-m", f"{rid}: run finished ({state}, {note}); progress summary appended\n\n"
                     "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock-test", metavar="DIR", default=None)
    ap.add_argument("--mock-min-free-gb", type=float, default=None)
    a = ap.parse_args()
    if a.mock_min_free_gb is not None:
        if not a.mock_test:
            raise SystemExit("--mock-min-free-gb 는 --mock-test 와만")
        d0.MIN_FREE_GB = a.mock_min_free_gb
    runs_base = a.mock_test or RUNS
    memdir = os.path.join(a.mock_test, "memory_logs") if a.mock_test else d0.MEMLOG_DIR
    os.makedirs(memdir, exist_ok=True)
    bad = d0.frozen_changed()
    if bad:
        print(f"!!! 동결 확인 실패: {bad} → 멈춤", flush=True); return 5
    print("동결 확인 OK", flush=True)
    for need in ("results/revision/oracle_chunks.csv", "results/revision/fixed_long_selection.json"):
        if not os.path.exists(need):
            print(f"!!! {need} 없음 → 멈춤", flush=True); return 5
    if a.dry_run:
        print("남은 메모리:", d0.memory(), flush=True)
        for rid, cond, extra in SEQUENCE:
            print("명령:", " ".join(["run_experiment.py", "--run-id", rid, "--condition", cond] + BASE + ["--concurrency", "2|1"] + extra),
                  "| 이미 있음" if os.path.exists(os.path.join(RUNS, rid)) else "", flush=True)
        return 0
    srv = d0.ensure_server()
    try:
        for rid, cond, extra in SEQUENCE:
            run_dir = os.path.join(runs_base, rid)
            mpath = os.path.join(memdir, f"{rid}.jsonl")
            if os.path.exists(run_dir):
                print(f"[건너뜀] {rid} 이미 있음", flush=True); continue
            if rid.startswith("E3"):
                bad = d0.frozen_changed()     # oracle_chunks.csv, fixed_long_selection.json 포함 동결 목록 전체 대조
                if bad:
                    print(f"!!! {rid}: 동결 파일 변경 감지 {bad} → 시작하지 않음", flush=True); return 5
                print(f"{rid}: 동결 대조 OK (oracle_chunks.csv, fixed_long_selection.json 포함)", flush=True)
            m = d0.memlog(mpath, "pre_start_check", threshold_gb=d0.MIN_FREE_GB, low_threshold_gb=LOW_FREE_GB)
            if m["avail_gb"] < LOW_FREE_GB:
                print(f"!!! 남은 메모리 {m['avail_gb']}GB < {LOW_FREE_GB}GB → {rid} 실행하지 않음", flush=True); return 4
            conc = "2" if m["avail_gb"] >= d0.MIN_FREE_GB else "1"
            if conc == "1":
                dev = {"ts_utc": lw.utc_now(), "run_id": rid, "avail_gb": m["avail_gb"], "concurrency": 1, "planned_concurrency": 2,
                       "reason": "pre-start free memory 4.0-5.0GB (researcher rule 2026-11-13)"}
                with open(os.path.join(memdir, "concurrency_deviations.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(dev, ensure_ascii=False) + "\n")
                print(f"[계획 이탈] {rid}: 남은 메모리 {m['avail_gb']}GB (4.0~5.0GB) → 동시 실행 1건", flush=True)
            mock_pages = "page_006,page_007,page_017,page_028" if rid.startswith("E3") else "page_001,page_002,page_005,page_010"
            mock = ["--mock-llm", "--runs-base", runs_base, "--pages", f"list:{mock_pages}"] if a.mock_test else []
            cmd = [sys.executable, "-W", "ignore", "experiments/revision/run_experiment.py", "--run-id", rid,
                   "--condition", cond] + BASE + ["--concurrency", conc] + extra + mock
            print(f"\n>>> 시작 {rid}: {' '.join(cmd[3:])}", flush=True)
            proc = subprocess.Popen(cmd)
            n_req = None
            for _ in range(600):   # run_meta.json 이 생기면 요청 페이지 수를 읽는다
                mp = os.path.join(run_dir, "run_meta.json")
                if os.path.exists(mp):
                    try:
                        n_req = len(json.load(open(mp, encoding="utf-8"))["pages"]); break
                    except Exception:
                        pass
                if proc.poll() is not None:
                    break
                threading.Event().wait(0.5)
            flags = {"mem": threading.Event(), "err": threading.Event()}
            stop = threading.Event()
            t = threading.Thread(target=watch, args=(run_dir, mpath, stop, proc, flags, n_req), daemon=True)
            t.start()
            try:
                rc = proc.wait()
            finally:
                stop.set(); t.join(timeout=15)
                n = sum(1 for _ in open(os.path.join(run_dir, "calls.jsonl"), encoding="utf-8")) \
                    if os.path.exists(os.path.join(run_dir, "calls.jsonl")) else 0
                d0.memlog(mpath, "run_end", records=n)
            if not a.mock_test:
                note = ("stopped: free memory < 4GB (state preserved)" if flags["mem"].is_set() else
                        "stopped: failed pages > 5% (state preserved)" if flags["err"].is_set() else f"rc={rc}")
                progress_append(rid, conc, run_dir, note)
            if flags["mem"].is_set():
                print(f"!!! {rid}: 메모리 {d0.STOP_BELOW_GB}GB 미만 → 멈춤, 상태 보존", flush=True); return 6
            if flags["err"].is_set():
                print(f"!!! {rid}: 실패 페이지가 요청의 5% 초과 → 멈춤, 상태 보존", flush=True); return 7
            if a.mock_test:
                print(f"[mock] {rid} rc={rc} verify={lw.verify_run(run_dir)}", flush=True); continue
            s = seq0.run_summary(rid)
            print(f"{rid} 잠금 확인: {'OK' if not lw.verify_run(run_dir) else 'MISMATCH'}", flush=True)
            if rc != 0 or s["aborted"]:
                print(f"!!! {rid} 중단 (rc={rc}): {s['abort_reason']} → 멈춤", flush=True); return 2
            if s["error_rate"] > MAX_ERR:
                print(f"!!! {rid} 오류율 {s['error_rate']:.1%} > 5% → 멈춤", flush=True); return 3
    finally:
        if srv is not None:
            srv.terminate(); srv.wait(timeout=10)
            print("테스트베드 서버 종료", flush=True)
    print("\n순서 완료 (E2-A2, E2-A3, E3-page, E3-oracle, E4-mobile).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
