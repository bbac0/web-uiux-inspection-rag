"""
API 호출 없이 파이프라인 전체(Playwright 수집 → 검색 → 프롬프트 → 로그 → 잠금)를 점검하기 위한 가짜 Gemini/벡터 DB.
실험 결과에는 절대 쓰지 않는다. 러너의 --mock-llm 과 단위 테스트에서만 사용한다.
"""

import json
from types import SimpleNamespace

from langchain_core.documents import Document


class FakeResponse:
    def __init__(self, text, prompt_tokens=1000, cand_tokens=200, thoughts=300, cached=0):
        self.text = text
        self.model_version = "mock-model-0"
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=prompt_tokens, cached_content_token_count=cached,
            candidates_token_count=cand_tokens,
            total_token_count=prompt_tokens + cand_tokens + thoughts + cached)


class FakeModel:
    fail_times = 0          # 테스트에서 일시적 오류 재시도를 흉내 낼 때 사용
    bad_json = False

    def __init__(self, model_name=None, generation_config=None):
        self.model_name = model_name

    def generate_content(self, inputs):
        if FakeModel.fail_times > 0:
            FakeModel.fail_times -= 1
            raise RuntimeError("429 rate limit (mock)")
        if FakeModel.bad_json:
            return FakeResponse("not json")
        body = {"status": "success", "total_checked_count": 30, "summary": "mock",
                "issues": [{"category": "디자인", "description": "mock issue", "suggestion": "mock",
                            "source_file": "gov_guide.pdf", "page_number": [1]}]}
        return FakeResponse(json.dumps(body, ensure_ascii=False))


class FakeEmbeddings:
    def embed_query(self, q):
        return [0.0] * 8


class FakeStore:
    def __init__(self, n=4):
        self.n = n
        self._embedding_function = FakeEmbeddings()

    def similarity_search_by_vector_with_relevance_scores(self, vec, k=4):
        return [(Document(page_content=f"chunk text {i}", metadata={"source": "x/gov_guide.pdf", "page": i},
                          id=f"mock-{i}"), 0.1 * (i + 1)) for i in range(min(k, self.n))]

    def similarity_search(self, q, k=4):
        return [d for d, _ in self.similarity_search_by_vector_with_relevance_scores(None, k)]

    def get(self, ids=None, include=None):
        return {"ids": list(ids), "documents": [f"oracle {i}" for i in ids],
                "metadatas": [{"source": "x/gov_check.pdf", "page": 0} for _ in ids]}


def install(analyzer_module, n_chunks=4):
    """analyzer 모듈의 genai 호출과 벡터 DB 를 가짜로 바꾼다."""
    g = analyzer_module.genai
    g.configure = lambda **kw: None
    g.upload_file = lambda path: SimpleNamespace(name="files/mock")
    g.delete_file = lambda name: None
    g.GenerativeModel = FakeModel
    analyzer_module.get_vector_store = lambda persist_directory="./chroma_db": FakeStore(n_chunks)
