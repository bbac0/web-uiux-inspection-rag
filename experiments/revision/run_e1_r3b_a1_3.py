"""
E1-R3 중단 후 재개 순서 (2026-11-12 연구자 결정). 기존 순서 드라이버(run_e1_a1_sequence.py, 동결)는 수정하지 않고 이 새 파일로 실행한다.

  E1-R3b (200페이지, 처음부터) → [관문] → E2-A1-3        각 run 동시 2건 (사전 규칙 '동시 4건 이하' 안)

- E1-R3 은 aborted 로 보존하며 분석에서 제외한다(이 스크립트는 건드리지 않음).
- 각 run 시작 전 남은 물리 메모리를 확인해 5GB 미만이면 실행하지 않고 종료 코드 4 로 멈춘다(연구자에게 보고).
- 실행 중 calls.jsonl 기록이 5건 늘 때마다 남은 메모리를 results/revision/memory_logs/{run_id}.jsonl 에 남긴다(append 전용).
  5GB 아래이면 경고를 남기고, **4GB 아래이면(2026-11-12 연구자 지시) 러너 프로세스 트리를 멈추고 상태를 그대로 보존한 채
  종료 코드 6 으로 끝낸다.** 이때 run 폴더는 잠그지도 aborted 로 표시하지도 않는다(처리와 재시작 여부는 연구자가 정함).
- 관문: E1-R3b 의 오류율(api/rag/acquisition 오류 페이지 / 요청 페이지) ≤ 5%, 파싱 실패 ≤ 2% 일 때만 E2-A1-3 으로 간다.
- 러너가 비정상 종료(402/429 즉시 중단, 오류율 20% 초과 등)하면 그 자리에서 멈춘다. 이미 있는 run_id 는 다시 돌리지 않는다.
- 시작 전 동결 확인(freeze_manifest --check)이 실패하면 멈춘다.
- 테스트베드 서버(localhost:8080)가 응답하지 않으면 이 스크립트가 `python -m http.server 8080 --bind 127.0.0.1` 을 저장소 루트에서
  띄우고 끝나면 내린다.

  python experiments/revision/run_e1_r3b_a1_3.py --dry-run      # API 없음: 메모리·서버·동결 확인과 실행 명령만 출력
  python experiments/revision/run_e1_r3b_a1_3.py                # 실제 실행 (연구자 알림 후)
  python experiments/revision/run_e1_r3b_a1_3.py --mock-test DIR # API 없음: 가짜 LLM, 6페이지, DIR 아래에 run 생성 (점검용)
"""

import argparse
import ctypes
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
from services import llm_wrapper as lw                           # noqa: E402
from experiments.revision import run_e1_a1_sequence as seq0      # noqa: E402  (읽기만: COMMON, run_summary, 관문 값)

RUNS = os.path.join("results", "revision", "runs")
MEMLOG_DIR = os.path.join("results", "revision", "memory_logs")
SEQUENCE = [
    ("E1-R3b", "E1", ["--concurrency", "2"]),
    ("E2-A1-3", "E2-A1", ["--concurrency", "2", "--no-rag"]),
]
MIN_FREE_GB = 5.0
STOP_BELOW_GB = 4.0        # 실행 중 5건 단위 기록이 이 값 아래면 멈춤
LOG_EVERY = 5
TESTBED_URL = "http://localhost:8080/testbed_200/page_001.html"


