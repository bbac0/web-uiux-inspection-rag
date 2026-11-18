"""
정리 보고서: E2-A2, E2-A3, E3-page, E3-oracle(related-clause), E4-mobile (2026-11-13, API 호출 없음, 통계 검정 없음).

- run 표: 상태, 동시 실행, 기록, 오류율, 이슈 합계, 페이지당 평균·범위, 비용.
- 유형별 탐지 표(TP·FP 페이지 수; 키워드 nominal/effective, 용어 string_match): 같은 페이지 집합에서 기존 run 과 나란히.
  - A2·A3: 200페이지, E1-R1·R2·R3b, E2-A1-1~3 과 비교.
  - E3: 용어 위반 45 + 대조군 39 = 84페이지. 같은 84페이지에서 E1-R1(= E3-fixed)·R2·R3b, A1-1~3 과 비교.
  - E4: 모바일 결함 56 + 대조군 39 = 95페이지. 같은 95페이지에서 비교. effective 라벨은 run 뷰포트에 맞춘다
    (E4 = 390x844 → effective_390, 나머지 run = 1280 → effective_1280; analysis_plan 1절).
- 지출 합계: Gemini 누적(testbed_200 run, E9 파일럿), Anthropic 시험 호출(표준가)을 따로.

  python experiments/revision/clean_report_a2_e4.py
출력: results/revision/reports/clean_report_a2_e4.md
"""
import hashlib
import json
import os
import statistics
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import issue_table              # noqa: E402
from experiments.revision import label_layers   # noqa: E402

OUT = "results/revision/reports/clean_report_a2_e4.md"
RUNS = "results/revision/runs"
NEW = ["E2-A2", "E2-A3", "E3-page", "E3-oracle", "E4-mobile"]
BASE = ["E1-R1", "E1-R2", "E1-R3b", "E2-A1-1", "E2-A1-2", "E2-A1-3"]
SHORT = {"E1-R1": "R1", "E1-R2": "R2", "E1-R3b": "R3b", "E2-A1-1": "A1-1", "E2-A1-2": "A1-2", "E2-A1-3": "A1-3",
         "E2-A2": "A2", "E2-A3": "A3", "E3-page": "E3-page", "E3-oracle": "E3-oracle", "E4-mobile": "E4"}
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping", "Standard Terminology Violation",
         "Duplicate ID Markup Error"]
TS = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
      "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복 ID"}
TERM = "Standard Terminology Violation"
FAIL = ("api_error", "rag_empty", "rag_error", "acquisition_error")
USED = []


def use(p):
    if p not in USED:
        USED.append(p)
    return p


def table(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "|".join("---" for _ in h) + "|"] + \
           ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def jl(p):
    return [json.loads(l) for l in open(use(p), encoding="utf-8") if l.strip()]


def run_meta(rid):
    return json.load(open(use(f"{RUNS}/{rid}/run_meta.json"), encoding="utf-8"))


def preds(rid):
    use(f"{RUNS}/{rid}/reports.jsonl")
    kw, sm = {}, set()
    for r in issue_table.build_rows(rid):
        for t in filter(None, r["keyword_types"].split(";")):
            kw.setdefault(t, set()).add(r["page_id"])
        if r["string_match_term"]:
            sm.add(r["page_id"])
    return kw, sm


def sec_runs():
    L = ["## 1. run 표", ""]
    a, b = [], []
    for rid in NEW:
        calls = jl(f"{RUNS}/{rid}/calls.jsonl")
        reps = jl(f"{RUNS}/{rid}/reports.jsonl")
        m = run_meta(rid)
        summ = json.load(open(use(f"{RUNS}/{rid}/summary.json"), encoding="utf-8"))
        st = Counter(c["status"] for c in calls)
        fail = sum(st.get(k, 0) for k in FAIL)
        n = [len((r.get("report") or {}).get("issues") or []) for r in reps]
        conc = m["args"]["concurrency"]
        a.append([rid, "aborted" if summ.get("aborted") else "complete", f"{conc}{'' if conc == 2 else ' (계획과 다름)'}",
                  len(m["pages"]), len(calls), st.get("ok", 0), st.get("parse_error", 0), f"{100 * fail / len(calls):.1f}%"])
        flags = [f"modality={m['args']['modality']}"]
        if m["args"]["query_mode"] != "fixed":
            flags.append(f"query={m['args']['query_mode']}")
        if m["args"].get("viewport_extra"):
            flags.append("viewport=390x844")
        b.append([rid, sum(n), f"{statistics.mean(n):.2f}", f"{min(n)}~{max(n)}",
                  f"${sum(c['cost_usd']['total'] for c in calls):.4f}",
                  ";".join(f"{k}청크×{v}" for k, v in sorted(Counter(str(c['rag']['n_chunks']) for c in calls).items())),
                  ", ".join(flags)])
    L += table(["run", "상태", "동시", "요청", "기록", "ok", "파싱 실패", "오류율"], a)
    L += ["", "동시 실행은 다섯 run 모두 계획(2건)과 같았다. 오류율 = (api/rag/acquisition 오류 기록 수) / 기록 수.", ""]
    L += table(["run", "이슈 합계", "페이지당 평균", "범위", "비용", "RAG 청크", "조건"], b)
    L += ["", "출처: run 별 `results/revision/runs/{run}/` 의", "`calls.jsonl`, `reports.jsonl`, `run_meta.json`, `summary.json`", ""]
    return L


