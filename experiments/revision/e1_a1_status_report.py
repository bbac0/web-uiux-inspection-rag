"""
E1/E2-A1 진행 보고용 기술 집계 (API 호출 없음, 통계 검정 없음 — E7 은 승인 후).

  run 별: 상태, 파싱 실패, 오류율, 이슈 수 분포, 총비용, 모델 버전, RAG 청크 수
  E1-R1/R2/R3b vs E2-A1-1~3: 유형별 '키워드 채점으로 탐지된 페이지 수' (nominal / effective 양성 페이지 기준) + string_match(용어)

출력: results/revision/tables/e1_a1_status.md, e1_a1_type_detection.csv
"""
import csv
import json
import os
import statistics
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from scoring import issue_table                 # noqa: E402
from experiments.revision import label_layers   # noqa: E402

RUNS = "results/revision/runs"
ORDER = ["E1-R1", "E2-A1-1", "E1-R2", "E2-A1-2", "E1-R3", "E1-R3b", "E2-A1-3"]
COMPARE = ["E1-R1", "E1-R2", "E1-R3b", "E2-A1-1", "E2-A1-2", "E2-A1-3"]   # E1-R3 은 aborted → 분석 제외
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]


def run_row(rid):
    d = os.path.join(RUNS, rid)
    if not os.path.isdir(d):
        return {"run_id": rid, "state": "not started"}
    recs = [json.loads(l) for l in open(os.path.join(d, "calls.jsonl"), encoding="utf-8")]
    meta = json.load(open(os.path.join(d, "run_meta.json"), encoding="utf-8"))
    aborted = os.path.exists(os.path.join(d, "ABORTED.json"))
    summ = json.load(open(os.path.join(d, "summary.json"), encoding="utf-8")) if os.path.exists(os.path.join(d, "summary.json")) else {}
    st = Counter(r["status"] for r in recs)
    req = len(meta["pages"])
    fail = sum(v for k, v in st.items() if k in ("api_error", "rag_empty", "rag_error", "acquisition_error"))
    n_iss = [len((json.loads(l).get("report") or {}).get("issues", []) or []) for l in open(os.path.join(d, "reports.jsonl"), encoding="utf-8")]
    return {"run_id": rid, "state": "aborted" if aborted else ("complete" if summ.get("aborted") is False else "?"),
            "condition": meta["condition"], "concurrency": meta["args"]["concurrency"], "rag": not meta["args"]["no_rag"],
            "pages_requested": req, "pages_recorded": len({r["page_id"] for r in recs}),
            "ok": st.get("ok", 0), "parse_error": st.get("parse_error", 0), "failed": fail,
            "error_rate": fail / max(1, len(recs)), "issues_total": sum(n_iss),
            "issues_mean": round(statistics.mean(n_iss), 2), "issues_median": statistics.median(n_iss),
            "issues_min": min(n_iss), "issues_max": max(n_iss),
            "cost_usd": round(sum(r["cost_usd"]["total"] for r in recs), 4),
            "model_versions": ";".join(sorted({r["model_version"] for r in recs if r.get("model_version")})),
            "rag_chunks": ";".join(f"{k}:{v}" for k, v in sorted(Counter(str(r["rag"]["n_chunks"]) for r in recs).items())),
            "started_utc": meta["started_utc"], "last_end_utc": max(r["ts_end_utc"] for r in recs)}


def detected_pages(rid):
    det = {t: set() for t in TYPES}
    sm = set()
    for r in issue_table.build_rows(rid):
        for t in filter(None, r["keyword_types"].split(";")):
            det[t].add(r["page_id"])
        if r["string_match_term"]:
            sm.add(r["page_id"])
    return det, sm


