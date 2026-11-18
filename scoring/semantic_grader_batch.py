"""
의미 채점기 — Message Batches 경로 (2026-11-13 작성; 경로 규칙은 pending_freeze_v5 12항 / analysis_plan 10절 12항).

표준 경로(`scoring/semantic_grader_anthropic.py`, 동결)의 입력 구성·누출 검사·요청 인자·프롬프트·설정을 **그대로 import 해서** 쓴다.
요청 본문은 표준 경로의 `build_request` 결과와 같고(같은 model, max_tokens, messages, thinking, output_config), 배치로 보낼 뿐이다.
응답 해석(텍스트 블록만, stop_reason 처리, parse_label)은 표준 경로 `grade_issue` 의 응답 처리와 같은 규칙을 이 파일에 옮겨 적었다
(동결 파일을 고치지 않기 위해; tests/test_semantic_grader_batch.py 가 두 경로의 라벨·상태가 같은지 확인한다).

한 채점 폴더(out_id)에는 한 경로만 쓴다. 표준 경로로 시작한 폴더를 배치로 잇지 않는다(반대도 같음).

명령
  submit   : 아직 최종 상태가 아니고, 회수하지 않은 배치에도 들어 있지 않은 이슈를 모아 배치 1개를 제출한다.
             제출 직후 batch_id 를 batches.jsonl 에 기록한다(프로세스가 죽어도 collect 로 회수 가능).
             처음이면 폴더를 만들고, --resume 이면 기존 폴더에 잇는다(설정이 다르면 거부, 회수하지 않은 배치가 있으면 거부).
  status   : 제출한 배치들의 처리 상태를 보여 준다(API 조회만).
  collect  : 끝난(ended) 배치의 결과를 받아 grades.jsonl 에 표준 경로와 같은 형식으로 붙인다(mode="batch").
             모든 이슈가 최종 상태(ok/parse_error/refusal)이면 폴더를 잠근다. 아직 처리 중인 배치가 있으면 종료 코드 3.
             errored/expired/canceled 는 status=api_error 로 남기고, 다음 submit --resume 이 그 이슈만 새 배치로 다시 낸다.

  python scoring/semantic_grader_batch.py submit  --run-id E1-R1 --out-id E1-R1-sem-p1 --pass 1 [--input-fields description] [--limit N] [--resume] [--mock]
  python scoring/semantic_grader_batch.py status  --out-id E1-R1-sem-p1 [--mock]
  python scoring/semantic_grader_batch.py collect --out-id E1-R1-sem-p1 [--mock]

키는 환경변수(api_key_env, 기본 ANTHROPIC_API_KEY)에서만 읽고 출력·기록하지 않는다.
배치 생성이 크레딧 부족·402·429 로 거부되면 재시도 없이 즉시 멈춘다(종료 코드 2).
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import semantic_grader_anthropic as g    # noqa: E402  (동결된 표준 경로: 입력·요청·설정·누출 검사)
from experiments import semantic_issue_classifier as sic   # noqa: E402
from services import llm_wrapper as lw                # noqa: E402

CUSTOM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def custom_id(issue_id, pass_no):
    """'E1-R1:page_001:00' → 'E1-R1__page_001__00__p1' (배치 custom_id 형식: 영문·숫자·_·-, 64자 이하)."""
    cid = issue_id.replace(":", "__") + f"__p{pass_no}"
    if not CUSTOM_ID_RE.match(cid):
        raise ValueError(f"custom_id format: {cid}")
    return cid


def make_client(cfg, mock=False):
    if mock:
        from scoring.mock_anthropic_batch import FakeBatchAnthropic
        return FakeBatchAnthropic._shared()
    return g.make_client(cfg, mock=False)


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def append_jsonl(path, rec):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush(); os.fsync(f.fileno())


def batch_state(out):
    """batches.jsonl → {batch_id: {"submitted": rec, "collected": rec|None}}"""
    st = {}
    for r in read_jsonl(os.path.join(out, "batches.jsonl")):
        if r["event"] == "submitted":
            st[r["batch_id"]] = {"submitted": r, "collected": None}
        elif r["event"] == "collected":
            st[r["batch_id"]]["collected"] = r
    return st


def record_from_message(rec, msg):
    """표준 경로 grade_issue 의 응답 처리와 같은 규칙."""
    usage = getattr(msg, "usage", None)
    rec["input_tokens"] = getattr(usage, "input_tokens", None)
    rec["output_tokens"] = getattr(usage, "output_tokens", None)
    rec["model_version"] = getattr(msg, "model", None)
    rec["stop_reason"] = getattr(msg, "stop_reason", None)
    rec["fallback_used"] = any(getattr(b, "type", None) == "fallback" for b in getattr(msg, "content", []) or [])
    raw = g.response_text(msg)
    rec["raw_response"] = raw
    rec["truncated"] = rec["stop_reason"] == "max_tokens"
    if rec["stop_reason"] == "refusal":
        rec["label"], rec["parse_ok"], rec["status"] = "refusal", False, "refusal"
        return rec
    label, ok = sic.parse_label(raw)
    if rec["truncated"]:
        rec["label"], rec["parse_ok"], rec["status"] = None, False, "parse_error"
        rec["label_if_parsed"] = label if ok else None
        return rec
    rec["label"], rec["parse_ok"] = (label, True) if ok else (None, False)
    rec["status"] = "ok" if ok else "parse_error"
    return rec


def fingerprint(a, cfg, config_path):
    return {"source_run": a.run_id, "pass": a.pass_no, "input_fields": cfg["input_fields"], "mock": a.mock,
            "config_sha256": lw.sha256_file(config_path), "judge_prompt_sha256": lw.sha256_text(sic.JUDGE_PROMPT),
            "mode": "batch"}


def cmd_submit(a):
    cfg = g.load_config(a.config)
    if a.input_fields:
        cfg["input_fields"] = a.input_fields.split(",")
    fp = fingerprint(a, cfg, a.config)
    out = os.path.join(a.out_base, a.out_id)
    meta_path = os.path.join(out, "run_meta.json")
    if a.resume:
        if not os.path.isdir(out):
            raise SystemExit(f"--resume: folder not found: {out}")
        if os.path.exists(os.path.join(out, "SHA256SUMS")):
            raise SystemExit(f"--resume: already completed and locked: {out}")
        meta = json.load(open(meta_path, encoding="utf-8"))
        diff = {k: (meta.get(k), v) for k, v in fp.items() if meta.get(k) != v}
        if diff:
            raise SystemExit(f"--resume: settings differ from the original run (or mode differs): {diff}")
        pending = [b for b, s in batch_state(out).items() if s["collected"] is None]
        if pending:
            raise SystemExit(f"--resume: uncollected batches exist, run collect first: {pending}")
    else:
        out = lw.create_run_dir(a.out_base, a.out_id)
        meta = dict(fp, out_id=a.out_id, config=cfg, started_utc=lw.utc_now())
        json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    done, _ = g.load_done(os.path.join(out, "grades.jsonl"))
    in_flight = set()
    for s in batch_state(out).values():
        if s["collected"] is None:
            in_flight.update(s["submitted"]["issue_ids"])
    issues = list(g.iter_run_issues(a.run_id, a.runs_base))
    reqs, ids, cmap = [], [], {}
    for issue_id, src, issue in issues:
        if (issue_id, a.pass_no) in done or issue_id in in_flight:
            continue
        if a.limit and len(reqs) >= a.limit:
            break
        text = g.build_input(issue, cfg)           # 누출 검사 포함
        params = g.build_request(text, cfg)        # 표준 경로와 같은 요청 본문
        cid = custom_id(issue_id, a.pass_no)
        reqs.append({"custom_id": cid, "params": params})
        ids.append(issue_id)
        cmap[cid] = {"issue_id": issue_id, "source": src, "prompt_sha256": lw.sha256_text(params["messages"][0]["content"]),
                     "input_sha256": lw.sha256_text(text)}
    if not reqs:
        print(json.dumps({"submitted": 0, "note": "nothing to submit"}, ensure_ascii=False))
        return 0
    client = make_client(cfg, a.mock)
    try:
        b = client.messages.batches.create(requests=reqs)
    except Exception as e:
        stop = bool(g.BILLING_RE.search(str(e)))
        append_jsonl(os.path.join(out, "batches.jsonl"), {"event": "submit_failed", "ts_utc": lw.utc_now(),
                                                          "n_requests": len(reqs), "billing_stop": stop,
                                                          "error": f"{type(e).__name__}: {str(e)[:300]}"})
        print(f"!!! batch create failed ({'billing/rate-limit stop' if stop else 'error'}): {type(e).__name__}: {str(e)[:200]}")
        return 2
    for cid, v in cmap.items():
        append_jsonl(os.path.join(out, "custom_ids.jsonl"), {"batch_id": b.id, "custom_id": cid, **v})
    rec = {"event": "submitted", "batch_id": b.id, "ts_utc": lw.utc_now(), "n_requests": len(reqs), "pass": a.pass_no,
           "issue_ids": ids, "custom_ids_sha256": lw.sha256_text("\n".join(r["custom_id"] for r in reqs)),
           "config_sha256": fp["config_sha256"], "processing_status": getattr(b, "processing_status", None),
           "resume": bool(a.resume)}
    append_jsonl(os.path.join(out, "batches.jsonl"), rec)
    meta.setdefault("sessions", []).append({"ts_utc": rec["ts_utc"], "action": "submit", "batch_id": b.id, "n": len(reqs),
                                            "resume": bool(a.resume)})
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({"submitted": len(reqs), "batch_id": b.id, "out": out}, ensure_ascii=False))
    return 0


def _load_out(a):
    out = os.path.join(a.out_base, a.out_id)
    meta = json.load(open(os.path.join(out, "run_meta.json"), encoding="utf-8"))
    if meta.get("mode") != "batch":
        raise SystemExit("this folder was not created by the batch path")
    return out, meta


def cmd_status(a):
    out, meta = _load_out(a)
    client = make_client(meta["config"], meta.get("mock", False) or a.mock)
    for bid, s in batch_state(out).items():
        b = client.messages.batches.retrieve(bid)
        rc = getattr(b, "request_counts", None)
        print(json.dumps({"batch_id": bid, "processing_status": b.processing_status, "collected": s["collected"] is not None,
                          "request_counts": {k: getattr(rc, k, None) for k in ("processing", "succeeded", "errored", "canceled", "expired")}},
                         ensure_ascii=False))
    return 0


def cmd_collect(a):
    out, meta = _load_out(a)
    cfg = meta["config"]
    client = make_client(cfg, meta.get("mock", False) or a.mock)
    cmap = {r["custom_id"]: r for r in read_jsonl(os.path.join(out, "custom_ids.jsonl"))}
    path = os.path.join(out, "grades.jsonl")
    still, stats = [], {}
    for bid, s in batch_state(out).items():
        if s["collected"] is not None:
            continue
        b = client.messages.batches.retrieve(bid)
        if b.processing_status != "ended":
            still.append({"batch_id": bid, "processing_status": b.processing_status})
            continue
        n = 0
        for res in client.messages.batches.results(bid):
            m = cmap[res.custom_id]
            rec = {"issue_id": m["issue_id"], "pass": s["submitted"]["pass"], "source": m["source"],
                   "mode": "batch", "pricing": "batch", "batch_id": bid, "custom_id": res.custom_id,
                   "batch_submitted_utc": s["submitted"]["ts_utc"], "batch_ended_utc": str(getattr(b, "ended_at", "") or ""),
                   "ts_start_utc": None, "ts_end_utc": None, "latency_sec": None,
                   "provider": cfg["provider"], "model_requested": cfg["model"], "judge_prompt_version": cfg.get("judge_prompt_version"),
                   "input_fields": cfg["input_fields"], "status": "api_error", "model_version": None, "input_tokens": None,
                   "output_tokens": None, "stop_reason": None, "truncated": None, "fallback_used": None, "raw_response": None,
                   "label": None, "parse_ok": None, "sent_via_extra_body": [], "attempts": 1, "errors": [],
                   "prompt_sha256": m["prompt_sha256"], "input_sha256": m["input_sha256"]}
            rt = res.result.type
            rec["result_type"] = rt
            if rt == "succeeded":
                record_from_message(rec, res.result.message)
            else:
                err = getattr(res.result, "error", None)
                inner = getattr(err, "error", None)
                etype = getattr(inner, "type", None) or getattr(err, "type", None)
                rec["errors"] = [{"type": rt, "error_type": etype, "message": str(getattr(inner, "message", "") or "")[:300]}]
            append_jsonl(path, rec)
            stats[rec["status"]] = stats.get(rec["status"], 0) + 1
            n += 1
        append_jsonl(os.path.join(out, "batches.jsonl"), {"event": "collected", "batch_id": bid, "ts_utc": lw.utc_now(),
                                                          "n_results": n, "status_counts": stats})
    issues = list(g.iter_run_issues(meta["source_run"], a.runs_base))
    done, total = g.load_done(path)
    complete = not still and all((i, meta["pass"]) in done for i, _, _ in issues)
    meta.update(total_records=total, final_issues=len(done), issues_in_run=len(issues), complete=complete,
                finished_utc=lw.utc_now())
    meta.setdefault("sessions", []).append({"ts_utc": lw.utc_now(), "action": "collect", "status_counts": stats,
                                            "still_processing": still})
    json.dump(meta, open(os.path.join(out, "run_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(meta, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if complete:
        lw.lock_run(out)
    print(json.dumps({"collected_status_counts": stats, "still_processing": still, "final_issues": len(done),
                      "issues_in_run": len(issues), "complete": complete}, ensure_ascii=False))
    errored = stats.get("api_error", 0)
    if stats and errored / max(1, sum(stats.values())) > 0.20:
        print("!!! errored/expired/canceled > 20% of collected results: report before resubmitting")
    return 3 if still else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("submit", "status", "collect"):
        p = sub.add_parser(name)
        p.add_argument("--out-id", required=True)
        p.add_argument("--mock", action="store_true")
        p.add_argument("--out-base", default=g.OUT_BASE)
        p.add_argument("--runs-base", default=g.RUNS_BASE)
        if name == "submit":
            p.add_argument("--run-id", required=True)
            p.add_argument("--pass", dest="pass_no", type=int, choices=[1, 2], required=True)
            p.add_argument("--input-fields", choices=["description", "description,suggestion"], default=None)
            p.add_argument("--limit", type=int, default=0)
            p.add_argument("--resume", action="store_true")
            p.add_argument("--config", default=g.CONFIG_PATH)
    a = ap.parse_args(argv)
    return {"submit": cmd_submit, "status": cmd_status, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
