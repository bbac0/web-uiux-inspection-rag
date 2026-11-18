"""
E9 본 실험 보고서 (run 1, run 2; API 호출 없음, 통계 검정 없음).

- run 표, 5조건 × 유형별 탐지(정규식 주 지표와 보조 분석: 결함 페이지 탐지와 대조군 위양성), E9-1 강도·E9-2 영역별,
  구조적 탐지 불가 층, 반복 규칙(analysis_plan_e9.md 2절) 계산, 지출 합계.
- 반복 규칙: 주 지표 유형 t ∈ {E9-1, E9-2, E9-3}, 탐지율 = 정규식 주 지표로 탐지된 결함 페이지 / 그 유형 결함 페이지.
  D_cond(t, 쌍) = |두 조건의 탐지율(두 실행 평균) 차이|, D_run(t) = 다섯 조건 중 |1회차 − 2회차 탐지율| 의 최댓값.
  쌍: 관련 조항 제공 vs RAG 끔, 관련 조항 제공 vs 고정 질의, 관련 조항 제공 vs fixed-long, fixed-long vs RAG 끔.
  하나라도 D_cond < D_run 이면 3회째 규칙 발동(실행은 연구자 승인 후).

  python experiments/revision/e9_main_report.py
출력: results/revision/reports/e9_main_report.md, results/revision/e9/tables_main/*.csv
"""
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e9_regex_table as tbl   # noqa: E402

RUNS = "results/revision/runs_e9"
META = "testbed_e9/dataset_metadata_e9.json"
GT = "results/revision/e9/ground_truth_e9.csv"
OUT = "results/revision/reports/e9_main_report.md"
TAB = "results/revision/e9/tables_main"
CONDS = ["norag", "fixed", "page", "related", "fixedlong"]
CNAME = {"norag": "RAG 끔", "fixed": "고정 질의", "page": "페이지별 질의", "related": "관련 조항 제공", "fixedlong": "fixed-long"}
PAIRS = [("related", "norag"), ("related", "fixed"), ("related", "fixedlong"), ("fixedlong", "norag")]
MAIN_TYPES = ["E9-1", "E9-2", "E9-3"]
FAIL = ("api_error", "rag_empty", "rag_error", "acquisition_error")
USED = []


def use(p):
    if p not in USED:
        USED.append(p)
    return p


def table(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "|".join("---" for _ in h) + "|"] + \
           ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def jl(p):
    return [json.loads(l) for l in open(use(p), encoding="utf-8") if l.strip()]


def rid(c, r):
    return f"e9-main-{c}-r{r}"


