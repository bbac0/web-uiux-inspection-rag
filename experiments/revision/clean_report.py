"""
읽기 쉬운 정리 보고서 (2026-11-13 연구자 요청, API 호출 없음).
모든 숫자는 원본 파일(run 폴더의 jsonl/json, results/revision 의 csv/json)에서 읽는다. 일반 파이프 표, 한 줄 100자 이하.

  python experiments/revision/clean_report.py
출력: results/revision/reports/clean_report_2026-11-13.md
"""
import csv
import hashlib
import json
import os
import statistics
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "results/revision/reports/clean_report_2026-11-13.md"
RUNS = "results/revision/runs"
ORDER = ["E1-R1", "E2-A1-1", "E1-R2", "E2-A1-2", "E1-R3", "E1-R3b", "E2-A1-3"]
SIX = ["E1-R1", "E1-R2", "E1-R3b", "E2-A1-1", "E2-A1-2", "E2-A1-3"]
SHORT = {"E1-R1": "R1", "E1-R2": "R2", "E1-R3b": "R3b", "E2-A1-1": "A1-1", "E2-A1-2": "A1-2", "E2-A1-3": "A1-3"}
TS = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
      "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복 ID"}
FAIL = ("api_error", "rag_empty", "rag_error", "acquisition_error")
USED = []


def src(*paths):
    for p in paths:
        if p not in USED:
            USED.append(p)
    if len(paths) == 1:
        return f"출처: `{paths[0]}`"
    return "출처:\n" + "\n".join(f"- `{p}`" for p in paths)


def rcsv(p):
    src(p)
    return list(csv.DictReader(open(p, encoding="utf-8")))


def rjson(p):
    src(p)
    return json.load(open(p, encoding="utf-8"))


def rjsonl(p):
    src(p)
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def sec1():
    L = ["## 1. run 전체 표 (pilot 제외)", ""]
    a, b = [], []
    for rid in ORDER:
        d = f"{RUNS}/{rid}"
        calls = rjsonl(f"{d}/calls.jsonl")
        reps = rjsonl(f"{d}/reports.jsonl")
        meta = rjson(f"{d}/run_meta.json")
        aborted = os.path.exists(f"{d}/ABORTED.json")
        if aborted:
            src(f"{d}/ABORTED.json")
        st = Counter(c["status"] for c in calls)
        fail = sum(st.get(k, 0) for k in FAIL)
        n = [len((r.get("report") or {}).get("issues") or []) for r in reps]
        chunks = Counter(str(c["rag"]["n_chunks"]) for c in calls)
        a.append([rid, "aborted" if aborted else "complete", meta["args"]["concurrency"], len(meta["pages"]),
                  len(calls), st.get("ok", 0), st.get("parse_error", 0), f"{100 * fail / len(calls):.1f}%"])
        b.append([rid, sum(n), f"{statistics.mean(n):.2f}", f"{min(n)}~{max(n)}",
                  f"${sum(c['cost_usd']['total'] for c in calls):.4f}",
                  ";".join(f"{k}청크×{v}" for k, v in sorted(chunks.items()))])
    L += table(["run", "상태", "동시", "요청 페이지", "기록", "ok", "파싱 실패", "오류율"], a)
    L += ["", "오류율 = (api/rag/acquisition 오류 기록 수) / 기록 수.", ""]
    L += table(["run", "이슈 합계", "이슈/페이지 평균", "범위", "비용", "RAG 청크"], b)
    L += ["", "출처: run 별 `results/revision/runs/{run}/calls.jsonl`, `reports.jsonl`, `run_meta.json`",
          "- E1-R3 은 160/200 에서 중단(aborted, 분석 제외): `results/revision/runs/E1-R3/ABORTED.json`", ""]
    return L


def sec2():
    rows = rcsv("results/revision/e7/exploratory_issue_counts.csv")
    by = {r["run"]: r for r in rows}
    L = ["## 2. 페이지당 이슈 수 분포 (페이지 수)", ""]
    hdr = ["run"] + [str(k) for k in range(11)] + [">10", "평균"]
    L += table(hdr, [[SHORT[r]] + [by[r][f"n_issues_{k}"] for k in range(11)] + [by[r]["n_issues_gt10"], by[r]["mean"]]
                     for r in SIX])
    L += ["", src("results/revision/e7/exploratory_issue_counts.csv"), ""]
    return L


