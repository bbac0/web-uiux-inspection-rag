"""
E8 (v) 근거 파일명 지표의 세 가지 정의 비교 (5.3절용, API 호출 없음, run2 읽기 전용).
기존 수치 289/1,016 은 출처를 찾을 수 없어 폐기했다(사용자 결정, 2026-11-12). 대신 정의 A/B/C 를 같은 데이터로 계산한다.
결과는 e8_run2_reanalysis.md 끝에 한 절로 덧붙이고(재실행해도 중복되지 않음) e8_v_definitions.csv 로도 쓴다.
"""
import csv
import glob
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
MD = "results/revision/e8_run2_reanalysis.md"
MARK = "## (v-c) 5.3절용: 근거 파일명 지표의 세 가지 정의"
CORPUS = ("gov_guide.pdf", "gov_check.pdf")

I = []
for f in sorted(glob.glob("paper_results/run2/report_page_*.json")):
    pid = os.path.basename(f)[7:-5]
    for i in json.load(open(f, encoding="utf-8")).get("issues", []) or []:
        if isinstance(i, dict):
            I.append((pid, i))
is_target = lambda p, i: f"testbed_200/{p}.html" in (i.get("description") or "")
missing = lambda i: i.get("source_file") in (None, "", "N/A")


def kind(sf):
    if sf is None:
        return "JSON null"
    if sf == "":
        return "빈 문자열"
    if sf == "N/A":
        return "'N/A'"
    if sf == "gov_guide.pdf":
        return "gov_guide.pdf"
    if sf == "gov_check.pdf":
        return "gov_check.pdf"
    return "말뭉치 밖 파일명(기타 문자열)"


def breakdown(S):
    return Counter(kind(i.get("source_file")) for _, i in S)


T = [x for x in I if is_target(*x)]
A_den = [x for x in I if not missing(x[1])]
A_num = [x for x in A_den if x[1].get("source_file") not in CORPUS]
B_den = I
B_num = [x for x in I if x[1].get("source_file") != "gov_guide.pdf"]
CA_den = [x for x in T if not missing(x[1])]
CA_num = [x for x in CA_den if x[1].get("source_file") not in CORPUS]
CB_den = T
CB_num = [x for x in T if x[1].get("source_file") != "gov_guide.pdf"]

defs = [
    ("A", "기존 audit 기준: null/''/'N/A' 제외, /login 포함", "말뭉치(gov_guide.pdf, gov_check.pdf)에 없는 파일명", A_den, A_num),
    ("B", "E8 기준: 전체 이슈, /login 포함", "gov_guide.pdf 가 아님 (결측 표기 포함)", B_den, B_num),
    ("C-A", "대상 페이지 이슈만, null/''/'N/A' 제외", "말뭉치에 없는 파일명", CA_den, CA_num),
    ("C-B", "대상 페이지 이슈만, 전체", "gov_guide.pdf 가 아님 (결측 표기 포함)", CB_den, CB_num),
]
NA_KEY = "num_'N/A'"
NA = "'N/A'"
kinds = ["JSON null", "빈 문자열", "'N/A'", "gov_check.pdf", "말뭉치 밖 파일명(기타 문자열)"]
rows = []
for k, den_def, num_def, den, num in defs:
    b = breakdown(num)
    rows.append({"definition": k, "denominator_rule": den_def, "numerator_rule": num_def,
                 "denominator": len(den), "numerator": len(num), "rate": round(len(num) / len(den), 4),
                 **{f"num_{x}": b.get(x, 0) for x in kinds}})
