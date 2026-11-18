"""
E7 보강 (2026-11-13 연구자 지시, API 호출 없음) — **added after seeing replicate results, before semantic scoring.**

사전 지정(analysis_plan.md 5절)에 덧붙이는 강건성 분석:
  RAG 켬 − 끔 쌍(R1 − A1-1, R2 − A1-2, R3b − A1-3)의 MCC, 정밀도, 특이도, 재현율 차이에 대한
  템플릿 짝 군집 부트스트랩 95% 구간(같은 재표집 템플릿을 두 조건에 함께 적용, B = 10,000, numpy default_rng 시드 20261111)과
  leave-one-template-out(LOTO) 차이(10개 값의 범위, jackknife SE)를 한 표에 낸다.
  기존 exact McNemar(셀 단위, 군집 미고려)는 보조로 같은 행에 붙이고 주석을 단다.

채점기: 키워드(5유형 micro, 유형별), string_match(용어 유형). 라벨 4층.
출력: results/revision/e7/paired_cluster_bootstrap.csv, paired_cluster_bootstrap.tex
"""
import csv
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e7_stats as e7   # noqa: E402

STATUS = "added after seeing replicate results, before semantic scoring"
PAIRS = [("E1-R1", "E2-A1-1", "primary comparison (pre-registered)"), ("E1-R2", "E2-A1-2", "replication"),
         ("E1-R3b", "E2-A1-3", "replication")]
MET = ["mcc", "precision", "specificity", "recall"]


