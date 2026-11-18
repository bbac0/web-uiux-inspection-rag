"""
라벨 3층 중 guideline_grounded 층 준비 (API 호출 없음, 원본 벡터 DB 의 sqlite 를 읽기 전용으로 사용).

guideline_grounded = "현재 색인된 문서(gov_guide.pdf, gov_check.pdf)에 그 결함을 위반으로 판정할 근거 조항이 있는가"
  - 유형 단위 판정. 용어 위반은 false (terminology_basis.py 결론).
  - 나머지 4개 유형은 근거 조항 후보를 표로 정리하고, 수치·규범이 명시적인 경우에만 candidate_true,
    애매하면 ambiguous, 조항이 없으면 false 로 둔다. 최종 판정(true/false)은 연구자가 정해
    results/revision/guideline_grounding_decisions.csv 의 decision 칸에 적는다 (이 스크립트는 그 칸을 덮어쓰지 않는다).

출력
  results/revision/guideline_grounding.md        유형별 근거 조항 표 (유형, 조항 요약, 청크 ID, 쪽, 명시성, 후보 판정) + 원문
  results/revision/guideline_grounding_decisions.csv   유형 | candidate | decision(연구자 입력, 비어 있으면 pending)
  results/revision/ground_truth.csv 에 열 추가 (기존 열은 그대로):
      guideline_grounded            유형 판정 (true / false / pending)
      guideline_grounded_candidate  candidate_true / ambiguous / false
      label_guideline_grounded      판정이 true 인 유형만 effective_1280 값, 그 밖에는 NA (이 층의 평가에서 제외)
      label_guideline_grounded_390  같은 규칙으로 effective_390 값 (E4 용)

  python experiments/revision/guideline_grounding.py
"""
import csv
import importlib.util
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "results/revision"
GT = os.path.join(OUT, "ground_truth.csv")
DEC = os.path.join(OUT, "guideline_grounding_decisions.csv")
spec = importlib.util.spec_from_file_location("oc", "experiments/revision/oracle_candidates.py")
oc = importlib.util.module_from_spec(spec); spec.loader.exec_module(oc)

TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]

