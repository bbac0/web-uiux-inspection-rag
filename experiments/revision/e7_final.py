"""
E7 최종: 의미 채점(재채점 병합 semantic_pass1_merged)을 주 채점기로 E7 셀 단위 통계를 다시 계산한다. API 호출 없음.

기존 E7(`e7_stats.py`, `e7_paired_cluster.py`)의 함수(라벨, 페이지·템플릿, 지표, 군집 집계, Fleiss/Cohen kappa)를 그대로
불러 쓰고, 그 파일들과 results/revision/e7/ 는 바꾸지 않는다. 채점 결과는 재채점 병합 통합표
(results/revision/issue_tables_merged/{run}.csv)에서 읽기만 한다.

채점기
  sem_merged  의미 채점, 재채점 병합 라벨(주)
  sem_orig    의미 채점 원 규칙: pass1 상태 ok 인 라벨만, 잘림(parse_error) = 음성 (민감도)
  keyword     키워드(보조) — 기존 E7 과 같은 예측인지 대조한다
  string_match 용어 유형만

  python experiments/revision/e7_final.py     # results/revision/e7_final/ (있으면 거부)
"""
import csv
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e7_stats as e7          # noqa: E402
from experiments.revision import label_layers            # noqa: E402

OUT = "results/revision/e7_final"
MERGED = "results/revision/issue_tables_merged/{run}.csv"
SCORERS = ["sem_merged", "sem_orig", "keyword", "string_match"]
SC_KO = {"sem_merged": "의미(병합)", "sem_orig": "의미(원)", "keyword": "키워드", "string_match": "string_match"}
LAY_KO = {"nominal": "nominal", "effective": "effective", "guideline_grounded": "근거(대비)",
          "guideline_grounded_btn_true": "근거+버튼"}
TS = {"micro (5 types)": "micro", "Contrast": "대비", "Mobile": "모바일", "Button": "버튼", "Terminology": "용어",
      "DupID": "중복ID"}
MET = ["precision", "recall", "specificity", "balanced_accuracy", "mcc"]
MKO = {"mcc": "MCC", "precision": "정밀도", "specificity": "특이도", "recall": "재현율"}
PMET = ["mcc", "precision", "specificity", "recall"]
PAIRS = [("E1-R1", "E2-A1-1", "주 비교(사전 지정)"), ("E1-R2", "E2-A1-2", "반복"), ("E1-R3b", "E2-A1-3", "반복"),
         ("E1-majority", "A1-majority", "3회 다수결")]
E3_PAIRS = [("E1-R1", "E3-page", "fixed − page"), ("E1-R1", "E3-oracle", "fixed − related"),
            ("E3-page", "E3-oracle", "page − related")]
E4_PAIRS = [("E4-mobile", "E1-R1", "E4 mobile − E1-R1")]
MODALITY = ["E2-A2", "E2-A3"]


# ------------------------------------------------------------------ 예측
def load_merged_preds(rid, pages):
    """병합표에서 네 채점기의 셀 예측. 실패 페이지(이슈 없음)는 0 (기존 E7 규칙과 같음)."""
    P = {s: {(p, t): 0 for p in pages for t in e7.TYPES} for s in SCORERS}
    for t in e7.TYPES:
        if t != e7.TERM:
            for p in pages:
                P["string_match"][(p, t)] = None
    path = MERGED.format(run=rid)
    has_sem = os.path.exists(path)
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig"))) if has_sem else None
    if rows is None:      # 의미 채점이 없는 run(A2, A3): 기존 E7 의 키워드·string_match 만
        kw = e7.load_preds(rid, pages)
        P["keyword"], P["string_match"] = kw["keyword"], kw["string_match"]
        P["sem_merged"] = P["sem_orig"] = None
        return P, False
    pset = set(pages)
    for r in rows:
        p = r["page_id"]
        if p not in pset:
            continue
        for t in filter(None, r["keyword_types"].split(";")):
            P["keyword"][(p, t)] = 1
        if r["semantic_pass1_merged"] in e7.TYPES:
            P["sem_merged"][(p, r["semantic_pass1_merged"])] = 1
        if r["semantic_pass1_status"] == "ok" and r["semantic_pass1"] in e7.TYPES:
            P["sem_orig"][(p, r["semantic_pass1"])] = 1
        if r["string_match_term"] == "1":
            P["string_match"][(p, e7.TERM)] = 1
    return P, True


