"""
'접속하기'(주입 표현)가 가이드라인 위반이라는 근거 조항이 있는지 확인 (API 호출 없음, sqlite 읽기 전용).
결과 요약을 oracle_candidates.md 맨 앞에 붙인다(재실행 시 교체). oracle_candidates.py 를 다시 돌리면 요약이 지워지므로
그 뒤에는 이 스크립트를 다시 실행한다.
"""
import importlib.util
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
MD = "results/revision/oracle_candidates.md"
START, END = "<!-- terminology-basis:start -->", "<!-- terminology-basis:end -->"
spec = importlib.util.spec_from_file_location("oc", "experiments/revision/oracle_candidates.py")
oc = importlib.util.module_from_spec(spec); spec.loader.exec_module(oc)
chunks = oc.load_chunks()

# (조항 분류, 청크 ID 앞 8자리, 찾을 문구(공백 제거 기준), 관련성 설명)
CLAUSES = [
    ("간접: 링크명 용어", "4e153a63", "07링크명에이해하기쉬운용어를사용한다",
     "메인 메뉴 링크명에 전문 용어·익숙하지 않은 용어를 쓰지 말라는 조항. '접속하기'는 전문 용어·축약어·외래어가 아니므로 직접 적용되지 않는다."),
    ("간접: 링크명 용어", "8a3438fd", "메인메뉴링크명에이해하기쉬운용어를사용하고있다",
     "같은 조항의 점검표. 점검 대상은 메인 메뉴이고, 판정 기준은 ①전문 용어 ②축약어 ③자주 쓰이지 않는 외래어·외국어다."),
    ("간접: 링크 레이블 예측 가능성", "b4c4ffd0", "링크레이블은연결된목적지정보를예측할수있는내용으로제공한다",
     "링크 레이블이 목적지를 예측할 수 있어야 한다는 조항. '접속하기'가 로그인 화면을 예측하게 하는지는 해석의 문제이며 특정 용어를 요구하지 않는다."),
    ("간접: 로그인 링크 목적지", "76648c77", "로그인링크는항상‘로그인’화면으로연결되어야한다",
     "로그인 링크의 '목적지'가 로그인 화면이어야 한다는 조항이며, 링크 '문구'를 규정하지 않는다."),
    ("간접: 로그인 링크 목적지", "87f08a4d", "로그인링크는항상‘로그인’화면으로연결되어야한다",
     "같은 조항의 준수 기준(미준수 사례는 '로그인 링크가 회원가입 화면으로 이동'). 문구 규정 아님."),
    ("서술적 예시", "51cab320", "로그인,회원가입,개인메뉴",
     "헤더 구성요소 설명에서 '로그인'을 예시 레이블로 쓴다. 규정이 아니라 예시다."),
    ("서술적 예시", "77741f18", "검색,로그인처럼",
     "아이콘 텍스트 레이블 생략 예외의 예시로 '로그인'을 쓴다. 규정이 아니라 예시다."),
]


def ctx_of(c, phrase, before=200, after=200):
    n, idx = oc.norm_with_map(c["text"])
    p = n.find(phrase.lower())
    if p < 0:
        return None
    s, e = idx[p], idx[min(len(idx) - 1, p + len(phrase) - 1)]
    return re.sub(r"\s+", " ", c["text"][max(0, s - before): e + 1 + after]).strip()


def main():
    by_prefix = {c["id"][:8]: c for c in chunks}
    norm_all = [(c, oc.norm_with_map(c["text"])[0]) for c in chunks]
    conn = [c for c, n in norm_all if "접속" in n]
    conn_label = [c for c, n in norm_all if re.search(r"접속하기|‘접속’|'접속'|\"접속\"", n)]
    std_term = [c for c, n in norm_all if re.search(r"표준용어|용어를일관|일관된용어|동일한용어|용어통일", n)]
    L = [START, "## 요약: '접속하기'(주입 표현)를 위반으로 보는 근거 조항 확인", "",
         f"- 검색 범위: `services/chroma_db` 청크 {len(chunks)}개 (gov_guide.pdf, gov_check.pdf), 공백을 지우고 비교.",
         "- **결론: '로그인'을 표준 용어로 규정하거나 '접속', '접속하기' 같은 변형 표현을 금지·대체하도록 규정한 조항은 없다.**",
         f"  - '접속'이 나오는 청크 {len(conn)}개는 모두 \"웹사이트에 접속한다\", \"접속하자마자\", \"접속 환경\" 같은 절차·서술 문맥이다.",
         f"  - '접속하기' 또는 따옴표로 묶인 '접속' 표현: {len(conn_label)}개 청크.",
         f"  - '표준 용어', '용어를 일관되게', '동일한 용어', '용어 통일' 같은 일반 용어 통일 조항: {len(std_term)}개 청크.",
         "- 따라서 표준 용어 위반 결함(`로그인` → `접속하기`)은 가이드라인 조항에 직접 근거한 위반이 아니다. 아래 간접 조항을 확장 해석해야만 위반으로 볼 수 있다.",
         "  E3 oracle 조건에 넣을 청크를 고를 때 이 점을 함께 고려해야 한다(직접 근거가 없으므로 oracle 은 '관련 조항 제공' 조건이 된다).", "",
         "| 분류 | 청크 ID | 파일 | 쪽 | 관련성 |", "|---|---|---|---:|---|"]
    rows = []
    for kind, pre, phrase, note in CLAUSES:
        c = by_prefix[pre]
        rows.append((kind, c, phrase, note))
        L.append(f"| {kind} | `{c['id']}` | {c['source']} | {c['page']} | {note} |")
    L += ["", "### 원문 (해당 문구 앞뒤 200자)", ""]
    for kind, c, phrase, note in rows:
        L += [f"**`{c['id']}`** — {c['source']} {c['page']}쪽 ({kind})", "", "```text", ctx_of(c, phrase) or "(문구 위치를 찾지 못함)", "```", ""]
    L += ["### '접속'이 나오는 청크 전부 (모두 절차·서술 문맥)", "", "| 청크 ID | 파일 | 쪽 | 문맥 |", "|---|---|---|---|"]
    for c in conn:
        L.append(f"| `{c['id']}` | {c['source']} | {c['page']} | {(ctx_of(c, '접속', 60, 60) or '').replace('|', '/')} |")
    L += ["", "(이 요약은 `experiments/revision/terminology_basis.py` 가 붙였다.)", END, ""]
    s = open(MD, encoding="utf-8").read()
    if START in s:
        s = s[:s.index(START)] + s[s.index(END) + len(END):].lstrip("\n")
    open(MD, "w", encoding="utf-8").write("\n".join(L) + "\n" + s)
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
