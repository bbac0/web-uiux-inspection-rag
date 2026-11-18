"""
E5b: 사람 최종 판정(human_final) 대비 채점기(키워드, 의미 채점, string_match) 이슈 단위 비교. API 호출 없음, 검정 없음.

계획: results/revision/human_eval/e5b_plan.md (2026-11-18 승인), 이탈: results/revision/e5b_deviations.md.
이 단계에서 처음으로 key/ 대응표(eval_key.csv, supp_key.csv)와 재채점 병합 통합표(issue_tables_merged)를 연다.
채점 모델·프롬프트·키워드 사전·채점 결과는 바꾸지 않는다(사전 지정 10절 5항). 입력 파일은 읽기만 한다.

  python experiments/revision/e5b_run.py      # results/revision/human_eval/e5b/ (있으면 거부)
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import make_eval_sheets as mes    # noqa: E402

R = os.path.join(ROOT, "results", "revision").replace("\\", "/")
HE = f"{R}/human_eval"
OUT = f"{HE}/e5b"
REL = "results/revision"
TYPES = mes.TYPES
TERM = mes.TERM
CONTRAST, BUTTON = "Poor Contrast Ratio", "Button Area Clipping"
KO2EN = {"명도 대비 부족": CONTRAST, "모바일 레이아웃 깨짐": "Mobile Layout Breakage", "버튼 영역 잘림": BUTTON,
         "표준 용어 위반": TERM, "중복 ID": "Duplicate ID Markup Error", "해당 없음": "None"}
SHORT = {CONTRAST: "명도 대비", "Mobile Layout Breakage": "모바일", BUTTON: "버튼 잘림", TERM: "표준 용어",
         "Duplicate ID Markup Error": "중복 ID", "None": "해당 없음"}
SIX = TYPES + ["None"]
B_CLU, SEED_CLU = 10000, 20261111      # 계획서 5절
B_ISS, SEED_ISS = 2000, 20261118       # 평가자 간 일치도 보고와 같은 회차·시드 (numpy default_rng)
SRC = {
    "hf_main": f"{REL}/human_eval/human_final_main.csv", "hf_supp": f"{REL}/human_eval/human_final_supp.csv",
    "eval_key": f"{REL}/human_eval/key/eval_key.csv", "supp_key": f"{REL}/human_eval/supp_label/key/supp_key.csv",
    "merged": f"{REL}/issue_tables_merged/{{run}}.csv", "meta": "testbed_200/dataset_metadata.json",
    "sheet_main": f"{REL}/human_eval/rater_A/eval_sheet_A.csv",
    "sheet_supp": f"{REL}/human_eval/supp_label/rater_A_supp/eval_sheet_A_supp.csv",
}
STATS = Counter()      # E5b-1 용 (정의 안 됨 칸, 작은 분모 칸)


def rd(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ 자료
def load():
    meta = json.load(open(os.path.join(ROOT, SRC["meta"]), encoding="utf-8"))
    template = {p["page_id"][:-5]: p["base_template"] for p in meta}
    merged, runs_loaded = {}, set()

    def mrow(run, page, idx):
        if run not in runs_loaded:
            p = os.path.join(ROOT, SRC["merged"].format(run=run))
            if os.path.exists(p):
                for r in rd(SRC["merged"].format(run=run)):
                    merged[r["issue_id"]] = r
            runs_loaded.add(run)
        return merged.get(f"{run}:{page}:{int(idx):02d}")

    desc = {r["issue_id"]: r["description"] for k in ("sheet_main", "sheet_supp") for r in rd(SRC[k])}
    ek = {r["issue_id"]: r for r in rd(SRC["eval_key"])}
    sk = {r["issue_id"]: r for r in rd(SRC["supp_key"])}
    recs, chk = [], Counter()
    for hf, scope_of in (("hf_main", None), ("hf_supp", "supp")):
        for h in rd(SRC[hf]):
            i = h["issue_id"]
            if scope_of == "supp":
                k = sk[i]
                scope, layer = "supp", k["stratum"]
                run, page, idx = k["run_id"], k["page_id"], k["issue_index"]
            else:
                k = ek[i]
                scope = "A_B" if h["source"] == "A_B_consensus" else "A_only"
                layer, run, page, idx = k["stratum"], k["run_id"], k["page_id"], k["issue_index"]
                if k["template_id"] != template.get(page):
                    chk["template_mismatch"] += 1
                if (k["in_sheet_B"] == "1") != (scope == "A_B"):
                    chk["in_sheet_B_mismatch"] += 1
            m = mrow(run, page, idx)
            r = {"scope": scope, "issue_id": i, "layer": layer, "run": run, "page": page, "template": template.get(page),
                 "hcat": KO2EN.get(h["6분류"], ""), "code": h["코드 존재"], "vis": h["화면 존재"],
                 "login": h["로그인 레이블 지적"], "desc": desc.get(i, ""), "mapped": m is not None,
                 "ko": {c: h[c] for c in ("6분류", "코드 존재", "화면 존재", "로그인 레이블 지적")}}
            if m is not None:
                r.update(kw=set(x for x in m["keyword_types"].split(";") if x), sem=m["semantic_pass1_merged"],
                         sem_orig=m["semantic_pass1"] if m["semantic_pass1_status"] == "ok" else "",
                         sem_status=m["semantic_pass1_status"], sm=int(m["string_match_term"]),
                         kw_raw=m["keyword_types"], merged_id=m["issue_id"])
                if scope == "supp" and (k["semantic_pass1_merged"], k["string_match_term"], k["keyword_types"]) != (
                        m["semantic_pass1_merged"], m["string_match_term"], m["keyword_types"]):
                    chk["supp_key_label_mismatch"] += 1
            recs.append(r)
    return recs, chk


# ------------------------------------------------------------------ 지표
def m2x2(c):
    """c[..., 4] = TP, FP, FN, TN → precision, recall, kappa (정의 안 되면 nan)."""
    tp, fp, fn, tn = (c[..., k].astype(float) for k in range(4))
    n = tp + fp + fn + tn
    with np.errstate(invalid="ignore", divide="ignore"):
        prec = np.where(tp + fp > 0, tp / (tp + fp), np.nan)
        rec = np.where(tp + fn > 0, tp / (tp + fn), np.nan)
        po = (tp + tn) / n
        pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
        kap = np.where((n > 0) & (pe < 1), (po - pe) / (1 - pe), np.nan)
    return prec, rec, kap


def kappa_k(c, k=6):
    c = c.reshape(c.shape[:-1] + (k, k)).astype(float)
    n = c.sum(axis=(-1, -2))
    po = np.trace(c, axis1=-2, axis2=-1) / n
    pe = (c.sum(-1) * c.sum(-2)).sum(-1) / (n * n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(pe < 1, (po - pe) / (1 - pe), np.nan)


_W = {}


def weights(kind, units):
    """같은 범위·묶음에서는 모든 행이 같은 재표집을 쓴다."""
    key = (kind, tuple(units))
    if key not in _W:
        U = len(units)
        B, seed = (B_CLU, SEED_CLU) if kind == "cluster" else (B_ISS, SEED_ISS)
        idx = np.random.default_rng(seed).integers(0, U, size=(B, U))
        W = np.zeros((B, U), dtype=np.int32)
        for b in range(B):
            W[b] = np.bincount(idx[b], minlength=U)
        _W[key] = W
    return _W[key]


def unit_counts(recs, vec_fn, width):
    """→ {'cluster': (units, (U,width)), 'issue': (...)}"""
    out = {}
    for kind, keyf in (("cluster", lambda r: r["template"]), ("issue", lambda r: r["issue_id"])):
        units = sorted({keyf(r) for r in recs})
        pos = {u: j for j, u in enumerate(units)}
        C = np.zeros((len(units), width), dtype=np.int64)
        for r in recs:
            C[pos[keyf(r)]] += vec_fn(r)
        out[kind] = (units, C)
    return out


def ci(boot):
    v = boot[~np.isnan(boot)]
    if len(v) == 0:
        return (np.nan, np.nan, 0)
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)), int(len(v)))


def binrow(recs, types, h_fn, s_fn, valid_fn, stats=True):
    """여러 유형을 묶으면 micro 합. → dict (점추정, 두 CI)."""
    use = [r for r in recs if r["mapped"] and valid_fn(r)]

    def vec(r):
        v = np.zeros(4, dtype=np.int64)
        for t in types:
            h, s = h_fn(r, t), s_fn(r, t)
            v[0 if h and s else 1 if s else 2 if h else 3] += 1
        return v
    tot = sum((vec(r) for r in use), np.zeros(4, dtype=np.int64))
    p, rc, k = (float(x) for x in m2x2(tot))
    row = {"n": len(use), "TP": int(tot[0]), "FP": int(tot[1]), "FN": int(tot[2]), "TN": int(tot[3]),
           "precision": p, "recall": rc, "kappa": k}
    if use:
        for kind, (units, C) in unit_counts(use, vec, 4).items():
            bp, br, bk = m2x2(weights(kind, units) @ C)
            for name, b in (("precision", bp), ("recall", br), ("kappa", bk)):
                lo, hi, nv = ci(b)
                row[f"{name}_{kind}_lo"], row[f"{name}_{kind}_hi"], row[f"{name}_{kind}_valid"] = lo, hi, nv
    for name, den in (("precision", tot[0] + tot[1]), ("recall", tot[0] + tot[2])):
        row[f"{name}_small"] = int(0 < den < 10)
        if stats:
            STATS["undefined"] += int(den == 0)
            STATS["small"] += int(0 < den < 10)
    if stats:
        STATS["undefined"] += int(np.isnan(k))
    return row


SCORERS = {
    "키워드": lambda r, t: t in r["kw"],
    "의미": lambda r, t: r["sem"] == t,
    "string_match": lambda r, t: t == TERM and r["sm"] == 1,
}
H_CAT = (lambda r, t: r["hcat"] == t, lambda r: r["hcat"] != "")
H_CODE = (lambda r, t: r["hcat"] == t and r["code"] == "예", lambda r: r["hcat"] != "" and r["code"] != "")
H_CODEVIS = (lambda r, t: r["hcat"] == t and r["code"] == "예" and r["vis"] == "예",
             lambda r: r["hcat"] != "" and r["code"] != "" and r["vis"] != "")
H_LOGIN = (lambda r, t: r["login"] == "예", lambda r: r["login"] != "")


def type_rows(recs, scope, crit_name, H, scorers=("키워드", "의미", "string_match"), sem_fn=None):
    rows = []
    for t in TYPES:
        for sc in scorers:
            if sc == "string_match" and t != TERM:
                continue
            s_fn = sem_fn if (sc == "의미" and sem_fn) else SCORERS[sc]
            rows.append(dict(scope=scope, criterion=crit_name, type=SHORT[t], scorer=sc, note="",
                             **binrow(recs, [t], H[0], s_fn, H[1])))
    for label, ts in (("참고a: 근거(대비)", [CONTRAST]),
                      ("참고b: 대비+버튼", [CONTRAST, BUTTON])):
        for sc in [s for s in ("키워드", "의미") if s in scorers]:
            s_fn = sem_fn if (sc == "의미" and sem_fn) else SCORERS[sc]
            rows.append(dict(scope=scope, criterion=crit_name, type=label, scorer=sc, note="참고용",
                             **binrow(recs, ts, H[0], s_fn, H[1])))
    return rows


# ------------------------------------------------------------------ 출력 도우미
def f3(x):
    return "정의 안 됨" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"


def cell(row, m, kind="cluster"):
    s = f3(row[m])
    lo = row.get(f"{m}_{kind}_lo")
    if s != "정의 안 됨" and lo is not None and not np.isnan(lo):
        s += f" [{lo:.2f},{row[f'{m}_{kind}_hi']:.2f}]"
    if row.get(f"{m}_small"):
        s += "†"
    return s


def write_csv(name, rows, cols):
    with open(f"{OUT}/{name}", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: (f"{r[c]:.6f}" if isinstance(r.get(c), float) and not np.isnan(r[c]) else
                            "" if isinstance(r.get(c), float) else r.get(c, "")) for c in cols})


METRIC_COLS = ["scope", "criterion", "type", "scorer", "note", "n", "TP", "FP", "FN", "TN"] + [
    f"{m}{s}" for m in ("precision", "recall", "kappa") for s in
    ("", "_cluster_lo", "_cluster_hi", "_cluster_valid", "_issue_lo", "_issue_hi", "_issue_valid", "_small")
    if not (m == "kappa" and s == "_small")]


def metric_md(rows, src, title_note=""):
    L = ["| 유형 | 채점기 | TP | FP | FN | TN | 정밀도 [군집 CI] | 재현율 [군집 CI] | kappa [군집 CI] |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['type']} | {r['scorer']} | {r['TP']} | {r['FP']} | {r['FN']} | {r['TN']} | "
                 f"{cell(r, 'precision')} | {cell(r, 'recall')} | {cell(r, 'kappa')} |")
    L += ["", f"출처: {src}", "",
          "이슈 단위 부트스트랩 구간(보조):", "",
          "| 유형 | 채점기 | 정밀도 [이슈 CI] | 재현율 [이슈 CI] | kappa [이슈 CI] |", "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['type']} | {r['scorer']} | {cell(r, 'precision', 'issue')} | {cell(r, 'recall', 'issue')} | "
                 f"{cell(r, 'kappa', 'issue')} |")
    L += ["", f"출처: {src}", ""]
    return L


def wrap(lines):
    """표가 아닌 100자 넘는 줄은 공백에서 나눈다."""
    import textwrap
    out = []
    for ln in lines:
        if len(ln) <= 100 or ln.startswith("|"):
            out.append(ln)
            continue
        out += textwrap.wrap(ln, 100, break_long_words=False, break_on_hyphens=False,
                             subsequent_indent="  " if ln.startswith("- ") else "")
    return out


# ------------------------------------------------------------------ 표
def main():
    if os.path.exists(OUT):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUT}")
    recs, chk = load()
    os.makedirs(OUT)
    by = defaultdict(list)
    for r in recs:
        by[r["scope"]].append(r)
    SRC_MAIN = (f"`{SRC['hf_main']}`, `{SRC['eval_key']}`, `{REL}/issue_tables_merged/E1-R1.csv`, "
                f"`{SRC['meta']}`")
    SRC_SUPP = f"`{SRC['hf_supp']}`, `{SRC['supp_key']}`, `{REL}/issue_tables_merged/{{run}}.csv`, `{SRC['meta']}`"
    MD = ["# E5b 표 (사람 최종 판정 대비 채점기)", "",
          "작성: `experiments/revision/e5b_run.py` (API 호출 없음, 검정 없음). 2026-11-18.",
          "계획: `results/revision/human_eval/e5b_plan.md`, 이탈: `results/revision/e5b_deviations.md`.",
          "군집 CI = 템플릿 군집 부트스트랩(B 10,000, numpy default_rng 20261111, 백분위 95%).",
          "이슈 CI = 이슈 단위 부트스트랩(B 2,000, default_rng 20261118). 같은 범위의 모든 행은 같은 재표집을 쓴다.",
          "† = 분모 10 미만. '정의 안 됨' = 분모 0. CI 는 정의되는 회차만으로 계산(유효 회차는 CSV).",
          "채점 모델·프롬프트·키워드 사전·채점 결과는 바꾸지 않았다(사전 지정 10절 5항).", ""]

    # E5b-2 / 6
    t2 = type_rows(by["A_B"], "A_B", "6분류", H_CAT)
    t6 = type_rows(by["A_only"], "A_only", "6분류", H_CAT)
    # E5b-2b 페이지 층 참고
    strata_rows = []
    for st in sorted({r["layer"] for r in by["A_B"]}):
        sub = [r for r in by["A_B"] if r["layer"] == st and r["mapped"] and r["hcat"]]
        row = {"stratum": st, "n": len(sub), "human_type_pos": sum(r["hcat"] != "None" for r in sub),
               "note": "참고용"}
        for sc in ("키워드", "의미"):
            tp = fp = fn = 0
            for r in sub:
                for t in TYPES:
                    h, s = r["hcat"] == t, SCORERS[sc](r, t)
                    tp += h and s
                    fp += s and not h
                    fn += h and not s
            row.update({f"{sc}_TP": tp, f"{sc}_FP": fp, f"{sc}_FN": fn})
        strata_rows.append(row)
    # E5b-3
    six = {}
    for variant in ("빈 라벨=해당 없음", "빈 라벨 제외"):
        use = [r for r in by["A_B"] if r["mapped"] and r["hcat"] and (variant == "빈 라벨=해당 없음" or r["sem"])]

        def v6(r):
            v = np.zeros(36, dtype=np.int64)
            v[SIX.index(r["hcat"]) * 6 + SIX.index(r["sem"] or "None")] = 1
            return v
        tot = sum((v6(r) for r in use), np.zeros(36, dtype=np.int64))
        res = {"n": len(use), "conf": tot.reshape(6, 6), "kappa": float(kappa_k(tot))}
        for kind, (units, C) in unit_counts(use, v6, 36).items():
            res[kind] = ci(kappa_k(weights(kind, units) @ C))
        STATS["undefined"] += int(np.isnan(res["kappa"]))
        six[variant] = res
    # E5b-4
    t4 = (type_rows(by["A_B"], "A_B", "민감도: 6분류 + 코드 존재=예", H_CODE) +
          type_rows(by["A_B"], "A_B", "민감도: 원 pass1(재채점 전)", H_CAT, scorers=("의미",),
                    sem_fn=lambda r, t: r["sem_orig"] == t) +
          type_rows(by["A_B"], "A_B", "탐색: 6분류 + 코드·화면=예", H_CODEVIS))
    # E5b-5 용어 세 해석
    t5 = []
    interp = {("string_match", "6분류=용어"): "언급 기반*",
              ("의미", "로그인=예"): "레이블 모호성*"}
    for scope_name, recs_s in (("A_B", by["A_B"]), ("A_only", by["A_only"])):
        for hname, H in (("6분류=용어", H_CAT), ("로그인=예", H_LOGIN)):
            for sc in ("string_match", "의미", "키워드"):
                t5.append(dict(scope=scope_name, criterion=hname, type=SHORT[TERM], scorer=sc,
                               note=interp.get((sc, hname), "교차"),
                               **binrow(recs_s, [TERM], H[0], SCORERS[sc], H[1])))
    # 추가 세트 층별 2x2 (재현율은 층 정의상 해석하지 않음)
    t5s = []
    for st in ("S1", "S2", "S3"):
        sub = [r for r in by["supp"] if r["layer"] == st]
        for hname, H in (("6분류=용어", H_CAT), ("로그인=예", H_LOGIN)):
            for sc in ("string_match", "의미", "키워드"):
                b = binrow(sub, [TERM], H[0], SCORERS[sc], H[1])
                t5s.append(dict(scope="supp", stratum=st, criterion=hname, scorer=sc,
                                note=interp.get((sc, hname), "교차"), **b))
    # 의미=용어 이슈의 사람 판정 분포 (층별)
    dist = []
    for scope_name, key in (("A_B", "layer"), ("A_only", "layer"), ("supp", "layer")):
        for st in sorted({r[key] for r in by[scope_name]}):
            sub = [r for r in by[scope_name] if r[key] == st and r["mapped"] and r["sem"] == TERM]
            if not sub:
                continue
            row = {"scope": scope_name, "layer": st, "n_sem_term": len(sub)}
            for ko in KO2EN:
                row[ko] = sum(r["ko"]["6분류"] == ko for r in sub)
            row["로그인 예"] = sum(r["login"] == "예" for r in sub)
            row["로그인 아니오"] = sum(r["login"] == "아니오" for r in sub)
            dist.append(row)
    # E5b-7 추가 세트 층별
    t7 = []
    for st in ("S1", "S2", "S3"):
        sub = [r for r in by["supp"] if r["layer"] == st and r["mapped"]]
        for label, fn in (("사람 6분류 = 표준 용어 위반", lambda r: r["hcat"] == TERM),
                          ("사람 로그인 레이블 지적 = 예", lambda r: r["login"] == "예")):
            b = binrow(sub, [TERM], lambda r, t, fn=fn: fn(r), lambda r, t: True, lambda r: True, stats=False)
            t7.append({"stratum": st, "measure": label, "k": b["TP"], "n": b["n"], "rate": b["precision"],
                       **{k: v for k, v in b.items() if k.startswith("precision")}})
    t7d = []
    for st in ("S1", "S2", "S3"):
        sub = [r for r in by["supp"] if r["layer"] == st and r["mapped"]]
        row = {"stratum": st, "n": len(sub)}
        for ko in KO2EN:
            row[ko] = sum(r["ko"]["6분류"] == ko for r in sub)
        for c, nm in (("code", "코드"), ("vis", "화면")):
            for v in ("예", "아니오", "판단 불가"):
                row[f"{nm} {v}"] = sum(r[c] == v for r in sub)
        row["키워드 용어 & 사람 용어"] = sum(TERM in r["kw"] and r["hcat"] == TERM for r in sub)
        row["키워드 용어 & 사람 아님"] = sum(TERM in r["kw"] and r["hcat"] != TERM for r in sub)
        row["키워드 아님 & 사람 용어"] = sum(TERM not in r["kw"] and r["hcat"] == TERM for r in sub)
        row["키워드 아님 & 사람 아님"] = sum(TERM not in r["kw"] and r["hcat"] != TERM for r in sub)
        t7d.append(row)
    dup = {}
    for r in rd(SRC["supp_key"]):
        dup[r["stratum"]] = dup.get(r["stratum"], 0) + int(r["dup_n_total"])
    # E5b-8 불일치 목록
    t8 = []
    for scope_name in ("A_B", "supp"):
        for r in by[scope_name]:
            if not r["mapped"]:
                continue
            ht, hl = r["hcat"] == TERM, r["login"] == "예"
            why = []
            if r["sm"] != ht:
                why.append("string_match≠사람 용어")
            if (r["sem"] == TERM) != ht:
                why.append("의미≠사람 용어")
            if (TERM in r["kw"]) != ht:
                why.append("키워드≠사람 용어")
            if (r["sem"] == TERM) != hl:
                why.append("의미 용어≠로그인 레이블")
            focus = "용어"
            if not why and scope_name == "A_B" and r["sem"] != r["hcat"] and r["hcat"]:
                why.append("의미≠사람 6분류")
                focus = "기타 유형"
            if why:
                t8.append({"범위": "본 평가 A·B" if scope_name == "A_B" else f"추가 세트 {r['layer']}",
                           "구분": focus, "issue_id": r["issue_id"], "불일치": ";".join(why),
                           "설명 앞 150자": r["desc"][:150].replace("\n", " "),
                           "사람 6분류": r["ko"]["6분류"], "사람 코드": r["ko"]["코드 존재"],
                           "사람 화면": r["ko"]["화면 존재"], "사람 로그인 레이블": r["ko"]["로그인 레이블 지적"],
                           "키워드": r["kw_raw"] or "(없음)", "의미": r["sem"] or "(빈 라벨)",
                           "string_match": r["sm"]})
    # E5b-1 (마지막에: 정의 안 됨·작은 분모 수가 모두 모인 뒤)
    t1 = []
    for scope_name, label in (("A_B", "본 평가 A·B 범위"), ("A_only", "본 평가 A 단독"), ("supp", "추가 세트")):
        s = by[scope_name]
        t1.append({"범위": label, "이슈": len(s), "대응": sum(r["mapped"] for r in s),
                   "대응 실패": sum(not r["mapped"] for r in s),
                   "의미 빈 라벨": sum(r["mapped"] and not r["sem"] for r in s),
                   "원 pass1 ok 아님": sum(r["mapped"] and r.get("sem_status") != "ok" for r in s),
                   "합의 불가": sum(not r["hcat"] for r in s),
                   "코드 판단 불가": sum(r["code"] == "판단 불가" for r in s),
                   "화면 판단 불가": sum(r["vis"] == "판단 불가" for r in s),
                   "템플릿": len({r["template"] for r in s})})

    # ---------------- 쓰기
    write_csv("E5b-1_counts.csv", t1, list(t1[0]))
    MD += ["## E5b-1 대응·제외 건수", "", "| " + " | ".join(t1[0]) + " |", "|" + "---|" * len(t1[0])]
    MD += ["| " + " | ".join(str(v) for v in r.values()) + " |" for r in t1]
    MD += ["", f"출처: {SRC_MAIN}; {SRC_SUPP}", "",
           f"- 표 전체에서 분모가 0 인 칸(정밀도·재현율·kappa '정의 안 됨'): {STATS['undefined']}칸.",
           f"- 분모 10 미만 칸(†): {STATS['small']}칸.",
           f"- 점검: eval_key 템플릿 ≠ 메타데이터 {chk['template_mismatch']}건, in_sheet_B ≠ source "
           f"{chk['in_sheet_B_mismatch']}건, 추가 세트 key 라벨 ≠ 현재 병합표 {chk['supp_key_label_mismatch']}건.", ""]
    write_csv("E5b-2_main_AB.csv", t2, METRIC_COLS)
    MD += ["## E5b-2 본 평가 A·B 범위 (204건): 유형별 정밀도·재현율·kappa", "",
           "사람 양성 = human_final 6분류가 그 유형. 참고용 행은 라벨 3층 대신 쓰는 행(이슈 단위 micro 합):",
           "참고a = 가이드라인 근거가 있는 유형(명도 대비)만, 참고b = 사전 지정 민감도(버튼 잘림도 근거 있음으로 볼 때).", ""]
    MD += metric_md(t2, f"`{REL}/human_eval/e5b/E5b-2_main_AB.csv` ← {SRC_MAIN}")
    write_csv("E5b-2b_page_strata_ref.csv", strata_rows, list(strata_rows[0]))
    MD += ["### E5b-2b 참고용: 페이지 층(eval_key stratum)별 건수 (A·B 범위)", "",
           "유형 5개 micro 합. B 표본은 층화 표본이라 층별 크기가 A 시트 비율과 다르다. 가중 보정 없음.", "",
           "| 층 | 이슈 | 사람 유형 양성 | 키워드 TP | 키워드 FP | 키워드 FN | 의미 TP | 의미 FP | 의미 FN | 비고 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    MD += [f"| {r['stratum']} | {r['n']} | {r['human_type_pos']} | {r['키워드_TP']} | {r['키워드_FP']} | {r['키워드_FN']} | "
           f"{r['의미_TP']} | {r['의미_FP']} | {r['의미_FN']} | 참고용 |" for r in strata_rows]
    MD += ["", f"출처: `{REL}/human_eval/e5b/E5b-2b_page_strata_ref.csv` ← {SRC_MAIN}", ""]
    rows3 = []
    for v, res in six.items():
        for i, h in enumerate(SIX):
            rows3.append({"variant": v, "human": SHORT[h], **{SHORT[s]: int(res["conf"][i, j]) for j, s in enumerate(SIX)}})
    write_csv("E5b-3_semantic_6x6.csv", rows3, list(rows3[0]))
    with open(f"{OUT}/E5b-3_semantic_kappa.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant", "n", "kappa", "cluster_lo", "cluster_hi", "cluster_valid", "issue_lo", "issue_hi",
                    "issue_valid"])
        for v, res in six.items():
            w.writerow([v, res["n"], f"{res['kappa']:.6f}", *[f"{x:.6f}" if isinstance(x, float) else x
                                                             for x in res["cluster"] + res["issue"]]])
    MD += ["## E5b-3 의미 채점 6분류: 혼동 행렬과 kappa (A·B 범위)", "",
           "| 판 | 이슈 | kappa | 군집 CI | 이슈 CI |", "|---|---|---|---|---|"]
    for v, res in six.items():
        MD.append(f"| {v} | {res['n']} | {f3(res['kappa'])} | [{res['cluster'][0]:.2f}, {res['cluster'][1]:.2f}] | "
                  f"[{res['issue'][0]:.2f}, {res['issue'][1]:.2f}] |")
    MD += ["", f"출처: `{REL}/human_eval/e5b/E5b-3_semantic_kappa.csv` ← {SRC_MAIN}", "",
           "혼동 행렬(빈 라벨=해당 없음 판, 행 = 사람, 열 = 의미 채점):", "",
           "| 사람 \\ 의미 | " + " | ".join(SHORT[s] for s in SIX) + " |", "|" + "---|" * 7]
    for i, h in enumerate(SIX):
        MD.append(f"| {SHORT[h]} | " + " | ".join(str(int(six['빈 라벨=해당 없음']['conf'][i, j])) for j in range(6)) + " |")
    MD += ["", f"출처: `{REL}/human_eval/e5b/E5b-3_semantic_6x6.csv` ← {SRC_MAIN}", "",
           "키워드는 여러 유형이 붙을 수 있어 6분류 kappa 대신 E5b-2 의 유형별 이진 지표로 보고한다.", ""]
    write_csv("E5b-4_sensitivity.csv", t4, METRIC_COLS)
    MD += ["## E5b-4 민감도 (A·B 범위)", ""]
    for crit in dict.fromkeys(r["criterion"] for r in t4):
        MD += [f"### {crit}", ""] + metric_md([r for r in t4 if r["criterion"] == crit],
                                                f"`{REL}/human_eval/e5b/E5b-4_sensitivity.csv` ← {SRC_MAIN}")
    MD += ["- '판단 불가'는 '예'가 아닌 것으로 셌다(건수는 E5b-1).", ""]
    write_csv("E5b-5_terminology.csv", t5, METRIC_COLS)
    MD += ["## E5b-5 표준 용어 유형의 세 해석", "",
           "- 언급 기반: string_match 대 사람 6분류 = 표준 용어 위반.",
           "- 레이블 모호성: 의미 채점 = 표준 용어 위반 대 사람 로그인 레이블 지적 = 예.",
           "- 해당 없음: 색인 문서에 근거 조항이 없어 가이드라인 근거 층에서 이 유형을 뺀다. 지표 없음.",
           "- 나머지 조합은 '교차 참고'로 함께 적었다.", "",
           "| 범위 | 사람 기준 | 채점기 | 해석 | TP | FP | FN | TN | 정밀도 | 재현율 | kappa |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in t5:
        MD.append(f"| {r['scope']} | {r['criterion']} | {r['scorer']} | {r['note']} | {r['TP']} | {r['FP']} | {r['FN']} | "
                  f"{r['TN']} | {cell(r, 'precision')} | {cell(r, 'recall')} | {f3(r['kappa'])} |")
    MD += ["| 전 범위 | - | - | 해당 없음* | - | - | - | - | - | - | - |", "",
           "* = 사전 지정 해석(10절 10항). 6분류=용어: 사람 6분류 = 표준 용어 위반. 로그인=예: 로그인 레이블 지적 = 예.", "",
           f"출처: `{REL}/human_eval/e5b/E5b-5_terminology.csv` ← {SRC_MAIN}. 정밀도·재현율 구간은 군집 CI. kappa 구간과 이슈 CI 는 CSV.", "",
           "A_only 행은 평가자 1명(A) 판정이다.", ""]
    write_csv("E5b-5b_supp_strata_terminology.csv", t5s, ["scope", "stratum"] + METRIC_COLS[1:])
    MD += ["### E5b-5b 추가 세트 층별 2×2 (층이 채점 결과로 정의돼 재현율은 해석하지 않음)", "",
           "| 층 | 사람 기준 | 채점기 | 해석 | TP | FP | FN | TN | 정밀도 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in t5s:
        MD.append(f"| {r['stratum']} | {r['criterion']} | {r['scorer']} | {r['note']} | {r['TP']} | {r['FP']} | "
                  f"{r['FN']} | {r['TN']} | {cell(r, 'precision')} |")
    MD += ["", f"출처: `{REL}/human_eval/e5b/E5b-5b_supp_strata_terminology.csv` ← {SRC_SUPP}", ""]
    write_csv("E5b-5c_sem_term_human_dist.csv", dist, list(dist[0]) if dist else ["scope"])
    ko6 = list(KO2EN)
    MD += ["### E5b-5c 의미 채점이 표준 용어 위반으로 본 이슈의 사람 판정 분포 (층별)", "",
           "층: 본 평가는 페이지 층(eval_key stratum), 추가 세트는 S1~S3.", "",
           "| 범위 | 층 | 이슈 | " + " | ".join(SHORT[KO2EN[k]] for k in ko6) + " | 로그인 예 | 로그인 아니오 |",
           "|---|---|---|" + "---|" * (len(ko6) + 2)]
    for r in dist:
        MD.append(f"| {r['scope']} | {r['layer']} | {r['n_sem_term']} | " + " | ".join(str(r[k]) for k in ko6)
                  + f" | {r['로그인 예']} | {r['로그인 아니오']} |")
    if not dist:
        MD.append("| - | - | 0 | " + " | ".join("-" for _ in ko6) + " | - | - |")
    MD += ["", f"출처: `{REL}/human_eval/e5b/E5b-5c_sem_term_human_dist.csv` ← {SRC_MAIN}; {SRC_SUPP}", ""]
    write_csv("E5b-6_A_only.csv", t6, METRIC_COLS)
    MD += ["## E5b-6 본 평가 A 단독 (240건, 평가자 1명 판정)", "",
           "**평가자 1명(A) 판정.** E5b-2 와 합치지 않는다. A 자기 일치도: `human_eval/retest_agreement.md`.", ""]
    MD += metric_md(t6, f"`{REL}/human_eval/e5b/E5b-6_A_only.csv` ← {SRC_MAIN}")
    write_csv("E5b-7_supp_strata.csv", t7, list(t7[0]))
    write_csv("E5b-7b_supp_strata_dist.csv", t7d, list(t7d[0]))
    MD += ["## E5b-7 추가 세트 층별 (S1, S2, S3)", "",
           "S1 = 의미 채점 용어 위반(전수), S2 = string_match 1 이고 S1 아님(전수), S3 = 나머지 중 무작위 30.",
           "층을 합친 비율과 모집단 가중 추정은 내지 않는다(부록 6절).", "",
           "| 층 | 항목 | 건수 | 이슈 | 비율 [군집 CI] | 비율 [이슈 CI] |", "|---|---|---|---|---|---|"]
    for r in t7:
        MD.append(f"| {r['stratum']} | {r['measure']} | {r['k']} | {r['n']} | {cell(r, 'precision')} | "
                  f"{cell(r, 'precision', 'issue')} |")
    MD += ["", f"출처: `{REL}/human_eval/e5b/E5b-7_supp_strata.csv` ← {SRC_SUPP}", "",
           "- S1 의 첫 행 = 의미 채점 용어 라벨의 층 내 정밀도, S2 의 첫 행 = string_match 의 층 내 정밀도(6분류 기준).", "",
           "층별 사람 판정 분포와 키워드 용어 라벨 2×2:", "",
           "| 층 | 이슈 | " + " | ".join(SHORT[KO2EN[k]] for k in ko6) + " | 코드 예 | 코드 아니오 | 화면 예 | 화면 아니오 |",
           "|---|---|" + "---|" * (len(ko6) + 4)]
    for r in t7d:
        MD.append(f"| {r['stratum']} | {r['n']} | " + " | ".join(str(r[k]) for k in ko6) +
                  f" | {r['코드 예']} | {r['코드 아니오']} | {r['화면 예']} | {r['화면 아니오']} |")
    MD += ["", "| 층 | 키워드 용어 & 사람 용어 | 키워드 용어 & 사람 아님 | 키워드 아님 & 사람 용어 | 키워드 아님 & 사람 아님 | "
                "같은 문장 반복 합계 |", "|---|---|---|---|---|---|"]
    for r in t7d:
        MD.append(f"| {r['stratum']} | {r['키워드 용어 & 사람 용어']} | {r['키워드 용어 & 사람 아님']} | "
                  f"{r['키워드 아님 & 사람 용어']} | {r['키워드 아님 & 사람 아님']} | {dup.get(r['stratum'], 0)} |")
    MD += ["", f"출처: `{REL}/human_eval/e5b/E5b-7b_supp_strata_dist.csv` ← {SRC_SUPP} (반복 합계는 dup_n_total)", ""]
    write_csv("E5b-8_disagreements.csv", t8, list(t8[0]))
    MD += ["## E5b-8 불일치 사례 목록", "",
           f"전체 {len(t8)}건(용어 {sum(r['구분'] == '용어' for r in t8)}, 기타 유형 {sum(r['구분'] == '기타 유형' for r in t8)}).",
           "용어: 어느 채점기의 용어 판정이 사람 6분류(표준 용어)와 다르거나, 의미 용어 라벨이 로그인 레이블 지적과 다른 이슈.",
           "기타 유형: 본 평가 A·B 범위에서 용어 쪽은 모두 일치하고 의미 라벨이 사람 6분류와 다른 이슈.",
           "설명은 앞 150자(지시에 따라 이 표의 줄은 100자를 넘는다).", ""]
    for scope_label in dict.fromkeys(r["범위"].split(" S")[0] if r["범위"].startswith("추가") else r["범위"] for r in t8):
        sub = [r for r in t8 if r["범위"].startswith(scope_label)]
        MD += [f"### {scope_label} ({len(sub)}건)", "",
               "| 범위 | 구분 | 설명 앞 150자 | 사람 6분류 | 사람 로그인 레이블 | 키워드 | 의미 | string_match |",
               "|---|---|---|---|---|---|---|---|"]
        MD += [f"| {r['범위']} | {r['구분']} | {r['설명 앞 150자'].replace('|', '/')} | {r['사람 6분류']} | "
               f"{r['사람 로그인 레이블']} | {r['키워드']} | {r['의미']} | {r['string_match']} |" for r in sub]
        MD += ["", f"출처: `{REL}/human_eval/e5b/E5b-8_disagreements.csv` (설명은 평가자 시트)", ""]
    open(f"{OUT}/e5b_tables.md", "w", encoding="utf-8", newline="\n").write("\n".join(wrap(MD)))
    json.dump({"stats": dict(STATS), "checks": dict(chk), "n": {k: len(v) for k, v in by.items()},
               "seeds": {"cluster": [B_CLU, SEED_CLU], "issue": [B_ISS, SEED_ISS]}, "sources": SRC},
              open(f"{OUT}/e5b_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{OUT}: A_B {len(by['A_B'])}, A_only {len(by['A_only'])}, supp {len(by['supp'])}; "
          f"unmapped {sum(not r['mapped'] for r in recs)}; undefined {STATS['undefined']}, small {STATS['small']}; "
          f"checks {dict(chk)}; disagreements {len(t8)}")


if __name__ == "__main__":
    main()
