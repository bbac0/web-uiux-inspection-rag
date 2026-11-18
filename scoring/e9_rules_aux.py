"""
E9 보조 분석 규칙: E9-1 변형 문구 전체 적용 (analysis_plan_e9.md 3.1a, `exp-freeze-e9-v2`). API 호출 없음.

동결된 주 지표 규칙(`scoring/e9_rules.py`)은 수정하지 않고 import 한다. 차이는 E9-1 의 '주입된 변형 문구' 절 하나뿐이다:
주 지표는 그 페이지에 실제로 주입된 문구만 보지만, 이 보조 규칙은 6개 변형 문구(E9-1a 3, E9-1b 3)를 모든 페이지에 적용한다.
정확 문자열 비교(공백 정규화 없음), 끝 마침표는 빼고 비교(주 지표와 같음).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import e9_rules as primary                 # noqa: E402  (동결, 수정하지 않음)
from experiments.revision import e9_generate as gen      # noqa: E402  (E9_1A, E9_1B 변형 목록)

VARIANTS = tuple(t for _, t in gen.E9_1A + gen.E9_1B)
TYPES = primary.TYPES


def match_issue(issue):
    """이슈 1건 → {유형: bool}. 페이지 라벨 정보를 쓰지 않는다."""
    m = primary.match_issue(issue, injected_banner_text=None)
    t = primary.issue_text(issue)
    m["E9-1"] = m["E9-1"] or any(v.rstrip(".") in t for v in VARIANTS)
    return m


def page_detections(issues):
    out = {k: 0 for k in TYPES}
    for i in issues:
        for k, v in match_issue(i).items():
            out[k] |= int(v)
    return out