class _MemStatus(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def memory():
    """남은 물리 메모리(GB). Windows: GlobalMemoryStatusEx, 그 밖: /proc/meminfo."""
    if os.name == "nt":
        s = _MemStatus(); s.dwLength = ctypes.sizeof(_MemStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        return {"avail_gb": round(s.ullAvailPhys / 2**30, 2), "total_gb": round(s.ullTotalPhys / 2**30, 2),
                "load_pct": int(s.dwMemoryLoad)}
    info = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}
    return {"avail_gb": round(info["MemAvailable"] / 2**20, 2), "total_gb": round(info["MemTotal"] / 2**20, 2),
            "load_pct": round(100 * (1 - info["MemAvailable"] / info["MemTotal"]))}


def memlog(path, event, **kw):
    rec = {"ts_utc": lw.utc_now(), "event": event, **memory(), **kw}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[메모리] {event} {json.dumps({k: rec[k] for k in rec if k != 'ts_utc'}, ensure_ascii=False)}", flush=True)
    return rec


def kill_tree(pid):
    if os.name == "nt":
        subprocess.call(["taskkill", "/T", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.kill(pid, 9)


def watch(run_dir, path, stop, proc=None, mem_abort=None):
    """calls.jsonl 기록 수가 LOG_EVERY 배수에 닿을 때마다 메모리를 남긴다. STOP_BELOW_GB 아래면 러너를 멈춘다."""
    calls = os.path.join(run_dir, "calls.jsonl")
    nxt = LOG_EVERY
    while True:
        last = stop.is_set()          # 멈춤 신호 뒤에도 한 번 더 세어 마지막 기록을 놓치지 않는다
        n = sum(1 for _ in open(calls, encoding="utf-8")) if os.path.exists(calls) else 0
        while n >= nxt:
            r = memlog(path, "progress", records=n, mark=nxt)
            if r["avail_gb"] < MIN_FREE_GB:
                memlog(path, "warning_below_threshold", records=n, threshold_gb=MIN_FREE_GB)
            if r["avail_gb"] < STOP_BELOW_GB and proc is not None and mem_abort is not None and not mem_abort.is_set():
                memlog(path, "stop_below_threshold", records=n, threshold_gb=STOP_BELOW_GB)
                mem_abort.set()
                kill_tree(proc.pid)
            nxt += LOG_EVERY
        if last:
            return
        stop.wait(2.0)


def frozen_changed():
    """freeze_manifest.csv 에 기록된 항목만 현재 해시와 대조한다(--check 는 동결 후 추가된 새 파일도 '바뀜'으로 세므로 쓰지 않음)."""
    import csv
    from experiments.revision import freeze_manifest as fm
    with open(fm.OUT, encoding="utf-8") as f:
        old = {(r["kind"], r["name"]): r["sha256"] for r in csv.DictReader(f)}
    cur = {(r["kind"], r["name"]): r["sha256"] for r in fm.rows()}
    return [n for (k, n), h in old.items() if n != fm.OUT and cur.get((k, n)) != h]


def server_up():
    try:
        with urllib.request.urlopen(TESTBED_URL, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_server():
    if server_up():
        return None
    p = subprocess.Popen([sys.executable, "-m", "http.server", "8080", "--bind", "127.0.0.1"], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(0.5)
        if server_up():
            print(f"테스트베드 서버 시작 (pid {p.pid})", flush=True)
            return p
    p.terminate()
    raise SystemExit("테스트베드 서버를 띄우지 못함 → 멈춤")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock-test", metavar="DIR", default=None)
    ap.add_argument("--mock-min-free-gb", type=float, default=None, help="--mock-test 에서만: 메모리 기준을 바꿔 점검")
    ap.add_argument("--mock-stop-below-gb", type=float, default=None, help="--mock-test 에서만: 실행 중 멈춤 기준을 바꿔 점검")
    a = ap.parse_args()
    global MIN_FREE_GB, STOP_BELOW_GB
    if a.mock_stop_below_gb is not None:
        if not a.mock_test:
            raise SystemExit("--mock-stop-below-gb 는 --mock-test 와만 쓸 수 있다")
        STOP_BELOW_GB = a.mock_stop_below_gb
    if a.mock_min_free_gb is not None:
        if not a.mock_test:
            raise SystemExit("--mock-min-free-gb 는 --mock-test 와만 쓸 수 있다")
        MIN_FREE_GB = a.mock_min_free_gb
    runs_base = a.mock_test or RUNS
    memdir = os.path.join(a.mock_test, "memory_logs") if a.mock_test else MEMLOG_DIR
    os.makedirs(memdir, exist_ok=True)
    extra_common = (["--mock-llm", "--runs-base", runs_base, "--pages", "list:page_001,page_002,page_003,page_004,page_005,page_006"]
                    if a.mock_test else [])

    bad = frozen_changed()
    if bad:
        print(f"!!! 동결 확인 실패 (목록에 있는 항목이 바뀜/없음): {bad} → 멈춤", flush=True); return 5
    print("동결 확인 OK (freeze_manifest.csv 에 있는 항목 모두 일치; 동결 후 새로 추가된 파일은 대상 아님)", flush=True)

    if a.dry_run:
        print("남은 메모리:", memory(), f"(기준 {MIN_FREE_GB}GB 이상)", flush=True)
        print("테스트베드 서버 응답:", server_up(), flush=True)
        for run_id, cond, extra in SEQUENCE:
            print("명령:", " ".join(["run_experiment.py", "--run-id", run_id, "--condition", cond] + seq0.COMMON + extra),
                  "| 이미 있음" if os.path.exists(os.path.join(RUNS, run_id)) else "", flush=True)
        return 0

    srv = ensure_server()
    try:
        for run_id, cond, extra in SEQUENCE:
            run_dir = os.path.join(runs_base, run_id)
            mpath = os.path.join(memdir, f"{run_id}.jsonl")
            if os.path.exists(run_dir):
                print(f"[건너뜀] {run_id} 이미 있음", flush=True)
                s = seq0.run_summary(run_id) if not a.mock_test else None
            else:
                m = memlog(mpath, "pre_start_check", threshold_gb=MIN_FREE_GB)
                if m["avail_gb"] < MIN_FREE_GB:
                    print(f"!!! 남은 메모리 {m['avail_gb']}GB < {MIN_FREE_GB}GB → {run_id} 실행하지 않음 (연구자에게 보고)", flush=True)
                    return 4
                cmd = [sys.executable, "-W", "ignore", "experiments/revision/run_experiment.py",
                       "--run-id", run_id, "--condition", cond] + seq0.COMMON + extra + extra_common
                print(f"\n>>> 시작 {run_id}: {' '.join(cmd[3:])}", flush=True)
                stop, mem_abort = threading.Event(), threading.Event()
                proc = subprocess.Popen(cmd)
                t = threading.Thread(target=watch, args=(run_dir, mpath, stop, proc, mem_abort), daemon=True)
                t.start()
                try:
                    rc = proc.wait()
                finally:
                    stop.set(); t.join(timeout=10)
                    n = sum(1 for _ in open(os.path.join(run_dir, "calls.jsonl"), encoding="utf-8")) \
                        if os.path.exists(os.path.join(run_dir, "calls.jsonl")) else 0
                    memlog(mpath, "run_end", records=n)
                if mem_abort.is_set():
                    print(f"!!! {run_id}: 실행 중 남은 메모리 {STOP_BELOW_GB}GB 미만 → 러너를 멈춤 (rc={rc}). "
                          f"run 폴더는 잠그거나 aborted 로 표시하지 않고 그대로 보존. 연구자 결정 대기", flush=True)
                    return 6
                if a.mock_test:
                    print(f"[mock] {run_id} rc={rc}, verify={lw.verify_run(run_dir)}", flush=True)
                    continue
                s = seq0.run_summary(run_id)
                bad = lw.verify_run(run_dir)
                print(f"{run_id} 잠금 확인: {'OK' if not bad else bad}", flush=True)
                if rc != 0 or s["aborted"]:
                    print(f"!!! {run_id} 중단 (rc={rc}): {s['abort_reason']} → 순서 실행 멈춤", flush=True)
                    return 2
            if run_id == "E1-R3b" and s is not None:
                if s["error_rate"] > seq0.GATE_ERROR or s["parse_rate"] > seq0.GATE_PARSE:
                    print(f"!!! R3b 관문 불통과: 오류율 {s['error_rate']:.1%} (≤{seq0.GATE_ERROR:.0%}), "
                          f"파싱 실패 {s['parse_rate']:.1%} (≤{seq0.GATE_PARSE:.0%}) → 멈춤", flush=True)
                    return 3
                print(f"R3b 관문 통과: 오류율 {s['error_rate']:.1%}, 파싱 실패 {s['parse_rate']:.1%} → 계속", flush=True)
    finally:
        if srv is not None:
            srv.terminate(); srv.wait(timeout=10)
            print("테스트베드 서버 종료", flush=True)
    print("\n재개 순서 완료 (E1-R3b, E2-A1-3).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
