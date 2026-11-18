"""
E7 통계 (API 호출 없음). 사전 지정: results/revision/analysis_plan.md 2·3·5절, 9절(A1 3회), 10절(라벨 3층, string_match, R3b 대체).

범위 (2026-11-13 연구자 지시):
  - E1(R1, R2, R3b) vs E2-A1(A1-1, A1-2, A1-3). E1-R3 은 aborted 로 제외.
  - 채점기: 키워드(description, 다중 라벨) 와 string_match(mention-based, 용어 유형만). 의미 채점은 아직 없음.
  - 라벨: nominal, effective(1280), guideline_grounded(주: 버튼 false), guideline_grounded 민감도(버튼 true).
  - 지표: 페이지×유형 셀 단위 정밀도, 재현율, 특이도, 균형 정확도, MCC (5유형 micro + 유형별), 페이지 단위 병기.
  - 템플릿 군집 부트스트랩 B=10,000 (numpy default_rng 시드 20261111, 백분위수 95% CI), LOTO(범위, jackknife SE).
  - exact McNemar: 주 검정 R1 vs A1-1 (E2 Holm 가족 = A1, A2, A3 vs R1; A2·A3 미실행이라 Holm 은 상한 3p 로 표시),
    보조 R2–A1-2, R3b–A1-3, 3회 다수결. 유형별 검정은 탐색적(보정 없음).
  - 실행 간 변동(9절 iv, v), 점수 재계산(반올림, AUC), total_checked_count 분포.
  - 탐색적(사전 지정 아님): 페이지당 이슈 수, 이슈 카테고리 분포, 프롬프트 예시 구조(3건, 카테고리별 1건) 수렴.

출력: results/revision/e7/*.csv, *.tex, e7_summary.md
"""
import csv
import glob
import json
import math
import os
import sys
from collections import Counter

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import label_layers   # noqa: E402
from scoring import issue_table                  # noqa: E402

OUT = "results/revision/e7"
RUNS = "results/revision/runs"
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
TSHORT = {"Poor Contrast Ratio": "Contrast", "Mobile Layout Breakage": "Mobile", "Button Area Clipping": "Button",
          "Standard Terminology Violation": "Terminology", "Duplicate ID Markup Error": "DupID", "micro": "micro (5 types)"}
TERM = "Standard Terminology Violation"
E1 = ["E1-R1", "E1-R2", "E1-R3b"]
A1 = ["E2-A1-1", "E2-A1-2", "E2-A1-3"]
RUN_IDS = E1 + A1
MAJ = {"E1-majority": E1, "A1-majority": A1}
B, SEED = 10000, 20261111
METRICS = ["precision", "recall", "specificity", "balanced_accuracy", "mcc"]
LAYERS = ["nominal", "effective", "guideline_grounded", "guideline_grounded_btn_true"]
SCORERS = ["keyword", "string_match"]
PAIRS = [("E1-R1", "E2-A1-1", "primary"), ("E1-R2", "E2-A1-2", "auxiliary"), ("E1-R3b", "E2-A1-3", "auxiliary"),
         ("E1-majority", "A1-majority", "robustness (3-run majority)")]
CATS = ["디자인", "운영", "기술"]


# ---------------------------------------------------------------- 데이터
def load_pages():
    man = [r for r in csv.DictReader(open("results/revision/testbed_manifest.csv", encoding="utf-8")) if r["role"] == "testbed_200_page"]
    pages = sorted(r["page_id"] for r in man)
    tmpl = {r["page_id"]: r["template_id"] for r in man}
    templates = sorted(set(tmpl.values()))
    return pages, tmpl, templates


def load_layers():
    L = {}
    L["nominal"], _ = label_layers.load_labels("nominal")
    L["effective"], _ = label_layers.load_labels("effective")
    L["guideline_grounded"], _ = label_layers.load_labels("guideline_grounded", strict=True)
    L["guideline_grounded_btn_true"], _ = label_layers.load_labels(
        "guideline_grounded", strict=True, grounded_override={"Button Area Clipping": True})
    return L


def run_status(rid):
    return {json.loads(l)["page_id"]: json.loads(l)["status"] for l in open(f"{RUNS}/{rid}/reports.jsonl", encoding="utf-8")}


