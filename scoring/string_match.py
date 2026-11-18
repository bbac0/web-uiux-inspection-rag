"""
결정적 문자열 채점기 (string_match). API 호출 없음.

규칙 (한 줄, 결과를 보고 수정하지 않는다 — analysis_plan 사전 지정):
  이슈의 description 또는 suggestion 에 문자열 '접속하기' 가 포함되면 그 이슈는 표준 용어 위반(Standard Terminology Violation)을 탐지한 것으로 본다.

대소문자·공백 정규화, 부분 일치 확장, 다른 유형 판정은 하지 않는다. 다른 4개 유형에 대해서는 판정하지 않는다(None).
"""

RULE_STRING = "접속하기"
RULE_TYPE = "Standard Terminology Violation"
RULE_TEXT = "description 또는 suggestion 에 문자열 '접속하기' 가 포함되면 Standard Terminology Violation 탐지"


def match(issue):
    """이슈 dict → True/False (용어 위반 탐지 여부)."""
    d = issue.get("description") or ""
    s = issue.get("suggestion") or ""
    return (RULE_STRING in d) or (RULE_STRING in s)
