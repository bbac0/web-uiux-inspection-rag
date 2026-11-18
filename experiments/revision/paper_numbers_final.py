"""
논문 숫자표 최종판의 새 절과 보고서 자동 대조 (API 호출 없음, 새 검정 없음). paper_numbers.py 가 불러 쓴다.

- 모든 표 행에 출처 열([n] = 표 아래 출처 목록)을 단다. 출처 파일이 없으면 그 행을 표에서 빼고 'unsourced' 목록에 넣는다.
- check(...) 로 등록한 숫자는 보고서의 같은 표·행·열 값과 자동 대조한다(고치지 않고 결과만 적는다).
"""
import csv
import glob
import hashlib
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

R = "results/revision"
REP = f"{R}/reports"
E7F = f"{R}/e7_final"
E5B = f"{R}/human_eval/e5b"
E9E = f"{R}/human_eval/e9_eval"
A52 = f"{E9E}/rater_A_e9_hit52/eval_sheet_A_e9_hit52_filled.csv"
A52_COPY = f"{E9E}/intake_hit52/eval_sheet_A_e9_hit52_filled_copy.csv"
TY = {"micro (5 types)": "micro", "Contrast": "명도 대비", "Mobile": "모바일", "Button": "버튼 잘림",
      "Terminology": "표준 용어", "DupID": "중복 ID"}
SC = {"sem_merged": "의미(병합)", "sem_orig": "의미(원)", "keyword": "키워드", "string_match": "sm"}
LB = {"nominal": "nominal", "effective": "effective", "guideline_grounded": "근거(대비)",
      "guideline_grounded_btn_true": "근거+버튼", "effective_390": "effective_390", "guideline_grounded_390": "근거(대비)_390"}
CMP = {"E1-R1 - E2-A1-1": "R1 − A1-1 (주)", "E1-R2 - E2-A1-2": "R2 − A1-2", "E1-R3b - E2-A1-3": "R3b − A1-3",
       "E1-majority - A1-majority": "다수결"}


