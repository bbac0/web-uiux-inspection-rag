"""
E9 3회째 보고서 (fixed-long, RAG 끔; API 호출 없음, 통계 검정 없음). analysis_plan_e9.md 사전 수정 (exp-freeze-e9-v4) (b) 방식.

- (1) 두 r3 run 의 상태, 동시 실행, 기록, 오류율, 이슈, 비용
- (2) 두 조건의 유형별 탐지(주 지표·보조 분석, 결함 페이지와 대조군 위양성) r1, r2, r3 나란히
- (3) D_run(t) = 다섯 조건 중 실행 간 최대 차이(fixed-long·RAG 끔은 3회 max−min, 나머지는 |r1−r2|),
      D_cond(t) = |fixed-long 3회 평균 − RAG 끔 3회 평균|, t ∈ {E9-1, E9-2, E9-3}
- (4) 지출 합계 갱신, (5) exp-freeze-e9-v4 해시 변경 목록
출력: results/revision/reports/e9_main_report_r3.md
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e9_regex_table as tbl   # noqa: E402

RUNS = "results/revision/runs_e9"
META = "testbed_e9/dataset_metadata_e9.json"
OUT = "results/revision/reports/e9_main_report_r3.md"
CONDS = ["norag", "fixed", "page", "related", "fixedlong"]
R3 = ["norag", "fixedlong"]
CNAME = {"norag": "RAG 끔", "fixed": "고정 질의", "page": "페이지별 질의", "related": "관련 조항 제공", "fixedlong": "fixed-long"}
MAIN = ["E9-1", "E9-2", "E9-3"]
FAIL = ("api_error", "rag_empty", "rag_error", "acquisition_error")


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def src(*p):
    return ["", "출처:"] + [f"- `{x}`" for x in p] + [""]


def reps_of(c, r):
    return [c_ for c_ in (1, 2, 3) if os.path.exists(f"{RUNS}/e9-main-{c}-r{c_}/reports.jsonl")] if r is None else None


def main():
    pages = {p["page_id"]: p for p in json.load(open(META, encoding="utf-8"))["pages"]}
    runs = {c: [r for r in (1, 2, 3) if os.path.exists(f"{RUNS}/e9-main-{c}-r{r}/reports.jsonl")] for c in CONDS}
    L = ["# E9 본 실험 3회째 보고 (fixed-long, RAG 끔)", "",
         "작성: `experiments/revision/e9_main_report_r3.py` (API 호출 없음, 기술 집계만, 통계 검정 없음).",
         "사전 수정: `results/revision/e9/analysis_plan_e9.md` (`exp-freeze-e9-v4`) — 3회째는 fixed-long 과 RAG 끔만,",
         "나머지 세 조건은 2회 보고. E9 LLM 판정과 E9-4 보조(390x844)는 하지 않는다. 실행: `experiments/revision/run_e9_r3.py`.", ""]

    # (1)
    L += ["## 1. 3회째 run", "", "| run | 상태 | 동시 실행 | 기록 | 상태별 | 오류율 | 이슈 | 비용 (USD) |",
          "|---|---|---|---|---|---|---|---|"]
    tot_r3 = 0.0
    for c in R3:
        rid = f"e9-main-{c}-r3"
        d = f"{RUNS}/{rid}"
        if not os.path.exists(f"{d}/run_meta.json"):
            L.append(f"| {rid} | 없음 | | | | | | |"); continue
        meta = json.load(open(f"{d}/run_meta.json", encoding="utf-8"))
        calls, reps = jl(f"{d}/calls.jsonl"), jl(f"{d}/reports.jsonl")
        st = {}
        for x in calls:
            st[x["status"]] = st.get(x["status"], 0) + 1
        fail = sum(v for k, v in st.items() if k in FAIL)
        cost = sum(x["cost_usd"]["total"] for x in calls)
        tot_r3 += cost
        aborted = os.path.exists(f"{d}/ABORTED.json")
        n_iss = sum(len((r.get("report") or {}).get("issues") or []) for r in reps)
        conc = (meta.get("args") or {}).get("concurrency", "?")
        L.append(f"| {rid} | {'aborted' if aborted else 'complete'} | {conc} | {len(calls)} | "
                 f"{', '.join(f'{k} {v}' for k, v in sorted(st.items()))} | {100 * fail / max(1, len(calls)):.1f}% | "
                 f"{n_iss} | {cost:.4f} |")
    L += ["", f"두 run 비용 합계 ${tot_r3:.4f} (상한 $2.5). 잠금 확인은 각 run 의 SHA256SUMS (러너)."]
    L += src(f"{RUNS}/e9-main-{{norag,fixedlong}}-r3/calls.jsonl", "reports.jsonl, run_meta.json")

    # (2)
    det = {}
    for c in CONDS:
        for r in runs[c]:
            det[(c, r)] = tbl.score_run(f"{RUNS}/e9-main-{c}-r{r}", pages)
    L += ["## 2. 유형별 탐지 (fixed-long, RAG 끔; r1 / r2 / r3)", "",
          "칸 = 탐지 결함 페이지/결함 페이지 (r1 / r2 / r3). 대조군 = 위양성 페이지/30. 주 지표 = 그 페이지의 주입 변형 문구만 인정,",
          "보조 = 6개 변형 문구를 모든 페이지에 적용(E9-1 만 다름). E9-4 는 주 지표 아님.", ""]
    for c in R3:
        L += [f"### {CNAME[c]}", "", "| 유형 | 규칙 | 결함 탐지 r1 / r2 / r3 | 대조군 위양성 r1 / r2 / r3 |", "|---|---|---|---|"]
        rows = {r: tbl.table_rows(c, f"e9-main-{c}-r{r}", det[(c, r)], pages) for r in runs[c]}
        for i, base in enumerate(rows[runs[c][0]]):
            cells_d = " / ".join(f"{rows[r][i]['detected']}/{rows[r][i]['defect_pages']}" for r in runs[c])
            cells_f = " / ".join(f"{rows[r][i]['control_detected']}/{rows[r][i]['controls']}" for r in runs[c])
            L.append(f"| {base['type']} | {'주 지표' if base['rule'] == 'primary' else '보조'} | {cells_d} | {cells_f} |")
        L += [""]
    L += src(f"{RUNS}/e9-main-{{조건}}-r{{1,2,3}}/reports.jsonl", "scoring/e9_rules.py", "scoring/e9_rules_aux.py")

    # (3)
    rate = {}
    for t in MAIN:
        pos = [p for p, m in pages.items() if m["defect_id"] == t]
        for c in CONDS:
            for r in runs[c]:
                rate[(t, c, r)] = sum(det[(c, r)][p]["primary"][t] for p in pos) / len(pos)
    L += ["## 3. 반복 규칙 재계산 (사전 수정 (b))", "",
          "탐지율 = 정규식 주 지표로 탐지된 결함 페이지 / 그 유형 결함 페이지.",
          "D_run(t) = 다섯 조건 중 실행 간 최대 차이(fixed-long·RAG 끔 = 3회 max−min, 나머지 = |r1 − r2|).",
          "D_cond(t) = |fixed-long 3회 평균 − RAG 끔 3회 평균|. 결과와 무관하게 4회째는 하지 않는다.", "",
          "### 3.1 탐지율", "", "| 유형 | 조건 | r1 | r2 | r3 | 평균 | 실행 간 최대 차이 |", "|---|---|---|---|---|---|---|"]
    drun, spread = {}, {}
    for t in MAIN:
        for c in CONDS:
            v = [rate[(t, c, r)] for r in runs[c]]
            spread[(t, c)] = max(v) - min(v)
            L.append(f"| {t} | {CNAME[c]} | " + " | ".join(f"{rate[(t, c, r)]:.3f}" if r in runs[c] else "-" for r in (1, 2, 3))
                     + f" | {sum(v) / len(v):.3f} | {spread[(t, c)]:.3f} |")
        drun[t] = max(spread[(t, c)] for c in CONDS)
    L += src(f"{RUNS}/e9-main-{{조건}}-r{{회차}}/reports.jsonl")
    L += ["### 3.2 fixed-long vs RAG 끔", "", "| 유형 | fixed-long 평균 | RAG 끔 평균 | D_cond | D_run | D_run 조건 | D_cond < D_run |",
          "|---|---|---|---|---|---|---|"]
    for t in MAIN:
        fl = sum(rate[(t, "fixedlong", r)] for r in runs["fixedlong"]) / len(runs["fixedlong"])
        nr = sum(rate[(t, "norag", r)] for r in runs["norag"]) / len(runs["norag"])
        dc = abs(fl - nr)
        arg = ", ".join(CNAME[c] for c in CONDS if abs(spread[(t, c)] - drun[t]) < 1e-12)
        L.append(f"| {t} | {fl:.3f} | {nr:.3f} | {dc:.3f} | {drun[t]:.3f} | {arg} | {'예' if dc < drun[t] else '아니오'} |")
    L += ["", f"평균에 쓴 회차 수: fixed-long {len(runs['fixedlong'])}회, RAG 끔 {len(runs['norag'])}회."]
    L += src(f"{RUNS}/e9-main-{{조건}}-r{{회차}}/reports.jsonl", "results/revision/e9/analysis_plan_e9.md")

    # (4) 지출
    subprocess.run([sys.executable, "experiments/revision/spend_summary.py"], capture_output=True, check=True)
    s = json.load(open("results/revision/tables/spend_summary.json", encoding="utf-8"))
    pilot = sum(x["cost_usd"]["total"] for d in sorted(os.listdir("results/revision/runs_e9_pilot"))
                for x in jl(f"results/revision/runs_e9_pilot/{d}/calls.jsonl"))
    e9 = {r: sum(x["cost_usd"]["total"] for c in CONDS for x in jl(f"{RUNS}/e9-main-{c}-r{r}/calls.jsonl")) for r in (1, 2, 3)}
    probe = jl("results/revision/semantic_scores/probe-E1-R1/probe.jsonl")
    pc = sum(x["input_tokens"] for x in probe) * 2 / 1e6 + sum(x["output_tokens"] for x in probe) * 10 / 1e6
    sem = 0.0
    for d in sorted(os.listdir("results/revision/semantic_scores")):
        g = f"results/revision/semantic_scores/{d}/grades.jsonl"
        for x in jl(g):
            if x.get("mode") == "batch":
                sem += ((x.get("input_tokens") or 0) * 1 + (x.get("output_tokens") or 0) * 5) / 1e6
    emb = [json.loads(l) for p in ("results/revision/e9/page_query_embedding/call_log.jsonl",
                                   "results/revision/e9/page_query_embedding_attempt1_failed/call_log.jsonl")
           for l in open(p, encoding="utf-8")]
    gem = s["recorded_total_usd"] + pilot + e9[1] + e9[2] + e9[3]
    L += ["## 4. 지출 합계 (갱신)", "", "| 항목 | 비용 (USD) |", "|---|---|",
          f"| Gemini: testbed_200 run (pilot·aborted 포함) | {s['recorded_total_usd']:.4f} |",
          f"| Gemini: E9 파일럿 2회 | {pilot:.4f} |",
          f"| Gemini: E9 본 실험 1·2회차 | {e9[1] + e9[2]:.4f} |",
          f"| Gemini: E9 3회째 (이 보고서) | {e9[3]:.4f} |",
          f"| **Gemini 합계** | **{gem:.4f}** |",
          f"| Anthropic: 의미 채점 시험 호출 20건 (표준가) | {pc:.4f} |",
          f"| Anthropic: 의미 채점 배치 (배치 단가 $1/$5 per 1M, 확인 배치 포함) | {sem:.4f} |",
          f"| **Anthropic 합계** | **{pc + sem:.4f}** |",
          f"| 임베딩 (gemini-embedding-001, 페이지별 질의 {len(emb)}회, 추정 상한) | "
          f"{sum(x['cost_estimate_usd_upper'] for x in emb):.6f} |", ""]
    e = s["unlogged_estimates"][0]["cost_usd"]
    L += [f"- E1-R3 미기록 과금 가능 추정 ${e['likely']:.4f}~${e['high_max_based']:.4f} 는 합계에 넣지 않았다.",
          "- 고정 질의 임베딩 1회와 File API 업로드는 비용 기록 대상이 아니다. 의미 채점 재채점은 아직 제출 전이다.",
          "- Anthropic 금액은 토큰 기록 × 단가로 계산한 값이며 실제 청구는 콘솔 기준으로 확인해야 한다."]
    L += src("results/revision/tables/spend_summary.json", "results/revision/runs_e9_pilot/{run}/calls.jsonl",
             f"{RUNS}/{{run}}/calls.jsonl", "results/revision/semantic_scores/{out_id}/grades.jsonl",
             "results/revision/semantic_scores/probe-E1-R1/probe.jsonl", "results/revision/e9/page_query_embedding/call_log.jsonl")

    # (5)
    L += ["## 5. exp-freeze-e9-v4: v3 대비 해시 변경", ""]
    L += [l for l in open("results/revision/e9/freeze_e9_v4_diff.md", encoding="utf-8").read().splitlines()[2:]]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print(OUT, "long:", [i + 1 for i, l in enumerate(L) if len(l) > 100])


if __name__ == "__main__":
    main()