def sec3():
    rows = rcsv("results/revision/tables/e1_a1_type_detection.csv")
    L = ["## 3. 유형별 탐지 페이지 수 (TP, FP)", "",
         "키워드 = 키워드 사전(description). string_match = '접속하기' 언급 기반(용어 유형만).", ""]

    def name(r):
        if "string_match" in r["defect_type"]:
            return "용어 string_match"
        return TS[r["defect_type"]]
    for kind in ("tp", "fp"):
        L += [f"### {kind.upper()} 페이지 수", ""]
        L += table(["유형", "라벨", "양성"] + [SHORT[s] for s in SIX],
                   [[name(r), r["label"], r["positives"]] + [r[f"{s}_{kind}_pages"] for s in SIX] for r in rows])
        L += [""]
    L += [src("results/revision/tables/e1_a1_type_detection.csv"), ""]
    return L


def sec4():
    L = ["## 4. E7 (키워드 채점, 5유형 합산 셀; R1 vs A1-1)", ""]
    cm = rcsv("results/revision/e7/cell_metrics.csv")
    labs = [("nominal", "nominal"), ("effective", "effective"), ("guideline_grounded", "grounded 명도 대비"),
            ("guideline_grounded_btn_true", "grounded 버튼 true")]
    g = lambda run, lab: next(r for r in cm if r["run"] == run and r["label"] == lab and r["scorer"] == "keyword"
                              and r["type"] == "micro (5 types)")
    L += ["### 4.1 MCC 와 템플릿 군집 부트스트랩 95% 구간", ""]
    L += table(["라벨", "셀", "R1 MCC", "R1 구간", "A1-1 MCC", "A1-1 구간"],
               [[n, g("E1-R1", l)["n_cells"], g("E1-R1", l)["mcc"], f"[{g('E1-R1', l)['mcc_ci_lo']}, {g('E1-R1', l)['mcc_ci_hi']}]",
                 g("E2-A1-1", l)["mcc"], f"[{g('E2-A1-1', l)['mcc_ci_lo']}, {g('E2-A1-1', l)['mcc_ci_hi']}]"] for l, n in labs])
    L += ["", src("results/revision/e7/cell_metrics.csv"), ""]
    L += ["### 4.2 정밀도, 재현율, 특이도, 균형 정확도", ""]
    L += table(["라벨", "run", "정밀도", "재현율", "특이도", "균형 정확도", "TP", "FP", "FN", "TN"],
               [[n, SHORT[run], g(run, l)["precision"], g(run, l)["recall"], g(run, l)["specificity"],
                 g(run, l)["balanced_accuracy"], g(run, l)["TP"], g(run, l)["FP"], g(run, l)["FN"], g(run, l)["TN"]]
                for l, n in labs for run in ("E1-R1", "E2-A1-1")])
    L += ["", src("results/revision/e7/cell_metrics.csv"), ""]
    pc = rcsv("results/revision/e7/paired_cluster_bootstrap.csv")
    p = lambda l: next(r for r in pc if r["comparison"] == "E1-R1 - E2-A1-1" and r["label"] == l and r["scorer"] == "keyword"
                       and r["type"] == "micro (5 types)")
    L += ["### 4.3 R1 − A1-1 차이 (짝 템플릿 군집 부트스트랩, 확정)", "",
          "added after seeing replicate results, before semantic scoring.", ""]
    L += table(["라벨", "MCC 차이", "구간", "LOTO 범위"],
               [[n, p(l)["mcc_diff"], f"[{p(l)['mcc_diff_ci_lo']}, {p(l)['mcc_diff_ci_hi']}]",
                 f"{p(l)['mcc_loto_diff_min']}~{p(l)['mcc_loto_diff_max']}"] for l, n in labs])
    L += ["", "주: **합산 MCC 는 서로 성격이 다른 유형(대비, 모바일, 버튼, 용어, 중복 ID)을 섞은 값**이다.",
          "유형별 차이는 `results/revision/reports/clean_report_c_section.md` 6절 참고.", ""]
    L += table(["라벨", "정밀도 차이 [구간]", "특이도 차이 [구간]", "재현율 차이 [구간]"],
               [[n] + [f"{p(l)[m + '_diff']} [{p(l)[m + '_diff_ci_lo']}, {p(l)[m + '_diff_ci_hi']}]"
                       for m in ("precision", "specificity", "recall")] for l, n in labs])
    L += ["", src("results/revision/e7/paired_cluster_bootstrap.csv"), ""]
    mc = rcsv("results/revision/e7/mcnemar.csv")
    L += ["### 4.4 exact McNemar (셀 단위, 군집 미고려, 보조)", "",
          "b = R1 만 맞음, c = A1-1 만 맞음. 주 검정의 Holm 가족(A1, A2, A3)은 A2·A3 미실행이라 미완성.", ""]
    m = lambda l, sc, t: next(r for r in mc if r["comparison"] == "E1-R1 vs E2-A1-1" and r["label"] == l
                              and r["scorer"] == sc and r["type"] == t)
    L += table(["라벨", "셀", "b", "c", "p (exact)", "Holm 상한 3p"],
               [[n, m(l, "keyword", "micro (5 types)")["n_cells"], m(l, "keyword", "micro (5 types)")["b_first_correct_only"],
                 m(l, "keyword", "micro (5 types)")["c_second_correct_only"], m(l, "keyword", "micro (5 types)")["p_exact"],
                 f"{min(1.0, 3 * float(m(l, 'keyword', 'micro (5 types)')['p_exact'])):.4g}"] for l, n in labs])
    L += ["", src("results/revision/e7/mcnemar.csv"), ""]
    L += ["### 4.5 string_match (용어 유형, mention-based) exact McNemar (탐색적, 보정 없음)", ""]
    L += table(["비교", "라벨", "셀", "b", "c", "p (exact)"],
               [[r["comparison"], r["label"], r["n_cells"], r["b_first_correct_only"], r["c_second_correct_only"], r["p_exact"]]
                for r in mc if r["scorer"] == "string_match"])
    L += ["", src("results/revision/e7/mcnemar.csv"), ""]
    rv = rcsv("results/revision/e7/run_variability.csv")
    L += ["### 4.6 실행 간 변동 (조건 안 3회)", "",
          "켬 = E1-R1, R2, R3b. 끔 = E2-A1-1, A1-2, A1-3. 3회 동일 = 세 run 예측이 모두 같은 셀 비율.", ""]
    rows = []
    for r in rv:
        rows.append(["켬" if r["condition"].startswith("E1") else "끔", r["scorer"], r["type"], r["detected_cells"],
                     r["sd"], r["all3_identical"], r["fleiss_kappa"]])
    L += table(["조건", "채점기", "유형", "탐지 셀 (3회)", "SD", "3회 동일", "Fleiss kappa"], rows)
    L += [""]
    L += table(["조건", "채점기", "유형", "쌍별 Cohen kappa (1-2;1-3;2-3)"],
               [["켬" if r["condition"].startswith("E1") else "끔", r["scorer"], r["type"], r["cohen_kappa_pairs"]] for r in rv])
    L += ["", src("results/revision/e7/run_variability.csv"), ""]
    return L