def rcsv(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


def exists(p):
    return bool(glob.glob(re.sub(r"\{[^}]*\}", "*", p)))


class Book:
    """표 행·출처·대조 항목 모음."""

    def __init__(self):
        self.unsourced, self.checks = [], []

    def table(self, L, h, rows, tab):
        """rows: (cells, [출처 경로…]). 출처 열 [n] 을 붙이고 표 아래 출처 목록을 쓴다."""
        keys, out = {}, []
        for cells, srcs in rows:
            miss = [s for s in srcs if not exists(s)]
            if not srcs or miss:
                self.unsourced.append({"where": L[-2] if len(L) > 1 else "", "row": " / ".join(map(str, cells)),
                                       "missing": ", ".join(miss) or "(출처 없음)"})
                continue
            out.append(list(cells) + [",".join(keys.setdefault(s, f"[{len(keys) + 1}]") for s in srcs)])
        L += tab(list(h) + ["출처"], out)
        L += ["", "출처:"] + [f"- {k} `{s}`" for s, k in keys.items()] + [""]

    def check(self, where, report, value, *, section=None, keys=None, col=None, idx=0, regex=None, ncols=None):
        self.checks.append(dict(where=where, report=report, value=str(value), section=section, keys=keys or {},
                                col=col, idx=idx, regex=regex, ncols=ncols))


def md_tables(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    head, out, i = "", [], 0
    while i < len(lines):
        if lines[i].startswith("#"):
            head = lines[i]
        if lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-:| ]+\|$", lines[i + 1]):
            hdr = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append((head, hdr, rows))
            i = j
            continue
        i += 1
    return out, "\n".join(lines)


NUM = re.compile(r"-?\d+(?:\.\d+)?|정의 안 됨")


def same(exp, got):
    if exp == got:
        return True
    try:
        e, g = float(exp), float(got)
    except ValueError:
        return False
    d = len(got.split(".")[1]) if "." in got else 0
    return abs(e - g) <= 0.5 * 10 ** -d + 1e-9


def run_checks(checks):
    cache, res = {}, []
    for c in checks:
        if c["report"] not in cache:
            cache[c["report"]] = md_tables(c["report"]) if os.path.exists(c["report"]) else (None, None)
        tables, text = cache[c["report"]]
        got, status = None, ""
        if tables is None:
            status = "보고서 없음"
        elif c["regex"]:
            m = re.search(c["regex"], text)
            got = m.group(1) if m else None
        else:
            cand = []
            for head, hdr, rows in tables:
                if c["section"] and c["section"] not in head:
                    continue
                if c["col"] not in hdr or any(k not in hdr for k in c["keys"]):
                    continue
                if c["ncols"] and len(hdr) != c["ncols"]:
                    continue
                for r in rows:
                    if len(r) == len(hdr) and all(r[hdr.index(k)] == v for k, v in c["keys"].items()):
                        cand.append(r[hdr.index(c["col"])])
            if len(cand) == 1:
                cell = cand[0]
                if isinstance(c["idx"], str):          # 'raw' = 칸 전체, 'split:/' 등
                    got = cell if c["idx"] == "raw" else cell.split(c["idx"][6:])[0].strip()
                else:
                    nums = NUM.findall(cell)
                    got = nums[c["idx"]] if len(nums) > c["idx"] else None
            elif len(cand) > 1:
                status = f"행 {len(cand)}개 일치(모호)"
        if not status:
            status = "찾지 못함" if got is None else ("일치" if same(c["value"], got) else "불일치")
        res.append({**c, "got": got, "status": status})
    return res


# ------------------------------------------------------------------ 절 만들기
def f3(x):
    return "-" if x in (None, "") else f"{float(x):.3f}"


def und(x):
    return "정의 안 됨" if x in (None, "") else f"{float(x):.3f}"


def ci(r, m, d=""):
    lo, hi = r.get(f"{m}{d}_ci_lo", ""), r.get(f"{m}{d}_ci_hi", "")
    return "-" if lo == "" else f"[{float(lo):.3f},{float(hi):.3f}]"


def sec_e7(L, B, tab):
    cm, pb = rcsv(f"{E7F}/cell_metrics.csv"), rcsv(f"{E7F}/paired_cluster_bootstrap.csv")
    var = rcsv(f"{E7F}/run_variability.csv")
    rep = f"{REP}/e7_final_report.md"
    L += ["## 4. E7 최종 (의미 채점 병합 = 주, 키워드 = 보조)", "",
          "모든 값은 `results/revision/e7_final/` CSV 그대로다(새 계산 없음). 구간은 템플릿 짝 군집 부트스트랩",
          "(B 10,000, 시드 20261111). 의미(원) = 원 pass1 규칙(잘림 = 음성) 민감도. sm = string_match(용어만).",
          "정의 안 됨 = 분모 0.", "",
          "### 4.1 셀 단위 지표 (E1/A1 블록 전체)", ""]
    rows = []
    for r in cm:
        rows.append(([r["run"], SC[r["scorer"]], LB[r["label"]], TY[r["type"]], r["TP"], r["FP"], r["FN"], r["TN"],
                      und(r["precision"]), und(r["recall"]), und(r["specificity"]), und(r["mcc"]), ci(r, "mcc")],
                     [f"{E7F}/cell_metrics.csv"]))
        if r["run"] in ("E1-R1", "E2-A1-1") and r["type"] == "micro (5 types)" and r["label"] in ("nominal", "effective") \
                and r["scorer"] in ("sem_merged", "keyword"):
            k = {"run": f"{r['run']} ({'켬' if r['run'] == 'E1-R1' else '끔'})", "채점기": SC[r["scorer"]], "라벨": r["label"]}
            w = f"4.1 {r['run']} {r['scorer']} {r['label']}"
            for col, v in (("정밀도", r["precision"]), ("재현율", r["recall"]), ("특이도", r["specificity"])):
                B.check(f"{w} {col}", rep, und(v), section="## 1", keys=k, col=col)
            for i, v in enumerate((r["mcc"], r["mcc_ci_lo"], r["mcc_ci_hi"])):
                B.check(f"{w} MCC[{i}]", rep, und(v), section="## 1", keys=k, col="MCC [CI]", idx=i)
    B.table(L, ["run", "채점", "라벨", "유형", "TP", "FP", "FN", "TN", "P", "R", "Sp", "MCC", "MCC CI"], rows, tab)

    L += ["### 4.2 RAG 켬 − 끔: 짝 군집 부트스트랩 (주 비교, 반복 쌍, 다수결)", "",
          "차이 = 켬 − 끔. * = 차이 구간이 0 을 포함하지 않음.", ""]
    rows = []
    col = {"sem_merged": "의미(병합), 주", "keyword": "키워드, 보조", "sem_orig": "의미(원), 민감도"}
    for r in pb:
        star = lambda m: "*" if r[f"{m}_ci_excludes_0"] == "yes" else ""      # noqa: E731
        rows.append(([CMP[r["comparison"]], SC[r["scorer"]], LB[r["label"]], TY[r["type"]],
                      und(r["mcc_a"]), und(r["mcc_b"]), und(r["mcc_diff"]) + star("mcc"), ci(r, "mcc", "_diff"),
                      und(r["precision_diff"]) + star("precision"), und(r["specificity_diff"]) + star("specificity"),
                      und(r["recall_diff"]) + star("recall")], [f"{E7F}/paired_cluster_bootstrap.csv"]))
        if r["type"] == "micro (5 types)" and r["scorer"] in col and \
                (r["comparison"] == "E1-R1 - E2-A1-1" or r["label"] in ("nominal", "effective")):
            k = {"비교": CMP[r["comparison"]], "라벨": LB[r["label"]]}
            for i, v in enumerate((r["mcc_diff"], r["mcc_diff_ci_lo"], r["mcc_diff_ci_hi"])):
                B.check(f"4.2 {r['comparison']} {r['scorer']} {r['label']} MCC차[{i}]", f"{REP}/e7_final_report.md",
                        und(v), section="## 2", keys=k, col=col[r["scorer"]], idx=i)
        if r["comparison"] == "E1-R1 - E2-A1-1" and r["label"] == "nominal" and r["type"] != "micro (5 types)":
            c3 = {"sem_merged": "의미(병합)", "keyword": "키워드", "string_match": "string_match"}.get(r["scorer"])
            if c3:
                B.check(f"4.2 주 비교 {r['type']} {r['scorer']} MCC차", f"{REP}/e7_final_report.md", und(r["mcc_diff"]),
                        section="## 3", keys={"유형": TY[r["type"]]}, col=c3)
    B.table(L, ["비교", "채점", "라벨", "유형", "MCC 켬", "MCC 끔", "MCC 차", "MCC 차 CI", "P 차", "Sp 차", "R 차"],
            rows, tab)

    L += ["### 4.3 실행 간 변동 (3회)", ""]
    rows = []
    for r in var:
        rows.append(([r["condition"], SC[r["scorer"]], TY[r["type"]], r["detected_cells"], r["all3_identical"],
                      r["fleiss_kappa"], r["cohen_kappa_pairs"]], [f"{E7F}/run_variability.csv"]))
        if r["type"] == "micro (5 types)" and r["scorer"] in ("sem_merged", "keyword"):
            k = {"조건": r["condition"], "채점기": SC[r["scorer"]]}
            for c_, v in (("탐지 셀(3회)", r["detected_cells"]), ("3회 동일", r["all3_identical"]),
                          ("Fleiss kappa", r["fleiss_kappa"]), ("쌍별 Cohen kappa", r["cohen_kappa_pairs"])):
                B.check(f"4.3 {r['condition']} {r['scorer']} {c_}", f"{REP}/e7_final_report.md", v, section="## 4",
                        keys=k, col=c_, idx="raw")
    B.table(L, ["조건", "채점", "유형", "탐지 셀", "3회 동일", "Fleiss", "쌍별 Cohen"], rows, tab)

    L += ["### 4.4 E3, E4 (셀 지표)", "", "E3 = 용어 45 + 대조군 39 페이지, E4 = 모바일 56 + 대조군 39 페이지.", ""]
    e34, rows = rcsv(f"{E7F}/e3_e4_cell_metrics.csv"), []
    run5 = {("E3", "E1-R1"): "E1-R1 (fixed)", ("E3", "E3-page"): "E3-page", ("E3", "E3-oracle"): "E3-oracle (related)",
            ("E4", "E1-R1"): "E1-R1", ("E4", "E4-mobile"): "E4-mobile"}
    grp = {"E3": "E3 용어(84페이지)", "E4": "E4 모바일(95페이지)"}
    for r in e34:
        rows.append(([r["block"], r["run"], SC[r["scorer"]], LB[r["label"]], TY[r["type"]], r["TP"], r["FP"], r["FN"],
                      r["TN"], und(r["precision"]), und(r["recall"]), und(r["mcc"]), ci(r, "mcc")],
                     [f"{E7F}/e3_e4_cell_metrics.csv"]))
        tt = "Terminology" if r["block"] == "E3" else "Mobile"
        if r["type"] == tt and r["label"] == "nominal" and r["scorer"] in ("sem_merged", "keyword"):
            c_ = "의미(병합) TP/FN, MCC" if r["scorer"] == "sem_merged" else "키워드 TP/FN, MCC"
            B.check(f"4.4 {r['block']} {r['run']} {r['scorer']}", f"{REP}/e7_final_report.md",
                    f"{r['TP']}/{r['FN']}, {und(r['mcc'])}", section="## 5",
                    keys={"묶음": grp[r["block"]], "run": run5[(r["block"], r["run"])]}, col=c_, idx="raw")
    B.table(L, ["묶음", "run", "채점", "라벨", "유형", "TP", "FP", "FN", "TN", "P", "R", "MCC", "MCC CI"], rows, tab)

    L += ["### 4.5 E3, E4 짝 비교 (MCC 차이)", ""]
    rows = [([r["block"], r["comparison"], SC[r["scorer"]], LB[r["label"]], TY[r["type"]], und(r["mcc_a"]),
              und(r["mcc_b"]), und(r["mcc_diff"]) + ("*" if r["mcc_ci_excludes_0"] == "yes" else ""),
              ci(r, "mcc", "_diff")], [f"{E7F}/e3_e4_paired_cluster_bootstrap.csv"])
            for r in rcsv(f"{E7F}/e3_e4_paired_cluster_bootstrap.csv")]
    B.table(L, ["묶음", "비교", "채점", "라벨", "유형", "MCC a", "MCC b", "차이", "차이 CI"], rows, tab)

    L += ["### 4.6 모달리티 (참고용, 키워드 기준만; A2·A3 는 의미 채점 없음)", ""]
    rows = [([r["run"], SC[r["scorer"]], LB[r["label"]], TY[r["type"]], r["TP"], r["FP"], r["FN"], r["TN"],
              und(r["precision"]), und(r["recall"]), und(r["mcc"])], [f"{E7F}/modality_keyword_reference.csv"])
            for r in rcsv(f"{E7F}/modality_keyword_reference.csv")]
    B.table(L, ["run", "채점", "라벨", "유형", "TP", "FP", "FN", "TN", "P", "R", "MCC"], rows, tab)


def sec_e5b(L, B, tab):
    rep = f"{REP}/e5b_report.md"
    L += ["## 9. 사람 평가 E5b: 사람 최종 판정 대 채점기", "",
          "본 평가 A·B 범위 204건(합의 반영 human_final), 이슈 단위. 구간: 템플릿 군집 B 10,000 / 이슈 B 2,000.",
          "값은 `results/revision/human_eval/e5b/` CSV 그대로다. 정의 안 됨 = 분모 0.", "",
          "### 9.1 유형별 (6분류 기준)", ""]
    rows = []
    for r in rcsv(f"{E5B}/E5b-2_main_AB.csv"):
        cl = lambda m: "-" if r[f"{m}_cluster_lo"] == "" else f"[{float(r[m + '_cluster_lo']):.2f},{float(r[m + '_cluster_hi']):.2f}]"  # noqa
        rows.append(([r["type"], r["scorer"], r["n"], r["TP"], r["FP"], r["FN"], und(r["precision"]), cl("precision"),
                      und(r["recall"]), und(r["kappa"]), cl("kappa")], [f"{E5B}/E5b-2_main_AB.csv"]))
        if r["type"].startswith("참고"):
            continue
        k = {"유형": r["type"], "채점기": r["scorer"]}
        for c_ in ("TP", "FP", "FN"):
            B.check(f"9.1 {r['type']} {r['scorer']} {c_}", rep, r[c_], section="## 1", keys=k, col=c_)
        for c_, m in (("정밀도", "precision"), ("재현율", "recall"), ("kappa", "kappa")):
            B.check(f"9.1 {r['type']} {r['scorer']} {c_}", rep, und(r[m]), section="## 1", keys=k, col=c_)
    B.table(L, ["유형", "채점기", "n", "TP", "FP", "FN", "P", "P 군집 CI", "R", "kappa", "kappa 군집 CI"], rows, tab)
    L += ["### 9.2 의미 채점 6분류 kappa", ""]
    rows = []
    for r in rcsv(f"{E5B}/E5b-3_semantic_kappa.csv"):
        rows.append(([r["variant"], r["n"], und(r["kappa"]), f"[{float(r['cluster_lo']):.3f},{float(r['cluster_hi']):.3f}]"],
                     [f"{E5B}/E5b-3_semantic_kappa.csv"]))
    B.check("9.2 의미 6분류 kappa", rep, f"{float(rcsv(f'{E5B}/E5b-3_semantic_kappa.csv')[0]['kappa']):.3f}",
            regex=r"의미 채점 6분류 kappa ([\d.]+)")
    B.table(L, ["변형", "n", "kappa", "군집 CI"], rows, tab)
    L += ["### 9.3 추가 평가 세트 층별 (표준 용어)", ""]
    rows = []
    for r in rcsv(f"{E5B}/E5b-7_supp_strata.csv"):
        rows.append(([r["stratum"], r["measure"], r["k"], r["n"], f3(r["rate"])], [f"{E5B}/E5b-7_supp_strata.csv"]))
        c_ = {"사람 6분류 = 표준 용어 위반": "사람 6분류 = 표준 용어",
              "사람 로그인 레이블 지적 = 예": "사람 로그인 레이블 지적 = 예"}[r["measure"]]
        B.check(f"9.3 {r['stratum']} {r['measure']} k", rep, r["k"], section="## 2", keys={"층": r["stratum"]}, col=c_)
        B.check(f"9.3 {r['stratum']} {r['measure']} rate", rep, f3(r["rate"]), section="## 2",
                keys={"층": r["stratum"]}, col=c_, idx=1)
    B.table(L, ["층", "측정", "k", "n", "비율"], rows, tab)


def sec_e6(L, B, tab, preds, lab, TYPES, SH):
    """E6 보고서 5절의 LLM 열(원 규칙)과 재채점 병합 값을 나란히."""
    from experiments.revision import e6_axe_report as e6
    rep = f"{REP}/e6_axe_report.md"
    scans = {k: json.load(open(f"{e6.D}/scan_{k[0]}_{k[1]}.json", encoding="utf-8"))["pages"] for k in (("A", "1280"), ("B", "1280"))}
    viol = {k: {p: {v["id"] for v in d[p]["violations"]} for p in d} for k, d in scans.items()}
    L += ["## 5. E6: axe-core 와 LLM (nominal, 1280, 유형별 TP / FP 페이지 수)", "",
          "의미(원) = E6 보고서 5절 값(원 pass1, 잘림 = 음성, 재채점 전). 의미(재) = 재채점(retry800) 병합. 검정 없음.", ""]
    rows = []
    sm = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
          "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복ID"}
    for t in TYPES:
        def c(pages, pred):
            return f"{sum(1 for p in pages if pred(p) and lab[(p, t)])} / {sum(1 for p in pages if pred(p) and not lab[(p, t)])}"
        allp = sorted({p for p, _ in lab})
        row = [sm[t], sum(lab[(p, t)] for p in allp)]
        row += [c(allp, lambda p, k=k: any(x in viol[k][p] for x in e6.MAP[t])) for k in (("A", "1280"), ("B", "1280"))]
        for rid in ("E1-R1", "E2-A1-1"):
            pages, P, _, _ = preds[rid]
            vals = [c(pages, lambda p: t in P["kw"][p]), c(pages, lambda p: t in P["sem"][p]),
                    c(pages, lambda p: t in P["merged"][p])]
            row += vals
            rn = "R1" if rid == "E1-R1" else "A1-1"
            for c_, v in ((f"{rn} 키워드", vals[0]), (f"{rn} 의미", vals[1])):
                B.check(f"11 {sm[t]} {c_}", rep, v, section="## 5", keys={"유형": sm[t]}, col=c_, idx="raw")
        rows.append((row, [f"{e6.D}/scan_A_1280.json", f"{e6.D}/scan_B_1280.json", "results/revision/ground_truth.csv",
                           "results/revision/runs/{E1-R1,E2-A1-1}/reports.jsonl",
                           "results/revision/semantic_scores/{E1-R1,E2-A1-1}-sem-p1/grades.jsonl",
                           "results/revision/semantic_scores/{E1-R1,E2-A1-1}-sem-p1-retry/grades.jsonl"]))
    B.table(L, ["유형", "양성", "axe A", "axe B", "R1 키", "R1 의(원)", "R1 의(재)", "A1-1 키", "A1-1 의(원)",
                "A1-1 의(재)"], rows, tab)


