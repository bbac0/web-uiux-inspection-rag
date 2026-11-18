"""
exp-freeze-e9-v1/v2/v3 동결 대상의 SHA-256 목록 → results/revision/e9/freeze_manifest_e9.csv (API 호출 없음).

  python experiments/revision/freeze_manifest_e9.py            # 작성
  python experiments/revision/freeze_manifest_e9.py --check    # 목록에 있는 항목이 모두 그대로인지 확인 (다르면 종료 코드 1)
"""
import csv
import glob
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "results/revision/e9/freeze_manifest_e9.csv"

GROUPS = {
    "generator": ["experiments/revision/e9_generate.py"],
    "verification": ["experiments/revision/e9_verify.py", "results/revision/e9/ground_truth_e9.csv",
                     "results/revision/e9/e9_verify_summary.json"],
    "testbed_hash_list": ["results/revision/e9/testbed_e9_manifest.csv", "testbed_e9/dataset_metadata_e9.json"],
    "testbed_files": sorted(p.replace("\\", "/") for p in glob.glob("testbed_e9/**/*", recursive=True) if os.path.isfile(p)),
    "condition_inputs": ["results/revision/e9/conditions_e9.json", "results/revision/e9/e9_related_clause_chunks.csv",
                         "results/revision/e9/e9_fixed_long_chunks.csv", "results/revision/fixed_long_selection.json",
                         "results/revision/fixed_query_embedding/ranking.csv", "results/revision/e9/e9_aux390_pages.txt"],
    "runner": ["experiments/revision/run_experiment_e9.py", "experiments/revision/run_experiment.py"],
    "judge_prompt": ["scoring/e9_judge_prompt.py", "docs/e9_judge_prompt_draft.md", "scoring/grader_config.json"],
    "deterministic_rules": ["scoring/e9_rules.py"],
    # exp-freeze-e9-v2 추가: 보조 분석(E9-1 변형 문구 전체 적용)과 주/보조 비교 표, 파일럿 세트(점검용, 분석 제외)
    "auxiliary_rules": ["scoring/e9_rules_aux.py", "experiments/revision/e9_regex_table.py"],
    "pilot": ["experiments/revision/e9_generate_pilot.py", "testbed_e9_pilot/dataset_metadata_e9_pilot.json",
              "results/revision/e9_pilot/ground_truth_e9.csv", "results/revision/e9_pilot/e9_verify_summary.json",
              "testbed_e9_pilot/flag.svg"]
             + sorted(p.replace("\\", "/") for p in glob.glob("testbed_e9_pilot/**/*.html", recursive=True)),
    "analysis_plan": ["results/revision/e9/analysis_plan_e9.md", "docs/e9_design.md"],
    "tests": ["tests/test_e9_freeze_items.py", "tests/test_e9_aux.py", "tests/test_e9_v3_strings.py"],
    # exp-freeze-e9-v3 추가: 목록 작성 도구 자체, 입력 수정안 문서
    "freeze_tool": ["experiments/revision/freeze_manifest_e9.py"],
    "input_fix_proposal": ["docs/e9_input_fix_proposal.md"],
}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def rows():
    out = []
    for g, files in GROUPS.items():
        for f in files:
            if f == "testbed_e9/dataset_metadata_e9.json" and g == "testbed_files":
                continue
            out.append({"group": g, "file": f, "sha256": sha(f)})
    return out


def main():
    cur = rows()
    if "--check" in sys.argv:
        old = {(r["group"], r["file"]): r["sha256"] for r in csv.DictReader(open(OUT, encoding="utf-8"))}
        bad = [f for (g, f), h in old.items() if not os.path.exists(f) or sha(f) != h]
        print("OK" if not bad else f"CHANGED: {bad}")
        return 1 if bad else 0
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["group", "file", "sha256"]); w.writeheader(); w.writerows(cur)
    print(f"{OUT}: {len(cur)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