def sec5():
    sh = rcsv("results/revision/e7/exploratory_category_shares_on_off.csv")
    ct = rcsv("results/revision/e7/exploratory_categories.csv")
    cv = rcsv("results/revision/e7/exploratory_prompt_structure_convergence.csv")
    cnt = {r["run"]: r for r in ct}
    L = ["## 5. 이슈 카테고리 비중과 프롬프트 예시 구조 (exploratory, 사전 지정 아님)", ""]
    rows = []
    for r in sh:
        run = r["run"]
        c = cnt.get(run)
        rows.append(["켬" if r["rag"] == "on" else "끔", SHORT.get(run, "합계 (3회)"), r["issues"],
                     f"{c['디자인']} ({r['디자인_share']})" if c else r["디자인_share"],
                     f"{c['운영']} ({r['운영_share']})" if c else r["운영_share"],
                     f"{c['기술']} ({r['기술_share']})" if c else r["기술_share"]])
    L += table(["RAG", "run", "이슈", "디자인 건수 (비중)", "운영 건수 (비중)", "기술 건수 (비중)"], rows)
    L += ["", "합계 행의 비중은 3회 합산 이슈 기준.", "",
          src("results/revision/e7/exploratory_category_shares_on_off.csv", "results/revision/e7/exploratory_categories.csv"), ""]
    L += table(["RAG", "run", "페이지", "이슈 정확히 3건", "3건 + 카테고리별 1건", "비율", "카테고리 각 1건 이상"],
               [["켬" if r["rag"] == "on" else "끔", SHORT.get(r["run"], r["run"].replace("pooled RAG on (3 runs)", "합계 (3회)")
                                                       .replace("pooled RAG off (3 runs)", "합계 (3회)")),
                 r["pages"], r["exactly_3_issues"], r["exactly_3_and_one_per_category"], r["share_converged"],
                 r["at_least_one_per_category"]] for r in cv])
    L += ["", src("results/revision/e7/exploratory_prompt_structure_convergence.csv"), ""]
    return L


