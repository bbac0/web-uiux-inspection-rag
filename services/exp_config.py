"""
실험 조건 설정. 모든 필드의 기본값은 기존 프로덕션 동작과 같다.
(ExperimentConfig() 를 넘기는 것과 config 를 넘기지 않는 것은 같은 프롬프트·입력을 만든다.)

동결 대상 (exp-freeze-v1): 프롬프트 문구, 모델, temperature, 청크 설정, 고정 질의, 뷰포트, HTML 5,000자 제한은
여기서 바꿀 수 없다. 조건 변경은 아래 플래그로만 한다.
"""

from dataclasses import dataclass, field
from typing import Optional

# --- 동결된 프로덕션 상수 (analyzer.py 와 테스트로 일치 확인) ---
MODEL_NAME = "models/gemini-2.5-flash"
TEMPERATURE = 0.0
RAG_QUERY = "웹 UI/UX 표준 가이드라인 공통 규정"
RAG_K = 4
HTML_CHAR_LIMIT = 5000
DEFAULT_VIEWPORT = (1280, 800)
MOBILE_VIEWPORT = (390, 844)
DEFAULT_CHROMA_PATH = "./chroma_db"
DEFAULT_MAX_PAGES = 5            # 기존 크롤러: 시작 페이지 + 링크 최대 4개

MODALITIES = ("both", "html", "screenshot")
QUERY_MODES = ("fixed", "page", "oracle")


@dataclass
class ExperimentConfig:
    run_id: Optional[str] = None            # None 이면 로깅하지 않음 (프로덕션)
    condition: str = "production"
    max_pages: int = DEFAULT_MAX_PAGES
    rag: bool = True                        # False = --no-rag (가이드라인 섹션 제목은 두고 내용만 비움)
    modality: str = "both"
    viewport: tuple = DEFAULT_VIEWPORT
    query_mode: str = "fixed"
    oracle_chunks: dict = field(default_factory=dict)   # page_id -> [chunk_id, ...]
    chroma_path: str = DEFAULT_CHROMA_PATH
    prompt_date: Optional[str] = None       # "YYYY-MM-DD"; None 이면 실행 당일 (프로덕션)
    concurrency: Optional[int] = None       # 한 사이트 안의 페이지 동시 분석 수; None = 제한 없음 (프로덕션)
    require_rag_chunks: bool = False        # True: RAG 켜짐 + 0청크 → 오류 (실험 러너는 항상 True)
    max_retries: int = 3                    # 재시도 횟수 (시도는 최대 max_retries+1 회). 프로덕션과 같음
    logger: object = None                   # services.llm_wrapper.RunLogger
    page_id: Optional[str] = None
    template_id: Optional[str] = None
    shots_dir: Optional[str] = None         # 지정하면 스크린샷을 보존

    def validate(self):
        if self.modality not in MODALITIES:
            raise ValueError(f"modality must be one of {MODALITIES}")
        if self.query_mode not in QUERY_MODES:
            raise ValueError(f"query_mode must be one of {QUERY_MODES}")
        if self.max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        if self.query_mode == "oracle" and not self.rag:
            raise ValueError("oracle query mode requires RAG enabled")
        if self.prompt_date is not None:
            import datetime
            datetime.date.fromisoformat(self.prompt_date)
        return self


def prompt_today(prompt_date: Optional[str]) -> str:
    """프롬프트에 들어가는 날짜 문자열. 형식은 프로덕션과 같다 ('%Y년 %m월 %d일')."""
    import datetime
    d = datetime.date.fromisoformat(prompt_date) if prompt_date else datetime.datetime.now()
    return d.strftime("%Y년 %m월 %d일")
