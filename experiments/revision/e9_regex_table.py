"""
E9 결정적 정규식 채점 표: 주 지표(scoring/e9_rules.py)와 보조 분석(scoring/e9_rules_aux.py, E9-1 변형 문구 전체 적용)을
같은 표에 나란히 낸다 (analysis_plan_e9.md 3.1, 3.1a). API 호출 없음.

  python experiments/revision/e9_regex_table.py [--runs-base results/revision/runs_e9] [--testbed main|pilot] [--out DIR]

- 대상 run: runs-base 아래 run 폴더 전부(run_meta.json 의 condition 별로 묶음). 대상 페이지 이슈 = description 의 [URL] 접두어가
  그 페이지(`/{page_id}.html`)인 이슈. 실패 페이지는 미탐지(0)로 둔다(본 실험 2절 규칙과 같음).
- 출력(조건 × run × 유형 × 규칙): 결함 페이지 수, 탐지 수, 재현율, 대조군 수, 대조군 탐지 수, 대조군 위양성률.
  유형 행: E9-1(전체), E9-1a, E9-1b, E9-2, E9-3, E9-4(보조; 주 지표 아님).
출력 파일: {out}/e9_regex_primary_vs_aux.csv, .md
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import e9_rules as primary      # noqa: E402
from scoring import e9_rules_aux as aux      # noqa: E402

META = {"main": "testbed_e9/dataset_metadata_e9.json", "pilot": "testbed_e9_pilot/dataset_metadata_e9_pilot.json"}
ROWS = [("E9-1", lambda p: p["defect_id"] == "E9-1"), ("E9-1a", lambda p: p["subtype"] == "E9-1a"),
        ("E9-1b", lambda p: p["subtype"] == "E9-1b"), ("E9-2", lambda p: p["defect_id"] == "E9-2"),
        ("E9-3", lambda p: p["defect_id"] == "E9-3"), ("E9-4", lambda p: p["defect_id"] == "E9-4")]


def target_issues(report, page_id):
    marker = f"/{page_id}.html"
    out = []
    for i in (report or {}).get("issues", []) or []:
        if isinstance(i, dict) and marker in (i.get("description") or "").split("]")[0]:
            out.append(i)
    return out


def score_run(run_dir, pages):
    reps = {}
    for l in open(os.path.join(run_dir, "reports.jsonl"), encoding="utf-8"):
        r = json.loads(l)
        reps[r["page_id"]] = r
    det = {}
    for pid, p in pages.items():
        r = reps.get(pid)
        iss = target_issues(r.get("report") if r and r["status"] == "ok" else None, pid)
        inj = p["injected_string"] if p["defect_id"] == "E9-1" else None
        det[pid] = {"primary": primary.page_detections(iss, inj), "aux": aux.page_detections(iss)}
    return det


def table_rows(cond, rid, det, pages):
    out = []
    controls = [pid for pid, p in pages.items() if p["defect_id"] is None]
    for name, sel in ROWS:
        typ = name[:4]
        pos = [pid for pid, p in pages.items() if sel(p)]
        for rule in ("primary", "aux"):
            tp = sum(det[pid][rule][typ] for pid in pos)
            fp = sum(det[pid][rule][typ] for pid in controls)
            out.append({"condition": cond, "run": rid, "type": name, "rule": rule,
                        "rule_desc": "page-specific injected variant (primary)" if rule == "primary"
                        else "all 6 variants on every page (auxiliary)",
                        "defect_pages": len(pos), "detected": tp, "recall": f"{tp / len(pos):.3f}" if pos else "",
                        "controls": len(controls), "control_detected": fp,
                        "control_fpr": f"{fp / len(controls):.3f}" if controls else "",
                        "main_metric": "no (auxiliary E9-4)" if typ == "E9-4" else "yes"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-base", default="results/revision/runs_e9")
    ap.add_argument("--testbed", choices=["main", "pilot"], default="main")
    ap.add_argument("--out", default="results/revision/e9/tables")
    a = ap.parse_args(argv)
    pages = {p["page_id"]: p for p in json.load(open(META[a.testbed], encoding="utf-8"))["pages"]}
    rows = []
    for rid in sorted(os.listdir(a.runs_base)) if os.path.isdir(a.runs_base) else []:
        d = os.path.join(a.runs_base, rid)
        if not os.path.exists(os.path.join(d, "reports.jsonl")):
            continue
        cond = json.load(open(os.path.join(d, "run_meta.json"), encoding="utf-8"))["condition"]
        rows += table_rows(cond, rid, score_run(d, pages), pages)
    if not rows:
        print("no runs found"); return 1
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "e9_regex_primary_vs_aux.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    L = ["| 조건 | run | 유형 | 규칙 | 탐지/결함 | 재현율 | 대조군 탐지/대조군 | 위양성률 |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['condition']} | {r['run']} | {r['type']} | {r['rule']} | {r['detected']}/{r['defect_pages']} | "
                 f"{r['recall']} | {r['control_detected']}/{r['controls']} | {r['control_fpr']} |")
    open(os.path.join(a.out, "e9_regex_primary_vs_aux.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"{len(rows)} rows → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
