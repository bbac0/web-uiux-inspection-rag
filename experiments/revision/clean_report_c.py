"""
정리 보고서 C절 (2026-11-13 연구자 지시 6~8번, API 호출 없음). 일반 파이프 표, 한 줄 100자 이하, 표마다 출처.

6. 유형별 짝 템플릿 군집 부트스트랩 (R1 − A1-1 주 비교, R2 − A1-2·R3b − A1-3 반복 재현): 특이도·정밀도·재현율 차이와 95% 구간.
   값은 e7_paired_cluster.py 가 B = 10,000, 시드 20261111 로 계산해 확정 보관한 paired_cluster_bootstrap.csv 의 유형별 행에서 읽는다.
   합산 MCC 표와 "합산 MCC 는 서로 성격이 다른 유형을 섞은 값" 주석도 함께 싣는다.
7. 용어 유형 탐색적 분석: string_match 가 탐지한 이슈의 카테고리(켬/끔), 용어 TP 페이지 수와 운영 카테고리 이슈 수의 관계.
8. 켬/끔 페이지당 카테고리 구성 분포 (exploratory).

  python experiments/revision/clean_report_c.py
출력: results/revision/reports/clean_report_c_section.md
"""
import csv
import hashlib
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import string_match            # noqa: E402
from experiments.revision import label_layers   # noqa: E402

OUT = "results/revision/reports/clean_report_c_section.md"
RUNS = "results/revision/runs"
E1 = ["E1-R1", "E1-R2", "E1-R3b"]
A1 = ["E2-A1-1", "E2-A1-2", "E2-A1-3"]
SHORT = {"E1-R1": "R1", "E1-R2": "R2", "E1-R3b": "R3b", "E2-A1-1": "A1-1", "E2-A1-2": "A1-2", "E2-A1-3": "A1-3"}
PAIRS = [("E1-R1 - E2-A1-1", "R1 − A1-1", "주 비교 (사전 지정)"), ("E1-R2 - E2-A1-2", "R2 − A1-2", "반복 재현"),
         ("E1-R3b - E2-A1-3", "R3b − A1-3", "반복 재현")]
CATS = ["디자인", "운영", "기술"]
TERM = "Standard Terminology Violation"
USED = []
STATUS = "added after seeing replicate results, before semantic scoring"


def use(p):
    if p not in USED:
        USED.append(p)
    return p


