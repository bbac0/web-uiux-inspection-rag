"""
조건별 프롬프트 변화를 results/revision/prompt_diffs/ 에 diff 로 저장한다 (API 호출 없음).
실제 analyzer 코드 경로로 프롬프트를 만들고(가짜 LLM 이 입력을 가로챔) 프로덕션 조건과 비교한다.
검색 컨텍스트는 자리표시 문자열로 바꿔 넣어 '문구' 차이만 보이게 한다.

  python experiments/revision/make_prompt_diffs.py
"""

import difflib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("GEMINI_API_KEY", "mock-not-a-key")

from langchain_core.documents import Document           # noqa: E402
from services import analyzer, exp_config as ec          # noqa: E402
from experiments.revision import mock_llm                # noqa: E402

OUT = os.path.join("results", "revision", "prompt_diffs")
SAMPLE_PAGE = "testbed_200/page_001.html"


class PlaceholderStore(mock_llm.FakeStore):
    def similarity_search_by_vector_with_relevance_scores(self, vec, k=4):
        return [(Document(page_content=f"<<검색 청크 {i + 1} 본문>>", metadata={"source": "gov_guide.pdf", "page": 0},
                          id=f"chunk-{i + 1}"), 0.0) for i in range(k)]

    def get(self, ids=None, include=None):
        return {"ids": list(ids), "documents": [f"<<oracle 청크 {i} 본문>>" for i in ids],
                "metadatas": [{"source": "gov_check.pdf", "page": 0} for _ in ids]}


def render(**kw):
    seen = []
    orig = mock_llm.FakeModel.generate_content
    mock_llm.FakeModel.generate_content = lambda self, inputs: (seen.append(inputs), orig(self, inputs))[1]
    try:
        cfg = ec.ExperimentConfig(prompt_date="2026-01-01", page_id="page_001", chroma_path="x", **kw).validate()
        html = open(SAMPLE_PAGE, encoding="utf-8").read()
        shot = os.path.join(OUT, "_tmp.png")
        open(shot, "wb").write(b"png")
        analyzer.analyze_with_gemini(html, shot, [], config=cfg, page_ctx={"url": "u", "signals": {
            "title": "정부24 메인", "headings": ["주요 서비스"], "buttons": ["신청하기"]}})
        os.remove(shot)
    finally:
        mock_llm.FakeModel.generate_content = orig
    inputs = seen[0]
    parts = ["<<IMAGE: 스크린샷 파일 (File API 업로드)>>" if not isinstance(x, str) else x for x in inputs]
    return "\n<<-- 다음 입력 파트 -->>\n".join(parts)


def main():
    mock_llm.install(analyzer)
    analyzer.get_vector_store = lambda persist_directory="./chroma_db": PlaceholderStore()
    os.makedirs(OUT, exist_ok=True)
    base = render()
    conds = {
        "E2-A1_no-rag": dict(rag=False),
        "E2-A2_modality-html": dict(modality="html"),
        "E2-A3_modality-screenshot": dict(modality="screenshot"),
        "E3_query-page": dict(query_mode="page"),
        "E3_query-oracle": dict(query_mode="oracle", oracle_chunks={"page_001": ["<chunk_id_1>", "<chunk_id_2>"]}),
        "E4_viewport-mobile": dict(viewport=ec.MOBILE_VIEWPORT),
    }
    with open(os.path.join(OUT, "production_prompt_sample.txt"), "w", encoding="utf-8") as f:
        f.write(base)
    index = ["# 조건별 프롬프트/입력 diff", "",
             f"기준: 프로덕션 조건 (RAG fixed, 스크린샷+HTML, 1280x800), 예시 페이지 `{SAMPLE_PAGE}`, 프롬프트 날짜 2026-01-01(예시).",
             "검색 청크 본문은 자리표시 문자열이다. 이미지 입력은 `<<IMAGE ...>>` 로 표시했다.", "",
             "| 조건 | 바뀐 줄 수 | 파일 |", "|---|---:|---|"]
    for name, kw in conds.items():
        other = render(**kw)
        diff = list(difflib.unified_diff(base.splitlines(), other.splitlines(),
                                         "production", name, lineterm=""))
        with open(os.path.join(OUT, f"{name}.diff"), "w", encoding="utf-8") as f:
            f.write("\n".join(diff) + ("\n" if diff else "(차이 없음: 프롬프트 문구와 입력 구성이 프로덕션과 같다. "
                                                        "바뀌는 것은 뷰포트로 찍은 스크린샷과 렌더링 DOM 뿐이다.)\n"))
        n = sum(1 for l in diff if l[:1] in "+-" and not l.startswith(("+++", "---")))
        index.append(f"| {name} | {n} | `{name}.diff` |")
    index += ["", "참고: E3 page/oracle 은 프롬프트 문구가 아니라 가이드라인 섹션에 들어가는 검색 결과만 바뀐다. "
              "실제 청크 본문은 run 로그의 청크 ID 로 추적한다."]
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index) + "\n")
    print("\n".join(index))


if __name__ == "__main__":
    main()
