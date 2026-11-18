"""
채점 전 시험 호출: run 의 대상 페이지 이슈 중 무작위 N건(기본 20)을 실제 채점 설정으로 호출해 호출당 입력/출력 토큰을 잰다.
**라벨은 보지 않는다:** 로그에 원본 응답과 라벨을 남기지 않고 토큰, stop_reason, 상태, 모델 버전, 지연시간만 남긴다.
이 결과는 채점 결과로 쓰지 않는다(본 채점은 처음부터 따로 실행).

실행 조건: API 키 준비, R1~A1 종료, 사용자 승인 후.
  python scoring/probe_tokens.py --run-id E1-R1 --out-id probe-E1-R1 [--n 20] [--seed 20261115] [--mock]
출력: results/revision/semantic_scores/{out_id}/probe.jsonl, summary.json (끝나면 잠금)
"""
import argparse
import json
import os
import random
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import semantic_grader_anthropic as g   # noqa: E402
from services import llm_wrapper as lw               # noqa: E402

DEFAULT_SEED = 20261115
BLINDED_FIELDS = ("raw_response", "label", "label_if_parsed", "parse_ok")   # 시험 호출에서는 기록하지 않음


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-id", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--config", default=g.CONFIG_PATH)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out-base", default=g.OUT_BASE)
    ap.add_argument("--runs-base", default=g.RUNS_BASE)
    a = ap.parse_args(argv)
    cfg = g.load_config(a.config)
    issues = list(g.iter_run_issues(a.run_id, a.runs_base))
    sample = random.Random(a.seed).sample(issues, min(a.n, len(issues)))
    client = g.make_client(cfg, mock=a.mock)
    out = lw.create_run_dir(a.out_base, a.out_id)
    recs, stop = [], None
    try:
        for issue_id, src, issue in sample:
            rec = g.grade_issue(client, issue, cfg, issue_id, src, pass_no=0)
            for k in BLINDED_FIELDS:
                rec.pop(k, None)
            rec["status_class"] = "answered" if rec["status"] in ("ok", "parse_error", "refusal") else rec["status"]
            rec.pop("status", None)                 # ok/parse_error 구분도 라벨 정보라 남기지 않는다
            with open(os.path.join(out, "probe.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            recs.append(rec)
            if rec["status_class"] == "billing_stop":
                stop = f"billing/rate-limit error at {issue_id}"
                break
    finally:
        it = [r["input_tokens"] for r in recs if r.get("input_tokens") is not None]
        ot = [r["output_tokens"] for r in recs if r.get("output_tokens") is not None]
        stat = lambda xs: ({"n": len(xs), "mean": round(statistics.mean(xs), 1), "min": min(xs), "max": max(xs)}
                           if xs else {"n": 0})
        s = {"out_id": a.out_id, "source_run": a.run_id, "seed": a.seed, "n_requested": a.n, "n_called": len(recs),
             "issues_in_run": len(issues), "mock": a.mock, "config_sha256": lw.sha256_file(a.config),
             "input_tokens": stat(it), "output_tokens": stat(ot),
             "stop_reasons": {k: sum(1 for r in recs if r.get("stop_reason") == k) for k in {r.get("stop_reason") for r in recs}},
             "truncated_max_tokens": sum(1 for r in recs if r.get("truncated")),
             "model_versions": sorted({r["model_version"] for r in recs if r.get("model_version")}),
             "sent_via_extra_body": sorted({f for r in recs for f in r.get("sent_via_extra_body", [])}),
             "stopped": stop, "finished_utc": lw.utc_now(),
             "note": "labels and raw responses are not recorded (blinded); not used as grading results"}
        with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        lw.lock_run(out)
    print(json.dumps({k: s[k] for k in ("n_called", "input_tokens", "output_tokens", "stop_reasons",
                                        "truncated_max_tokens", "model_versions", "stopped")}, ensure_ascii=False))
    return 2 if stop else 0


if __name__ == "__main__":
    sys.exit(main())