def load_preds(rid, pages):
    """{scorer: {(page, type): 0/1/None}}. 실패 페이지는 0 (주 분석 규칙). string_match 는 용어 유형만, 나머지 None."""
    kw = {(p, t): 0 for p in pages for t in TYPES}
    sm = {(p, t): (0 if t == TERM else None) for p in pages for t in TYPES}
    for r in issue_table.build_rows(rid):
        for t in filter(None, r["keyword_types"].split(";")):
            kw[(r["page_id"], t)] = 1
        if r["string_match_term"]:
            sm[(r["page_id"], TERM)] = 1
    return {"keyword": kw, "string_match": sm}


def majority(preds_list, scorer):
    keys = preds_list[0][scorer].keys()
    out = {}
    for k in keys:
        v = [p[scorer][k] for p in preds_list]
        out[k] = None if v[0] is None else int(sum(v) >= 2)
    return out


# ---------------------------------------------------------------- 지표
def metrics_from_counts(c):
    """c: (..., 4) = TP, FP, FN, TN → dict of arrays (nan = 정의되지 않음)."""
    c = np.asarray(c, dtype=float)
    tp, fp, fn, tn = c[..., 0], c[..., 1], c[..., 2], c[..., 3]
    with np.errstate(divide="ignore", invalid="ignore"):
        prec = np.where(tp + fp > 0, tp / (tp + fp), np.nan)
        rec = np.where(tp + fn > 0, tp / (tp + fn), np.nan)
        spec = np.where(tn + fp > 0, tn / (tn + fp), np.nan)
        ba = (rec + spec) / 2
        den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
        mcc = np.where(den > 0, (tp * tn - fp * fn) / den, np.nan)
    return {"precision": prec, "recall": rec, "specificity": spec, "balanced_accuracy": ba, "mcc": mcc}


def cell_keys(types):
    return types


def counts_by_template(pred, lab, pages, tmpl, templates, types):
    """(n_templates, 4) TP FP FN TN. 라벨 None 또는 예측 None 셀은 제외."""
    idx = {t: i for i, t in enumerate(templates)}
    C = np.zeros((len(templates), 4), dtype=np.int64)
    for p in pages:
        for t in types:
            y, yh = lab[(p, t)], pred[(p, t)]
            if y is None or yh is None:
                continue
            j = 0 if (yh and y) else 1 if (yh and not y) else 2 if (y and not yh) else 3
            C[idx[tmpl[p]], j] += 1
    return C


def fmt(x, d=3):
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}"