# (유형, 청크 ID 앞 8자리, 찾을 문구(공백 제거 기준), 조항 요약, 명시성)
CLAUSES = [
    ("Poor Contrast Ratio", "ff7cefaf", "4.5:1(매직넘버:50)",
     "글자 색상은 명도 대비를 준수한다. 일반 텍스트 AA 4.5:1, 큰 텍스트 AA 3:1 (표)", "명시적: 수치 기준(4.5:1)과 '준수한다' 규범"),
    ("Poor Contrast Ratio", "0f817b6f", "매직넘버50㏂명도대비4.5:1",
     "매직넘버 40/50/70/90 = 명도 대비 3:1 / 4.5:1 / 7:1 / 15:1 로 색상 간 구분을 정의", "명시적: 수치 정의 (색상 체계 설명)"),
    ("Poor Contrast Ratio", "f6cfe97d", "명도대비를준수한다",
     "접근성을 고려한 대비율: 명도 대비를 준수한다", "규범 명시, 수치는 다른 쪽(122쪽)에 있음"),
    ("Mobile Layout Breakage", "4536a37e", "화면에가로스크롤이없음",
     "[첨부파일 점검] 화면에 가로 스크롤이 없음, 미준수: 작은 화면 너비에서 화면 자체에 가로 스크롤이 생성되는 경우 (근거: 모바일을 염두에 두고 디자인)",
     "애매: 기준은 명시적이지만 '첨부파일' 기본 패턴의 점검 항목 안에 있어 페이지 전체 일반 규칙인지 불분명"),
    ("Mobile Layout Breakage", "3b89f2be", "풀반응형그리드",
     "레이아웃: 화면 크기에 따라 콘텐츠 영역을 유지/축소하는 반응형 그리드", "애매: 설계 지침(서술), 위반 판정 기준 아님"),
    ("Mobile Layout Breakage", "4782b967", "Mobilesmall360px이상",
     "브레이크포인트: small 360px 이상, medium 768px 이상, large 1024px 이상", "애매: 수치는 있으나 넘침 금지 규범이 아님"),
    ("Mobile Layout Breakage", "27829051", "패널영역에별도의세로,가로스크롤이생성되어서는안된다",
     "[패널 컴포넌트] 패널 영역에 별도의 세로, 가로 스크롤이 생성되어서는 안 된다", "애매: 특정 컴포넌트 규칙"),
    ("Button Area Clipping", "33a944f1", "버튼을적절한크기로제공한다",
     "[버튼] 버튼을 적절한 크기로 제공한다. 마우스 17×17px, 터치 44×44px 이상 '권장' (KWCAG 2.2 조작 가능, WCAG Target Size AAA)",
     "애매: 수치 기준은 명시적이지만 '권장' 수준. 높이 2px·글자 크기 0 버튼은 어떤 수치로도 미달"),
    ("Button Area Clipping", "d777af5c", "<height>,<width>값이모두24px이상",
     "[부록 도구 활용] 타겟 사이즈: 계산된 height, width 가 모두 24px 이상인지 확인", "애매: 점검 도구 설명(부록), 버튼 컴포넌트 규칙과 직접 연결은 아님"),
    ("Button Area Clipping", "38dfc017", "브레드크럼경로중가장짧은항목의너비와높이가모두24px이상임을확인한다",
     "[브레드크럼 13 점검 절차] 브레드크럼 경로 중 가장 짧은 항목의 너비와 높이가 모두 24px 이상임을 확인한다 (근거: 브레드크럼 경로 링크 간 간격을 충분히 제공한다)",
     "브레드크럼 전용, 점검 절차 문장('확인한다'), 근거 문장은 규범형이나 수치 없음"),
    ("Button Area Clipping", "645124a6", "40*406pxButton",
     "[크기 토큰] Medium 40px: 주로 버튼, 인풋에 사용", "애매: 디자인 토큰 정의, 위반 판정 기준 아님"),
    ("Duplicate ID Markup Error", None, None,
     "id 값 중복 금지, 마크업 오류(파싱) 방지에 해당하는 조항 없음. 'id 속성'이 나오는 청크는 탭 컴포넌트의 aria-controls 연결 설명(gov_guide 457쪽)과 "
     "건너뛰기 링크 점검 방법(gov_check 84쪽)뿐이고, '오류 방지'(gov_guide 141쪽, 터치 오류)와 '중복되지'(gov_guide 291쪽, 스크린리더 정보 중복)는 무관",
     "조항 없음"),
    ("Standard Terminology Violation", None, None,
     "'로그인'을 표준 용어로 정하거나 '접속하기' 등 변형 표현을 금지하는 조항 없음 (oracle_candidates.md 맨 앞 요약, terminology_basis.py)",
     "조항 없음"),
]
CANDIDATE = {
    "Poor Contrast Ratio": "candidate_true",
    "Mobile Layout Breakage": "ambiguous",
    "Button Area Clipping": "ambiguous",
    "Duplicate ID Markup Error": "false",
    "Standard Terminology Violation": "false",
}
# 사전 규칙 (2026-11-12, 사용자 지정): true 조건 = (a) 색인된 문서에 규범형('~한다')으로 쓰인 명시적 조항이 있고,
# (b) 특정 컴포넌트에 한정되지 않은 일반 조항이며, (c) 주입된 결함이 그 조항을 명백히 위반한다. '권장' 수준은 해당하지 않는다.
RULE = ("true 조건: (a) 색인된 문서에 규범형('~한다')으로 쓰인 명시적 조항, (b) 특정 컴포넌트에 한정되지 않은 일반 조항, "
        "(c) 주입된 결함이 그 조항을 명백히 위반. '권장' 수준은 해당하지 않음.")
