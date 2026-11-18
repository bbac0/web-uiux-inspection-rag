"""
exp-freeze-v1 동결 대상의 SHA-256 목록 (v5 에서 채점기·라벨·E3/E9 입력 추가) → results/revision/freeze_manifest.csv
파일 해시와 함께 '내용' 해시(프롬프트 템플릿, 키워드 사전, 채점 프롬프트)를 따로 남겨, 파일의 다른 부분이 바뀌어도
동결 대상 자체가 그대로인지 확인할 수 있게 한다.

  python experiments/revision/freeze_manifest.py            # 작성
  python experiments/revision/freeze_manifest.py --check    # 현재 상태가 목록과 같은지 확인 (다르면 종료 코드 1)
"""
import ast, csv, glob, hashlib, importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "results/revision/freeze_manifest.csv"

FILES = (["services/analyzer.py", "services/exp_config.py", "services/llm_wrapper.py", "services/indexer.py", "cli.py",
          "experiments/evaluate_performance_v5.py", "experiments/semantic_issue_classifier.py",
          "experiments/generate_200_testbed.py", "testbed_200/dataset_metadata.json",
          "results/revision/analysis_plan.md", "results/revision/testbed_manifest.csv",
          "results/revision/oracle_chunks.csv", "data/gov_guide.pdf", "data/gov_check.pdf",
          # exp-freeze-v5 추가: 채점기, 라벨, E3/E9 입력, 사람 평가 지침
          "scoring/grader_config.json", "results/revision/ground_truth.csv",
          "results/revision/guideline_grounding_decisions.csv", "results/revision/fixed_long_selection.json",
          "results/revision/fixed_query_embedding/ranking.csv", "docs/rater_guidelines.md"]
         + sorted(p.replace("\\", "/") for p in glob.glob("scoring/*.py"))
         + sorted(glob.glob("experiments/revision/*.py")) + sorted(glob.glob("testbed_200/page_*.html"))
         + sorted(p.replace("\\", "/") for p in glob.glob("services/chroma_db/**/*", recursive=True) if os.path.isfile(p)))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, rel)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def prompt_template_source():
    tree = ast.parse(open("services/analyzer.py", encoding="utf-8").read())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_analyze_impl")
    node = next(n for n in ast.walk(fn) if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "prompt")
    return ast.unparse(node.value)


def rows():
    out = [{"kind": "file", "name": f, "sha256": sha(open(f, "rb").read())} for f in FILES if os.path.exists(f)]
    kw = load("kw", "experiments/evaluate_performance_v5.py")
    sem = load("sem", "experiments/semantic_issue_classifier.py")
    out += [
        {"kind": "content", "name": "production_prompt_template (analyzer._analyze_impl prompt f-string, ast.unparse)",
         "sha256": sha(prompt_template_source().encode("utf-8"))},
        {"kind": "content", "name": "keyword_dictionary (CATEGORY_PHRASES, json sorted)",
         "sha256": sha(json.dumps(kw.CATEGORY_PHRASES, ensure_ascii=False, sort_keys=True).encode("utf-8"))},
        {"kind": "content", "name": "semantic_judge_prompt (semantic_issue_classifier.JUDGE_PROMPT v1)",
         "sha256": sha(sem.JUDGE_PROMPT.encode("utf-8"))},
    ]
    return out


def main():
    cur = rows()
    if "--check" in sys.argv:
        with open(OUT, encoding="utf-8") as f:
            old = {(r["kind"], r["name"]): r["sha256"] for r in csv.DictReader(f)}
        bad = [r["name"] for r in cur if old.get((r["kind"], r["name"])) != r["sha256"]
               and r["name"] != OUT]
        missing = [n for (k, n) in old if not any(r["name"] == n for r in cur)]
        print("OK" if not bad and not missing else f"CHANGED: {bad} MISSING: {missing}")
        return 1 if bad or missing else 0
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["kind", "name", "sha256"]); w.writeheader(); w.writerows(cur)
    print(f"{OUT}: {len(cur)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