with open("results/revision/e8_v_definitions.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

L = [MARK, "",
     "기존 수치(1,016건 중 289건, 28.4%)는 출처 스크립트와 판정 기준을 찾을 수 없어 논문 서술에서 폐기한다(2026-11-12 결정). "
     "같은 run2 리포트 200개(이슈 1,054건: 대상 페이지 502, `/login` 404 페이지 552)로 다음 세 정의를 계산했다. 파일명은 정규화하지 않았다.", "",
     "| 정의 | 분모 기준 | 분자 기준 | 분모 | 분자 | 비율 | 분자 내역: null | '' | 'N/A' | gov_check.pdf | 말뭉치 밖 파일명 |",
     "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
for r in rows:
    L.append(f"| {r['definition']} | {r['denominator_rule']} | {r['numerator_rule']} | {r['denominator']} | {r['numerator']} | "
             f"{100 * r['rate']:.1f}% | {r['num_JSON null']} | {r['num_빈 문자열']} | {r[NA_KEY]} | "
             f"{r['num_gov_check.pdf']} | {r['num_말뭉치 밖 파일명(기타 문자열)']} |")
b394 = breakdown(B_num)
L += ["",
      f"E8 (v)의 '말뭉치에 없는 파일명 394건(37.4%)'은 정의 B 와 같은 값이며, 그 안에 결측 표기 {b394['JSON null'] + b394['빈 문자열'] + b394[NA]}건"
      f"(JSON null {b394['JSON null']}, 빈 문자열 {b394['빈 문자열']}, 'N/A' {b394[NA]})이 포함되어 있다. "
      f"gov_check.pdf 를 인용한 이슈는 {sum(i.get('source_file') == 'gov_check.pdf' for _, i in I)}건이라 정의 B 의 '말뭉치 밖'과 'gov_guide.pdf 아님'이 같은 값이 된다.", "",
      f"정의 차이: 정의 A 는 결측 표기를 분모에서 빼고 실제 파일명이 적힌 이슈만 대상으로 '말뭉치에 없는 이름'을 세므로 "
      f"{rows[0]['numerator']}/{rows[0]['denominator']}({100 * rows[0]['rate']:.1f}%)이고, 정의 B 는 결측 표기까지 분모와 분자에 넣어 "
      f"{rows[1]['numerator']}/{rows[1]['denominator']}({100 * rows[1]['rate']:.1f}%)로 높아진다. 두 정의 모두 크롤러가 따라간 `/login` 404 페이지의 이슈를 "
      f"포함하는데, 이 {len(I) - len(T)}건 중 {sum(1 for x in I if not is_target(*x) and x[1].get('source_file') not in CORPUS)}건이 말뭉치 밖 파일명(정의 A 분자의 "
      f"{sum(1 for x in I if not is_target(*x) and x[1].get('source_file') not in CORPUS) / len(A_num):.0%})이고 나머지는 모두 gov_guide.pdf·[12]여서 "
      "결과를 크게 좌우한다. 대상 페이지 이슈만 세는 정의 C 에서는 "
      f"결측 제외 시 {rows[2]['numerator']}/{rows[2]['denominator']}({100 * rows[2]['rate']:.1f}%), 결측 포함 시 "
      f"{rows[3]['numerator']}/{rows[3]['denominator']}({100 * rows[3]['rate']:.1f}%)이다. 테스트베드 페이지에 대한 시스템의 근거 기록을 평가한다는 "
      "목적에는 정의 C 가 가장 가깝고, 이번 재실험(`--max-pages 1`)의 수치도 정의 C 와 같은 범위(대상 페이지만)로 계산된다. "
      "모든 정의에서 run2 는 검색 컨텍스트가 비어 있었으므로 적힌 파일명은 모두 컨텍스트 없이 모델이 만든 값이다. "
      "이 절은 `experiments/revision/e8_v_definitions.py` 가 덧붙였고 수치는 `e8_v_definitions.csv` 에 있다."]
s = open(MD, encoding="utf-8").read()
if MARK in s:
    s = s[:s.index(MARK)].rstrip() + "\n"
open(MD, "w", encoding="utf-8").write(s.rstrip() + "\n\n" + "\n".join(L) + "\n")
print("\n".join(L))
