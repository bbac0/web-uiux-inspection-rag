"""
키워드 사전 감사 (API 호출 없음, 사전은 고치지 않음, 통계 검정 없음).

- 사전: experiments/evaluate_performance_v5.CATEGORY_PHRASES (동결) 를 그대로 읽는다. 매칭 = description 소문자에 구문 포함.
- 대상 run: E1-R1, R2, R3b (RAG 켬), E2-A1-1~3 (RAG 끔). 이슈 = scoring/issue_table 의 대상 페이지 이슈.
- 구문별: 매칭 이슈 수(켬/끔), 그 이슈의 의미 채점 pass1 라벨 분포, 이슈가 속한 페이지의 주입 결함 유형(nominal) 분포.
- 주입 CSS 원문: experiments/generate_200_testbed.py 의 주입 문자열과 testbed_200 페이지 HTML 에서 'overflow' 를 확인.
출력: results/revision/reports/keyword_phrase_audit.md
"""
import csv
import glob
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import semantic_grader_anthropic as g     # noqa: E402

_spec = importlib.util.spec_from_file_location("kw", "experiments/evaluate_performance_v5.py")
kw = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(kw)

SEM = "results/revision/semantic_scores"
GT = "results/revision/ground_truth.csv"
GEN = "experiments/generate_200_testbed.py"
OUT = "results/revision/reports/keyword_phrase_audit.md"
ON, OFF = ["E1-R1", "E1-R2", "E1-R3b"], ["E2-A1-1", "E2-A1-2", "E2-A1-3"]
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
SH = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
      "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복ID", "None": "None",
      "control": "대조군", "nonok": "비성공"}
FOCUS = ["overflow", "viewport", "반응형", "레이아웃이 깨"]


def src(*p):
    return ["", "출처:"] + [f"- `{x}`" for x in p] + [""]


def fmt(c, keys):
    return " / ".join(f"{SH.get(k, k)} {c[k]}" for k in keys if c[k])


