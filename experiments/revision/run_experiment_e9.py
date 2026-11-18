"""
E9 러너 (2026-11-13). 동결된 `experiments/revision/run_experiment.py` 를 **수정하지 않고** import 해서 쓴다.

동결 러너는 페이지 메타데이터를 `testbed_200/dataset_metadata.json` 에서만 읽는다(`load_meta`). 이 파일은 러너 모듈의
`load_meta` 를 E9 메타데이터를 읽는 함수로 바꿔 끼우고(같은 반환 형식), `env_info` 에 E9 테스트베드 정보(경로, 메타데이터 SHA-256,
E9 동결 태그 커밋)를 덧붙인 뒤 러너의 `main` 을 그대로 호출한다. 분석 경로(프롬프트, 모델, 설정, RAG, 로깅, 잠금)는 동결 러너와 같다.

  python experiments/revision/run_experiment_e9.py --testbed main|pilot --run-id E9-R1-related --condition E9-related-clause \
      --pages all --max-pages 1 --chroma-path services/chroma_db --prompt-date 2026-11-11 --concurrency 2 \
      --query-mode oracle --oracle-chunks results/revision/e9/e9_related_clause_chunks.csv

- --testbed main  → testbed_e9/       (서버: python -m http.server 8090 --bind 127.0.0.1 --directory testbed_e9),       기본 --base-url http://localhost:8090
- --testbed pilot → testbed_e9_pilot/ (서버: python -m http.server 8091 --bind 127.0.0.1 --directory testbed_e9_pilot), 기본 --base-url http://localhost:8091
- 기본 --runs-base: results/revision/runs_e9 (main), results/revision/runs_e9_pilot (pilot). testbed_200 run 과 섞이지 않는다.
나머지 인자는 동결 러너와 같다(--no-rag, --query-mode, --oracle-chunks, --viewport-extra, --mock-llm 등).
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import run_experiment as rx   # noqa: E402  (동결 러너, 수정하지 않음)

TESTBEDS = {"main": {"dir": "testbed_e9", "port": 8090, "runs": os.path.join("results", "revision", "runs_e9")},
            "pilot": {"dir": "testbed_e9_pilot", "port": 8091, "runs": os.path.join("results", "revision", "runs_e9_pilot")}}


def e9_meta_path(tb):
    name = "dataset_metadata_e9.json" if tb == "main" else "dataset_metadata_e9_pilot.json"
    return os.path.join(TESTBEDS[tb]["dir"], name)


def make_load_meta(tb):
    """동결 러너 load_meta 와 같은 형식: {page_id: {"page_id": "x.html", "base_template", "has_defect", "defects": [{"type"}]}}"""
    def load_meta():
        doc = json.load(open(e9_meta_path(tb), encoding="utf-8"))
        out = {}
        for p in doc["pages"]:
            d = p["defect_id"]
            out[p["page_id"]] = {"page_id": p["page_id"] + ".html", "base_template": p["body_template"],
                                 "has_defect": d is not None,
                                 "defects": ([{"type": d, "subtype": p["subtype"], "intensity": p["intensity"]}] if d else [])}
        return out
    return load_meta


def make_env_info(tb, orig):
    def env_info():
        e = orig()
        mp = e9_meta_path(tb)
        tag = subprocess.run(["git", "rev-list", "-n", "1", "exp-freeze-e9-v1"], capture_output=True, text=True).stdout.strip()
        e["e9"] = {"runner": "experiments/revision/run_experiment_e9.py", "testbed": tb, "testbed_dir": TESTBEDS[tb]["dir"],
                   "metadata_path": mp, "metadata_sha256": hashlib.sha256(open(mp, "rb").read()).hexdigest(),
                   "freeze_tag_e9_commit": tag or None}
        return e
    return env_info


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    tb = "main"
    if "--testbed" in argv:
        i = argv.index("--testbed")
        tb = argv[i + 1]
        del argv[i:i + 2]
    if tb not in TESTBEDS:
        raise SystemExit("--testbed must be main or pilot")
    if "--base-url" not in argv:
        argv += ["--base-url", f"http://localhost:{TESTBEDS[tb]['port']}"]
    if "--runs-base" not in argv:
        argv += ["--runs-base", TESTBEDS[tb]["runs"]]
    rx.load_meta = make_load_meta(tb)
    rx.env_info = make_env_info(tb, rx.env_info)
    return rx.main(argv)


if __name__ == "__main__":
    sys.exit(main())
