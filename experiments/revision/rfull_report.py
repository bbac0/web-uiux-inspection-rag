"""
R-full 보고서 (API 호출 없음). 사전 지정: results/revision/analysis_plan_addendum_rfull.md (f9b9067).

입력(읽기만): results/revision/runs/{E1-Rfull-r1,E1-R1,E2-A1-1}/, results/revision/issue_tables_merged/{run}.csv,
      results/revision/semantic_scores/E1-Rfull-r1-sem-p1[-retry]/grades.jsonl
지표 계산은 experiments/revision/e7_final.py 의 cell_block, pair_block 을 그대로 쓴다(템플릿 짝 군집 부트스트랩
B=10,000, 시드 20261111). R1·A1-1 의 값은 results/revision/e7_final/ CSV 와 대조해 일치 여부를 적는다.

  python experiments/revision/rfull_report.py
출력(덮어쓰지 않음): results/revision/rfull/{cell_metrics.csv, paired.csv}, results/revision/reports/rfull_report.md
"""
import csv
import glob
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e7_stats as e7          # noqa: E402
from experiments.revision import e7_final as e7f         # noqa: E402
from scoring import semantic_grader_anthropic as sga     # noqa: E402

RF, R1, A1 = "E1-Rfull-r1", "E1-R1", "E2-A1-1"
RUNS = [RF, R1, A1]
NAME = {RF: "R-full", R1: "R1", A1: "A1-1 (RAG 끔)"}
OUTD = "results/revision/rfull"
REP = "results/revision/reports/rfull_report.md"
SEM = "results/revision/semantic_scores"
SC = ["sem_merged", "keyword", "string_match"]
SCK = {"sem_merged": "의미(병합)", "keyword": "키워드", "string_match": "string_match"}
LAYS = ["nominal", "effective"]


def jl(p):
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()] if os.path.exists(p) else []


