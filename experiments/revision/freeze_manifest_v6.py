"""
exp-freeze-v6-semretry 동결 목록 (API 호출 없음).

v5 목록(results/revision/freeze_manifest.csv, 동결)의 모든 항목을 현재 상태와 대조하고(바뀐 것이 있으면 종료 코드 1),
v5 의 파일 범위(scoring/*.py, experiments/revision/*.py, services/chroma_db/**, testbed_200/page_*.html)에 새로 생긴 파일과
재채점 관련 새 파일을 '추가'로 더해 results/revision/freeze_manifest_v6.csv 를 쓴다.

  python experiments/revision/freeze_manifest_v6.py            # 대조 + 작성 (v5 항목이 바뀌었으면 쓰지 않고 종료 코드 1)
  python experiments/revision/freeze_manifest_v6.py --check    # 현재 상태가 v6 목록과 같은지 (다르면 종료 코드 1)
"""
import csv
import glob
import hashlib
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
V5 = "results/revision/freeze_manifest.csv"
OUT = "results/revision/freeze_manifest_v6.csv"
EXPLICIT = ["scoring/grader_config_retry800.json", "results/revision/analysis_plan_addendum_semantic_retry.md",
            "results/revision/semantic_truncation_targets.csv", "tests/test_semantic_grader_retry.py",
            "docs/semantic_truncation_retry_plan.md"]


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def norm(p):
    return p.replace("\\", "/")


def v5_tool():
    spec = importlib.util.spec_from_file_location("fm5", "experiments/revision/freeze_manifest.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def compare_v5():
    old = list(csv.DictReader(open(V5, encoding="utf-8")))
    cur_content = {r["name"]: r["sha256"] for r in v5_tool().rows() if r["kind"] == "content"}
    changed, missing = [], []
    for r in old:
        if r["kind"] == "file":
            if not os.path.exists(r["name"]):
                missing.append(r["name"]); continue
            if sha_file(r["name"]) != r["sha256"]:
                changed.append(r["name"])
        elif cur_content.get(r["name"]) != r["sha256"]:
            changed.append(r["name"])
    return old, changed, missing


def added_files(old):
    known = {norm(r["name"]) for r in old if r["kind"] == "file"}
    scope = (glob.glob("scoring/*.py") + glob.glob("experiments/revision/*.py") + glob.glob("testbed_200/page_*.html")
             + [p for p in glob.glob("services/chroma_db/**/*", recursive=True) if os.path.isfile(p)])
    out = sorted({norm(p) for p in scope} - known)
    for p in EXPLICIT:
        if p not in out and p not in known:
            out.append(p)
    return out


def rows():
    old, changed, missing = compare_v5()
    add = added_files(old)
    r = [{"kind": o["kind"], "name": o["name"], "sha256": o["sha256"], "status": "v5"} for o in old]
    r += [{"kind": "file", "name": p, "sha256": sha_file(p), "status": "added_v6"} for p in add]
    return r, changed, missing, add


def main():
    if "--check" in sys.argv:
        cur, changed, missing, _ = rows()
        saved = {(x["kind"], x["name"]): x["sha256"] for x in csv.DictReader(open(OUT, encoding="utf-8"))}
        bad = [x["name"] for x in cur if x["status"] == "added_v6" and saved.get((x["kind"], x["name"])) != x["sha256"]]
        bad += changed + missing
        print("OK" if not bad else f"CHANGED: {bad}")
        return 1 if bad else 0
    cur, changed, missing, add = rows()
    if changed or missing:
        print(f"!!! v5 entries changed: {changed} missing: {missing} -> not writing {OUT}")
        return 1
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["kind", "name", "sha256", "status"]); w.writeheader(); w.writerows(cur)
    print(f"{OUT}: {len(cur)} entries (v5 {len(cur) - len(add)} unchanged, added {len(add)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
