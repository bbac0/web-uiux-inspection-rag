"""
용어 관련 조항 후보 중 gov_check.pdf 45쪽(76648c77…)과 208쪽(87f08a4d…) 청크의 원문 전체와 앞뒤 문맥을 덤프한다
(API 호출 없음, 원본 벡터 DB 의 sqlite 를 읽기 전용으로 사용). 연구자가 직접 읽고 판단하기 위한 자료다.

앞뒤 문맥 = 같은 PDF 의 앞쪽(p-1), 같은 쪽, 뒤쪽(p+1)에 속한 청크 전부(청크 본문 그대로, 줄바꿈 보존).
청크는 1,000자/100자 중첩이므로 인접 청크 사이에 문장이 겹칠 수 있다.

출력: results/revision/oracle_terminology_context.md
"""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
spec = importlib.util.spec_from_file_location("oc", "experiments/revision/oracle_candidates.py")
oc = importlib.util.module_from_spec(spec); spec.loader.exec_module(oc)
TARGETS = ["76648c77", "87f08a4d"]


def main():
    chunks = oc.load_chunks()
    by_pre = {c["id"][:8]: c for c in chunks}
    L = ["# 용어 관련 조항 원문 (gov_check.pdf 45쪽, 208쪽)", "",
         "- 출처: `services/chroma_db` (sqlite 읽기 전용). 청크 본문은 PDF 추출 텍스트 그대로이며 줄바꿈을 보존했다.",
         "- 각 대상 청크 아래에 같은 PDF 의 앞쪽·같은 쪽·뒤쪽 청크 전부를 문맥으로 붙였다(쪽 순서).",
         "- 판단은 연구자가 한다. 이 파일은 해석을 덧붙이지 않는다.", ""]
    for pre in TARGETS:
        t = by_pre[pre]
        L += [f"## 대상 청크 `{t['id']}` — {t['source']} {t['page']}쪽 ({len(t['text'])}자)", "",
              "```text", t["text"], "```", ""]
        neigh = [c for c in chunks if c["source"] == t["source"] and abs(c["page"] - t["page"]) <= 1 and c["id"] != t["id"]]
        neigh.sort(key=lambda c: (c["page"], c["id"]))
        L += [f"### 문맥: {t['source']} {t['page'] - 1}~{t['page'] + 1}쪽의 다른 청크 {len(neigh)}개", ""]
        for c in neigh:
            L += [f"#### `{c['id']}` — {c['page']}쪽 ({len(c['text'])}자)", "", "```text", c["text"], "```", ""]
        total = len(t["text"]) + sum(len(c["text"]) for c in neigh)
        L += [f"(대상 + 문맥 합계 {total}자)", ""]
    open("results/revision/oracle_terminology_context.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(l for l in L if l.startswith(("#", "("))))


if __name__ == "__main__":
    main()