def sec_e9(L, B, tab):
    from experiments.revision import e9_regex_table as tbl
    pages9 = {p["page_id"]: p for p in json.load(open("testbed_e9/dataset_metadata_e9.json", encoding="utf-8"))["pages"]}
    name = {"norag": "RAG 끔", "fixed": "고정 질의", "page": "페이지별 질의", "related": "관련 조항 제공", "fixedlong": "fixed-long"}
    rep3 = f"{REP}/e9_main_report_r3.md"
    L += ["## 6. E9 주 결과 (정규식 기준, 탐지/결함 페이지와 대조군 위양성)", "",
          "규칙 `scoring/e9_rules.py`(주), `scoring/e9_rules_aux.py`(보조).",
          "3회째는 RAG 끔과 fixed-long 만. E9-4 는 주 지표 아님.", ""]
    rows, det = [], defaultdict(dict)
    for c in name:
        for rr in (1, 2, 3):
            d = f"{R}/runs_e9/e9-main-{c}-r{rr}"
            if not os.path.exists(f"{d}/reports.jsonl"):
                continue
            for x in tbl.table_rows(c, f"e9-main-{c}-r{rr}", tbl.score_run(d, pages9), pages9):
                rows.append(([name[c], f"r{rr}", x["type"], "주" if x["rule"] == "primary" else "보조",
                              f"{x['detected']}/{x['defect_pages']}", x["recall"],
                              f"{x['control_detected']}/{x['controls']}", x["control_fpr"]],
                             [f"{d}/reports.jsonl", "testbed_e9/dataset_metadata_e9.json"]))
                det[(c, x["type"], x["rule"])][rr] = x
    for (c, t, rule), byr in det.items():
        if t in ("E9-1", "E9-2", "E9-3") and rule == "primary":
            for rr, x in byr.items():
                B.check(f"6 {c} {t} r{rr} 탐지율", rep3, x["recall"], section="### 3.1",
                        keys={"유형": t, "조건": name[c]}, col=f"r{rr}", idx="raw")
        if c in ("norag", "fixedlong") and len(byr) == 3:
            sec = "### RAG 끔" if c == "norag" else "### fixed-long"
            k = {"유형": t, "규칙": "주 지표" if rule == "primary" else "보조"}
            B.check(f"6 {c} {t} {rule} 결함", rep3, " / ".join(f"{byr[i]['detected']}/{byr[i]['defect_pages']}" for i in (1, 2, 3)),
                    section=sec, keys=k, col="결함 탐지 r1 / r2 / r3", idx="raw")
            B.check(f"6 {c} {t} {rule} 대조군", rep3, " / ".join(f"{byr[i]['control_detected']}/{byr[i]['controls']}" for i in (1, 2, 3)),
                    section=sec, keys=k, col="대조군 위양성 r1 / r2 / r3", idx="raw")
    B.table(L, ["조건", "회차", "유형", "규칙", "탐지/결함", "재현율", "대조군 위양성", "위양성률"], rows, tab)