PROPOSED = {
    "Poor Contrast Ratio": "true",
    "Mobile Layout Breakage": "false",
    "Button Area Clipping": "false",
    "Duplicate ID Markup Error": "false",
    "Standard Terminology Violation": "false",
}
PROPOSED_REASON = {
    "Poor Contrast Ratio": "(a) gov_guide 122쪽 '이때 명도 대비를 준수하여 시각적 접근성을 확보한다' + 대비율 표(일반 텍스트 AA 4.5:1), "
                           "(b) 타이포그래피 '글자 색상' 일반 조항, (c) 주입값 1.26:1 은 4.5:1 에 명백히 미달.",
    "Mobile Layout Breakage": "(b) 불충족: '가로 스크롤 없음'은 첨부파일 패턴(gov_check 182쪽)·패널 컴포넌트(gov_guide 413쪽) 문맥에만 있고 페이지 전체 일반 조항이 없음.",
    "Button Area Clipping": "(a)·(b) 불충족: 수치 조항은 44×44px '권장'(gov_guide 520쪽), 24px 은 브레드크럼 전용 점검 절차(gov_check 98쪽)와 "
                            "부록 도구 사용법(269쪽)뿐. '버튼을 적절한 크기로 제공한다'(520쪽)는 규범형이지만 수치 기준이 '권장'이고 버튼 컴포넌트 조항.",
    "Duplicate ID Markup Error": "(a) 불충족: 근거 조항 없음.",
    "Standard Terminology Violation": "(a) 불충족: 근거 조항 없음 (gov_check 208쪽은 링크 목적지 규정).",
}
REASON = {
    "Poor Contrast Ratio": "일반 텍스트 4.5:1 수치 기준과 '명도 대비를 준수한다' 규범이 명시됨. 주입값 1.26:1 은 명백한 미달.",
    "Mobile Layout Breakage": "'가로 스크롤 없음' 기준은 첨부파일 패턴·패널 컴포넌트 같은 특정 문맥에만 명시되어 페이지 전체 규칙인지 애매.",
    "Button Area Clipping": "44×44px(터치)·17×17px(마우스) 수치가 있으나 '권장'. 24px 타겟 사이즈는 부록 점검 방법. 규범 강도가 애매.",
    "Duplicate ID Markup Error": "색인된 두 문서에 근거 조항 없음.",
    "Standard Terminology Violation": "색인된 두 문서에 근거 조항 없음 (사용자 지시로 false 고정).",
}


def ctx(c, phrase, before=150, after=250):
    n, idx = oc.norm_with_map(c["text"])
    p = n.find(phrase.lower())
    if p < 0:
        return re.sub(r"\s+", " ", c["text"][:400]).strip() + " …(문구 위치 미확인)"
    return re.sub(r"\s+", " ", c["text"][max(0, idx[p] - before): idx[min(len(idx) - 1, p + len(phrase))] + after]).strip()


def read_decisions():
    if not os.path.exists(DEC):
        return {}
    return {r["defect_type"]: (r.get("decision") or "").strip().lower() for r in csv.DictReader(open(DEC, encoding="utf-8"))}


def read_decision_meta():
    """연구자가 적은 decided_by / decided_on / memo 를 보존한다."""
    if not os.path.exists(DEC):
        return {}
    return {r["defect_type"]: {k: r.get(k, "") for k in ("decided_by", "decided_on", "memo")}
            for r in csv.DictReader(open(DEC, encoding="utf-8"))}


