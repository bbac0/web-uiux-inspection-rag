"""
E8 (v) 집계와 기존 수치(이슈 1,016건 중 289건, 28.4%)의 차이 비교 (API 호출 없음).
동결된 e8_run2_reanalysis.py 는 수정하지 않고, 비교 결과를 e8_run2_reanalysis.md 끝에 한 절로 덧붙이고
근거 표를 e8_v_reconciliation.csv 로 쓴다. 여러 번 실행해도 절이 중복되지 않는다.
"""
import csv
import glob
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
MD = "results/revision/e8_run2_reanalysis.md"
MARK = "## (v-b) 기존 수치(1,016건 중 289건)와의 차이"
CORPUS = {"gov_guide.pdf", "gov_check.pdf"}

I = []
for f in sorted(glob.glob("paper_results/run2/report_page_*.json")):
    pid = os.path.basename(f)[7:-5]
    for i in json.load(open(f, encoding="utf-8")).get("issues", []) or []:
        if isinstance(i, dict):
            I.append((pid, i))
role = lambda p, i: "target" if f"testbed_200/{p}.html" in (i.get("description") or "") else "linked"
na = lambda i: i.get("source_file") in (None, "", "N/A")
N = [x for x in I if not na(x[1])]
ex = lambda i: i.get("page_number") in ([12], [12, 13])
gov = lambda i: i.get("source_file") == "gov_guide.pdf"

rows = [
    ("A. 전체 이슈 (E8 분모)", len(I), ""),
    ("  source_file = JSON null", sum(i.get("source_file") is None for _, i in I), "E8: 말뭉치 밖으로 셈"),
    ("  source_file = 'N/A'", sum(i.get("source_file") == "N/A" for _, i in I), "E8: 말뭉치 밖으로 셈"),
    ("  source_file = ''", sum(i.get("source_file") == "" for _, i in I), ""),
    ("B. source_file 이 null/''/'N/A' 아님 (audit_pipeline_artifacts.py 분모)", len(N), "기존 1,016 과 일치"),
    ("B 중 대상 페이지 이슈", sum(role(p, i) == "target" for p, i in N), ""),
    ("B 중 링크된 /login 404 페이지 이슈", sum(role(p, i) == "linked" for p, i in N), ""),
    ("B 중 gov_guide.pdf + [12] (모두 /login 이슈)", sum(gov(i) and i.get("page_number") == [12] and role(p, i) == "linked" for p, i in N), "후보: 288"),
    ("B 중 gov_guide.pdf 이면서 쪽이 예시값 아님", sum(gov(i) and not ex(i) for _, i in N), "후보: 291"),
    ("B 중 'General ...' 계열 파일명", sum(str(i.get("source_file")).lower().startswith("general") for _, i in N), "후보: 294"),
    ("B 중 말뭉치에 없는 파일명", sum(i.get("source_file") not in CORPUS for _, i in N), ""),
    ("B 중 gov_guide.pdf + 예시 쪽", sum(gov(i) and ex(i) for _, i in N), "E8 '파일과 쪽 모두 예시값'과 같음"),
]
with open("results/revision/e8_v_reconciliation.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["집계", "건수", "비고"]); w.writerows(rows)

d = dict((r[0], r[1]) for r in rows)
para = f"""{MARK}

두 집계는 분모부터 다르다. E8 (v)는 run2 리포트 200개의 이슈 전체 {len(I)}건을 분모로 하고, source_file 이 JSON null(17건)이나
문자열 'N/A'(19건)인 이슈도 그대로 남겨 "말뭉치에 없는 파일명"에 넣었다(37.4%). 기존 수치의 분모 1,016건은
`experiments/audit_pipeline_artifacts.py` 의 기준(source_file 이 null, 빈 문자열, 'N/A' 가 아닌 이슈만)과 정확히 같다
({len(I)} − 17 − 19 − 2 = {len(N)}; 2건은 빈 문자열). 두 집계 모두 대상 페이지 이슈만 고르지 않고 크롤러가 따라간
`/login` 404 페이지의 이슈({sum(role(p, i) == 'linked' for p, i in N)}건)를 포함하며, 파일명은 정규화하지 않았다(대소문자가 다른
'General web standards'와 'General Web Standards'를 별개로 셈). 분자 289건은 이 저장소의 어떤 스크립트도 출력하지 않으며, 같은 분모에서
단순한 조건 조합으로는 정확히 재현되지 않았다. 가장 가까운 후보는 (1) `/login` 이슈 중 gov_guide.pdf·[12] 를 단 288건(28.3%),
(2) gov_guide.pdf 이면서 쪽이 예시값이 아닌 291건, (3) 'General …' 계열 파일명 294건이다(`e8_v_reconciliation.csv`).
따라서 차이는 (a) null/'N/A' 처리(분모 {len(I)} vs {len(N)})와 (b) 분자의 판정 기준이 문서화되어 있지 않은 데서 온다. 289건의 정의(어떤 조건을
센 것인지)를 확인해 주면 같은 기준으로 다시 계산해 이 절을 갱신한다. 이 절은 `experiments/revision/e8_reconcile.py` 가 덧붙였다.
"""
s = open(MD, encoding="utf-8").read()
if MARK in s:
    s = s[:s.index(MARK)].rstrip() + "\n"
open(MD, "w", encoding="utf-8").write(s.rstrip() + "\n\n" + para)
print(para)
for r in rows:
    print(r)
