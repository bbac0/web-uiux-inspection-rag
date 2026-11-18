"""
단계별 지연시간 표 (API 호출 없음). run 의 calls.jsonl 에서 status=ok 인 대상 페이지 레코드만 쓴다.

  python experiments/revision/latency_table.py E1-R1
출력: results/revision/tables/latency_{run_id}.csv, .tex, .md
"""
import csv
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
STAGES = [("acquisition", "수집 (페이지 로드 + 고정 대기 3초 + 스크린샷 + DOM)", "Acquisition$^{a}$"),
          ("query_embedding", "질의 임베딩", "Query embedding"),
          ("vector_search", "벡터 검색", "Vector search"),
          ("upload", "이미지 업로드 (File API)", "Image upload"),
          ("llm", "LLM 생성", "LLM generation"),
          ("other", "기타 (프롬프트 구성, 파싱, 파일 삭제 등 = 합계 − 위 단계)", "Other$^{b}$"),
          ("total", "합계", "Total")]
NOTE_KO = ("a 수집 단계에는 프로덕션 코드의 고정 대기 3초(`networkidle` 후 `asyncio.sleep(3)`)가 포함된다. "
           "b 합계에서 측정한 단계들을 뺀 나머지.")
NOTE_EN = ("$^{a}$Includes the fixed 3-s wait after network idle in the production pipeline. "
           "$^{b}$Total minus the measured stages (prompt assembly, JSON parsing, file deletion).")


def pct(xs, q):
    xs = sorted(xs); k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def main(run_id):
    d = os.path.join("results", "revision", "runs", run_id)
    recs = [json.loads(l) for l in open(os.path.join(d, "calls.jsonl"), encoding="utf-8")]
    recs = [r for r in recs if r["status"] == "ok" and "#linked:" not in (r["page_id"] or "")]
    vals = {k: [] for k, _, _ in STAGES}
    for r in recs:
        lat = r["latency_sec"]
        parts = [lat.get(k) or 0.0 for k in ("acquisition", "query_embedding", "vector_search", "upload", "llm")]
        for k, _, _ in STAGES:
            if k == "other":
                vals[k].append(lat["total"] - sum(parts))
            elif lat.get(k) is not None:
                vals[k].append(lat[k])
    rows = []
    for k, ko, en in STAGES:
        xs = vals[k]
        rows.append({"stage": k, "label_ko": ko, "label_en": en, "n": len(xs),
                     "mean": statistics.mean(xs), "sd": statistics.stdev(xs) if len(xs) > 1 else 0.0,
                     "median": statistics.median(xs), "p95": pct(xs, 0.95), "min": min(xs), "max": max(xs),
                     "share_of_total_mean": statistics.mean(xs) / statistics.mean(vals["total"])})
    out = os.path.join("results", "revision", "tables")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f"latency_{run_id}.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    T = [r"\begin{table}[ht]", r"\centering",
         r"\caption{Per-stage latency (s), run " + run_id.replace("_", r"\_") + f", $n={rows[0]['n']}$ pages, sequential." + "}",
         r"\begin{tabular}{lrrrrr}", r"\toprule", r"Stage & Mean & SD & Median & P95 & Share \\", r"\midrule"]
    for r in rows:
        if r["stage"] == "total":
            T.append(r"\midrule")
        T.append(f"{r['label_en']} & {r['mean']:.2f} & {r['sd']:.2f} & {r['median']:.2f} & {r['p95']:.2f} & "
                 f"{100 * r['share_of_total_mean']:.1f}\\% \\\\")
    T += [r"\bottomrule", r"\end{tabular}", "", r"\vspace{2pt}\footnotesize " + NOTE_EN, r"\end{table}"]
    open(os.path.join(out, f"latency_{run_id}.tex"), "w", encoding="utf-8").write("\n".join(T) + "\n")
    M = [f"### 단계별 지연시간 ({run_id}, 성공 {rows[0]['n']}페이지, 초)", "",
         "| 단계 | 평균 | 표준편차 | 중앙값 | P95 | 최소 | 최대 | 합계 대비 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        M.append(f"| {r['label_ko']} | {r['mean']:.2f} | {r['sd']:.2f} | {r['median']:.2f} | {r['p95']:.2f} | "
                 f"{r['min']:.2f} | {r['max']:.2f} | {100 * r['share_of_total_mean']:.1f}% |")
    M += ["", "주: " + NOTE_KO]
    open(os.path.join(out, f"latency_{run_id}.md"), "w", encoding="utf-8").write("\n".join(M) + "\n")
    print("\n".join(M))


if __name__ == "__main__":
    main(sys.argv[1])