def main():
    ptypes = defaultdict(set)
    for r in csv.DictReader(open(GT, encoding="utf-8")):
        if r["nominal_injected"] == "1":
            ptypes[r["page_id"]].add(r["defect_type"])
    recs = []
    for run in ON + OFF:
        sem = {}
        for l in open(f"{SEM}/{run}-sem-p1/grades.jsonl", encoding="utf-8"):
            x = json.loads(l)
            sem[x["issue_id"]] = x["label"] if x["status"] == "ok" else "nonok"
        for iid, s, iss in g.iter_run_issues(run):
            recs.append({"run": run, "rag": "켬" if run in ON else "끔", "iid": iid, "page": s["page_id"],
                         "desc": (iss.get("description") or "").lower(), "sem": sem.get(iid, "nonok")})
    phrases = [(t, p) for t, ps in kw.CATEGORY_PHRASES.items() for p in ps]

    L = ["# 키워드 사전 감사 (구문별)", "",
         "작성: `experiments/revision/keyword_phrase_audit.py` (API 호출 없음, 사전 수정 없음, 기술 집계만).",
         "사전 = `experiments/evaluate_performance_v5.CATEGORY_PHRASES` (동결). 매칭 = description 소문자에 구문 포함",
         "(한 이슈가 여러 구문에 걸릴 수 있음). run = E1-R1·R2·R3b (RAG 켬), E2-A1-1~3 (RAG 끔), 3회 합계.",
         "의미 = 의미 채점 pass1 라벨(잘림 등 비성공은 '비성공'). 페이지 유형 = nominal 주입 유형(2개면 둘 다 셈).", ""]

    L += ["## 1. 전체 구문: 매칭 이슈 수", "",
          "| 사전 유형 | 구문 | 켬 | 끔 | 의미 라벨이 사전 유형과 같음 | 매칭 페이지가 그 유형 주입 |",
          "|---|---|---|---|---|---|"]
    for t, p in phrases:
        m = [r for r in recs if p.lower() in r["desc"]]
        on, off = sum(r["rag"] == "켬" for r in m), sum(r["rag"] == "끔" for r in m)
        same = sum(r["sem"] == t for r in m)
        inj = sum(t in ptypes[r["page"]] for r in m)
        L.append(f"| {SH[t]} | {p} | {on} | {off} | {same}/{len(m)} | {inj}/{len(m)} |")
    L += src("experiments/evaluate_performance_v5.py", "results/revision/runs/{run}/reports.jsonl",
             f"{SEM}/{{run}}-sem-p1/grades.jsonl", GT)

    L += ["## 2. 모바일 구문 상세 (overflow, viewport, 반응형, 레이아웃이 깨)", ""]
    labs = TYPES + ["None", "nonok"]
    for p in FOCUS:
        L += [f"### '{p}'", "", "| RAG | 매칭 이슈 | 의미 라벨 분포 | 페이지 주입 유형 분포 |", "|---|---|---|---|"]
        for rag in ("켬", "끔"):
            m = [r for r in recs if r["rag"] == rag and p.lower() in r["desc"]]
            cs = Counter(r["sem"] for r in m)
            cp = Counter()
            for r in m:
                for t in (ptypes[r["page"]] or {"control"}):
                    cp[t] += 1
            L.append(f"| {rag} | {len(m)} | {fmt(cs, labs) or '-'} | {fmt(cp, TYPES + ['control']) or '-'} |")
        L += [""]
    L += src("results/revision/runs/{run}/reports.jsonl", f"{SEM}/{{run}}-sem-p1/grades.jsonl", GT)

    L += ["### 2a. 'overflow' 매칭 이슈의 문맥 (description 안 'overflow' 앞뒤 문자열, 상위 8개)", ""]
    ctx = Counter()
    for r in recs:
        for mt in re.finditer(r"overflow[\w\-]*\s*:\s*[\w\-]+", r["desc"]):
            ctx[mt.group(0).replace(" ", "")] += 1
    L += ["| 문자열 | 이슈 내 등장 수 |", "|---|---|"] + [f"| `{k}` | {v} |" for k, v in ctx.most_common(8)]
    L += src("results/revision/runs/{run}/reports.jsonl")

    # 3. 주입 CSS 원문
    gen = open(GEN, encoding="utf-8").read().splitlines()
    L += ["## 3. 주입 CSS 원문의 'overflow'", "", f"`{GEN}` 에서 'overflow' 가 들어 있는 줄:", ""]
    for i, line in enumerate(gen, 1):
        if "overflow" in line.lower():
            m = re.search(r"<style>(.*?)</style>", line)
            body = m.group(1) if m else line.strip()
            L.append(f"- {i}행:")
            while body:
                L.append("  `" + body[:90] + "`"); body = body[90:]
    for i, line in enumerate(gen, 1):
        if '"type": "' in line and ("Button" in line or "Mobile" in line):
            L.append(f"- {i}행 유형 표기: `{line.strip()[:90]}`")
    L += ["", "testbed_200 페이지 HTML 에서 주입 문자열 확인 (nominal 라벨과 대조):", "",
          "| 문자열 | 들어 있는 페이지 | 그중 버튼 주입 | 그중 모바일 주입 |", "|---|---|---|---|"]
    for sstr in ("overflow: hidden !important", "overflow-x: scroll !important"):
        pg = [os.path.basename(p)[:-5] for p in glob.glob("testbed_200/page_*.html")
              if sstr in open(p, encoding="utf-8").read()]
        L.append(f"| `{sstr}` | {len(pg)} | {sum('Button Area Clipping' in ptypes[p] for p in pg)} | "
                 f"{sum('Mobile Layout Breakage' in ptypes[p] for p in pg)} |")
    nb = sum("Button Area Clipping" in v for v in ptypes.values())
    nm = sum("Mobile Layout Breakage" in v for v in ptypes.values())
    L += ["", f"nominal 버튼 주입 페이지 {nb}, 모바일 주입 페이지 {nm}.",
          "버튼 잘림 주입 CSS 에 `overflow: hidden !important` 가 들어 있어, 모델이 이 CSS 를 인용하면 모바일 사전 구문",
          "'overflow' 에 걸린다. 모바일 주입 CSS 에도 `overflow-x: scroll !important` 가 있다."]
    L += src(GEN, "testbed_200/page_*.html", GT)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print(OUT, "long:", [i + 1 for i, l in enumerate(L) if len(l) > 100])


if __name__ == "__main__":
    main()