def main():
    chunks = {c["id"][:8]: c for c in oc.load_chunks()}
    old = read_decisions()
    meta_old = read_decision_meta()
    dec = {}
    for t in TYPES:
        if t == "Standard Terminology Violation":
            dec[t] = "false"                                   # 사용자 지시
        else:
            dec[t] = old.get(t) if old.get(t) in ("true", "false") else ""
    with open(DEC, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["defect_type", "candidate", "proposed", "proposed_reason", "decision", "decided_by", "decided_on",
                    "memo", "reason", "rule"])
        for t in TYPES:
            m = meta_old.get(t, {})
            w.writerow([t, CANDIDATE[t], PROPOSED[t], PROPOSED_REASON[t], dec[t], m.get("decided_by", ""),
                        m.get("decided_on", ""), m.get("memo", ""), REASON[t], RULE])

    L = ["# guideline_grounded 층: 유형별 근거 조항", "",
         "정의: 현재 색인된 문서(gov_guide.pdf, gov_check.pdf)에 그 결함을 위반으로 판정할 근거 조항이 있는가 (유형 단위).",
         "후보 판정은 수치 또는 규범이 명시적인 경우에만 `candidate_true`, 판단이 애매하면 `ambiguous`, 조항이 없으면 `false`.",
         "최종 판정은 연구자가 `guideline_grounding_decisions.csv` 의 decision 칸(true/false)에 적는다. 비어 있으면 pending.", "",
         "## 사전 규칙에 따른 제안 (proposed)", "", f"규칙: {RULE}", "",
         "| 유형 | 제안(proposed) | 규칙 적용 근거 | 현재 결정 |", "|---|---|---|---|"]
    for t in TYPES:
        L.append(f"| {t} | `{PROPOSED[t]}` | {PROPOSED_REASON[t]} | {dec[t] or 'pending'} |")
    L += ["", "## 이전 단계의 후보 판정 (참고)", "", "| 유형 | 후보 판정 | 이유 |", "|---|---|---|"]
    for t in TYPES:
        L.append(f"| {t} | `{CANDIDATE[t]}` | {REASON[t]} |")
    L += ["", "## 근거 조항 후보 표", "",
          "| 유형 | 조항 원문 요약 | 청크 ID | 파일 | 쪽 | 수치 또는 규범이 명시적인가 |", "|---|---|---|---|---:|---|"]
    for t, pre, phrase, summary, explicit in CLAUSES:
        if pre:
            c = chunks[pre]
            L.append(f"| {t} | {summary} | `{c['id']}` | {c['source']} | {c['page']} | {explicit} |")
        else:
            L.append(f"| {t} | {summary} | - | - | - | {explicit} |")
    L += ["", "## 원문 (해당 문구 주변)", ""]
    for t, pre, phrase, summary, explicit in CLAUSES:
        if pre:
            c = chunks[pre]
            L += [f"**{t}** — `{c['id']}` {c['source']} {c['page']}쪽", "", "```text", ctx(c, phrase), "```", ""]
    L.append("(이 문서는 `experiments/revision/guideline_grounding.py` 가 만든다.)")
    open(os.path.join(OUT, "guideline_grounding.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    # ground_truth.csv 에 열 추가 (기존 열 보존, 재실행 시 갱신)
    rows = list(csv.DictReader(open(GT, encoding="utf-8")))
    base_cols = [k for k in rows[0] if not k.startswith(("guideline_grounded", "label_guideline_grounded"))]
    for r in rows:
        t = r["defect_type"]
        g = dec[t] if dec[t] in ("true", "false") else "pending"
        r["guideline_grounded"] = g
        r["guideline_grounded_candidate"] = CANDIDATE[t]
        r["label_guideline_grounded"] = r["effective_1280"] if g == "true" else "NA"
        r["label_guideline_grounded_390"] = r["effective_390"] if g == "true" else "NA"
    cols = base_cols + ["guideline_grounded", "guideline_grounded_candidate", "label_guideline_grounded", "label_guideline_grounded_390"]
    with open(GT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print("\n".join(L[:16]))
    print(f"ground_truth.csv: {len(rows)} rows, columns added; decisions = {dec}")


if __name__ == "__main__":
    main()
