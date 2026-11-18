"""
E9 관련 조항 제공 조건, 대조군 위양성 교차 (API 호출 없음, 기술 집계만).

(a) 조항 청크 문구와 15자 이상 일치한 대조군 이슈 (e9_main_retrieval_check.py 1절과 같은 방식)
(b) E9-3 정규식(주 지표 e9_rules.match_issue(issue, None); 대조군은 주입 문구 없음)에 걸린 대조군 이슈
→ run(r1, r2) 별 이슈 단위 교차표, 페이지 단위 교차, 해당 이슈 원문(e9_rules.issue_text) 앞 150자.
출력: results/revision/reports/e9_related_control_overlap.md
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import e9_rules as primary                      # noqa: E402
from scoring import e9_rules_aux as aux                      # noqa: E402
from experiments.revision import e9_regex_table as tbl       # noqa: E402
from experiments.revision import e9_pilot_report as pr       # noqa: E402

RUNS = "results/revision/runs_e9"
META = "testbed_e9/dataset_metadata_e9.json"
OUT = "results/revision/reports/e9_related_control_overlap.md"


def src(*p):
    return ["", "출처:"] + [f"- `{x}`" for x in p] + [""]


def main():
    pages = {p["page_id"]: p for p in json.load(open(META, encoding="utf-8"))["pages"]}
    controls = sorted(p for p, m in pages.items() if m["defect_id"] in (None, "None"))
    grams = set()
    for t in pr.chunk_texts(pr.RELATED).values():
        n = pr.norm(t)
        grams.update(n[i:i + 15] for i in range(0, max(0, len(n) - 14)))

    L = ["# E9 관련 조항 제공: 대조군 위양성 교차 (조항 문구 15자+ 일치 대 E9-3 정규식)", "",
         "작성: `experiments/revision/e9_related_control_overlap.py` (API 호출 없음, 기술 집계만).",
         f"대조군 {len(controls)}페이지. (a) = 이슈 문구와 관련 조항 6청크 본문이 공백 제거 후 15자 이상 연속 일치.",
         "(b) = E9-3 정규식 주 지표(signup|회원가입 과 로그인 이 함께 나옴). 보조 규칙의 E9-3 판정은 주 지표와 같다(아래 확인).", ""]
    details = []
    for r in (1, 2):
        rid = f"e9-main-related-r{r}"
        reps = {json.loads(l)["page_id"]: json.loads(l) for l in open(f"{RUNS}/{rid}/reports.jsonl", encoding="utf-8")}
        c, pa, pb, pab = Counter(), set(), set(), set()
        auxdiff = 0
        for pid in controls:
            rec = reps.get(pid)
            iss = tbl.target_issues(rec.get("report") if rec and rec["status"] == "ok" else None, pid)
            for k, i in enumerate(iss):
                t = primary.issue_text(i)
                n = pr.norm(t)
                a = any(n[x:x + 15] in grams for x in range(0, max(0, len(n) - 14)))
                m = primary.match_issue(i, None)
                b = m["E9-3"]
                auxdiff += aux.match_issue(i)["E9-3"] != b
                c[(a, b)] += 1
                if a: pa.add(pid)
                if b: pb.add(pid)
                if a and b: pab.add(pid)
                if a or b:
                    other = [x for x in ("E9-1", "E9-2", "E9-4") if m[x]]
                    details.append((r, pid, k, a, b, other, t))
        L += [f"## r{r} ({rid})", "",
              "| 이슈 단위 | E9-3 정규식 걸림 | 안 걸림 | 합계 |", "|---|---|---|---|",
              f"| 15자+ 일치 | {c[(True, True)]} | {c[(True, False)]} | {c[(True, True)] + c[(True, False)]} |",
              f"| 일치 없음 | {c[(False, True)]} | {c[(False, False)]} | {c[(False, True)] + c[(False, False)]} |",
              f"| 합계 | {c[(True, True)] + c[(False, True)]} | {c[(True, False)] + c[(False, False)]} | {sum(c.values())} |",
              "",
              f"페이지 단위: (a) {len(pa)}페이지, (b) {len(pb)}페이지, 둘 다 {len(pab)}페이지 "
              f"(같은 이슈가 아니어도 같은 페이지면 셈). 보조 규칙과 E9-3 판정이 다른 이슈 {auxdiff}건."]
        L += src(f"{RUNS}/{rid}/reports.jsonl", "services/chroma_db/chroma.sqlite3 (읽기 전용, 6청크 본문)",
                 "scoring/e9_rules.py")
    L += ["## 이슈 원문 앞 150자 ((a) 또는 (b) 에 해당하는 대조군 이슈)", "",
          "표기: run, 페이지, 이슈 순번, (a) 일치 여부, (b) E9-3 여부, 그 밖에 걸린 정규식 유형. 파이프는 '/'로 바꿈.", ""]
    for r, pid, k, a, b, other, t in details:
        L.append(f"- r{r} {pid} #{k} (a){'O' if a else 'X'} (b){'O' if b else 'X'}"
                 + (f" 기타 {','.join(other)}" if other else "") + ":")
        s = t[:150].replace("\n", " ").replace("|", "/")
        while s:
            L.append("  " + s[:45]); s = s[45:]
    L += src(f"{RUNS}/e9-main-related-r{{1,2}}/reports.jsonl")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print(OUT, "long:", [i + 1 for i, l in enumerate(L) if len(l) > 100])


if __name__ == "__main__":
    main()
