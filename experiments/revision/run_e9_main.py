"""
E9 본 실험 (2026-11-13 연구자 신호; `exp-freeze-e9-v3`). 91페이지 × 5조건 × 반복 2회. 3회째와 E9-4 보조(390x844)는 하지 않는다.

- 순서: run 1 의 5조건(norag, fixed, page, related, fixedlong)을 먼저 끝낸 뒤 run 2 의 5조건.
- run_id: e9-main-{조건}-r{1,2}, runs-base: results/revision/runs_e9 (러너 `run_experiment_e9.py --testbed main`, 끝나면 읽기 전용 잠금).
- 조건 인자: results/revision/e9/conditions_e9.json (동결) 그대로.
- 각 run 시작 전: E9 동결 목록 대조(freeze_manifest_e9.py --check), 남은 메모리 5GB 이상 동시 2건, 4.0~5.0GB 1건(계획 이탈 기록),
  4.0GB 미만이면 실행하지 않고 멈춘다(종료 코드 4).
- 실행 중: 기록 5건마다 메모리 기록. 4.0GB 미만이면 러너를 멈추고 aborted 표시(ABORTED.json) 후 잠그고 멈춘다(종료 코드 6).
  실패 페이지가 요청의 5% 를 넘으면 같은 방식으로 멈춘다(종료 코드 7). 402/429 는 러너가 즉시 중단한다(종료 코드 2).
- run 이 끝날 때마다 results/revision/reports/e9_main_progress.md 에 요약을 덧붙이고 run 결과와 함께 커밋한다.
- E9 LLM 판정과 의미 채점은 하지 않는다.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from services import llm_wrapper as lw                       # noqa: E402
from experiments.revision import run_e1_r3b_a1_3 as d0       # noqa: E402  (memory, memlog, kill_tree)

COND = json.load(open("results/revision/e9/conditions_e9.json", encoding="utf-8"))
ORDER = ["norag", "fixed", "page", "related", "fixedlong"]
RUNS = "results/revision/runs_e9"
MEMDIR = "results/revision/memory_logs"
PROGRESS = "results/revision/reports/e9_main_progress.md"
FAIL = ("api_error", "rag_empty", "rag_error", "acquisition_error")
MAX_ERR = 0.05


def server_up(port=8090):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/login/", timeout=2)
        return True
    except Exception:
        return False


def watch(run_dir, path, stop, proc, flags, n_req):
    calls = os.path.join(run_dir, "calls.jsonl")
    nxt = d0.LOG_EVERY
    while True:
        last = stop.is_set()
        recs = [json.loads(l) for l in open(calls, encoding="utf-8")] if os.path.exists(calls) else []
        n = len(recs)
        while n >= nxt:
            r = d0.memlog(path, "progress", records=n, mark=nxt)
            if r["avail_gb"] < 4.0 and not flags["mem"].is_set():
                d0.memlog(path, "stop_below_threshold", records=n, threshold_gb=4.0)
                flags["mem"].set(); d0.kill_tree(proc.pid)
            nxt += d0.LOG_EVERY
        failed = len({r["page_id"] for r in recs if r["status"] in FAIL})
        if n_req and failed / n_req > MAX_ERR and not flags["err"].is_set():
            d0.memlog(path, "stop_error_rate", records=n, failed_pages=failed, requested=n_req)
            flags["err"].set(); d0.kill_tree(proc.pid)
        if last:
            return
        stop.wait(2.0)


def mark_aborted(rid, run_dir, cause):
    meta = json.load(open(os.path.join(run_dir, "run_meta.json"), encoding="utf-8"))
    recs = [json.loads(l) for l in open(os.path.join(run_dir, "calls.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(run_dir, "calls.jsonl")) else []
    done = {r["page_id"] for r in recs}
    marker = {"run_id": rid, "status": "aborted", "marked_utc": lw.utc_now(), "cause": cause,
              "run_started_utc": meta["started_utc"], "records": len(recs),
              "pages_requested": len(meta["pages"]), "pages_missing": sorted(set(meta["pages"]) - done),
              "note": "멈춘 순간 진행 중이던 페이지는 API 호출이 이루어졌어도 기록되지 않았을 수 있다. 기존 파일은 수정하지 않았다."}
    if os.path.exists(os.path.join(run_dir, "SHA256SUMS")):
        return            # 러너가 이미 잠금(정상 종료 경로)
    json.dump(marker, open(os.path.join(run_dir, "ABORTED.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    cp = (meta.get("chroma") or {}).get("copy_path")
    if cp and os.path.isdir(cp) and "services" not in cp.replace("\\", "/").split("/"):
        shutil.rmtree(os.path.dirname(cp), ignore_errors=True)
    lw.lock_run(run_dir)


def progress_append(rid, conc, run_dir, note):
    calls = [json.loads(l) for l in open(os.path.join(run_dir, "calls.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(run_dir, "calls.jsonl")) else []
    reps = [json.loads(l) for l in open(os.path.join(run_dir, "reports.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(run_dir, "reports.jsonl")) else []
    summ_p = os.path.join(run_dir, "summary.json")
    summ = json.load(open(summ_p, encoding="utf-8")) if os.path.exists(summ_p) else {}
    aborted = os.path.exists(os.path.join(run_dir, "ABORTED.json")) or summ.get("aborted")
    st = {}
    for c in calls:
        st[c["status"]] = st.get(c["status"], 0) + 1
    fail = sum(v for k, v in st.items() if k in FAIL)
    n_iss = [len((r.get("report") or {}).get("issues") or []) for r in reps]
    L = [] if os.path.exists(PROGRESS) else ["# E9 본 실험 진행 기록", "", "run 이 끝날 때마다 덧붙인다(기술 집계만).", ""]
    L += [f"## {rid} ({lw.utc_now()[:19]} UTC 기록)", "", "| 항목 | 값 |", "|---|---|",
          f"| 상태 | {'aborted' if aborted else 'complete'} ({note}) |",
          f"| 동시 실행 | {conc}{' (계획 2건과 다름)' if conc != '2' else ''} |",
          f"| 기록 | {len(calls)} |", f"| 상태별 | {', '.join(f'{k} {v}' for k, v in sorted(st.items()))} |",
          f"| 오류율 | {100 * fail / max(1, len(calls)):.1f}% |", f"| 이슈 합계 | {sum(n_iss)} |",
          f"| 비용 (USD) | {sum(c['cost_usd']['total'] for c in calls):.4f} |", "",
          f"출처: `{run_dir.replace(os.sep, '/')}/calls.jsonl`, `reports.jsonl`, `summary.json`", ""]
    with open(PROGRESS, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    subprocess.call(["git", "add", PROGRESS, run_dir, MEMDIR])
    subprocess.call(["git", "commit", "-q", "-m", f"{rid}: E9 main run finished ({'aborted' if aborted else 'complete'}, {note})\n\n"
                     "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"])


def main():
    srv = None
    if not server_up():
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8090", "--bind", "127.0.0.1", "--directory", "testbed_e9"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if server_up():
                break
            time.sleep(0.25)
    try:
        for rep in (1, 2):
            for cond in ORDER:
                rid = f"e9-main-{cond}-r{rep}"
                run_dir = os.path.join(RUNS, rid)
                if os.path.exists(run_dir):
                    print(f"[건너뜀] {rid} 이미 있음", flush=True); continue
                if subprocess.call([sys.executable, "experiments/revision/freeze_manifest_e9.py", "--check"]) != 0:
                    print(f"!!! {rid}: E9 동결 대조 실패 → 멈춤", flush=True); return 5
                mpath = os.path.join(MEMDIR, f"{rid}.jsonl")
                m = d0.memlog(mpath, "pre_start_check", threshold_gb=5.0, low_threshold_gb=4.0)
                if m["avail_gb"] < 4.0:
                    print(f"!!! 남은 메모리 {m['avail_gb']}GB < 4.0GB → {rid} 실행하지 않음", flush=True); return 4
                conc = "2" if m["avail_gb"] >= 5.0 else "1"
                if conc == "1":
                    dev = {"ts_utc": lw.utc_now(), "run_id": rid, "avail_gb": m["avail_gb"], "concurrency": 1,
                           "planned_concurrency": 2, "reason": "pre-start free memory 4.0-5.0GB (researcher rule 2026-11-13)"}
                    with open(os.path.join(MEMDIR, "concurrency_deviations.jsonl"), "a", encoding="utf-8") as f:
                        f.write(json.dumps(dev, ensure_ascii=False) + "\n")
                    print(f"[계획 이탈] {rid}: 남은 메모리 {m['avail_gb']}GB → 동시 실행 1건", flush=True)
                cmd = [sys.executable, "-W", "ignore", "experiments/revision/run_experiment_e9.py", "--run-id", rid,
                       "--condition", f"E9-{cond}"] + COND["common_args"] + COND["conditions"][cond]["args"] + ["--concurrency", conc]
                print(f"\n>>> 시작 {rid} (동시 {conc}): {' '.join(cmd[3:])}", flush=True)
                proc = subprocess.Popen(cmd)
                n_req = None
                for _ in range(600):
                    mp = os.path.join(run_dir, "run_meta.json")
                    if os.path.exists(mp):
                        try:
                            n_req = len(json.load(open(mp, encoding="utf-8"))["pages"]); break
                        except Exception:
                            pass
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
                flags = {"mem": threading.Event(), "err": threading.Event()}
                stop = threading.Event()
                t = threading.Thread(target=watch, args=(run_dir, mpath, stop, proc, flags, n_req), daemon=True)
                t.start()
                try:
                    rc = proc.wait()
                finally:
                    stop.set(); t.join(timeout=15)
                    d0.memlog(mpath, "run_end", rc=rc)
                if flags["mem"].is_set():
                    mark_aborted(rid, run_dir, "실행 중 남은 메모리 4.0GB 미만으로 멈춤(연구자 규칙)")
                    progress_append(rid, conc, run_dir, "stopped: free memory < 4GB")
                    print(f"!!! {rid}: 메모리 4GB 미만 → aborted 표시·보존, 연구자 지시 대기", flush=True); return 6
                if flags["err"].is_set():
                    mark_aborted(rid, run_dir, "실패 페이지가 요청의 5% 초과로 멈춤")
                    progress_append(rid, conc, run_dir, "stopped: failed pages > 5%")
                    print(f"!!! {rid}: 실패 페이지 5% 초과 → aborted 표시·보존, 연구자 지시 대기", flush=True); return 7
                s = json.load(open(os.path.join(run_dir, "summary.json"), encoding="utf-8"))
                progress_append(rid, conc, run_dir, f"rc={rc}")
                print(f"{rid}: rc={rc} status={s.get('status_counts')} aborted={s.get('aborted')} "
                      f"verify={'OK' if not lw.verify_run(run_dir) else 'MISMATCH'}", flush=True)
                if rc != 0 or s.get("aborted"):
                    print(f"!!! {rid} 중단: {s.get('abort_reason')} → 멈춤", flush=True); return 2
    finally:
        if srv is not None:
            srv.terminate(); srv.wait(timeout=10)
    print("E9 본 실험 run 1·2 완료 (10개 run)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