def src(*paths):
    for p in paths:
        use(p)
    if len(paths) == 1:
        return f"출처: `{paths[0]}`"
    return "출처:\n" + "\n".join(f"- `{p}`" for p in paths)


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    return out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def reports(rid):
    p = use(f"{RUNS}/{rid}/reports.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def issues_of(rec):
    return [i for i in ((rec.get("report") or {}).get("issues") or []) if isinstance(i, dict)]


def sec6():
    pc = list(csv.DictReader(open(use("results/revision/e7/paired_cluster_bootstrap.csv"), encoding="utf-8")))
    get = lambda cmp, sc, lab, typ: next((r for r in pc if r["comparison"] == cmp and r["scorer"] == sc and r["label"] == lab
                                          and r["type"] == typ), None)
    L = ["## 6. 유형별 짝 템플릿 군집 부트스트랩 (RAG 켬 − 끔)", "",
         f"분석 상태: **{STATUS}**.",
         "B = 10,000, numpy default_rng 시드 20261111, 같은 재표집 템플릿을 두 조건에 적용, 백분위수 95% 구간.",
         "주 비교 R1 − A1-1 (사전 지정), R2 − A1-2 와 R3b − A1-3 은 반복 재현.", ""]
    L += ["### 6.0 합산 MCC (5유형 셀 합산, 키워드)", ""]
    rows = []
    for cmp, name, role in PAIRS:
        for lab in ("nominal", "effective"):
            r = get(cmp, "keyword", lab, "micro (5 types)")
            rows.append([name, role, lab, r["mcc_diff"], f"[{r['mcc_diff_ci_lo']}, {r['mcc_diff_ci_hi']}]",
                         f"{r['mcc_loto_diff_min']}~{r['mcc_loto_diff_max']}"])
    L += table(["비교", "역할", "라벨", "MCC 차이", "95% 구간", "LOTO 범위"], rows)
    L += ["", "주: **합산 MCC 는 서로 성격이 다른 유형(대비, 모바일, 버튼, 용어, 중복 ID)을 섞은 값**이다.",
          "유형별 차이는 아래 6.1~6.6 에서 본다.", "", src("results/revision/e7/paired_cluster_bootstrap.csv"), ""]
    specs = [("6.1 대비 (키워드)", "keyword", "nominal", "Contrast", "nominal = effective (같은 라벨 값)"),
             ("6.2 모바일 (키워드)", "keyword", "nominal", "Mobile", "nominal = effective (같은 라벨 값)"),
             ("6.3 버튼 (키워드, effective)", "keyword", "effective", "Button", "effective 양성 20페이지"),
             ("6.4 용어 (키워드)", "keyword", None, "Terminology", "nominal 양성 45, effective 양성 42"),
             ("6.5 용어 (string_match, mention-based)", "string_match", None, "Terminology", "nominal 양성 45, effective 양성 42"),
             ("6.6 중복 ID (키워드)", "keyword", "nominal", "DupID", "nominal = effective (같은 라벨 값)")]
    for title, sc, lab, typ, note in specs:
        L += [f"### {title}", "", note, ""]
        rows = []
        for cmp, name, role in PAIRS:
            for lb in ([lab] if lab else ["nominal", "effective"]):
                r = get(cmp, sc, lb, typ)
                cell = lambda m: f"{r[m + '_diff']} [{r[m + '_diff_ci_lo']}, {r[m + '_diff_ci_hi']}]"
                rows.append([name, lb, cell("specificity"), cell("precision"), cell("recall")])
        L += table(["비교", "라벨", "특이도 차이 [95% 구간]", "정밀도 차이 [95% 구간]", "재현율 차이 [95% 구간]"], rows)
        L += ["", src("results/revision/e7/paired_cluster_bootstrap.csv"), ""]
    L += ["정밀도 차이가 0.000 [0.000, 0.000] 인 행은 두 조건 모두 위양성이 0 이라 정밀도가 1.000 으로 같은 경우다.", ""]
    return L


def sec7():
    nom, _ = label_layers.load_labels("nominal")
    use("results/revision/ground_truth.csv")
    L = ["## 7. 용어 유형 탐색적 분석 (exploratory, 사전 지정 아님)", "",
         "string_match = 이슈의 description 또는 suggestion 에 '접속하기' 포함 (mention-based).", ""]
    rows, rel = [], []
    pooled = {"켬": Counter(), "끔": Counter()}
    for rid in E1 + A1:
        cond = "켬" if rid in E1 else "끔"
        c = Counter()
        tp_pages, ops_issues, ops_sm = set(), 0, 0
        for rec in reports(rid):
            pid = rec["page_id"]
            for i in issues_of(rec):
                hit = string_match.match(i)
                cat = i.get("category") if i.get("category") in CATS else "기타"
                if cat == "운영":
                    ops_issues += 1
                if hit:
                    c[cat] += 1
                    ops_sm += cat == "운영"
                    if nom[(pid, TERM)] == 1:
                        tp_pages.add(pid)
        pooled[cond].update(c)
        n = sum(c.values())
        rows.append([cond, SHORT[rid], n] + [f"{c[k]} ({c[k] / n:.3f})" if n else "0" for k in CATS + ["기타"]])
        rel.append([cond, SHORT[rid], len(tp_pages), ops_issues, ops_sm, n])
    for cond in ("켬", "끔"):
        c = pooled[cond]; n = sum(c.values())
        rows.append([cond, "합계 (3회)", n] + [f"{c[k]} ({c[k] / n:.3f})" if n else "0" for k in CATS + ["기타"]])
    L += ["### 7.1 string_match 가 탐지한 이슈의 카테고리 (건수, 비중)", ""]
    L += table(["RAG", "run", "탐지 이슈", "디자인", "운영", "기술", "기타"], rows)
    L += ["", src(*[f"{RUNS}/{r}/reports.jsonl" for r in E1 + A1]), ""]
    L += ["### 7.2 용어 TP 페이지 수와 운영 카테고리 이슈 수", "",
          "TP 페이지 = string_match 탐지 이슈가 있는 nominal 용어 양성 페이지. 운영 이슈 = 그 run 의 전체 운영 카테고리 이슈.", ""]
    L += table(["RAG", "run", "용어 TP 페이지", "운영 이슈 (전체)", "운영 이슈 중 string_match 탐지", "string_match 탐지 이슈"], rel)
    L += ["", src(*([f"{RUNS}/{r}/reports.jsonl" for r in E1 + A1] + ["results/revision/ground_truth.csv"])), ""]
    return L


def sec8():
    combos = ["없음", "디자인만", "운영만", "기술만", "디자인+운영", "디자인+기술", "운영+기술", "세 카테고리 모두"]

    def combo(issues):
        s = {i.get("category") for i in issues if i.get("category") in CATS}
        if not s:
            return "없음"
        if len(s) == 3:
            return "세 카테고리 모두"
        order = [k for k in CATS if k in s]
        return order[0] + "만" if len(order) == 1 else "+".join(order)
    L = ["## 8. 페이지당 카테고리 구성 분포 (exploratory, 사전 지정 아님)", "",
         "각 페이지의 이슈에 나타난 카테고리 조합별 페이지 수.", ""]
    per, pooled = [], {"켬": Counter(), "끔": Counter()}
    for rid in E1 + A1:
        cond = "켬" if rid in E1 else "끔"
        c = Counter(combo(issues_of(rec)) for rec in reports(rid))
        pooled[cond].update(c)
        per.append((cond, SHORT[rid], c))
    for cond in ("켬", "끔"):
        per.append((cond, "합계 (3회)", pooled[cond]))
    half = [combos[:4], combos[4:]]
    for k, cols in enumerate(half):
        L += [f"### 8.{k + 1} 조합 {'1~4' if k == 0 else '5~8'}", ""]
        L += table(["RAG", "run"] + cols, [[cond, run] + [c.get(x, 0) for x in cols] for cond, run, c in per])
        L += ["", src(*[f"{RUNS}/{r}/reports.jsonl" for r in E1 + A1]), ""]
    return L


def main():
    L = ["# 정리 보고서 C절 (2026-11-13)", "",
         "API 호출 없음. 모든 숫자는 각 표 아래 출처 파일에서 읽었다. 6절은 사전 지정 뒤에 추가한 강건성 분석,",
         "7·8절은 탐색적 분석(사전 지정 아님)이다. 통계 검정은 하지 않았다.", ""]
    L += sec6() + sec7() + sec8()
    L += ["## 9. 이 보고서에 사용한 파일", ""]
    L += table(["경로", "SHA-256 앞 16자리"], [[f"`{p}`", hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]] for p in USED])
    L += ["", "생성 스크립트: `experiments/revision/clean_report_c.py`", ""]
    L = [x for l in L for x in str(l).split("\n")]
    bad = [l for l in L if len(l) > 100]
    if bad:
        raise SystemExit("lines over 100 chars:\n" + "\n".join(f"{len(l)}: {l}" for l in bad))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(OUT)


if __name__ == "__main__":
    sys.exit(main())