def tab(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def grading_cost(out_id):
    g = jl(f"{SEM}/{out_id}/grades.jsonl")
    b = [x for x in g if x.get("mode") == "batch"]
    st = Counter("truncated" if x.get("truncated") else x["status"] for x in g)
    usd = sum((x.get("input_tokens") or 0) + 5 * (x.get("output_tokens") or 0) for x in b) / 1e6
    return len(g), st, usd


def citation(rid):
    calls = {c["page_id"]: c for c in jl(f"results/revision/runs/{rid}/calls.jsonl")}
    cnt = Counter()
    for iid, s, iss in sga.iter_run_issues(rid):
        sf, pn = iss.get("source_file"), iss.get("page_number")
        cnt["n"] += 1
        if sf in (None, "", "N/A"):
            cnt["miss"] += 1
        elif sf in ("gov_guide.pdf", "gov_check.pdf"):
            cnt[sf] += 1
        else:
            cnt["out"] += 1
        pl = pn if isinstance(pn, list) else ([pn] if pn not in (None, "") else [])
        cnt["empty_pn"] += not pl
        cnt["pn12"] += pl == [12]
        ch = ((calls.get(s["page_id"]) or {}).get("rag") or {}).get("chunks") or []
        prov = {(c.get("source"), c.get("page")) for c in ch}
        cnt["prov"] += any((sf, p) in prov for p in pl if isinstance(p, int))
    return cnt


def main():
    for p in (OUTD, REP):
        if os.path.exists(p):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {p}")
    pages, tmpl, templates = e7.load_pages()
    layers = {k: v for k, v in e7.load_layers().items() if k in LAYS}
    preds = {}
    for rid in RUNS:
        P, ok = e7f.load_merged_preds(rid, pages)
        if not ok:
            raise SystemExit(f"{rid}: 병합 통합표 없음")
        preds[rid] = {k: P[k] for k in SC}
    W = e7f.boot_weights(len(templates))
    cells, store = e7f.cell_block(RUNS, preds, layers, pages, tmpl, templates, W, SC, "R-full")
    pairs = e7f.pair_block([(RF, R1, "R-full − R1"), (RF, A1, "R-full − A1-1")], store, SC, layers, W, len(templates),
                           "R-full")
    os.makedirs(OUTD)
    for name, rows in (("cell_metrics.csv", cells), ("paired.csv", pairs)):
        with open(f"{OUTD}/{name}", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    # 기존 E7 최종과 대조 (R1, A1-1)
    ref = {(r["run"], r["scorer"], r["label"], r["type"]): r for r in csv.DictReader(
        open("results/revision/e7_final/cell_metrics.csv", encoding="utf-8-sig")) if r["block"] == "E1/A1"}
    keys = ["TP", "FP", "FN", "TN", "precision", "recall", "mcc", "mcc_ci_lo", "mcc_ci_hi"]
    chk = [all(str(r[k]) == ref[(r["run"], r["scorer"], r["label"], r["type"])][k] for k in keys)
           for r in cells if r["run"] in (R1, A1) and (r["run"], r["scorer"], r["label"], r["type"]) in ref]
    write_report(cells, pairs, chk)
    print(f"{REP}; e7_final match {sum(chk)}/{len(chk)}")


def write_report(cells, pairs, chk):
    C = {(r["run"], r["scorer"], r["label"], r["type"]): r for r in cells}
    calls = jl(f"results/revision/runs/{RF}/calls.jsonl")
    summ = json.load(open(f"results/revision/runs/{RF}/summary.json", encoding="utf-8"))
    meta = json.load(open(f"results/revision/runs/{RF}/run_meta.json", encoding="utf-8"))
    L = ["# R-full 보고서: 전체 색인으로 주 조건 R 1회 재실행", "",
         "작성: `experiments/revision/rfull_report.py`.",
         "사전 지정: `results/revision/analysis_plan_addendum_rfull.md` (f9b9067).",
         "숫자만 적는다(해석 없음). 구간은 짝 템플릿 군집 부트스트랩(B 10,000, 시드 20261111, 백분위 95%).",
         f"검증: 같은 함수로 다시 계산한 R1·A1-1 셀 지표가 `e7_final/cell_metrics.csv` 와 {sum(chk)}/{len(chk)} 일치.", ""]
    # 1) 호출·오류·비용
    st = Counter(c["status"] for c in calls)
    rows = [["생성 (Gemini, E1-Rfull-r1)", len(calls), ", ".join(f"{k} {v}" for k, v in sorted(st.items())),
             f"{summ['cost_usd_total']:.4f}"]]
    tot = summ["cost_usd_total"]
    for o in sorted(d for d in os.listdir(SEM) if d.startswith(f"{RF}-sem")):
        n, s, usd = grading_cost(o)
        rows.append([f"의미 채점 배치 ({o})", n, ", ".join(f"{k} {v}" for k, v in sorted(s.items())), f"{usd:.4f}"])
        tot += usd
    rows.append(["합계", "", "", f"{tot:.4f}"])
    L += ["## 1. 호출·오류·비용", ""] + tab(["항목", "호출", "상태", "USD"], rows)
    L += ["", f"출처: `results/revision/runs/{RF}/calls.jsonl`, `summary.json`,", f"`{SEM}/{RF}-sem-*/grades.jsonl`",
          "생성 비용은 러너가 호출마다 기록한 값의 합, 채점 비용은 배치 단가 $1/$5 per 1M(입력/출력) × 기록 토큰.",
          f"실행 시각(UTC): {summ['started_utc']} ~ {summ['finished_utc']}. 중단: {summ.get('aborted')}.", ""]
    # 2) 검색 청크
    sets = Counter(tuple((x["source"], x["page"]) for x in c["rag"]["chunks"]) for c in calls)
    L += ["## 2. 고정 질의로 검색된 4청크", ""]
    L += tab(["4청크 (문서, 쪽)", "페이지 수"], [[" / ".join(f"{s} {p}" for s, p in k), v] for k, v in sets.most_common()])
    L += ["", f"색인 원본: `{meta['chroma']['source']}` (러너가 임시 폴더로 복사해 사용). 출처: `calls.jsonl` 의 rag.chunks", ""]
    # 3) 지표
    L += ["## 3. 셀 지표 (마이크로 5유형과 유형별)", ""]
    for sc in SC:
        for lay in LAYS:
            rows = []
            for rid in RUNS:
                for t in ["micro (5 types)", "Contrast", "Mobile", "Button", "Terminology", "DupID"]:
                    r = C.get((rid, sc, lay, t))
                    if r:
                        rows.append([NAME[rid], e7f.TS.get(t, t), r["TP"], r["FP"], r["FN"], r["TN"],
                                     r["precision"] or "정의 안 됨", r["recall"] or "정의 안 됨", r["mcc"] or "정의 안 됨",
                                     f"[{r['mcc_ci_lo']},{r['mcc_ci_hi']}]" if r["mcc_ci_lo"] != "" else "-"])
            if rows:
                L += [f"### {SCK[sc]}, {lay}", ""] + tab(["run", "유형", "TP", "FP", "FN", "TN", "P", "R", "MCC", "MCC CI"], rows)
                L += ["", f"출처: `{OUTD}/cell_metrics.csv`", ""]
    # 4) 짝 비교
    L += ["## 4. MCC 차이 (짝 템플릿 군집 부트스트랩)", ""]
    u = lambda v: v if v != "" else "정의 안 됨"      # noqa: E731
    rows = [[r["role"], SCK[r["scorer"]], r["label"], e7f.TS.get(r["type"], r["type"]), u(r["mcc_a"]), u(r["mcc_b"]),
             u(r["mcc_diff"]), f"[{r['mcc_diff_ci_lo']},{r['mcc_diff_ci_hi']}]" if r["mcc_diff_ci_lo"] != "" else "-"]
            for r in pairs]
    L += tab(["비교", "채점", "라벨", "유형", "MCC a", "MCC b", "차이", "95% 구간"], rows)
    L += ["", f"출처: `{OUTD}/paired.csv`", ""]
    # 5) 용어
    L += ["## 5. 표준 용어 유형 (nominal)", ""]
    rows = []
    for sc in SC:
        for rid in RUNS:
            r = C.get((rid, sc, "nominal", "Terminology"))
            if r:
                rows.append([SCK[sc], NAME[rid], int(r["TP"]) + int(r["FP"]), r["TP"], r["FP"]])
    L += tab(["채점", "run", "탐지 페이지", "TP", "FP"], rows) + ["", f"출처: `{OUTD}/cell_metrics.csv`", ""]
    # 6) 인용
    L += ["## 6. 출처 인용 점검 (대상 이슈의 source_file, page_number; paper_numbers 10절과 같은 정의)", ""]
    rows = []
    for rid in (RF, R1, A1):
        c = citation(rid)
        rows.append([NAME[rid], c["n"], c["gov_guide.pdf"], c["gov_check.pdf"], c["out"], c["miss"], c["pn12"], c["prov"],
                     f"{c['prov'] / c['n']:.3f}" if c["n"] else "-"])
    L += tab(["run", "이슈", "guide", "check", "코퍼스 밖", "결측", "쪽 [12]", "제공 청크 일치", "비율"], rows)
    L += ["", "출처: `results/revision/runs/{run}/reports.jsonl`, `calls.jsonl` (rag.chunks)", ""]
    open(REP, "w", encoding="utf-8", newline="\n").write("\n".join(L))


if __name__ == "__main__":
    main()