def main():
    pages, tmpl, templates = e7.load_pages()
    layers = e7.load_layers()
    preds = {rid: e7.load_preds(rid, pages) for rid in e7.RUN_IDS}
    rng = np.random.default_rng(e7.SEED)
    draws = rng.integers(0, len(templates), size=(e7.B, len(templates)))
    W = np.stack([np.bincount(d, minlength=len(templates)) for d in draws]).astype(float)
    n_t = len(templates)
    mcn = {(r["comparison"], r["scorer"], r["label"], r["type"]): r
           for r in csv.DictReader(open(os.path.join(e7.OUT, "mcnemar.csv"), encoding="utf-8"))}
    rows = []
    for a, b, role in PAIRS:
        for sc in e7.SCORERS:
            tsets = [("micro", e7.TYPES)] + [(t, [t]) for t in e7.TYPES] if sc == "keyword" else [(e7.TERM, [e7.TERM])]
            for lay in e7.LAYERS:
                for tname, tl in tsets:
                    Ca = e7.counts_by_template(preds[a][sc], layers[lay], pages, tmpl, templates, tl)
                    Cb = e7.counts_by_template(preds[b][sc], layers[lay], pages, tmpl, templates, tl)
                    if Ca.sum() == 0:
                        continue
                    pa, pb = e7.metrics_from_counts(Ca.sum(0)), e7.metrics_from_counts(Cb.sum(0))
                    ba, bb = e7.metrics_from_counts(W @ Ca), e7.metrics_from_counts(W @ Cb)
                    la = e7.metrics_from_counts(Ca.sum(0)[None, :] - Ca)
                    lb = e7.metrics_from_counts(Cb.sum(0)[None, :] - Cb)
                    row = {"analysis_status": STATUS, "comparison": f"{a} - {b}", "role": role, "scorer": sc, "label": lay,
                           "type": e7.TSHORT[tname], "n_cells": int(Ca.sum())}
                    for m in MET:
                        d = ba[m] - bb[m]
                        ok = ~np.isnan(d)
                        lo, hi = np.percentile(d[ok], [2.5, 97.5]) if ok.any() else (np.nan, np.nan)
                        ld = la[m] - lb[m]
                        lok = ld[~np.isnan(ld)]
                        se = math.sqrt((n_t - 1) / n_t * np.sum((lok - lok.mean()) ** 2)) if len(lok) == n_t else float("nan")
                        row.update({f"{m}_on": e7.fmt(float(pa[m])), f"{m}_off": e7.fmt(float(pb[m])),
                                    f"{m}_diff": e7.fmt(float(pa[m] - pb[m])),
                                    f"{m}_diff_ci_lo": e7.fmt(float(lo)), f"{m}_diff_ci_hi": e7.fmt(float(hi)),
                                    f"{m}_ci_excludes_0": ("" if np.isnan(lo) else "yes" if (lo > 0 or hi < 0) else "no"),
                                    f"{m}_boot_undefined": int((~ok).sum()),
                                    f"{m}_loto_diff_min": e7.fmt(float(lok.min())) if len(lok) else "",
                                    f"{m}_loto_diff_max": e7.fmt(float(lok.max())) if len(lok) else "",
                                    f"{m}_loto_jackknife_se": e7.fmt(se)})
                    mr = mcn.get((f"{a} vs {b}", sc, lay, e7.TSHORT[tname]))
                    row.update({"mcnemar_b": mr["b_first_correct_only"] if mr else "", "mcnemar_c": mr["c_second_correct_only"] if mr else "",
                                "mcnemar_p_exact": mr["p_exact"] if mr else "",
                                "mcnemar_note": "auxiliary; cell-level exact McNemar does not account for template clustering"})
                    rows.append(row)
    e7.wcsv("paired_cluster_bootstrap.csv", rows)
    show = [r for r in rows if r["type"] in ("micro (5 types)", "Terminology")]
    tex = []
    for r in show:
        cell = lambda m: f"{r[m + '_diff']} [{r[m + '_diff_ci_lo']}, {r[m + '_diff_ci_hi']}]" if r[m + "_diff"] else "undef."
        loto = lambda m: f"{r[m + '_loto_diff_min']} to {r[m + '_loto_diff_max']}" if r[m + "_loto_diff_min"] else ""
        tex.append({"cmp": r["comparison"], "role": r["role"], "sc": r["scorer"], "lab": r["label"], "type": r["type"],
                    "mcc": cell("mcc"), "mcc_loto": loto("mcc"), "prec": cell("precision"), "spec": cell("specificity"),
                    "rec": cell("recall"), "mcn": f"{r['mcnemar_b']}/{r['mcnemar_c']}, p={r['mcnemar_p_exact']}"})
    e7.wtex("paired_cluster_bootstrap.tex", tex,
            [("Comparison (on - off)", "cmp"), ("Role", "role"), ("Scorer", "sc"), ("Label", "lab"), ("Type", "type"), ("MCC diff [95% CI]", "mcc"),
             ("MCC diff LOTO range", "mcc_loto"), ("Precision diff", "prec"), ("Specificity diff", "spec"), ("Recall diff", "rec"),
             ("McNemar b/c, p (aux.)", "mcn")],
            "FINAL. RAG on minus off: paired template-cluster bootstrap 95% intervals (same resampled templates applied to both conditions, "
            "B=10,000, seed 20261111) and leave-one-template-out differences. Added after seeing replicate results, before semantic scoring.",
            "tab:e7-paired-cluster",
            "Primary comparison: R1 - A1-1 (pre-registered); R2 - A1-2 and R3b - A1-3 are replications. "
            "Robustness analysis added to the pre-registered plan after the replicate results were seen and before any semantic scoring. "
            "McNemar (auxiliary) is a cell-level exact test that does not account for template clustering. "
            "Per-type rows are in paired_cluster_bootstrap.csv.")
    for r in show:
        print(r["comparison"], r["scorer"], r["label"], r["type"],
              "MCC", r["mcc_diff"], f"[{r['mcc_diff_ci_lo']},{r['mcc_diff_ci_hi']}]", "LOTO", r["mcc_loto_diff_min"], r["mcc_loto_diff_max"],
              "| P", r["precision_diff"], f"[{r['precision_diff_ci_lo']},{r['precision_diff_ci_hi']}]",
              "| Sp", r["specificity_diff"], f"[{r['specificity_diff_ci_lo']},{r['specificity_diff_ci_hi']}]",
              "| R", r["recall_diff"], f"[{r['recall_diff_ci_lo']},{r['recall_diff_ci_hi']}]")


if __name__ == "__main__":
    main()
