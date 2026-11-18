"""
지출 합계 (Gemini 생성 호출 기준, API 호출 없음).

- results/revision/runs/*/calls.jsonl 의 cost_usd.total 을 run 별로 더한다(가짜 LLM run 은 제외).
- 단가: 입력 $0.30/1M, 캐시 입력 $0.03/1M, 출력+사고 $2.50/1M (러너가 호출마다 기록한 값을 그대로 합산).
- 질의 임베딩 호출과 File API 업로드는 비용 기록 대상이 아니다(생성 호출 기준).
- aborted run 의 미기록 과금 가능 호출은 ABORTED.json 의 추정(amendments[].unlogged_billable_estimate)을 따로 표시한다.

출력: results/revision/tables/spend_summary.md, spend_summary.json
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
RUNS = os.path.join("results", "revision", "runs")


def main():
    rows, est = [], []
    for rid in sorted(os.listdir(RUNS), key=lambda r: os.path.getmtime(os.path.join(RUNS, r, "run_meta.json"))):
        d = os.path.join(RUNS, rid)
        meta = json.load(open(os.path.join(d, "run_meta.json"), encoding="utf-8"))
        if meta.get("mock"):
            continue
        recs = [json.loads(l) for l in open(os.path.join(d, "calls.jsonl"), encoding="utf-8")]
        tok = {k: sum(r["cost_usd"]["tokens"][k] for r in recs) for k in ("input_uncached", "input_cached", "output_incl_thinking")}
        aborted = os.path.exists(os.path.join(d, "ABORTED.json"))
        rows.append({"run_id": rid, "condition": meta["condition"], "state": "aborted" if aborted else "complete",
                     "calls": len(recs), "attempts": sum(r.get("attempts", 1) for r in recs), **tok,
                     "cost_usd": round(sum(r["cost_usd"]["total"] for r in recs), 4)})
        if aborted:
            ab = json.load(open(os.path.join(d, "ABORTED.json"), encoding="utf-8"))
            for a in ab.get("amendments", []):
                if "unlogged_billable_estimate" in a:
                    est.append({"run_id": rid, **a["unlogged_billable_estimate"]})
    total = round(sum(r["cost_usd"] for r in rows), 4)
    analysis = round(sum(r["cost_usd"] for r in rows if r["condition"] != "pilot" and r["state"] == "complete"), 4)
    L = ["# 지출 합계 (Gemini 생성 호출 기준)", "",
         "단가: 입력 $0.30/1M, 캐시 입력 $0.03/1M, 출력+사고 $2.50/1M. 질의 임베딩과 File API 업로드는 비용 기록 대상이 아니다.", "",
         "| run | 조건 | 상태 | 기록 호출 | 시도 수 | 입력 토큰 | 캐시 입력 | 출력+사고 토큰 | 비용 |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        L.append(f"| {r['run_id']} | {r['condition']} | {r['state']} | {r['calls']} | {r['attempts']} | {r['input_uncached']:,} | "
                 f"{r['input_cached']:,} | {r['output_incl_thinking']:,} | ${r['cost_usd']:.2f} |")
    L.append(f"| **기록된 합계** | | | {sum(r['calls'] for r in rows)} | {sum(r['attempts'] for r in rows)} | | | | **${total:.2f}** |")
    L += ["", f"- 분석 대상 완료 run(파일럿·aborted 제외) 소계: ${analysis:.2f}"]
    for e in est:
        c = e["cost_usd"]; n = e["generation_calls_possible"]
        L += [f"- **{e['run_id']} 미기록 과금 가능 호출 추정**: 생성 호출 {n['low']}~{n['high']}건(가능성 높은 값 {n['likely']}건), "
              f"${c['likely']:.4f} (가능성 높은 값) ~ ${c['high_mean_based']:.4f} (3건 × R3 평균) ~ ${c['high_max_based']:.4f} (3건 × R3 최대). 기록된 합계에 포함하지 않았다.",
              f"  - 근거: {e['basis']}"]
        L += [f"  - {k}: {v}" for k, v in e["pages"].items()]
        hi = round(total + c["high_max_based"], 4)
        L += [f"- 추정 포함 총액 범위: ${total:.2f} ~ ${hi:.2f}"]
    out = "results/revision/tables"
    open(os.path.join(out, "spend_summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump({"rows": rows, "recorded_total_usd": total, "analysis_complete_subtotal_usd": analysis, "unlogged_estimates": est},
              open(os.path.join(out, "spend_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
