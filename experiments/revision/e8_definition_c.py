"""
5.3절용 확정 표 — E8 정의 C (run2 대상 페이지 이슈만, API 호출 없음).
e8_run2_reanalysis.md 끝에 "(v-d)" 절로 덧붙이고(재실행 시 중복 없음) e8_definition_c.csv 로 쓴다.
고정 질의의 검색 청크 출처는 pilot-02 / E1-R1 실행 로그(calls.jsonl)에서 읽는다.
"""
import csv
import glob
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
MD = "results/revision/e8_run2_reanalysis.md"
MARK = "## (v-d) 5.3절 확정 표: 정의 C (대상 페이지 이슈만)"
CORPUS = ("gov_guide.pdf", "gov_check.pdf")
EXAMPLE_PAGES = ([12], [12, 13])

T = []
for f in sorted(glob.glob("paper_results/run2/report_page_*.json")):
    pid = os.path.basename(f)[7:-5]
    for i in json.load(open(f, encoding="utf-8")).get("issues", []) or []:
        if isinstance(i, dict) and f"testbed_200/{pid}.html" in (i.get("description") or ""):
            T.append(i)
N = len(T)
missing = [i for i in T if i.get("source_file") in (None, "", "N/A")]
named = [i for i in T if i not in missing]
example = [i for i in T if i.get("source_file") == "gov_guide.pdf" and i.get("page_number") in EXAMPLE_PAGES]
noncorpus_named = [i for i in named if i.get("source_file") not in CORPUS]
gov_check = [i for i in T if i.get("source_file") == "gov_check.pdf"]
miss_kind = Counter("JSON null" if i.get("source_file") is None else repr(i.get("source_file")) for i in missing)

rows = [
    ("(a) 파일명 결측 (null, '', 'N/A')", len(missing), N),
    ("(b) 프롬프트 예시값과 일치 (gov_guide.pdf 이면서 page_number [12] 또는 [12, 13])", len(example), N),
    ("(c-1) 말뭉치에 없는 파일명 — 파일명이 있는 이슈 기준", len(noncorpus_named), len(named)),
    ("(c-2) 말뭉치에 없는 파일명 — 대상 이슈 전체 기준 (결측은 분자에 넣지 않음)", len(noncorpus_named), N),
    ("(c-3) 말뭉치에 없는 파일명 + 결측 — 대상 이슈 전체 기준", len(noncorpus_named) + len(missing), N),
    ("(d) gov_check.pdf 를 인용한 이슈", len(gov_check), N),
]
with open("results/revision/e8_definition_c.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["지표", "분자", "분모", "비율"])
    for name, a, b in rows:
        w.writerow([name, a, b, round(a / b, 4)])

# 고정 질의 검색 청크 (실행 로그)
chunk_sets, sources = Counter(), Counter()
logs = [p for p in ("results/revision/runs/pilot-02/calls.jsonl", "results/revision/runs/E1-R1/calls.jsonl") if os.path.exists(p)]
n_calls = 0
for p in logs:
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        if r["status"] != "ok" or r["rag"].get("query_mode") != "fixed":
            continue
        n_calls += 1
        chunk_sets[tuple(c["id"] for c in r["rag"]["chunks"])] += 1
        for c in r["rag"]["chunks"]:
            sources[c["source"]] += 1
top = chunk_sets.most_common(1)[0][0] if chunk_sets else ()

L = [MARK, "",
     f"run2 대상 페이지 이슈 {N}건 (링크된 `/login` 404 페이지 이슈 제외). 파일명은 정규화하지 않았다.", "",
     "| 지표 | 분자 | 분모 | 비율 |", "|---|---:|---:|---:|"]
for name, a, b in rows:
    L.append(f"| {name} | {a} | {b} | {100 * a / b:.1f}% |")
L += ["",
      f"- 결측 내역: {dict(miss_kind)}",
      f"- 말뭉치에 없는 파일명 상위: {dict(Counter(i.get('source_file') for i in noncorpus_named).most_common(6))}",
      f"- 고정 질의 검색 결과(실행 로그 {n_calls}건: {', '.join(os.path.basename(os.path.dirname(p)) for p in logs)}): "
      f"청크 조합 {len(chunk_sets)}종, 출처 {dict(sources)} → 4개 청크가 모두 gov_guide.pdf 이다.",
      "- gov_check.pdf 청크(288개)가 고정 질의 상위 K 에 들어갈 가능성: 실행 로그에는 상위 4개의 거리(0.4518~0.4626)만 있으므로, "
      "gov_check.pdf 청크의 최상위 거리는 0.4626 이상이고 순위는 5위 이하라는 것만 확정된다. 정확한 최상위 거리와 순위는 "
      "고정 질의 임베딩이 필요해 Gemini 임베딩 API 1회 호출이 있어야 계산할 수 있다(API 호출 없이 하라는 지시에 따라 계산하지 않음).",
      "", "이 절은 `experiments/revision/e8_definition_c.py` 가 덧붙였고 수치는 `e8_definition_c.csv` 에 있다."]
s = open(MD, encoding="utf-8").read()
if MARK in s:
    s = s[:s.index(MARK)].rstrip() + "\n"
open(MD, "w", encoding="utf-8").write(s.rstrip() + "\n\n" + "\n".join(L) + "\n")
print("\n".join(L))
