"""
E9 본 실험 3회째 (2026-11-13 연구자 지시, `exp-freeze-e9-v4` 사전 수정 (a)). fixed-long 과 RAG 끔만, 각 91페이지.
run_id: e9-main-norag-r3, e9-main-fixedlong-r3 (이 순서). 다른 조건, E9 LLM 판정, E9-4 보조에는 API 를 쓰지 않는다.

- 각 run 시작 전: E9 동결 목록 대조(freeze_manifest_e9.py --check, v4 목록), 남은 메모리 5GB 이상 동시 2건,
  4.0~5.0GB 1건(계획 이탈 기록), 4.0GB 미만이면 실행하지 않고 멈춘다(종료 코드 4).
- 실행 중: 기록 5건마다 메모리 기록, 4.0GB 미만이면 멈추고 aborted 표시(종료 코드 6). 실패 페이지 5% 초과(종료 코드 7),
  402/429 는 러너가 즉시 중단(종료 코드 2).
- **비용 상한:** 두 run 의 calls.jsonl 비용 합계가 $2.5 를 넘으면 즉시 러너를 멈추고 aborted 표시(종료 코드 8).
- 끝나면 읽기 전용 잠금(러너), run 마다 e9_main_progress.md 에 덧붙이고 커밋(run_e9_main.progress_append 재사용).
"""
import json
import os
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from services import llm_wrapper as lw                       # noqa: E402
from experiments.revision import run_e1_r3b_a1_3 as d0       # noqa: E402
from experiments.revision import run_e9_main as m9           # noqa: E402

ORDER = ["norag", "fixedlong"]
RIDS = [f"e9-main-{c}-r3" for c in ORDER]
COST_CAP = 2.5


def run_cost(rid):
    p = os.path.join(m9.RUNS, rid, "calls.jsonl")
    if not os.path.exists(p):
        return 0.0
    return sum(json.loads(l)["cost_usd"]["total"] for l in open(p, encoding="utf-8") if l.strip())


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
        failed = len({r["page_id"] for r in recs if r["status"] in m9.FAIL})
        if n_req and failed / n_req > m9.MAX_ERR and not flags["err"].is_set():
            d0.memlog(path, "stop_error_rate", records=n, failed_pages=failed, requested=n_req)
            flags["err"].set(); d0.kill_tree(proc.pid)
        tot = sum(run_cost(x) for x in RIDS)
        if tot > COST_CAP and not flags["cost"].is_set():
            d0.memlog(path, "stop_cost_cap", records=n, cumulative_cost_usd=round(tot, 4), cap_usd=COST_CAP)
            flags["cost"].set(); d0.kill_tree(proc.pid)
        if last:
            return
        stop.wait(2.0)


def main():
    srv = None
    if not m9.server_up():
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8090", "--bind", "127.0.0.1", "--directory", "testbed_e9"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if m9.server_up():
                break
            time.sleep(0.25)
    try:
        for cond, rid in zip(ORDER, RIDS):
            run_dir = os.path.join(m9.RUNS, rid)
            if os.path.exists(run_dir):
                print(f"[건너뜀] {rid} 이미 있음", flush=True); continue
            if subprocess.call([sys.executable, "experiments/revision/freeze_manifest_e9.py", "--check"]) != 0:
                print(f"!!! {rid}: E9 동결 대조 실패 → 멈춤", flush=True); return 5
            if sum(run_cost(x) for x in RIDS) > COST_CAP:
                print(f"!!! 누적 비용 상한 초과 → {rid} 시작하지 않음", flush=True); return 8
            mpath = os.path.join(m9.MEMDIR, f"{rid}.jsonl")
            m = d0.memlog(mpath, "pre_start_check", threshold_gb=5.0, low_threshold_gb=4.0)
            if m["avail_gb"] < 4.0:
                print(f"!!! 남은 메모리 {m['avail_gb']}GB < 4.0GB → {rid} 실행하지 않음", flush=True); return 4
            conc = "2" if m["avail_gb"] >= 5.0 else "1"
            if conc == "1":
                dev = {"ts_utc": lw.utc_now(), "run_id": rid, "avail_gb": m["avail_gb"], "concurrency": 1,
                       "planned_concurrency": 2, "reason": "pre-start free memory 4.0-5.0GB (researcher rule 2026-11-13)"}
                with open(os.path.join(m9.MEMDIR, "concurrency_deviations.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(dev, ensure_ascii=False) + "\n")
                print(f"[계획 이탈] {rid}: 남은 메모리 {m['avail_gb']}GB → 동시 실행 1건", flush=True)
            cmd = [sys.executable, "-W", "ignore", "experiments/revision/run_experiment_e9.py", "--run-id", rid,
                   "--condition", f"E9-{cond}"] + m9.COND["common_args"] + m9.COND["conditions"][cond]["args"] + ["--concurrency", conc]
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
            flags = {"mem": threading.Event(), "err": threading.Event(), "cost": threading.Event()}
            stop = threading.Event()
            t = threading.Thread(target=watch, args=(run_dir, mpath, stop, proc, flags, n_req), daemon=True)
            t.start()
            try:
                rc = proc.wait()
            finally:
                stop.set(); t.join(timeout=15)
                d0.memlog(mpath, "run_end", rc=rc)
            for key, cause, note, code in (
                    ("mem", "실행 중 남은 메모리 4.0GB 미만으로 멈춤(연구자 규칙)", "stopped: free memory < 4GB", 6),
                    ("err", "실패 페이지가 요청의 5% 초과로 멈춤", "stopped: failed pages > 5%", 7),
                    ("cost", f"두 run 누적 비용 ${COST_CAP} 초과로 멈춤(연구자 규칙)", "stopped: cumulative cost > $2.5", 8)):
                if flags[key].is_set():
                    m9.mark_aborted(rid, run_dir, cause)
                    m9.progress_append(rid, conc, run_dir, note)
                    print(f"!!! {rid}: {cause} → aborted 표시·보존, 연구자 지시 대기", flush=True)
                    return code
            s = json.load(open(os.path.join(run_dir, "summary.json"), encoding="utf-8"))
            m9.progress_append(rid, conc, run_dir, f"rc={rc}")
            print(f"{rid}: rc={rc} status={s.get('status_counts')} aborted={s.get('aborted')} "
                  f"verify={'OK' if not lw.verify_run(run_dir) else 'MISMATCH'} "
                  f"cum_cost={sum(run_cost(x) for x in RIDS):.4f}", flush=True)
            if rc != 0 or s.get("aborted"):
                print(f"!!! {rid} 중단: {s.get('abort_reason')} → 멈춤", flush=True); return 2
    finally:
        if srv is not None:
            srv.terminate(); srv.wait(timeout=10)
    print("E9 3회째 (RAG 끔, fixed-long) 완료", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