def majority(preds_list, sc):
    out = {}
    for k in preds_list[0][sc]:
        v = [p[sc][k] for p in preds_list]
        out[k] = None if v[0] is None else int(sum(v) >= 2)
    return out


def tsets(sc):
    if sc == "string_match":
        return [("Terminology", [e7.TERM])]
    return [("micro (5 types)", e7.TYPES)] + [(e7.TSHORT[t], [t]) for t in e7.TYPES]


def boot_weights(n_t):
    rng = np.random.default_rng(e7.SEED)
    draws = rng.integers(0, n_t, size=(e7.B, n_t))
    return np.stack([np.bincount(d, minlength=n_t) for d in draws]).astype(float)


def jk(vals, n_t):
    v = vals[~np.isnan(vals)]
    if len(v) != n_t:
        return float("nan")
    return math.sqrt((n_t - 1) / n_t * np.sum((v - v.mean()) ** 2))


# ------------------------------------------------------------------ 계산 묶음
def cell_block(run_ids, preds, layers, pages, tmpl, templates, W, scorers, block):
    rows, store = [], {}
    n_t = len(templates)
    for rid in run_ids:
        for sc in scorers:
            if preds[rid].get(sc) is None:
                continue
            for lay, lab in layers.items():
                for tname, tl in tsets(sc):
                    C = e7.counts_by_template(preds[rid][sc], lab, pages, tmpl, templates, tl)
                    tot = C.sum(0)
                    if tot.sum() == 0:
                        continue
                    point, boot = e7.metrics_from_counts(tot), e7.metrics_from_counts(W @ C)
                    loto = e7.metrics_from_counts(tot[None, :] - C)
                    store[(rid, sc, lay, tname)] = C
                    row = {"block": block, "run": rid, "scorer": sc, "label": lay, "type": tname, "n_cells": int(tot.sum()),
                           "TP": int(tot[0]), "FP": int(tot[1]), "FN": int(tot[2]), "TN": int(tot[3])}
                    for m in MET:
                        bv = boot[m]
                        ok = ~np.isnan(bv)
                        lo, hi = np.percentile(bv[ok], [2.5, 97.5]) if ok.any() else (np.nan, np.nan)
                        lv = loto[m][~np.isnan(loto[m])]
                        row.update({m: e7.fmt(float(point[m])), f"{m}_ci_lo": e7.fmt(float(lo)),
                                    f"{m}_ci_hi": e7.fmt(float(hi)), f"{m}_boot_undefined": int((~ok).sum()),
                                    f"{m}_loto_min": e7.fmt(float(lv.min())) if len(lv) else "",
                                    f"{m}_loto_max": e7.fmt(float(lv.max())) if len(lv) else "",
                                    f"{m}_jackknife_se": e7.fmt(jk(loto[m], n_t))})
                    rows.append(row)
    return rows, store


def pair_block(pairs, store, scorers, layers, W, n_t, block):
    rows = []
    for a, b, role in pairs:
        for sc in scorers:
            for lay in layers:
                for tname, _ in tsets(sc):
                    ka, kb = (a, sc, lay, tname), (b, sc, lay, tname)
                    if ka not in store or kb not in store:
                        continue
                    Ca, Cb = store[ka], store[kb]
                    pa, pb = e7.metrics_from_counts(Ca.sum(0)), e7.metrics_from_counts(Cb.sum(0))
                    ba, bb = e7.metrics_from_counts(W @ Ca), e7.metrics_from_counts(W @ Cb)
                    la = e7.metrics_from_counts(Ca.sum(0)[None, :] - Ca)
                    lb = e7.metrics_from_counts(Cb.sum(0)[None, :] - Cb)
                    row = {"block": block, "comparison": f"{a} - {b}", "role": role, "scorer": sc, "label": lay,
                           "type": tname, "n_cells": int(Ca.sum())}
                    for m in PMET:
                        d = ba[m] - bb[m]
                        ok = ~np.isnan(d)
                        lo, hi = np.percentile(d[ok], [2.5, 97.5]) if ok.any() else (np.nan, np.nan)
                        ld = la[m] - lb[m]
                        lv = ld[~np.isnan(ld)]
                        row.update({f"{m}_a": e7.fmt(float(pa[m])), f"{m}_b": e7.fmt(float(pb[m])),
                                    f"{m}_diff": e7.fmt(float(pa[m] - pb[m])), f"{m}_diff_ci_lo": e7.fmt(float(lo)),
                                    f"{m}_diff_ci_hi": e7.fmt(float(hi)),
                                    f"{m}_ci_excludes_0": "" if np.isnan(lo) else "yes" if (lo > 0 or hi < 0) else "no",
                                    f"{m}_boot_undefined": int((~ok).sum()),
                                    f"{m}_loto_diff_min": e7.fmt(float(lv.min())) if len(lv) else "",
                                    f"{m}_loto_diff_max": e7.fmt(float(lv.max())) if len(lv) else "",
                                    f"{m}_loto_jackknife_se": e7.fmt(jk(ld, n_t))})
                    rows.append(row)
    return rows


