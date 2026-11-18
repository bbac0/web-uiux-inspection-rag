"""
E9 파일럿 실행 (2026-11-13 연구자 신호). testbed_e9_pilot/ 8페이지 × 5조건 × 1회. 파일럿 결과는 분석에서 제외한다.

- 조건 인자는 results/revision/e9/conditions_e9.json 그대로 쓰되 --testbed pilot 으로 바꾸고, oracle 입력은 같은 청크·같은 순서로
  파일럿 페이지 ID 에 맞춰 만든 results/revision/e9_pilot/e9p_{related_clause,fixed_long}_chunks.csv 를 쓴다(이 스크립트가 만든다).
- run_id: {prefix}-{condition} (--prefix, 기본 e9-pilot; 재파일럿은 e9-pilot2). runs-base: results/revision/runs_e9_pilot.
- 각 run 시작 전 남은 메모리: 5GB 이상 동시 2건, 4.0~5.0GB 1건(기록), 4.0GB 미만 실행 안 함(종료 코드 4).
  실행 중 기록 5건마다 메모리 기록, 4GB 미만이면 멈춤. 402/429 는 러너가 즉시 중단(종료 코드 2 → 순서 멈춤).
- 서버: python -m http.server 8091 --bind 127.0.0.1 --directory testbed_e9_pilot (이 스크립트가 띄우고 내린다).
- Anthropic 의미 채점과 E9 LLM 판정은 하지 않는다.
"""
import csv
import json
import os
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
RUNS = "results/revision/runs_e9_pilot"
MEMDIR = "results/revision/memory_logs"
PILOT_META = "testbed_e9_pilot/dataset_metadata_e9_pilot.json"
OUTDIR = "results/revision/e9_pilot"


def pilot_chunk_files():
    pages = sorted(p["page_id"] for p in json.load(open(PILOT_META, encoding="utf-8"))["pages"])
    out = {}
    for name in ("related_clause", "fixed_long"):
        src = f"results/revision/e9/e9_{name}_chunks.csv"
        rows = list(csv.DictReader(open(src, encoding="utf-8")))
        first = rows[0]["page_id"]
        ids = [r["chunk_id"] for r in rows if r["page_id"] == first]
        dst = os.path.join(OUTDIR, f"e9p_{name}_chunks.csv")
        with open(dst, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["page_id", "chunk_id"])
            for p in pages:
                for c in ids:
                    w.writerow([p, c])
        out[src] = dst
    return out


def server_up(port):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/login/", timeout=2)
        return True
    except Exception:
        return False


def watch(run_dir, path, stop, proc, flag):
    calls = os.path.join(run_dir, "calls.jsonl")
    nxt = d0.LOG_EVERY
    while True:
        last = stop.is_set()
        n = sum(1 for _ in open(calls, encoding="utf-8")) if os.path.exists(calls) else 0
        while n >= nxt:
            r = d0.memlog(path, "progress", records=n, mark=nxt)
            if r["avail_gb"] < d0.STOP_BELOW_GB and not flag.is_set():
                d0.memlog(path, "stop_below_threshold", records=n, threshold_gb=d0.STOP_BELOW_GB)
                flag.set(); d0.kill_tree(proc.pid)
            nxt += d0.LOG_EVERY
        if last:
            return
        stop.wait(2.0)


def main():
    prefix = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else "e9-pilot"
    os.makedirs(OUTDIR, exist_ok=True)
    remap = pilot_chunk_files()
    srv = None
    if not server_up(8091):
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8091", "--bind", "127.0.0.1", "--directory", "testbed_e9_pilot"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if server_up(8091):
                break
            time.sleep(0.25)
    try:
        for cond, spec in COND["conditions"].items():
            rid = f"{prefix}-{cond}"
            run_dir = os.path.join(RUNS, rid)
            if os.path.exists(run_dir):
                print(f"[건너뜀] {rid} 이미 있음", flush=True); continue
            mpath = os.path.join(MEMDIR, f"{rid}.jsonl")
            m = d0.memlog(mpath, "pre_start_check", threshold_gb=5.0, low_threshold_gb=4.0)
            if m["avail_gb"] < 4.0:
                print(f"!!! 남은 메모리 {m['avail_gb']}GB < 4.0GB → {rid} 실행 안 함", flush=True); return 4
            conc = "2" if m["avail_gb"] >= 5.0 else "1"
            if conc == "1":
                dev = {"ts_utc": lw.utc_now(), "run_id": rid, "avail_gb": m["avail_gb"], "concurrency": 1,
                       "planned_concurrency": 2, "reason": "pre-start free memory 4.0-5.0GB (researcher rule 2026-11-13)"}
                with open(os.path.join(MEMDIR, "concurrency_deviations.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(dev, ensure_ascii=False) + "\n")
                print(f"[계획 이탈] {rid}: 남은 메모리 {m['avail_gb']}GB → 동시 실행 1건", flush=True)
            args = [a if a not in remap else remap[a] for a in COND["common_args"] + spec["args"]]
            args[args.index("--testbed") + 1] = "pilot"
            cmd = [sys.executable, "-W", "ignore", "experiments/revision/run_experiment_e9.py", "--run-id", rid,
                   "--condition", f"E9-{prefix[3:]}-{cond}"] + args + ["--concurrency", conc]
            print(f"\n>>> 시작 {rid} (동시 {conc}): {' '.join(cmd[3:])}", flush=True)
            proc = subprocess.Popen(cmd)
            stop, flag = threading.Event(), threading.Event()
            t = threading.Thread(target=watch, args=(run_dir, mpath, stop, proc, flag), daemon=True)
            t.start()
            try:
                rc = proc.wait()
            finally:
                stop.set(); t.join(timeout=15)
                d0.memlog(mpath, "run_end", rc=rc)
            if flag.is_set():
                print(f"!!! {rid}: 메모리 4GB 미만 → 멈춤, 상태 보존", flush=True); return 6
            s = json.load(open(os.path.join(run_dir, "summary.json"), encoding="utf-8"))
            print(f"{rid}: rc={rc} status={s.get('status_counts')} aborted={s.get('aborted')} "
                  f"verify={'OK' if not lw.verify_run(run_dir) else 'MISMATCH'}", flush=True)
            if rc != 0 or s.get("aborted"):
                print(f"!!! {rid} 중단: {s.get('abort_reason')} → 멈춤", flush=True); return 2
    finally:
        if srv is not None:
            srv.terminate(); srv.wait(timeout=10)
    print(f"E9 파일럿 5조건 완료 ({prefix})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
