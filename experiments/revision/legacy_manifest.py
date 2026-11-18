"""
기존 run2 결과 사본의 SHA-256 목록 (읽기 전용 참조, 이동·수정하지 않음).
  paper_results/run2/   (git 추적, 논문 보관본)
  results_run2/, results/ 의 report_page_*.json, run_manifest.json  (작업 폴더 사본, git 무시 대상)
출력: results/revision/legacy_run2_manifest.csv  (파일명별로 세 위치의 해시와 일치 여부)
"""
import csv, glob, hashlib, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
LOCS = ["paper_results/run2", "results_run2", "results"]
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
names = sorted({os.path.basename(p) for loc in LOCS for p in glob.glob(f"{loc}/report_page_*.json") + glob.glob(f"{loc}/run_manifest.json")})
rows = []
for n in names:
    r = {"file": n}
    for loc in LOCS:
        p = os.path.join(loc, n)
        r[loc] = h(p) if os.path.exists(p) else ""
    present = [r[l] for l in LOCS if r[l]]
    r["all_present_identical"] = int(len(present) == len(LOCS) and len(set(present)) == 1)
    rows.append(r)
os.makedirs("results/revision", exist_ok=True)
with open("results/revision/legacy_run2_manifest.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["file"] + LOCS + ["all_present_identical"]); w.writeheader(); w.writerows(rows)
run2 = [r for r in rows if r["paper_results/run2"]]
print(f"files {len(rows)}; in paper_results/run2 {len(run2)}; identical in all 3 locations {sum(r['all_present_identical'] for r in rows)}")
print("not in paper_results/run2:", [r["file"] for r in rows if not r["paper_results/run2"]])
print("run2 files differing elsewhere:", [r["file"] for r in run2 if not r["all_present_identical"]])