# ---------------------------------------------------------------- 검정·일치도
def binom_two_sided(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = np.mean(a == b)
    pe = np.mean(a) * np.mean(b) + (1 - np.mean(a)) * (1 - np.mean(b))
    return float("nan") if pe == 1 else float((po - pe) / (1 - pe))


def fleiss_kappa(M):
    """M: (n_items, n_raters) 이진."""
    M = np.asarray(M)
    n, r = M.shape
    ones = M.sum(1)
    counts = np.stack([r - ones, ones], 1)
    P_i = (np.sum(counts ** 2, 1) - r) / (r * (r - 1))
    p_j = counts.sum(0) / (n * r)
    Pe = np.sum(p_j ** 2)
    return float("nan") if Pe == 1 else float((P_i.mean() - Pe) / (1 - Pe))


def auc(neg_scores, pos_scores):
    """P(대조군 점수 > 결함 페이지 점수) + 0.5·동점 (점수가 높을수록 결함이 적다는 가정)."""
    neg, pos = np.asarray(neg_scores, float), np.asarray(pos_scores, float)
    if len(neg) == 0 or len(pos) == 0:
        return float("nan")
    g = (neg[:, None] > pos[None, :]).sum() + 0.5 * (neg[:, None] == pos[None, :]).sum()
    return float(g / (len(neg) * len(pos)))


# ---------------------------------------------------------------- 출력 도우미
def wcsv(name, rows):
    os.makedirs(OUT, exist_ok=True)
    if not rows:
        return
    fields = list(rows[0].keys())
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def tex_escape(s):
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("$", r"\$"),
                 ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s


def wtex(name, rows, cols, caption, label, notes=None):
    """rows: dict 목록, cols: [(header, key)]. booktabs 표."""
    spec = "l" * 1 + "r" * (len(cols) - 1)
    first_text = [all(not _isnum(r.get(k)) for r in rows) for _, k in cols]
    spec = "".join("l" if ft else "r" for ft in first_text)
    T = [r"\begin{table}[t]", r"\centering", r"\small", rf"\caption{{{tex_escape(caption)}}}", rf"\label{{{label}}}",
         rf"\begin{{tabular}}{{{spec}}}", r"\toprule", " & ".join(tex_escape(h) for h, _ in cols) + r" \\", r"\midrule"]
    for r in rows:
        T.append(" & ".join(tex_escape(r.get(k, "")) for _, k in cols) + r" \\")
    T += [r"\bottomrule", r"\end{tabular}"]
    if notes:
        T.append(r"\par\footnotesize " + tex_escape(notes))
    T.append(r"\end{table}")
    open(os.path.join(OUT, name), "w", encoding="utf-8").write("\n".join(T) + "\n")


def _isnum(v):
    if v is None or v == "":
        return True
    try:
        float(str(v).split(" ")[0].replace("[", "").replace("]", "").split(",")[0])
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- 본체
def main():
    pages, tmpl, templates = load_pages()
    layers = load_layers()
    status = {rid: run_status(rid) for rid in RUN_IDS}
    preds = {rid: load_preds(rid, pages) for rid in RUN_IDS}
    for m, members in MAJ.items():
        preds[m] = {s: majority([preds[r] for r in members], s) for s in SCORERS}
    ALL = RUN_IDS + list(MAJ)
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(templates), size=(B, len(templates)))
    W = np.stack([np.bincount(d, minlength=len(templates)) for d in draws]).astype(float)   # (B, 10)
    n_t = len(templates)

    def type_sets(scorer):
        return [(t, [t]) for t in TYPES] + ([("micro", TYPES)] if scorer == "keyword" else [])

    # ---- 1. 셀 단위 지표 + 부트스트랩 CI + LOTO ----
    cellrows, store = [], {}
    for rid in ALL:
        for sc in SCORERS:
            for lay in LAYERS:
                for tname, tl in type_sets(sc):
                    if sc == "string_match" and tname != TERM:
                        continue
                    C = counts_by_template(preds[rid][sc], layers[lay], pages, tmpl, templates, tl)
                    tot = C.sum(0)
                    if tot.sum() == 0:
                        continue
                    point = metrics_from_counts(tot)
                    boot = metrics_from_counts(W @ C)
                    loto = metrics_from_counts(tot[None, :] - C)
                    store[(rid, sc, lay, tname)] = (C, boot)
                    row = {"run": rid, "scorer": sc, "label": lay, "type": TSHORT[tname], "n_cells": int(tot.sum()),
                           "TP": int(tot[0]), "FP": int(tot[1]), "FN": int(tot[2]), "TN": int(tot[3])}
                    for m in METRICS:
                        v = float(point[m])
                        bv = boot[m]
                        ok = ~np.isnan(bv)
                        lo, hi = (np.percentile(bv[ok], [2.5, 97.5]) if ok.any() else (np.nan, np.nan))
                        lv = loto[m]
                        lok = lv[~np.isnan(lv)]
                        se = (math.sqrt((n_t - 1) / n_t * np.sum((lok - lok.mean()) ** 2)) if len(lok) == n_t else float("nan"))
                        row.update({m: fmt(v), f"{m}_ci_lo": fmt(float(lo)), f"{m}_ci_hi": fmt(float(hi)),
                                    f"{m}_boot_undefined": int((~ok).sum()),
                                    f"{m}_loto_min": fmt(float(lok.min())) if len(lok) else "",
                                    f"{m}_loto_max": fmt(float(lok.max())) if len(lok) else "",
                                    f"{m}_jackknife_se": fmt(se)})
                    cellrows.append(row)
    wcsv("cell_metrics.csv", cellrows)

    # ---- 2. 쌍 비교: 지표 차이(CI) + exact McNemar ----
    diffrows, mcn = [], []
    for a, b_, role in PAIRS:
        for sc in SCORERS:
            for lay in LAYERS:
                for tname, tl in type_sets(sc):
                    if sc == "string_match" and tname != TERM:
                        continue
                    ka, kb = (a, sc, lay, tname), (b_, sc, lay, tname)
                    if ka not in store or kb not in store:
                        continue
                    Ca, ba = store[ka]; Cb, bb = store[kb]
                    pa, pb = metrics_from_counts(Ca.sum(0)), metrics_from_counts(Cb.sum(0))
                    row = {"comparison": f"{a} - {b_}", "role": role, "scorer": sc, "label": lay, "type": TSHORT[tname]}
                    for m in METRICS:
                        d = ba[m] - bb[m]
                        ok = ~np.isnan(d)
                        lo, hi = np.percentile(d[ok], [2.5, 97.5]) if ok.any() else (np.nan, np.nan)
                        row.update({f"{m}_diff": fmt(float(pa[m] - pb[m])), f"{m}_diff_ci_lo": fmt(float(lo)),
                                    f"{m}_diff_ci_hi": fmt(float(hi))})
                    diffrows.append(row)
                    # McNemar: 셀 단위 정오
                    bcount = ccount = 0
                    n = 0
                    for p in pages:
                        for t in tl:
                            y = layers[lay][(p, t)]
                            ya, yb = preds[a][sc][(p, t)], preds[b_][sc][(p, t)]
                            if y is None or ya is None or yb is None:
                                continue
                            n += 1
                            ca, cb = int(ya == y), int(yb == y)
                            bcount += int(ca and not cb)
                            ccount += int(cb and not ca)
                    pv = binom_two_sided(bcount, ccount)
                    fam = ("E2 family (A1/A2/A3 vs R1), Holm" if (role == "primary" and sc == "keyword" and tname == "micro")
                           else "exploratory (unadjusted)" if tname != "micro" or sc == "string_match"
                           else f"{role} (unadjusted)")
                    mcn.append({"comparison": f"{a} vs {b_}", "role": role, "scorer": sc, "label": lay, "type": TSHORT[tname],
                                "n_cells": n, "b_first_correct_only": bcount, "c_second_correct_only": ccount,
                                "p_exact": f"{pv:.4g}", "family": fam,
                                "holm_note": ("A2, A3 not yet run: Holm-adjusted p will be computed when the family is complete; "
                                              f"upper bound min(1, 3p) = {min(1.0, 3 * pv):.4g}") if fam.startswith("E2 family") else ""})
    wcsv("pair_differences.csv", diffrows)
    wcsv("mcnemar.csv", mcn)

    # ---- 3. 실행 간 변동 (9절 iv, v) ----
    var_rows, agree_rows, pair9 = [], [], []
    for cond, members in (("E1 (RAG on)", E1), ("E2-A1 (RAG off)", A1)):
        for tname, tl in [(t, [t]) for t in TYPES] + [("micro", TYPES)]:
            det = [sum(preds[r]["keyword"][(p, t)] for p in pages for t in tl) for r in members]
            M = np.array([[preds[r]["keyword"][(p, t)] for r in members] for p in pages for t in tl])
            same = float(np.mean(np.all(M == M[:, :1], axis=1)))
            pk = [cohen_kappa(M[:, i], M[:, j]) for i, j in ((0, 1), (0, 2), (1, 2))]
            var_rows.append({"condition": cond, "scorer": "keyword", "type": TSHORT[tname], "runs": ";".join(members),
                             "detected_cells": ";".join(map(str, det)), "mean": fmt(float(np.mean(det)), 2),
                             "sd": fmt(float(np.std(det, ddof=1)), 2), "range": f"{min(det)}-{max(det)}",
                             "all3_identical": fmt(same), "fleiss_kappa": fmt(fleiss_kappa(M)),
                             "cohen_kappa_pairs": ";".join(fmt(k) for k in pk)})
        # string_match
        det = [sum(preds[r]["string_match"][(p, TERM)] for p in pages) for r in members]
        M = np.array([[preds[r]["string_match"][(p, TERM)] for r in members] for p in pages])
        var_rows.append({"condition": cond, "scorer": "string_match", "type": "Terminology", "runs": ";".join(members),
                         "detected_cells": ";".join(map(str, det)), "mean": fmt(float(np.mean(det)), 2),
                         "sd": fmt(float(np.std(det, ddof=1)), 2), "range": f"{min(det)}-{max(det)}",
                         "all3_identical": fmt(float(np.mean(np.all(M == M[:, :1], axis=1)))),
                         "fleiss_kappa": fmt(fleiss_kappa(M)),
                         "cohen_kappa_pairs": ";".join(fmt(cohen_kappa(M[:, i], M[:, j])) for i, j in ((0, 1), (0, 2), (1, 2)))})
    # (iv) 조건 간 평균 차이 vs 조건 내 SD
    for tname in [TSHORT[t] for t in TYPES] + ["micro (5 types)"]:
        for sc in ("keyword",) + (("string_match",) if tname == "Terminology" else ()):
            e = next(r for r in var_rows if r["condition"].startswith("E1") and r["type"] == tname and r["scorer"] == sc)
            a_ = next(r for r in var_rows if r["condition"].startswith("E2") and r["type"] == tname and r["scorer"] == sc)
            agree_rows.append({"scorer": sc, "type": tname, "E1_mean": e["mean"], "E1_sd": e["sd"], "E1_range": e["range"],
                               "A1_mean": a_["mean"], "A1_sd": a_["sd"], "A1_range": a_["range"],
                               "mean_diff_E1_minus_A1": fmt(float(e["mean"]) - float(a_["mean"]), 2)})
    # (v) 3x3 실행 쌍 9개 차이 분포 (탐지 셀 수, micro BA)
    for lay in ("nominal", "effective"):
        for tname, tl in [(t, [t]) for t in TYPES] + [("micro", TYPES)]:
            dets, bas = [], []
            for e in E1:
                for a_ in A1:
                    de = sum(preds[e]["keyword"][(p, t)] for p in pages for t in tl)
                    da = sum(preds[a_]["keyword"][(p, t)] for p in pages for t in tl)
                    dets.append(de - da)
                    me = metrics_from_counts(store[(e, "keyword", lay, tname)][0].sum(0))["balanced_accuracy"]
                    ma = metrics_from_counts(store[(a_, "keyword", lay, tname)][0].sum(0))["balanced_accuracy"]
                    bas.append(float(me - ma))
            pair9.append({"label": lay, "scorer": "keyword", "type": TSHORT[tname],
                          "detected_diff_9pairs": ";".join(map(str, dets)), "detected_diff_min": min(dets),
                          "detected_diff_median": float(np.median(dets)), "detected_diff_max": max(dets),
                          "ba_diff_min": fmt(min(bas)), "ba_diff_median": fmt(float(np.median(bas))), "ba_diff_max": fmt(max(bas)),
                          "pairs_with_E1_higher_ba": sum(x > 0 for x in bas)})
    wcsv("run_variability.csv", var_rows)
    wcsv("condition_mean_vs_within_sd.csv", agree_rows)
    wcsv("nine_pair_differences.csv", pair9)

    # ---- 4. 페이지 단위 병기 (기존 논문 방식) ----
    pagerows = []
    for rid in ALL:
        for lay in ("nominal", "effective"):
            tp = fp = fn = tn = 0
            for p in pages:
                true_t = {t for t in TYPES if layers[lay][(p, t)]}
                pred_t = {t for t in TYPES if preds[rid]["keyword"][(p, t)]}
                if true_t:
                    if true_t & pred_t:
                        tp += 1
                    else:
                        fn += 1
                else:
                    if pred_t:
                        fp += 1
                    else:
                        tn += 1
            prec = tp / (tp + fp) if tp + fp else float("nan")
            rec = tp / (tp + fn) if tp + fn else float("nan")
            f1 = 2 * prec * rec / (prec + rec) if prec + rec else float("nan")
            fpr = fp / (fp + tn) if fp + tn else float("nan")
            pagerows.append({"run": rid, "scorer": "keyword", "label": lay, "defect_pages": tp + fn, "control_pages": fp + tn,
                             "TP": tp, "FP": fp, "FN": fn, "TN": tn, "precision": fmt(prec), "recall": fmt(rec), "f1": fmt(f1),
                             "fpr": fmt(fpr)})
    wcsv("page_level_legacy.csv", pagerows)

    # ---- 5. 점수 재계산과 AUC, total_checked_count 분포 ----
    def calc(total, faults, rounding):
        raw = (1 - faults / total) * 100 if total else 0
        return int(max(0, round(raw))) if rounding == "round" else int(max(0, raw // 1))

    nominal_defect = {p: any(layers["nominal"][(p, t)] for t in TYPES) for p in pages}
    score_rows, tcc_rows, auc_rows = [], [], []
    tidx = {t: i for i, t in enumerate(templates)}
    for rid in RUN_IDS:
        recs = [json.loads(l) for l in open(f"{RUNS}/{rid}/reports.jsonl", encoding="utf-8")]
        tc = Counter()
        per = {}
        mism = 0
        for r in recs:
            rep = r.get("report") or {}
            tot = rep.get("total_count")
            tc["30" if tot == 30 else "60" if tot == 60 else "other"] += 1
            faults = {"디자인": rep.get("design_faults", 0), "운영": rep.get("ops_faults", 0), "기술": rep.get("tech_faults", 0)}
            stored = rep.get("scores", {})
            rnd = {c: calc(tot, faults[c], "round") for c in CATS}
            if any(rnd[c] != stored.get(c) for c in CATS):
                mism += 1
            per[r["page_id"]] = {"mean": float(np.mean([rnd[c] for c in CATS])), "min": float(min(rnd[c] for c in CATS)),
                                 "stored_mean": float(np.mean([stored.get(c, 0) for c in CATS]))}
        others = Counter(json.loads(l)["report"].get("total_count") for l in open(f"{RUNS}/{rid}/reports.jsonl", encoding="utf-8")
                         if json.loads(l)["report"].get("total_count") not in (30, 60))
        tcc_rows.append({"run": rid, "n_pages": len(recs), "total_checked_30": tc["30"], "total_checked_60": tc["60"],
                         "total_checked_other": tc["other"],
                         "other_values": ";".join(f"{k}:{v}" for k, v in sorted(others.items(), key=lambda x: (str(type(x[0])), x[0])))})
        score_rows.append({"run": rid, "pages": len(recs), "recomputed_round_vs_stored_mismatch_pages": mism,
                           "note": "--max-pages 1: page average over a single page, so // and round give the same value"})
        for agg in ("mean", "min"):
            neg = [per[p][agg] for p in pages if not nominal_defect[p]]
            pos = [per[p][agg] for p in pages if nominal_defect[p]]
            point = auc(neg, pos)
            bs = []
            negT = [(tidx[tmpl[p]], per[p][agg]) for p in pages if not nominal_defect[p]]
            posT = [(tidx[tmpl[p]], per[p][agg]) for p in pages if nominal_defect[p]]
            for d in draws[:B]:
                cnt = np.bincount(d, minlength=n_t)
                nn = [s for (ti, s) in negT for _ in range(cnt[ti])]
                pp = [s for (ti, s) in posT for _ in range(cnt[ti])]
                bs.append(auc(nn, pp))
            bs = np.array(bs)
            ok = ~np.isnan(bs)
            lo, hi = np.percentile(bs[ok], [2.5, 97.5])
            auc_rows.append({"run": rid, "page_score": agg, "rounding": "round", "auc_control_gt_defect": fmt(point),
                             "ci_lo": fmt(float(lo)), "ci_hi": fmt(float(hi)), "boot_undefined": int((~ok).sum()),
                             "n_control": len(neg), "n_defect": len(pos)})
    # 레거시 run2 (저장된 점수 = 분석 2건 // 평균, 그대로)
    run2 = {}
    for f in sorted(glob.glob("paper_results/run2/report_page_*.json")):
        p = os.path.basename(f)[len("report_"):-5]
        rep = json.load(open(f, encoding="utf-8"))
        sc = rep.get("scores", {})
        run2[p] = {"mean": float(np.mean([sc.get(c, 0) for c in CATS])), "min": float(min(sc.get(c, 0) for c in CATS))}
    if run2:
        for agg in ("mean", "min"):
            neg = [run2[p][agg] for p in pages if p in run2 and not nominal_defect[p]]
            pos = [run2[p][agg] for p in pages if p in run2 and nominal_defect[p]]
            auc_rows.append({"run": "legacy run2", "page_score": agg, "rounding": "stored (// across 2 analyses)",
                             "auc_control_gt_defect": fmt(auc(neg, pos)), "ci_lo": "", "ci_hi": "", "boot_undefined": "",
                             "n_control": len(neg), "n_defect": len(pos)})
        tc2 = Counter(("30" if json.load(open(f, encoding="utf-8")).get("total_count") == 30 else
                       "60" if json.load(open(f, encoding="utf-8")).get("total_count") == 60 else "other")
                      for f in glob.glob("paper_results/run2/report_page_*.json"))
        tcc_rows.append({"run": "legacy run2 (report total_count, 2 analyses)", "n_pages": sum(tc2.values()),
                         "total_checked_30": tc2["30"], "total_checked_60": tc2["60"], "total_checked_other": tc2["other"],
                         "other_values": ""})
    wcsv("score_recompute.csv", score_rows)
    wcsv("score_auc.csv", auc_rows)
    wcsv("total_checked_count.csv", tcc_rows)

    # ---- 6. 탐색적 (사전 지정 아님) ----
    exp_n, exp_cat, exp_conv = [], [], []
    pooled = {"on": Counter(), "off": Counter()}
    for rid in RUN_IDS:
        cond = "on" if rid in E1 else "off"
        recs = [json.loads(l) for l in open(f"{RUNS}/{rid}/reports.jsonl", encoding="utf-8")]
        ncount, cats = Counter(), Counter()
        conv = exact3 = one_each = 0
        for r in recs:
            iss = [i for i in ((r.get("report") or {}).get("issues") or []) if isinstance(i, dict)]
            ncount[len(iss)] += 1
            cc = Counter(i.get("category") for i in iss)
            for c, v in cc.items():
                cats[c if c in CATS else "other"] += v
            e3 = len(iss) == 3
            oe = all(cc.get(c, 0) == 1 for c in CATS) and len(iss) == 3
            exact3 += e3
            conv += oe
            one_each += all(cc.get(c, 0) >= 1 for c in CATS)
        pooled[cond].update({"pages": len(recs), "conv": conv, "exact3": exact3, "one_each": one_each})
        row = {"analysis": "exploratory", "run": rid, "rag": cond, "pages": len(recs)}
        row.update({f"n_issues_{k}": ncount.get(k, 0) for k in range(0, 11)})
        row["n_issues_gt10"] = sum(v for k, v in ncount.items() if k > 10)
        row["mean"] = fmt(sum(k * v for k, v in ncount.items()) / len(recs), 2)
        exp_n.append(row)
        tot = sum(cats.values())
        exp_cat.append({"analysis": "exploratory", "run": rid, "rag": cond, "issues": tot,
                        **{f"{c}": cats.get(c, 0) for c in CATS + ["other"]},
                        **{f"{c}_share": fmt(cats.get(c, 0) / tot) for c in CATS + ["other"]}})
        exp_conv.append({"analysis": "exploratory", "run": rid, "rag": cond, "pages": len(recs),
                         "exactly_3_issues": exact3, "exactly_3_and_one_per_category": conv,
                         "share_converged": fmt(conv / len(recs)), "at_least_one_per_category": one_each})
    for cond in ("on", "off"):
        P = pooled[cond]
        exp_conv.append({"analysis": "exploratory", "run": f"pooled RAG {cond} (3 runs)", "rag": cond, "pages": P["pages"],
                         "exactly_3_issues": P["exact3"], "exactly_3_and_one_per_category": P["conv"],
                         "share_converged": fmt(P["conv"] / P["pages"]), "at_least_one_per_category": P["one_each"]})
    wcsv("exploratory_issue_counts.csv", exp_n)
    wcsv("exploratory_categories.csv", exp_cat)
    wcsv("exploratory_prompt_structure_convergence.csv", exp_conv)

    # ---- 오류 페이지 수 (2절) ----
    err_rows = [{"run": rid, **dict(Counter(status[rid].values()))} for rid in RUN_IDS]
    wcsv("run_status_counts.csv", err_rows)

    # ---- LaTeX 표 ----
    def pick(rows, **kw):
        return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]

    def ci(r, m):
        return f"{r[m]} [{r[m + '_ci_lo']}, {r[m + '_ci_hi']}]" if r[m] else "undef."

    for lay in LAYERS:
        trs = []
        for rid in ALL:
            for r in pick(cellrows, run=rid, label=lay):
                trs.append({"run": rid, "scorer": r["scorer"], "type": r["type"], "n": r["n_cells"],
                            "P": ci(r, "precision"), "R": ci(r, "recall"), "Spec": ci(r, "specificity"),
                            "BA": ci(r, "balanced_accuracy"), "MCC": ci(r, "mcc")})
        wtex(f"cell_metrics_{lay}.tex", trs,
             [("Run", "run"), ("Scorer", "scorer"), ("Type", "type"), ("Cells", "n"), ("Precision", "P"), ("Recall", "R"),
              ("Specificity", "Spec"), ("Bal. acc.", "BA"), ("MCC", "MCC")],
             f"Cell-level metrics, label layer: {lay}. Keyword and string_match (mention-based, terminology only) scorers side by side. "
             "95% CI: template-cluster bootstrap (B=10,000, seed 20261111).", f"tab:e7-cells-{lay}",
             "undef. = denominator zero. string_match judges only the terminology type.")
    wtex("mcnemar.tex", [r for r in mcn if r["type"] == "micro (5 types)" or r["scorer"] == "string_match"],
         [("Comparison", "comparison"), ("Role", "role"), ("Scorer", "scorer"), ("Label", "label"), ("Type", "type"),
          ("Cells", "n_cells"), ("b", "b_first_correct_only"), ("c", "c_second_correct_only"), ("p (exact)", "p_exact"),
          ("Family", "family")],
         "Exact McNemar tests on cell-level correctness (RAG on vs off).", "tab:e7-mcnemar",
         "b: cells correct only in the first condition; c: only in the second. Primary test R1 vs A1-1 (keyword, micro) belongs to the "
         "pre-registered E2 Holm family with A2 and A3, which have not run yet; Holm-adjusted p is reported once the family is complete "
         "(upper bound 3p). Per-type tests are exploratory (see mcnemar.csv).")
    wtex("run_variability.tex", var_rows,
         [("Condition", "condition"), ("Scorer", "scorer"), ("Type", "type"), ("Detected cells (3 runs)", "detected_cells"),
          ("Mean", "mean"), ("SD", "sd"), ("All 3 identical", "all3_identical"), ("Fleiss kappa", "fleiss_kappa"),
          ("Pairwise Cohen kappa", "cohen_kappa_pairs")],
         "Run-to-run variability within condition (E1: R1, R2, R3b; E2-A1: A1-1, A1-2, A1-3).", "tab:e7-variability")
    wtex("pair_differences_primary.tex",
         [r for r in diffrows if r["type"] in ("micro (5 types)", "Terminology") and r["label"] in ("nominal", "effective", "guideline_grounded")],
         [("Comparison", "comparison"), ("Scorer", "scorer"), ("Label", "label"), ("Type", "type"),
          ("BA diff", "balanced_accuracy_diff"), ("CI lo", "balanced_accuracy_diff_ci_lo"), ("CI hi", "balanced_accuracy_diff_ci_hi"),
          ("MCC diff", "mcc_diff"), ("CI lo ", "mcc_diff_ci_lo"), ("CI hi ", "mcc_diff_ci_hi")],
         "Metric differences RAG on minus off (template-cluster bootstrap 95% CI).", "tab:e7-diffs")
    wtex("page_level_legacy.tex", pagerows,
         [("Run", "run"), ("Label", "label"), ("TP", "TP"), ("FP", "FP"), ("FN", "FN"), ("TN", "TN"), ("Precision", "precision"),
          ("Recall", "recall"), ("F1", "f1"), ("FPR", "fpr")],
         "Page-level results in the original paper's definition (keyword scorer).", "tab:e7-page")
    wtex("score_auc.tex", auc_rows,
         [("Run", "run"), ("Page score", "page_score"), ("Rounding", "rounding"), ("AUC", "auc_control_gt_defect"),
          ("CI lo", "ci_lo"), ("CI hi", "ci_hi"), ("Controls", "n_control"), ("Defect pages", "n_defect")],
         "Separation of defect and control pages by the Eq. 3 score (AUC = P(control score > defect score)).", "tab:e7-auc")
    wtex("total_checked_count.tex", tcc_rows,
         [("Run", "run"), ("Pages", "n_pages"), ("30", "total_checked_30"), ("60", "total_checked_60"), ("Other", "total_checked_other"),
          ("Other values", "other_values")], "Distribution of total_checked_count.", "tab:e7-tcc")
    wtex("exploratory_convergence.tex", exp_conv,
         [("Run", "run"), ("RAG", "rag"), ("Pages", "pages"), ("Exactly 3 issues", "exactly_3_issues"),
          ("3 issues, one per category", "exactly_3_and_one_per_category"), ("Share", "share_converged"),
          (">=1 per category", "at_least_one_per_category")],
         "EXPLORATORY (not pre-registered): convergence to the prompt example structure (3 issues, one per category).",
         "tab:e7-exp-conv")
    wtex("exploratory_categories.tex", exp_cat,
         [("Run", "run"), ("RAG", "rag"), ("Issues", "issues"), ("Design", "디자인_share"), ("Ops", "운영_share"),
          ("Tech", "기술_share"), ("Other", "other_share")],
         "EXPLORATORY (not pre-registered): issue category shares.", "tab:e7-exp-cat")
    print(json.dumps({"cell_rows": len(cellrows), "pairs": len(diffrows), "mcnemar": len(mcn), "out": OUT}, ensure_ascii=False))


if __name__ == "__main__":
    main()