def main():
    rows = [run_row(r) for r in ORDER]
    nom, _ = label_layers.load_labels("nominal")
    eff, _ = label_layers.load_labels("effective")
    pos = lambda lab, t: {p for (p, tt), v in lab.items() if tt == t and v}
    neg = lambda lab, t: {p for (p, tt), v in lab.items() if tt == t and v == 0}
    comp = []
    cmp_runs = [r for r in COMPARE if os.path.exists(os.path.join(RUNS, r, "SHA256SUMS"))
                and not os.path.exists(os.path.join(RUNS, r, "ABORTED.json"))]
    dets = {rid: detected_pages(rid) for rid in cmp_runs}
    for t in TYPES:
        for lab_name, lab in (("nominal", nom), ("effective", eff)):
            row = {"defect_type": t, "label": lab_name, "positives": len(pos(lab, t))}
            for rid in cmp_runs:
                d = dets[rid][0][t]
                row[f"{rid}_tp_pages"] = len(d & pos(lab, t))
                row[f"{rid}_fp_pages"] = len(d & neg(lab, t))
            comp.append(row)
    for lab_name, lab in (("nominal", nom), ("effective", eff)):
        t = "Standard Terminology Violation"
        row = {"defect_type": t + " [string_match, mention-based]", "label": lab_name, "positives": len(pos(lab, t))}
        for rid in cmp_runs:
            d = dets[rid][1]
            row[f"{rid}_tp_pages"] = len(d & pos(lab, t))
            row[f"{rid}_fp_pages"] = len(d & neg(lab, t))
        comp.append(row)
    out = "results/revision/tables"
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "e1_a1_type_detection.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(comp[0])); w.writeheader(); w.writerows(comp)
    L = ["# E1 / E2-A1 진행 보고 (기술 집계, 통계 검정 없음)", "", "## run 별 상태", "",
         "| run | 상태 | 조건 | 동시 | 요청 | 기록 | ok | 파싱 실패 | 오류 | 오류율 | 이슈 합계 | 이슈/페이지 평균 (중앙값, 범위) | 비용 | RAG 청크 | 기간(UTC) |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|"]
    for r in rows:
        if r["state"] == "not started":
            L.append(f"| {r['run_id']} | 시작 안 됨 | | | | | | | | | | | | | |"); continue
        L.append(f"| {r['run_id']} | {r['state']} | {r['condition']} | {r['concurrency']} | {r['pages_requested']} | {r['pages_recorded']} | "
                 f"{r['ok']} | {r['parse_error']} | {r['failed']} | {100 * r['error_rate']:.1f}% | {r['issues_total']} | "
                 f"{r['issues_mean']} ({r['issues_median']}, {r['issues_min']}~{r['issues_max']}) | ${r['cost_usd']:.2f} | {r['rag_chunks']} | "
                 f"{r['started_utc'][11:19]}~{r['last_end_utc'][11:19]} |")
    L += ["", f"- 모델 버전: {', '.join(sorted({r['model_versions'] for r in rows if r.get('model_versions')}))}",
          "", "## E1 (RAG 켬) vs E2-A1 (RAG 끔): 유형별 키워드 채점 탐지 페이지 수", "",
          f"비교 run: {', '.join(cmp_runs)} (E1-R3 은 aborted 로 제외).", "",
          "키워드 사전(수정 없음, description 만)으로 해당 유형 이슈가 1건 이상 있는 페이지 수. TP = 정답 양성 페이지 중 탐지, FP = 정답 음성 페이지 중 탐지.",
          "주 채점기(의미 채점)와 통계 검정은 승인 후 E7 에서 계산한다.", "",
          "| 유형 | 라벨 | 양성 페이지 | " + " | ".join(f"{r} TP" for r in cmp_runs) + " | " + " | ".join(f"{r} FP" for r in cmp_runs) + " |",
          "|---|---|---:|" + "---:|" * (2 * len(cmp_runs))]
    for c in comp:
        L.append(f"| {c['defect_type']} | {c['label']} | {c['positives']} | "
                 + " | ".join(str(c[f"{r}_tp_pages"]) for r in cmp_runs) + " | "
                 + " | ".join(str(c[f"{r}_fp_pages"]) for r in cmp_runs) + " |")
    open(os.path.join(out, "e1_a1_status.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