def sec_e9_human(L, B, tab):
    from experiments.revision import e9_human_compare as ec
    from experiments.revision import e9_human_sample as hs
    from experiments.revision import e9_human_supp as sup
    # 사람 평가 52건
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()      # noqa: E731
    if not (os.path.exists(A52) and os.path.exists(A52_COPY)) or sha(A52) != sha(A52_COPY):
        L += ["## 11. E9 사람 평가", "", "평가자 A 입력 파일이 없거나 원본과 작업 복사본이 달라 만들지 않았다.", ""]
        B.unsourced.append({"where": "11", "row": "E9 사람 평가 전체", "missing": A52})
        return
    A, K = ec.read_sheet(A52_COPY), ec.read_key(f"{E9E}/key/e9_key_hit52.csv")
    res = ec.compare(A, K)
    rep = f"{REP}/e9_human_report.md"
    RN = {"e9-main-related-r1": "RAG 켬", "e9-main-norag-r1": "RAG 끔"}
    PG = {"E9-1": "E9-1", "E9-2": "E9-2", "E9-3": "E9-3", "control": "대조군"}
    srcs = [A52, f"{E9E}/key/e9_key_hit52.csv", f"{E9E}/e9_compare_hit52.md"]
    L += ["## 11. E9 사람 평가: 정규식 걸린 52건의 정밀도 (평가자 A 1인, 부록 3)", "",
          "단위 (이슈, 정규식이 잡은 유형) 쌍. 칸 = n건 중 m건(m = A '예'). 재현 누락·재평가는 실시하지 않음. 신뢰구간 없음.",
          "RAG 켬 = 관련 조항 제공(related-r1), RAG 끔 = norag-r1.", ""]
    rows = []
    for run in ("e9-main-related-r1", "e9-main-norag-r1"):
        for s in ec.STRATA:
            cells = []
            for t in ("E9-1", "E9-2", "E9-3"):
                x = res["counts"].get((run, s, t))
                v = f"{x['n']}건 중 {x['yes']}건" if x else "-"
                cells.append(v)
                if x:
                    B.check(f"12 {run} {s} {t}", rep, v, section="## 3",
                            keys={"조건": RN[run], "페이지 결함 유형": PG[s]}, col=ec.TYPE_COL[t], idx="raw")
            if any(v != "-" for v in cells):
                rows.append(([RN[run], PG[s]] + cells, srcs))
    B.table(L, ["조건", "페이지 결함 유형", "banner-text", "spec-values", "login-address"], rows, tab)
    rows = []
    for run in ("e9-main-related-r1", "e9-main-norag-r1"):
        cells = []
        for t in ("E9-1", "E9-2", "E9-3"):
            x = res["totals"].get((run, t))
            v = f"{x['n']}건 중 {x['yes']}건" if x else "-"
            cells.append(v)
            B.check(f"12 합계 {run} {t}", rep, v, section="## 3", keys={"조건": RN[run]}, col=ec.TYPE_COL[t], idx="raw",
                    ncols=4)
        rows.append(([RN[run]] + cells, srcs))
    amb = re.compile(r"모호|구체 없음|일반 주장|DOM 불일치|판단 불가|애매")
    n_amb = sum(1 for r in A.values() if amb.search(r["notes"]))
    rows.append((["불일치 쌍(정규식 걸림, A 아니오)", str(len(res["no"])), "", ""], srcs))
    rows.append((["모호 표시 이슈", str(n_amb), "", ""], srcs))
    B.check("12 불일치 쌍", rep, len(res["no"]), regex=r"## 5\. 불일치 목록 \(.*?, (\d+)쌍\)")
    B.check("12 모호", rep, n_amb, regex=r"모호 표시\(.*?\)가 있는 이슈 \| (\d+) \|")
    L += ["### 11.1 조건별 합계와 기타", ""]
    B.table(L, ["조건", "banner-text", "spec-values", "login-address"], rows, tab)

    # 보조 하한
    rows_s = sup.analyse(A, K, hs.pages_meta())
    reps = f"{REP}/e9_human_report_supp.md"
    L += ["## 12. E9 보조 분석: 페이지 단위 검출 하한 (부록 4, 사후 보조 분석, 주 결과를 대체하지 않음)", "",
          "표본 페이지(층별 15쪽). (가) 유형 일치, (나) 유형 무시. 대조군은 (가) 없음. 신뢰구간·검정 없음.", ""]
    rows = []
    for r in rows_s:
        ga = "-" if r["ga"] is None else str(r["ga"])
        nm = "관련 조항" if r["run"].endswith("related-r1") else "RAG 끔"
        rows.append(([nm, PG[r["stratum"]], r["pages"], r["hit_issues"], r["regex"], ga, r["na"],
                      f"{r['regex_all']}/{r['all_pages']}"], [A52, f"{E9E}/key/e9_key_hit52.csv",
                                                              "results/revision/runs_e9/{run}/reports.jsonl"]))
        k = {"조건": nm, "페이지 층": PG[r["stratum"]]}
        for c_, v in (("표본 쪽", r["pages"]), ("걸린 이슈", r["hit_issues"]), ("정규식", r["regex"]),
                      ("하한 (가)", ga), ("하한 (나)", r["na"])):
            B.check(f"13 {nm} {r['stratum']} {c_}", reps, v, section="## 1", keys=k, col=c_, idx="raw")
        B.check(f"13 {nm} {r['stratum']} 전체", reps, f"{r['regex_all']}/{r['all_pages']}", section="## 2", keys=k,
                col="정규식 검출 / 전체 쪽", idx="raw")
        if r["stratum"] == "control":
            for c_, v in (("A 결함 아님(세 열 모두 아니오)", r["ctrl_no"]), ("A '예' 하나 이상", r["ctrl_yes"])):
                B.check(f"13 {nm} 대조군 {c_}", reps, v, section="## 3", keys={"조건": nm}, col=c_, idx="raw")
    B.table(L, ["조건", "페이지 층", "표본 쪽", "걸린 이슈", "정규식", "하한 (가)", "하한 (나)", "전체 정규식"], rows, tab)
    rows = [([("관련 조항" if r["run"].endswith("related-r1") else "RAG 끔"), r["hit_issues"], r["ctrl_no"], r["ctrl_yes"]],
             [A52, f"{E9E}/key/e9_key_hit52.csv"]) for r in rows_s if r["stratum"] == "control"]
    L += ["### 12.1 대조군: 정규식 걸린 이슈의 A 판정", ""]
    B.table(L, ["조건", "걸린 이슈", "A 결함 아님", "A '예' 하나 이상"], rows, tab)