def detection(title, pages, runs, label_vp, note):
    """pages: 페이지 집합, runs: run 목록, label_vp: {run: '1280'|'390'}"""
    L = [f"## {title}", "", note, ""]
    labs = {}
    for vp in sorted(set(label_vp.values())):
        labs[("nominal", vp)] = label_layers.load_labels("nominal", vp)[0]
        labs[("effective", vp)] = label_layers.load_labels("effective", vp)[0]
    use("results/revision/ground_truth.csv")
    P = {r: preds(r) for r in runs}
    rows_tp, rows_fp = [], []
    for kind in ("keyword", "string_match"):
        for t in (TYPES if kind == "keyword" else [TERM]):
            for lab in ("nominal", "effective"):
                name = TS[t] if kind == "keyword" else "용어 string_match"
                pos_by_vp = {vp: {p for p in pages if labs[(lab, vp)][(p, t)]} for vp in set(label_vp.values())}
                neg_by_vp = {vp: {p for p in pages if labs[(lab, vp)][(p, t)] == 0} for vp in set(label_vp.values())}
                pos_txt = "/".join(str(len(pos_by_vp[vp])) for vp in sorted(pos_by_vp))
                tp, fp = [name, lab, pos_txt], [name, lab, pos_txt]
                for r in runs:
                    vp = label_vp[r]
                    det = (P[r][0].get(t, set()) if kind == "keyword" else P[r][1]) & set(pages)
                    tp.append(len(det & pos_by_vp[vp]))
                    fp.append(len(det & neg_by_vp[vp]))
                rows_tp.append(tp); rows_fp.append(fp)
    vps = sorted(set(label_vp.values()))
    pos_hdr = "양성" if len(vps) == 1 else "양성 (" + "/".join(vps) + ")"
    groups = [runs[i:i + 5] for i in range(0, len(runs), 5)]
    for kind, rows in (("TP", rows_tp), ("FP", rows_fp)):
        for gi, grp in enumerate(groups):
            idx = [runs.index(r) for r in grp]
            L += [f"### {kind} 페이지 수{'' if len(groups) == 1 else f' ({gi + 1}/{len(groups)})'}", ""]
            L += table(["유형", "라벨", pos_hdr] + [SHORT[r] for r in grp], [row[:3] + [row[3 + i] for i in idx] for row in rows])
            L += [""]
    L += ["출처:", "- run 별 `results/revision/runs/{run}/reports.jsonl` (판정: `scoring/issue_table.py`)",
          "- `results/revision/ground_truth.csv`", ""]
    return L