def sec6():
    meta = rjson("testbed_e9/dataset_metadata_e9.json")
    summ = rjson("results/revision/e9/e9_verify_summary.json")
    names = [("E9-1a", "E9-1a 배너 문구 단어 변경"), ("E9-1b", "E9-1b 배너 문구 띄어쓰기 변경"), ("E9-2-banner", "E9-2 배너 규격값"),
             ("E9-2-header", "E9-2 헤더 규격값"), ("E9-2-footer", "E9-2 푸터 규격값"), ("E9-3", "E9-3 로그인 링크 → /signup"),
             ("E9-4", "E9-4 768px 이하 로그인 숨김 (보조)"), ("control", "대조군")]
    c = Counter(p["subtype"] for p in meta["pages"])
    L = ["## 6. E9 테스트베드", "", "### 6.1 본 실험 91페이지 (`testbed_e9/`, 시드 20261116)", ""]
    rows = [[n, c[k], summ["by_subtype"][k]["verification_pass"], summ["by_subtype"][k].get("structurally_undetectable", "-")]
            for k, n in names]
    rows.append(["**합계**", sum(c.values()), summ["verification_pass"], summ["structurally_undetectable"]])
    L += table(["유형", "페이지", "검증 통과", "구조적 탐지 불가"], rows)
    L += ["", src("testbed_e9/dataset_metadata_e9.json", "results/revision/e9/e9_verify_summary.json"), ""]
    pm = rjson("testbed_e9_pilot/dataset_metadata_e9_pilot.json")
    ps = rjson("results/revision/e9_pilot/e9_verify_summary.json")
    gt = {r["page_id"]: r for r in rcsv("results/revision/e9_pilot/ground_truth_e9.csv")}
    L += ["### 6.2 파일럿 8페이지 (`testbed_e9_pilot/`, 시드 20261117, 분석 제외)", ""]
    L += table(["페이지", "유형", "본문 템플릿", "변형", "검증", "본 실험과 같은 HTML"],
               [[p["page_id"], p["subtype"], p["body_template"], p["variant"] or "-", gt[p["page_id"]]["verification_pass"],
                 p["identical_to_main_page"] or "아니오"] for p in sorted(pm["pages"], key=lambda x: x["page_id"])])
    L += ["", f"검증 통과 {ps['verification_pass']}/{ps['pages']}.", "",
          src("testbed_e9_pilot/dataset_metadata_e9_pilot.json", "results/revision/e9_pilot/ground_truth_e9.csv",
              "results/revision/e9_pilot/e9_verify_summary.json"), ""]
    return L


def sec7():
    s = rjson("results/revision/tables/spend_summary.json")
    L = ["## 7. 지출 합계 (Gemini 생성 호출 기준)", ""]
    L += table(["run", "조건", "상태", "기록 호출", "비용 (USD)"],
               [[r["run_id"], r["condition"], r["state"], r["calls"], f"{r['cost_usd']:.4f}"] for r in s["rows"]])
    e = s["unlogged_estimates"][0]
    L += ["", f"- 기록된 합계: ${s['recorded_total_usd']:.4f}",
          f"- 분석 대상 완료 run 소계(pilot·aborted 제외): ${s['analysis_complete_subtotal_usd']:.4f}",
          f"- E1-R3 미기록 과금 가능 생성 호출: {e['generation_calls_possible']['low']}~{e['generation_calls_possible']['high']}건 "
          f"(가능성 높은 값 {e['generation_calls_possible']['likely']}건)",
          f"- 미기록 추정 비용: ${e['cost_usd']['likely']:.4f} (가능성 높은 값) ~ ${e['cost_usd']['high_max_based']:.4f} (상한)",
          f"- 추정 포함 총액 범위: ${s['recorded_total_usd']:.4f} ~ ${s['recorded_total_usd'] + e['cost_usd']['high_max_based']:.4f}",
          "- 고정 질의 임베딩 1회와 File API 업로드는 비용 기록 대상이 아니다.", "",
          src("results/revision/tables/spend_summary.json", "results/revision/runs/E1-R3/ABORTED.json"), ""]
    return L


def main():
    L = ["# 정리 보고서 (2026-11-13)", "",
         "모든 숫자는 각 표 아래 출처 파일에서 읽은 값이다. API 호출 없음. 통계 검정은 사전 지정 범위 안에서만 보고한다.", ""]
    for f in (sec1, sec2, sec3, sec4, sec5, sec6, sec7):
        L += f()
    L += ["## 8. 이 보고서에 사용한 파일", ""]
    files = []
    for p in USED:
        if os.path.isfile(p):
            files.append([f"`{p}`", hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]])
    L += table(["경로", "SHA-256 앞 16자리"], files)
    L += ["", "생성 스크립트: `experiments/revision/clean_report.py`", ""]
    L = [x for l in L for x in str(l).split("\n")]
    long_lines = [l for l in L if len(l) > 100]
    if long_lines:
        raise SystemExit("lines over 100 chars:\n" + "\n".join(f"{len(l)}: {l}" for l in long_lines))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(OUT)


if __name__ == "__main__":
    sys.exit(main())
