"""
E9 판정 프롬프트와 파싱 규칙 (보조 LLM 판정; docs/e9_judge_prompt_draft.md 의 승인된 전문 그대로, `exp-freeze-e9-v1` 동결 대상).

- PROMPT 는 문서의 ```text 블록과 문자 단위로 같다(tests/test_e9_freeze_items.py 가 확인).
- 입력: 이슈의 description(파이프라인 "[URL]" 접두어 제거)과 suggestion 만. suggestion 이 비면 "(없음)".
- 파싱(문서 '파싱 규칙' 그대로): text 블록만 읽고 JSON 객체 하나를 찾는다. 네 키의 값이 모두 "예"/"아니오"이고 none 이 불리언이어야 유효.
  none 이 네 값과 모순이면 파싱 실패. stop_reason=max_tokens 는 파싱 실패, refusal 은 라벨 refusal (호출 코드에서 처리).
- 채점 설정은 본 실험과 같다(scoring/grader_config.json: claude-sonnet-5-5, thinking between_tools, effort high, max_tokens 100).
"""
import json
import re

KEYS = ("banner_text", "style_spec", "login_destination", "login_small_screen")
PROMPT = '다음은 웹페이지 자동 검수 시스템이 보고한 결함 한 건의 설명문과 제안문입니다. 아래 네 가지 점검 항목 각각에 대해, 이 설명문과 제안문이 그 항목의 위반을 지적하는지 판단하세요. 지적하면 "예", 지적하지 않으면 "아니오"로 답하세요. 네 항목이 모두 "아니오"이면 none 을 true 로, 하나라도 "예"이면 false 로 답하세요.\n\n[점검 항목 — 디지털 정부서비스 UI/UX 가이드라인 점검 기준]\n- banner_text: 공식 배너의 텍스트를 변형하지 않고 있다. 공식 배너 텍스트의 내용과 띄어쓰기는 "이 누리집은 대한민국 공식 전자정부 누리집입니다."와 동일해야 한다. 텍스트를 임의로 변형하거나 띄어쓰기를 다르게 제공했다는 지적이면 "예".\n- style_spec: 공식 배너, 헤더, 푸터의 스타일을 변형하지 않고 있다. 글자 크기, 글자 굵기, 글자 색상, 배경 색상, 높이와 같은 스타일 값이 가이드라인에 정해진 값과 다르다는 지적이면 "예".\n- login_destination: 로그인 링크가 항상 \'로그인\' 화면으로 연결되고 있다. 로그인 링크를 눌렀을 때 로그인 화면이 아닌 다른 화면으로 이동한다는 지적이면 "예".\n- login_small_screen: 작은 화면 너비에서 로그인 링크를 숨기지 않고 있다. 가로 768px 이하의 작은 화면 너비에서 로그인 링크를 숨긴다는 지적이면 "예".\n\n[설명문]\n<<DESC>>\n\n[제안문]\n<<SUGG>>\n\nJSON으로만 답하세요: {"banner_text": "예 또는 아니오", "style_spec": "예 또는 아니오", "login_destination": "예 또는 아니오", "login_small_screen": "예 또는 아니오", "none": true 또는 false}'
URL_PREFIX_RE = re.compile(r"^\s*\[(?:https?|file)://[^\]]*\]\s*")


def build_prompt(issue):
    desc = URL_PREFIX_RE.sub("", issue.get("description") or "", count=1).strip()
    sugg = (issue.get("suggestion") or "").strip() or "(없음)"
    return PROMPT.replace("<<DESC>>", desc).replace("<<SUGG>>", sugg)


def parse(text):
    """→ (labels dict 또는 None, ok)."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None, False
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None, False
    if not isinstance(d, dict) or any(d.get(k) not in ("예", "아니오") for k in KEYS) or not isinstance(d.get("none"), bool):
        return None, False
    any_yes = any(d[k] == "예" for k in KEYS)
    if d["none"] == any_yes:          # 모순: 모두 아니오인데 none=false, 또는 예가 있는데 none=true
        return None, False
    return {k: d[k] == "예" for k in KEYS} | {"none": d["none"]}, True