def sec_spend():
    subprocess.run([sys.executable, "experiments/revision/spend_summary.py"], capture_output=True, check=True)
    s = json.load(open(use("results/revision/tables/spend_summary.json"), encoding="utf-8"))
    L = ["## 5. 지출 합계", "", "### 5.1 Gemini (생성 호출, 누적)", ""]
    rows = [[r["run_id"], r["condition"], r["state"], r["calls"], f"{r['cost_usd']:.4f}"] for r in s["rows"]]
    pilot_cost, pilot_calls = 0.0, 0
    for d in sorted(os.listdir("results/revision/runs_e9_pilot")):
        calls = jl(f"results/revision/runs_e9_pilot/{d}/calls.jsonl")
        pilot_cost += sum(c["cost_usd"]["total"] for c in calls)
        pilot_calls += len(calls)
        rows.append([d, "E9 pilot", "complete", len(calls), f"{sum(c['cost_usd']['total'] for c in calls):.4f}"])
    L += table(["run", "조건", "상태", "기록 호출", "비용 (USD)"], rows)
    e = s["unlogged_estimates"][0]["cost_usd"]
    tot = s["recorded_total_usd"] + pilot_cost
    L += ["", f"- Gemini 기록 합계: ${tot:.4f} (testbed_200 run ${s['recorded_total_usd']:.4f} + E9 파일럿 ${pilot_cost:.4f})",
          f"- E1-R3 미기록 추정 포함 범위: ${tot + e['likely']:.4f} (가능성 높은 값) ~ ${tot + e['high_max_based']:.4f} (상한)",
          "- 고정 질의 임베딩 1회, File API 업로드는 비용 기록 대상이 아니다.", "",
          "출처:", f"- `{use('results/revision/tables/spend_summary.json')}` (`experiments/revision/spend_summary.py` 로 갱신)",
          "- `results/revision/runs_e9_pilot/{run}/calls.jsonl`", ""]
    p = jl("results/revision/semantic_scores/probe-E1-R1/probe.jsonl")
    ti, to = sum(r["input_tokens"] for r in p), sum(r["output_tokens"] for r in p)
    L += ["### 5.2 Anthropic (의미 채점 시험 호출, 표준가 입력 $2/1M, 출력 $10/1M)", ""]
    L += table(["항목", "호출", "입력 토큰 합", "출력 토큰 합", "비용 (USD)"],
               [["probe-E1-R1 (시험 호출, 채점 결과 아님)", len(p), f"{ti:,}", f"{to:,}", f"{ti * 2 / 1e6 + to * 10 / 1e6:.4f}"]])
    L += ["", "출처: `results/revision/semantic_scores/probe-E1-R1/probe.jsonl`", ""]
    return L


def main():
    gt = label_layers.load_labels("nominal")[0]
    all_pages = sorted({p for p, _ in gt})
    e3_pages = run_meta("E3-page")["pages"]
    e4_pages = run_meta("E4-mobile")["pages"]
    assert run_meta("E3-oracle")["pages"] == e3_pages
    L = ["# 정리 보고서: A2, A3, E3, E4 (2026-11-13)", "",
         "API 호출 없음. 기술 집계만(통계 검정 없음). 모든 숫자는 각 표 아래 출처 파일에서 읽었다.",
         "E3-oracle 은 문서상 관련 조항 제공(related-clause) 조건이다(플래그 이름만 oracle). E3-fixed = E1-R1 재사용.", ""]
    L += sec_runs()
    L += detection("2. A2(HTML만), A3(스크린샷만): 200페이지", all_pages, BASE + ["E2-A2", "E2-A3"],
                   {r: "1280" for r in BASE + ["E2-A2", "E2-A3"]},
                   "A2·A3 는 의미 채점 대상이 아니다(사전 지정 13항). 키워드·string_match 만.")
    L += detection(f"3. E3: 용어 위반 45 + 대조군 39 = {len(e3_pages)}페이지", e3_pages,
                   ["E1-R1", "E1-R2", "E1-R3b", "E3-page", "E3-oracle", "E2-A1-1", "E2-A1-2", "E2-A1-3"],
                   {r: "1280" for r in BASE + ["E3-page", "E3-oracle"]},
                   "같은 84페이지에서 기존 run 결과를 나란히 계산했다. R1 = E3-fixed.\n"
                   "용어 위반 페이지 중 일부에는 다른 유형 결함도 함께 주입되어 있어 다른 유형의 양성도 있다(양성 열).")
    L += detection(f"4. E4: 모바일 결함 56 + 대조군 39 = {len(e4_pages)}페이지", e4_pages, ["E1-R1", "E1-R2", "E1-R3b", "E4-mobile",
                   "E2-A1-1", "E2-A1-2", "E2-A1-3"], dict({r: "1280" for r in BASE}, **{"E4-mobile": "390"}),
                   "effective 라벨은 run 뷰포트 기준: E4 는 390x844(effective_390), 나머지는 1280(effective_1280). "
                   "양성 열은 1280/390 순.")
    L += sec_spend()
    L += ["## 6. 이 보고서에 사용한 파일", ""]
    L += table(["경로", "SHA-256 앞 16자리"], [[f"`{p}`", hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]]
                                          for p in USED if os.path.isfile(p)])
    L += ["", "생성 스크립트: `experiments/revision/clean_report_a2_e4.py`", ""]
    L = [x for l in L for x in str(l).split("\n")]
    bad = [l for l in L if len(l) > 100]
    if bad:
        raise SystemExit("lines over 100 chars:\n" + "\n".join(f"{len(l)}: {l}" for l in bad))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(OUT)


if __name__ == "__main__":
    sys.exit(main())