def sec_audit(L, B, res):
    L += ["## 13. 출처와 보고서 대조", "", "### 13.1 출처를 찾지 못한 숫자 (표에서 뺌)", ""]
    L += [f"- {u['where']}: {u['row'][:60]} (없는 출처: {u['missing']})" for u in B.unsourced] or ["- 없음 (0건)"]
    by = defaultdict(lambda: defaultdict(int))
    for r in res:
        by[r["report"]][r["status"]] += 1
    L += ["", "### 13.2 보고서 자동 대조 (같은 표·행·열 값)", "",
          "| 보고서 | 대조 | 일치 | 불일치 | 찾지 못함·모호 |", "|---|---|---|---|---|"]
    for rep, c in sorted(by.items()):
        n = sum(c.values())
        L.append(f"| `{os.path.basename(rep)}` | {n} | {c['일치']} | {c['불일치']} | {n - c['일치'] - c['불일치']} |")
    L += ["", "출처: 위 보고서들 (`results/revision/reports/`), 이 파일의 표", ""]
    bad = [r for r in res if r["status"] != "일치"]
    L += ["### 13.3 일치하지 않거나 찾지 못한 항목", ""]
    if not bad:
        L += ["없음 (0건).", ""]
    else:
        L += ["| 항목 | 보고서 | 숫자표 값 | 보고서 값 | 상태 |", "|---|---|---|---|---|"]
        L += [f"| {r['where']} | {os.path.basename(r['report'])} | {r['value']} | {r['got']} | {r['status']} |" for r in bad]
        L += ["", "출처: 위와 같음", ""]