def variability(preds, pages, scorers):
    rows = []
    for cond, members in (("E1 (RAG 켬)", e7.E1), ("E2-A1 (RAG 끔)", e7.A1)):
        for sc in scorers:
            for tname, tl in tsets(sc):
                det = [sum(preds[r][sc][(p, t)] for p in pages for t in tl) for r in members]
                M = np.array([[preds[r][sc][(p, t)] for r in members] for p in pages for t in tl])
                rows.append({"condition": cond, "scorer": sc, "type": tname, "runs": ";".join(members),
                             "detected_cells": ";".join(map(str, det)), "mean": e7.fmt(float(np.mean(det)), 2),
                             "sd": e7.fmt(float(np.std(det, ddof=1)), 2), "range": f"{min(det)}-{max(det)}",
                             "all3_identical": e7.fmt(float(np.mean(np.all(M == M[:, :1], axis=1)))),
                             "fleiss_kappa": e7.fmt(e7.fleiss_kappa(M)),
                             "cohen_kappa_pairs": ";".join(e7.fmt(e7.cohen_kappa(M[:, i], M[:, j]))
                                                           for i, j in ((0, 1), (0, 2), (1, 2)))})
    return rows


# ------------------------------------------------------------------ 출력
def wcsv(name, rows):
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(f"{OUT}/{name}", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def ci(r, m, d=False):
    k = f"{m}_diff" if d else m
    if not r.get(k):
        return "정의 안 됨"
    lo, hi = r[f"{k}_ci_lo"], r[f"{k}_ci_hi"]
    s = f"{r[k]} [{lo},{hi}]" if lo else r[k]
    return s + ("*" if d and r.get(f"{m}_ci_excludes_0") == "yes" else "")


def pick(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def run_ab(x):
    return (x.replace("E1-majority - A1-majority", "다수결").replace("E1-", "").replace("E2-", "")
            .replace("majority", "다수결"))


def main():
    if os.path.exists(OUT):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUT}")
    pages, tmpl, templates = e7.load_pages()
    layers = e7.load_layers()
    n_t = len(templates)
    W = boot_weights(n_t)
    preds, has_sem = {}, {}
    for rid in e7.RUN_IDS:
        preds[rid], has_sem[rid] = load_merged_preds(rid, pages)
    # 기존 E7 키워드·string_match 예측과 같은지
    check = {}
    for rid in e7.RUN_IDS:
        old = e7.load_preds(rid, pages)
        check[rid] = {s: sum(old[s][k] != preds[rid][s][k] for k in old[s]) for s in ("keyword", "string_match")}
    for m, members in e7.MAJ.items():
        preds[m] = {s: majority([preds[r] for r in members], s) for s in SCORERS}
    os.makedirs(OUT)
    ALL = e7.RUN_IDS + list(e7.MAJ)

    # 1. 셀 단위 (E1, A1, 다수결)
    cell, store = cell_block(ALL, preds, layers, pages, tmpl, templates, W, SCORERS, "E1/A1")
    wcsv("cell_metrics.csv", cell)
    # 2. 짝 군집 부트스트랩
    pairs = pair_block(PAIRS, store, SCORERS, layers, W, n_t, "E1/A1")
    wcsv("paired_cluster_bootstrap.csv", pairs)
    # 3. 실행 간 변동
    var = variability(preds, pages, SCORERS)
    wcsv("run_variability.csv", var)

    # 5. E3, E4 (의미 채점 있음): 그 run 의 페이지 집합, 같은 형식
    ext_cells, ext_pairs = [], []
    for block, runs_, prs, vp in (("E3", ["E1-R1", "E3-page", "E3-oracle"], E3_PAIRS, "1280"),
                                  ("E4", ["E1-R1", "E4-mobile"], E4_PAIRS, "390")):
        sub = json.load(open(f"results/revision/runs/{runs_[-1]}/run_meta.json", encoding="utf-8"))["pages"]
        sub = sorted(p if not p.endswith(".html") else p[:-5] for p in sub)
        lay_b = dict(layers)
        if vp == "390":    # E4: 모바일 화면 run 이라 effective·근거 층은 390 판정도 함께 낸다
            lay_b["effective_390"], _ = label_layers.load_labels("effective", viewport="390")
            lay_b["guideline_grounded_390"], _ = label_layers.load_labels("guideline_grounded", viewport="390", strict=True)
        P = {r: load_merged_preds(r, sub)[0] for r in runs_}
        tm = sorted({tmpl[p] for p in sub})
        Wb = boot_weights(len(tm))
        c_, s_ = cell_block(runs_, P, lay_b, sub, tmpl, tm, Wb, SCORERS, block)
        ext_cells += c_
        ext_pairs += pair_block(prs, s_, SCORERS, lay_b, Wb, len(tm), block)
    wcsv("e3_e4_cell_metrics.csv", ext_cells)
    wcsv("e3_e4_paired_cluster_bootstrap.csv", ext_pairs)
    # 모달리티 A2, A3: 의미 채점 없음 → 키워드·string_match 만, 참고용
    mod_preds = {r: load_merged_preds(r, pages)[0] for r in MODALITY}
    mod_preds["E1-R1"] = preds["E1-R1"]
    mc, ms = cell_block(["E1-R1"] + MODALITY, mod_preds, layers, pages, tmpl, templates, W,
                        ["keyword", "string_match"], "modality(참고용)")
    mp = pair_block([("E1-R1", "E2-A2", "참고용"), ("E1-R1", "E2-A3", "참고용")], ms, ["keyword", "string_match"],
                    layers, W, n_t, "modality(참고용)")
    for r in mc + mp:
        r["note"] = "참고용: A2·A3 는 의미 채점이 없어 의미 채점 기준으로 비교할 수 없다(키워드 기준만)"
    wcsv("modality_keyword_reference.csv", mc + mp)

    json.dump({"keyword_string_match_vs_e7_mismatch_cells": check, "has_semantic": has_sem,
               "bootstrap": {"B": e7.B, "seed": e7.SEED, "templates": templates},
               "e4_viewport_note": "E4 블록은 nominal, effective(1280), effective_390, 근거 층(1280, 390) 모두 계산"},
              open(f"{OUT}/e7_final_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(cell, pairs, var, ext_cells, ext_pairs, mc, mp, check)
    print(f"{OUT}: cells {len(cell)}, pairs {len(pairs)}, var {len(var)}, e3/e4 {len(ext_cells)}/{len(ext_pairs)}, "
          f"modality {len(mc)}/{len(mp)}; kw/sm mismatch vs E7 {sum(v['keyword'] + v['string_match'] for v in check.values())}")


def write_md(cell, pairs, var, ext_cells, ext_pairs, mc, mp, check):
    S = "results/revision/e7_final"
    L = ["# E7 최종 표 (의미 채점 재채점 병합 = 주 채점기)", "",
         "작성: `experiments/revision/e7_final.py` (API 호출 없음). 2026-11-18.",
         "채점기: 의미(병합) = semantic_pass1_merged(주), 의미(원) = 원 pass1 규칙(잘림 = 음성, 민감도),",
         "키워드(보조), string_match(용어만). 라벨: nominal, effective(1280), 근거(대비) = guideline_grounded 주,",
         "근거+버튼 = 버튼 true 민감도. 구간: 템플릿 군집 부트스트랩(B 10,000, 시드 20261111, 백분위 95%).",
         "짝 비교는 같은 재표집 템플릿을 두 조건에 함께 적용했다. * = 차이 구간이 0 을 포함하지 않음.",
         "키워드·string_match 예측이 기존 E7 과 다른 셀: "
         f"{sum(v['keyword'] + v['string_match'] for v in check.values())}개 (`e7_final_meta.json`).", ""]
    # T1 셀 지표 micro
    L += ["## 1. 셀 단위 지표 (5유형 micro, string_match 는 용어)", "",
          "| run | 채점기 | 라벨 | 셀 | P | R | Sp | BA | MCC [CI] |", "|---|---|---|---|---|---|---|---|---|"]
    for r in cell:
        if r["type"] in ("micro (5 types)", "Terminology") and (r["scorer"] == "string_match") == (r["type"] == "Terminology"):
            L.append(f"| {run_ab(r['run'])} | {SC_KO[r['scorer']]} | {LAY_KO[r['label']]} | {r['n_cells']} | "
                     f"{r['precision'] or '-'} | {r['recall'] or '-'} | {r['specificity'] or '-'} | "
                     f"{r['balanced_accuracy'] or '-'} | {ci(r, 'mcc')} |")
    L += ["", f"출처: `{S}/cell_metrics.csv` (유형별 행, 모든 지표의 CI·LOTO 포함)", ""]
    # T2 짝 비교: 주 표(의미 병합) / 보조(키워드)
    for sc, title in (("sem_merged", "주 표: 의미(병합)"), ("keyword", "보조 표: 키워드"), ("sem_orig", "민감도: 의미(원)")):
        L += [f"## 2. RAG 켬 − 끔, {title} (5유형 micro)", ""]
        for grp in (("mcc", "precision"), ("specificity", "recall")):
            L += ["| 비교 | 라벨 | " + " | ".join(f"{MKO[m]} 차이 [CI]" for m in grp) + " |", "|---|---|" + "---|" * len(grp)]
            for r in pick(pairs, scorer=sc, type="micro (5 types)"):
                L.append(f"| {run_ab(r['comparison'])} | {LAY_KO[r['label']]} | "
                         + " | ".join(ci(r, m, True) for m in grp) + " |")
            L += ["", f"출처: `{S}/paired_cluster_bootstrap.csv`", ""]
    # T2c 채점기에 따라 바뀌는 점
    L += ["## 3. 채점기에 따라 차이가 어떻게 바뀌는가 (MCC 차이, 5유형 micro)", "",
          "| 비교 | 라벨 | 의미(병합) | 키워드 | 의미(원) |", "|---|---|---|---|---|"]
    idx = {(r["comparison"], r["label"], r["scorer"], r["type"]): r for r in pairs}
    for a, b, _ in PAIRS:
        for lay in LAY_KO:
            cells = [idx.get((f"{a} - {b}", lay, sc, "micro (5 types)")) for sc in ("sem_merged", "keyword", "sem_orig")]
            L.append(f"| {run_ab(f'{a} - {b}')} | {LAY_KO[lay]} | " + " | ".join(ci(c, "mcc", True) if c else "-"
                                                                             for c in cells) + " |")
    L += ["", f"출처: `{S}/paired_cluster_bootstrap.csv`", ""]
    # T3 유형별 (주 비교)
    L += ["## 4. 유형별 RAG 켬 − 끔: 주 비교 R1 − A1-1 (MCC 차이)", "",
          "| 라벨 | 유형 | 의미(병합) | 키워드 | string_match |", "|---|---|---|---|---|"]
    for lay in LAY_KO:
        for t in ["Contrast", "Mobile", "Button", "Terminology", "DupID"]:
            cs = [idx.get(("E1-R1 - E2-A1-1", lay, sc, t)) for sc in ("sem_merged", "keyword", "string_match")]
            if not any(cs):
                continue
            L.append(f"| {LAY_KO[lay]} | {TS[t]} | " + " | ".join(ci(c, "mcc", True) if c else "-" for c in cs) + " |")
    L += ["", f"출처: `{S}/paired_cluster_bootstrap.csv` (반복 쌍·다수결과 정밀도·특이도·재현율은 CSV)", ""]
    # T4 변동
    L += ["## 5. 실행 간 변동 (3회 동일 셀 비율, Fleiss kappa, 쌍별 Cohen kappa)", "",
          "| 조건 | 채점기 | 유형 | 탐지 셀(3회) | 3회 동일 | Fleiss | 쌍별 Cohen |", "|---|---|---|---|---|---|---|"]
    for r in var:
        if r["type"] in ("micro (5 types)", "Terminology") and (r["scorer"] == "string_match") == (r["type"] == "Terminology"):
            L.append(f"| {r['condition']} | {SC_KO[r['scorer']]} | {TS[r['type']]} | {r['detected_cells']} | "
                     f"{r['all3_identical']} | {r['fleiss_kappa']} | {r['cohen_kappa_pairs']} |")
    L += ["", f"출처: `{S}/run_variability.csv` (유형별 행 포함)", ""]
    # T5 E3, E4
    L += ["## 6. E3 (용어 45 + 대조군 39 페이지)와 E4 (모바일 + 대조군, 390 화면): 같은 형식", "",
          "E3 는 용어 유형, E4 는 모바일 유형 행만 보인다(다른 유형·micro 는 CSV). nominal 라벨.",
          "related = 관련 조항 제공(E3-oracle, 10절 8항). fixed = E1-R1 의 같은 84페이지.", "",
          "| 묶음 | run | 채점기 | 유형 | 셀 | TP | FP | FN | MCC [CI] |", "|---|---|---|---|---|---|---|---|---|"]
    for r in ext_cells:
        want = "Terminology" if r["block"] == "E3" else "Mobile"
        if r["type"] == want and r["label"] == "nominal":
            L.append(f"| {r['block']} | {run_ab(r['run'])} | {SC_KO[r['scorer']]} | {TS[want]} | {r['n_cells']} | {r['TP']} | "
                     f"{r['FP']} | {r['FN']} | {ci(r, 'mcc')} |")
    L += ["", f"출처: `{S}/e3_e4_cell_metrics.csv`", ""]
    for grp in (("mcc",), ("precision", "recall")):
        L += ["| 묶음 | 비교 | 채점기 | 라벨 | " + " | ".join(f"{MKO[m]} 차이 [CI]" for m in grp) + " |",
              "|---|---|---|---|" + "---|" * len(grp)]
        for r in ext_pairs:
            want = "Terminology" if r["block"] == "E3" else "Mobile"
            if r["type"] == want and r["label"] in ("nominal", "effective", "effective_390"):
                L.append(f"| {r['block']} | {r['role']} | {SC_KO[r['scorer']]} | {r['label']} | "
                         + " | ".join(ci(r, m, True) for m in grp) + " |")
        L += ["", f"출처: `{S}/e3_e4_paired_cluster_bootstrap.csv`", ""]
    L += ["## 7. 모달리티 A2(html 만), A3(스크린샷 만): 참고용, 키워드 기준만", "",
          "**A2, A3 는 의미 채점을 하지 않아(사전 지정 13항) 의미 채점 기준으로 E1 과 비교할 수 없다. 참고용.**", ""]
    for grp in (("mcc", "precision"), ("recall",)):
        L += ["| 비교 | 채점기 | 라벨 | " + " | ".join(f"{MKO[m]} 차이 [CI]" for m in grp) + " | 비고 |",
              "|---|---|---|" + "---|" * (len(grp) + 1)]
        for r in mp:
            if r["type"] in ("micro (5 types)", "Terminology") and (r["scorer"] == "string_match") == (
                    r["type"] == "Terminology"):
                L.append(f"| {run_ab(r['comparison'])} | {SC_KO[r['scorer']]} | {LAY_KO[r['label']]} | "
                         + " | ".join(ci(r, m, True) for m in grp) + " | 참고용 |")
        L += ["", f"출처: `{S}/modality_keyword_reference.csv`", ""]
    open(f"{OUT}/e7_final_tables.md", "w", encoding="utf-8", newline="\n").write("\n".join(L))


if __name__ == "__main__":
    main()
