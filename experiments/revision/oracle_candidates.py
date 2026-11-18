"""
E3 oracle 청크 후보 덤프 (API 호출 없음). 원본 services/chroma_db 의 sqlite 를 읽기 전용(immutable)으로 열어
1,020개 청크 본문을 키워드로 검색한다. Chroma 클라이언트로 열지 않으므로 원본이 바뀌지 않는다.

PDF 추출 텍스트에는 글자 사이에 공백이 끼어 있는 경우가 있어("가 이 드 라 인"), 공백을 모두 지운 문자열끼리 비교한다.
점수 = 3 × (핵심 키워드 종류 수) + (보조 키워드 종류 수). 유형별로 점수 순 상위 N개를 앞뒤 200자 문맥과 함께 쓴다.

  python experiments/revision/oracle_candidates.py [--top 40]
출력: results/revision/oracle_candidates.md, results/revision/oracle_candidates.csv
"""
import argparse
import csv
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

GROUPS = {
    "a_terminology": ("(a) 표준 용어 · 로그인 등 용어 규정",
                      ["표준용어", "로그인", "로그아웃", "용어", "명칭"],
                      ["레이블", "버튼명", "링크텍스트", "쉬운말", "외래어", "회원가입", "본인인증"]),
    "b_contrast": ("(b) 명도 대비",
                   ["명도대비", "색대비", "대비율", "4.5:1", "contrast"],
                   ["3:1", "전경색", "배경색", "고대비", "색상"]),
    "c_responsive": ("(c) 반응형 · 모바일",
                     ["반응형", "가로스크롤", "뷰포트", "viewport", "모바일"],
                     ["화면크기", "해상도", "브레이크포인트", "가로폭", "확대", "320", "360"]),
    "d_markup": ("(d) 중복 ID · 마크업",
                 ["중복", "id속성", "고유한id", "마크업", "웹표준", "문법"],
                 ["html", "유효성", "aria", "태그", "속성", "구조"]),
}


def load_chunks():
    db = os.path.abspath("services/chroma_db/chroma.sqlite3").replace("\\", "/")
    con = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    rows = con.execute("select e.embedding_id, m.key, m.string_value, m.int_value from embeddings e "
                       "join embedding_metadata m on e.id = m.id").fetchall()
    con.close()
    ch = {}
    for cid, k, s, i in rows:
        ch.setdefault(cid, {})[k] = s if s is not None else i
    out = []
    for cid, d in ch.items():
        out.append({"id": cid, "source": re.split(r"[\\/]", d.get("source", "") or "")[-1],
                    "page": (d.get("page") or 0) + 1, "text": d.get("chroma:document", "") or ""})
    return sorted(out, key=lambda c: (c["source"], c["page"], c["id"]))


def norm_with_map(text):
    chars, idx = [], []
    for i, ch in enumerate(text):
        if not ch.isspace():
            chars.append(ch.lower()); idx.append(i)
    return "".join(chars), idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    chunks = load_chunks()
    L = ["# E3 oracle 청크 후보", "",
         f"- 대상: `services/chroma_db` 청크 {len(chunks)}개 (sqlite 읽기 전용). 키워드 검색은 공백을 지우고 소문자로 비교한다.",
         "- 점수 = 3 × 핵심 키워드 종류 수 + 보조 키워드 종류 수. 각 유형 점수 순 상위 후보와 첫 핵심 키워드(없으면 첫 보조 키워드) 앞뒤 200자.",
         "- 이 목록은 후보일 뿐이다. 정답 청크는 연구자가 골라 `oracle_chunks.csv` (`page_id,chunk_id`)에 적는다.", ""]
    csv_rows = []
    for gk, (title, core, aux) in GROUPS.items():
        hits = []
        for c in chunks:
            n, idx = norm_with_map(c["text"])
            mc = [k for k in core if k.lower() in n]
            ma = [k for k in aux if k.lower() in n]
            if not mc and not (ma and len(ma) >= 2):
                continue
            score = 3 * len(mc) + len(ma)
            key = (mc or ma)[0].lower()
            p = n.index(key)
            s0 = idx[p]
            ctx = c["text"][max(0, s0 - 200): s0 + 200 + len(key)]
            hits.append((score, c, mc, ma, ctx))
        hits.sort(key=lambda h: (-h[0], h[1]["source"], h[1]["page"]))
        L += [f"## {title}", "", f"- 후보 {len(hits)}개 (핵심 키워드 {core}, 보조 {aux}); 상위 {min(a.top, len(hits))}개 표시", ""]
        for r, (score, c, mc, ma, ctx) in enumerate(hits[:a.top], 1):
            L += [f"### {gk}-{r}. `{c['id']}` — {c['source']} {c['page']}쪽 (점수 {score}; 핵심 {mc}, 보조 {ma})", "",
                  "```text", re.sub(r"\s+", " ", ctx).strip(), "```", ""]
        for score, c, mc, ma, ctx in hits:
            csv_rows.append({"group": gk, "chunk_id": c["id"], "source": c["source"], "page": c["page"], "score": score,
                             "core_matches": ";".join(mc), "aux_matches": ";".join(ma),
                             "context_400": re.sub(r"\s+", " ", ctx).strip()})
    open("results/revision/oracle_candidates.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
    with open("results/revision/oracle_candidates.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0])); w.writeheader(); w.writerows(csv_rows)
    for gk in GROUPS:
        print(gk, sum(1 for r in csv_rows if r["group"] == gk))


if __name__ == "__main__":
    main()