def main():
    pages = {p["page_id"]: p for p in json.load(open(use(META), encoding="utf-8"))["pages"]}
    present = [(c, r) for r in (1, 2) for c in CONDS if os.path.exists(f"{RUNS}/{rid(c, r)}/reports.jsonl")]
    L = ["# E9 본 실험 보고서 (run 1, run 2; 2026-11-13)", "",
         "- 입력: `testbed_e9/` 91페이지(v3, `exp-freeze-e9-v3`), 5조건 × 2회.",
         "- 러너 `run_experiment_e9.py`, 순서 실행 `run_e9_main.py`.",
         "- 채점: 정규식 주 지표(`scoring/e9_rules.py`)와 보조 분석(`scoring/e9_rules_aux.py`)만. E9 LLM 판정과 의미 채점은 하지 않았다.",
         "- 기술 집계만(통계 검정 없음). 3회째와 E9-4 보조(390x844)는 실행하지 않았다.", ""]

    # 1. run 표
    L += ["## 1. run 표", ""]
    rows, tot = [], 0.0
    for c, r in present:
        d = f"{RUNS}/{rid(c, r)}"
        calls = jl(f"{d}/calls.jsonl")
        reps = jl(f"{d}/reports.jsonl")
        meta = json.load(open(use(f"{d}/run_meta.json"), encoding="utf-8"))
        aborted = os.path.exists(f"{d}/ABORTED.json")
        st = Counter(x["status"] for x in calls)
        fail = sum(st.get(k, 0) for k in FAIL)
        n = [len((x.get("report") or {}).get("issues") or []) for x in reps]
        cost = sum(x["cost_usd"]["total"] for x in calls)
        tot += cost
        conc = meta["args"]["concurrency"]
        rows.append([rid(c, r), "aborted" if aborted else "complete", f"{conc}{'' if conc == 2 else ' (계획과 다름)'}",
                     len(calls), st.get("ok", 0), st.get("parse_error", 0), f"{100 * fail / max(1, len(calls)):.1f}%",
                     sum(n), f"{cost:.4f}"])
    L += table(["run", "상태", "동시", "기록", "ok", "파싱 실패", "오류율", "이슈", "비용"], rows)
    L += ["", f"E9 본 실험 비용 합계: ${tot:.4f} ({sum(int(x[3]) for x in rows)}호출).", "",
          "출처: `" + RUNS + "/e9-main-{조건}-r{회차}/calls.jsonl`, `reports.jsonl`, `run_meta.json`", ""]

    # 2. 탐지 (주 지표·보조)
    os.makedirs(TAB, exist_ok=True)
    det = {}
    allrows = []
    for c, r in present:
        d = f"{RUNS}/{rid(c, r)}"
        dd = tbl.score_run(d, pages)
        det[(c, r)] = dd
        allrows += tbl.table_rows(c, rid(c, r), dd, pages)
    with open(f"{TAB}/e9_regex_primary_vs_aux.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allrows[0])); w.writeheader(); w.writerows(allrows)
    use(f"{TAB}/e9_regex_primary_vs_aux.csv")
    controls = [p for p, m in pages.items() if m["defect_id"] is None]
    groups = [("E9-1", lambda m: m["defect_id"] == "E9-1"), ("E9-1a", lambda m: m["subtype"] == "E9-1a"),
              ("E9-1b", lambda m: m["subtype"] == "E9-1b"), ("E9-2", lambda m: m["defect_id"] == "E9-2"),
              ("E9-2 배너", lambda m: m["subtype"] == "E9-2-banner"), ("E9-2 헤더", lambda m: m["subtype"] == "E9-2-header"),
              ("E9-2 푸터", lambda m: m["subtype"] == "E9-2-footer"), ("E9-3", lambda m: m["defect_id"] == "E9-3"),
              ("E9-4 (보조)", lambda m: m["defect_id"] == "E9-4")]
    L += ["## 2. 5조건별 유형별 탐지 (정규식)", "",
          "칸 = run 1 / run 2. 결함 = 탐지된 결함 페이지 수 / 그 유형 결함 페이지 수. 대조군 = 그 유형으로 탐지된 대조군 수 / 30.",
          "E9-4 는 1280x800 실행에 포함된 보조 유형이며 주 지표가 아니다.", ""]
    for rule, rname in (("primary", "주 지표 (그 페이지에 주입된 변형 문구만 인정)"), ("aux", "보조 분석 (6개 변형 문구를 모든 페이지에 적용)")):
        for part, conds in (("a", CONDS[:3]), ("b", CONDS[3:])):
            L += [f"### 2.{1 if rule == 'primary' else 2}{part} {rname}: {', '.join(CNAME[c] for c in conds)}", ""]
            rows = []
            for name, sel in groups:
                typ = name.split()[0][:4]
                pos = [p for p, m in pages.items() if sel(m)]
                row = [name, len(pos)]
                for c in conds:
                    cells = []
                    for r in (1, 2):
                        if (c, r) not in det:
                            cells.append("-"); continue
                        dd = det[(c, r)]
                        cells.append(f"{sum(dd[p][rule][typ] for p in pos)}")
                    row.append("/".join(cells))
                    fps = []
                    for r in (1, 2):
                        fps.append("-" if (c, r) not in det else str(sum(det[(c, r)][p][rule][typ] for p in controls)))
                    row.append("/".join(fps))
                rows.append(row)
            hdr = ["유형", "결함 페이지"]
            for c in conds:
                hdr += [f"{CNAME[c]} 결함", f"{CNAME[c]} 대조군"]
            L += table(hdr, rows)
            L += [""]
    L += ["출처:", f"- `{TAB}/e9_regex_primary_vs_aux.csv`", "  (`experiments/revision/e9_regex_table.py` 의 score_run 으로 계산)",
          "- run 별 `reports.jsonl`", ""]

    # 3. 구조적 탐지 불가 층
    gt = list(csv.DictReader(open(use(GT), encoding="utf-8")))
    und = [g for g in gt if g.get("structurally_undetectable") == "1"]
    L += ["## 3. 구조적 탐지 불가 층", "",
          f"결정적 검증(`{GT}`)에서 구조적 탐지 불가",
          f"(앞 5,000자 밖 또는 1280x800 뷰포트 밖) 결함은 **{len(und)}페이지**다.",
          "따라서 이 층은 비어 있고, 2절의 결함 페이지는 모두 '탐지 가능' 층이다. E9-3(목적지만 바뀜)과 E9-4(768px 이하에서만 숨김)는",
          "정의상 화면만으로는 보이지 않는 결함이지만, 링크 요소와 주입 문자열은 HTML 앞 5,000자와 뷰포트 안에 있다(설계 §3).", ""]

    # 4. 반복 규칙
    L += ["## 4. 반복 규칙 (analysis_plan_e9.md 2절, 정규식 주 지표, 주 지표 유형 E9-1·E9-2·E9-3)", ""]
    both = all((c, r) in det for c in CONDS for r in (1, 2))
    if not both:
        L += ["run 1·run 2 가 모두 끝나지 않아 계산하지 않았다.", ""]
    else:
        rate = {}
        for t in MAIN_TYPES:
            pos = [p for p, m in pages.items() if m["defect_id"] == t]
            for c in CONDS:
                for r in (1, 2):
                    rate[(t, c, r)] = sum(det[(c, r)][p]["primary"][t] for p in pos) / len(pos)
        L += ["### 4.1 탐지율 (run 1 / run 2 / 평균)", ""]
        for part in (CONDS[:3], CONDS[3:]):
            L += table(["유형"] + [CNAME[c] for c in part],
                       [[t] + [f"{rate[(t, c, 1)]:.3f} / {rate[(t, c, 2)]:.3f} / {(rate[(t, c, 1)] + rate[(t, c, 2)]) / 2:.3f}"
                               for c in part] for t in MAIN_TYPES])
            L += [""]
        drun = {t: max(abs(rate[(t, c, 1)] - rate[(t, c, 2)]) for c in CONDS) for t in MAIN_TYPES}
        rows, trig = [], []
        for t in MAIN_TYPES:
            for a, b in PAIRS:
                dc = abs((rate[(t, a, 1)] + rate[(t, a, 2)]) / 2 - (rate[(t, b, 1)] + rate[(t, b, 2)]) / 2)
                hit = dc < drun[t]
                if hit:
                    trig.append((t, a, b))
                rows.append([t, f"{CNAME[a]} vs {CNAME[b]}", f"{dc:.3f}", f"{drun[t]:.3f}", "예" if hit else "아니오"])
        L += ["### 4.2 D_cond 와 D_run", ""]
        L += table(["유형", "비교 쌍", "D_cond", "D_run", "D_cond < D_run"], rows)
        L += ["", f"- **판정: {'3회째 규칙 발동' if trig else '3회째 규칙 발동하지 않음'}**"
              + (f" (D_cond < D_run 인 경우 {len(trig)}건)." if trig else "."),
              "- 3회째는 연구자 승인 후에만 실행한다(자동으로 시작하지 않았다).", "",
              f"출처: `{TAB}/e9_regex_primary_vs_aux.csv`, run 별 `reports.jsonl`", ""]

    # 5. 지출
    subprocess.run([sys.executable, "experiments/revision/spend_summary.py"], capture_output=True, check=True)
    s = json.load(open(use("results/revision/tables/spend_summary.json"), encoding="utf-8"))
    pilot = 0.0
    for d in sorted(os.listdir("results/revision/runs_e9_pilot")):
        pilot += sum(c["cost_usd"]["total"] for c in jl(f"results/revision/runs_e9_pilot/{d}/calls.jsonl"))
    probe = jl("results/revision/semantic_scores/probe-E1-R1/probe.jsonl")
    pc = sum(x["input_tokens"] for x in probe) * 2 / 1e6 + sum(x["output_tokens"] for x in probe) * 10 / 1e6
    L += ["## 5. 지출 합계", ""]
    L += table(["항목", "비용 (USD)"],
               [["Gemini: testbed_200 run (pilot·aborted 포함)", f"{s['recorded_total_usd']:.4f}"],
                ["Gemini: E9 파일럿 2회", f"{pilot:.4f}"], ["Gemini: E9 본 실험 (이 보고서 1절)", f"{tot:.4f}"],
                ["**Gemini 합계**", f"**{s['recorded_total_usd'] + pilot + tot:.4f}**"],
                ["Anthropic: 의미 채점 시험 호출 20건 (표준가)", f"{pc:.4f}"]])
    e = s["unlogged_estimates"][0]["cost_usd"]
    L += ["", f"- E1-R3 미기록 과금 가능 추정 ${e['likely']:.4f}~${e['high_max_based']:.4f} 는 위 합계에 넣지 않았다.",
          "- 고정 질의 임베딩 1회와 File API 업로드는 비용 기록 대상이 아니다.", "",
          "출처:", "- `results/revision/tables/spend_summary.json`", "- `results/revision/runs_e9_pilot/{run}/calls.jsonl`",
          "- `results/revision/runs_e9/{run}/calls.jsonl`", "- `results/revision/semantic_scores/probe-E1-R1/probe.jsonl`", ""]

    L += ["## 6. 이 보고서에 사용한 파일", ""]
    L += table(["경로", "SHA-256 앞 16자리"], [[f"`{p}`", hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]]
                                          for p in USED if os.path.isfile(p) and "runs_e9_pilot" not in p and "probe" not in p])
    L += ["", "생성 스크립트: `experiments/revision/e9_main_report.py`", ""]
    L = [x for l in L for x in str(l).split("\n")]
    bad = [l for l in L if len(l) > 100]
    if bad:
        raise SystemExit("lines over 100 chars:\n" + "\n".join(f"{len(l)}: {l}" for l in bad))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(OUT)


if __name__ == "__main__":
    sys.exit(main())
