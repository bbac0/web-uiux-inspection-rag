"""
E9 결정적 정규식 규칙 (docs/e9_design.md §6.1 그대로, `exp-freeze-e9-v1` 동결 대상). API 호출 없음.

- 이슈 텍스트 = description(파이프라인이 붙인 "[URL]" 접두어 제거) + 공백 1칸 + suggestion.
- 정규식은 대소문자 무시. 공백 허용은 §6.1 패턴에 적힌 `\\s*` 그대로다.
- 이슈 단위로 판정하고, 유형별로 조건을 만족하는 이슈가 1건 이상이면 그 페이지에서 그 유형을 탐지한 것으로 본다.
- E9-1 의 '주입된 변형 문구(정확 문자열)' 절은 **그 페이지에 실제로 주입된 문구**로 해석한다(§6.1 문구 그대로).
  E9-1 결함 페이지가 아니면 이 절은 적용되지 않고(주입 문구 없음), 규정 문구 인용 절과 주제어 절만 적용된다.
  정확 문자열 비교는 공백을 정규화하지 않는다(E9-1b 는 띄어쓰기만 다르므로).
"""
import re

REQUIRED_BANNER = "이 누리집은 대한민국 공식 전자정부 누리집입니다"
F = re.I

E9_1_TOPIC = re.compile(r"(공식\s*배너|배너)", F)
E9_1_ASPECT = re.compile(r"(문구|텍스트|문장|내용|띄어쓰기)", F)
E9_2_REGION = re.compile(r"(공식\s*배너|배너|헤더|header|푸터|footer)", F)
E9_2_PROP = re.compile(r"(px|글자\s*크기|글씨\s*크기|font-size|굵기|font-weight|색상|color|#[0-9a-f]{6}|높이|height|padding)", F)
E9_3_A = re.compile(r"(signup|회원\s*가입)", F)
E9_3_B = re.compile(r"로그인", F)
E9_4_A = re.compile(r"로그인", F)
E9_4_B = re.compile(r"(숨|감춰|display\s*:\s*none|보이지\s*않|사라)", F)
E9_4_C = re.compile(r"(768|모바일|작은\s*화면|좁은\s*화면|화면\s*너비|media)", F)
URL_PREFIX_RE = re.compile(r"^\s*\[(?:https?|file)://[^\]]*\]\s*")
TYPES = ("E9-1", "E9-2", "E9-3", "E9-4")


def issue_text(issue):
    desc = URL_PREFIX_RE.sub("", issue.get("description") or "", count=1).strip()
    return desc + " " + (issue.get("suggestion") or "").strip()


def match_issue(issue, injected_banner_text=None):
    """이슈 1건 → {유형: bool}. injected_banner_text: 그 페이지가 E9-1 결함 페이지일 때 주입된 배너 문구(아니면 None)."""
    t = issue_text(issue)
    e91 = bool(E9_1_TOPIC.search(t) and E9_1_ASPECT.search(t)) or REQUIRED_BANNER in t \
        or (bool(injected_banner_text) and injected_banner_text.rstrip(".") in t)
    return {"E9-1": e91,
            "E9-2": bool(E9_2_REGION.search(t) and E9_2_PROP.search(t)),
            "E9-3": bool(E9_3_A.search(t) and E9_3_B.search(t)),
            "E9-4": bool(E9_4_A.search(t) and E9_4_B.search(t) and E9_4_C.search(t))}


def page_detections(issues, injected_banner_text=None):
    """대상 페이지 이슈 목록 → {유형: 0/1} (유형별 1건 이상이면 1)."""
    out = {k: 0 for k in TYPES}
    for i in issues:
        for k, v in match_issue(i, injected_banner_text).items():
            out[k] |= int(v)
    return out
