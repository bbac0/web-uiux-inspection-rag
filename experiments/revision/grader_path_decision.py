"""
의미 채점 경로(표준 vs 배치) 판정 (analysis_plan.md 10절 12항 사전 규칙, API 호출 없음).

- 호출당 평균 비용 = 시험 호출 20건(results/revision/semantic_scores/probe-E1-R1/)의 평균 입력 토큰 × $2/1M + 평균 출력 토큰 × $10/1M.
- 규칙: 전체 의미 채점 호출 수 × 호출당 평균 비용이 $10 이하이면 모든 의미 채점을 표준 경로로, 초과하면 모두 배치 경로로(섞지 않음).
  E9 3회째는 합계에 넣지 않고 판단한다.
- 호출 수: 연구자가 지정한 사전 추정 8,874 로 판정하고, 12항 문구대로 실행이 끝난 run 은 실제 대상 페이지 이슈 수로 다시 센 값도 함께 적는다.

출력: results/revision/reports/grader_path_decision.md
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import semantic_grader_anthropic as g   # noqa: E402  (iter_run_issues: 대상 페이지 이슈)
from services import llm_wrapper as lw               # noqa: E402

PROBE = "results/revision/semantic_scores/probe-E1-R1"
OUT = "results/revision/reports/grader_path_decision.md"
PRICE_IN, PRICE_OUT, THRESH = 2.0, 10.0, 10.0


def n_issues(rid):
    return sum(1 for _ in g.iter_run_issues(rid))


def main():
    s = json.load(open(f"{PROBE}/summary.json", encoding="utf-8"))
    recs = [json.loads(l) for l in open(f"{PROBE}/probe.jsonl", encoding="utf-8")]
    bad = lw.verify_run(PROBE)
    mi, mo = s["input_tokens"]["mean"], s["output_tokens"]["mean"]
    per = mi * PRICE_IN / 1e6 + mo * PRICE_OUT / 1e6
    cnt = {r: n_issues(r) for r in ["E1-R1", "E1-R2", "E1-R3b", "E2-A1-1", "E2-A1-2", "E2-A1-3", "E3-page", "E3-oracle", "E4-mobile"]}
    e1a1 = [("E1-R1, R2, R3b pass1", cnt["E1-R1"] + cnt["E1-R2"] + cnt["E1-R3b"], 1920),
            ("E2-A1-1, A1-2, A1-3 pass1", cnt["E2-A1-1"] + cnt["E2-A1-2"] + cnt["E2-A1-3"], 1920),
            ("E1-R1 pass2", cnt["E1-R1"], 640), ("E1-R1 description-only 민감도", cnt["E1-R1"], 640)]
    e34 = [("E3-page, E3-oracle pass1", cnt["E3-page"] + cnt["E3-oracle"], 538), ("E4-mobile pass1", cnt["E4-mobile"], 304)]
    e9 = [("E9 본 실험 2회 pass1 (91 × 5조건 × 2, 페이지당 3.2건 추정)", 2912, 2912)]
    e9c = [("E9 3회째 (조건부, 판정에서 제외)", 1456, 1456)]
    pre_total = sum(x[2] for x in e1a1 + e34 + e9)
    act_total = sum(x[1] for x in e1a1 + e34 + e9)
    L = ["# 의미 채점 경로 판정 (2026-11-13)", "",
         "- 근거: analysis_plan.md 10절 12항(사전 규칙), 13항(채점 범위). API 호출 없음(시험 호출 결과 파일만 읽음).",
         "- **시험 호출 20건은 라벨과 원본 응답을 저장하지 않았으므로 채점 결과가 아니다.**",
         "  토큰·stop_reason·모델 버전만 기록했고, 본 채점은 처음부터 따로 실행한다.", "",
         "## 1. 시험 호출 확인 (`" + PROBE + "/`)", "",
         "| 항목 | 연구자 출력 | 로그에서 다시 계산 | 일치 |", "|---|---|---|---|"]
    it = [r["input_tokens"] for r in recs]
    ot = [r["output_tokens"] for r in recs]
    chk = [("호출 수", "20", str(len(recs)), len(recs) == 20),
           ("입력 토큰 평균 (범위)", "892.1 (780~996)", f"{sum(it) / len(it):.1f} ({min(it)}~{max(it)})",
            round(sum(it) / len(it), 1) == 892.1 and min(it) == 780 and max(it) == 996),
           ("출력 토큰 평균 (범위)", "12.7 (10~20)", f"{sum(ot) / len(ot):.1f} ({min(ot)}~{max(ot)})",
            round(sum(ot) / len(ot), 1) == 12.7 and min(ot) == 10 and max(ot) == 20),
           ("stop_reason", "end_turn 20", ", ".join(f"{k} {v}" for k, v in s["stop_reasons"].items()), s["stop_reasons"] == {"end_turn": 20}),
           ("잘림(max_tokens)", "0", str(sum(bool(r.get("truncated")) for r in recs)), not any(r.get("truncated") for r in recs)),
           ("모델 버전", "claude-sonnet-5-5", ", ".join(s["model_versions"]), s["model_versions"] == ["claude-sonnet-5-5"])]
    L += [f"| {a} | {b} | {c} | {'예' if d else '아니오'} |" for a, b, c, d in chk]
    L += ["", f"- 설정 해시(config_sha256) `{s['config_sha256'][:16]}` = 동결된 `scoring/grader_config.json` 해시와 같음: "
          f"{'예' if s['config_sha256'] == lw.sha256_file('scoring/grader_config.json') else '아니오'}",
          f"- 폴더 무결성(SHA256SUMS): {'통과' if not bad else bad}. 라벨·원본 응답 필드 없음(블라인드): "
          f"{'예' if not any(k in recs[0] for k in ('label', 'raw_response', 'label_if_parsed', 'parse_ok')) else '아니오'}",
          f"- 입력 필드 {recs[0]['input_fields']}, 오류 기록 {sum(len(r.get('errors') or []) for r in recs)}건, "
          f"extra_body 전환 {s['sent_via_extra_body'] or '없음'}.", "",
          "출처: `" + PROBE + "/summary.json`, `probe.jsonl`, `SHA256SUMS`", "",
          "## 2. 호출당 비용 (표준가 입력 $2/1M, 출력 $10/1M)", "",
          f"- 호출당 표준가 = {mi} × $2/1M + {mo} × $10/1M = **${per:.6f}** (배치는 50%: ${per / 2:.6f})", "",
          "## 3. 범위별 호출 수와 비용", "",
          "사전 추정 = analysis_plan 10절 13항 표(페이지당 3.2건 가정). 실제 = 끝난 run 의 대상 페이지 이슈 수(E9 는 아직 없음).", "",
          "| 범위 | 항목 | 사전 추정 호출 | 실제 호출 | 표준가 (실제) | 배치 (실제) |", "|---|---|---|---|---|---|"]
    for grp, items in (("E1·A1", e1a1), ("E3·E4", e34), ("E9", e9), ("E9 3회째", e9c)):
        for name, act, pre in items:
            L.append(f"| {grp} | {name} | {pre:,} | {act:,} | ${act * per:.2f} | ${act * per / 2:.2f} |")
    L += [f"| **합계 (3회째 제외)** | | **{pre_total:,}** | **{act_total:,}** | **${act_total * per:.2f}** | **${act_total * per / 2:.2f}** |", "",
          "출처: 실제 호출 수는 `results/revision/runs/{run}/reports.jsonl` 의 대상 페이지 이슈 수", "",
          "## 4. 경로 규칙 적용", "",
          f"- 연구자 지정 호출 수 8,874 × ${per:.6f} = **${8874 * per:.2f}** → $10 {'초과' if 8874 * per > THRESH else '이하'}",
          f"- 실제 이슈 수로 다시 센 {act_total:,} × ${per:.6f} = ${act_total * per:.2f} → $10 {'초과' if act_total * per > THRESH else '이하'}",
          f"- **판정: {'모든 의미 채점(pass1, pass2, 민감도 포함)을 배치 경로(Message Batches)로 한다.' if 8874 * per > THRESH else '모든 의미 채점을 표준 경로로 한다.'}**",
          "  두 계산 모두 같은 결론이다." if (8874 * per > THRESH) == (act_total * per > THRESH) else "  두 계산의 결론이 다르다(연구자 확인 필요).",
          "- 사전 규칙에 따라 배치 경로를 쓰기 전에 1건짜리 확인 배치를 보내 thinking between_tools, effort high 수락 여부와 응답 형태를 확인한다.",
          "  거부되면 표준 경로로 확정한다(연구자 승인 후 실행).", ""]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    L = [x for l in L for x in l.split("\n")]
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(OUT, f"per={per:.6f}", f"8874→{8874 * per:.2f}", f"actual {act_total}→{act_total * per:.2f}", cnt)


if __name__ == "__main__":
    sys.exit(main())
