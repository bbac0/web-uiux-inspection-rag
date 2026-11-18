"""
의미 채점 잘림 건 재채점기 — Message Batches 경로 (2026-11-13; results/revision/analysis_plan_addendum_semantic_retry.md).

원 채점(max_tokens 100)에서 stop_reason=max_tokens 로 잘린 이슈만, 원 설정과 max_tokens 만 다른 설정
(scoring/grader_config_retry800.json)으로 **1회** 다시 채점한다. 결과는 새 폴더 `{원 out_id}-retry` 에 쓰고 원 폴더는 읽기만 한다.

요청 본문은 동결된 표준 경로(`semantic_grader_anthropic.build_input` / `build_request`)로 만들고, 응답 해석은 배치 경로
(`semantic_grader_batch.record_from_message`)를 그대로 쓴다.

검사 (하나라도 어긋나면 제출하지 않고 폴더도 만들지 않는다)
  - 대상(--targets CSV 에서 out_id == --orig-out-id)이 원 grades.jsonl 에서 모두 truncated=true 인지
  - 새 설정이 원 설정과 max_tokens, _notes 외에는 같은지 (입력 필드는 원 채점의 것을 그대로 쓴다)
  - 각 대상의 입력 sha256 과 프롬프트 sha256 이 원 폴더 custom_ids.jsonl 의 값과 같은지

명령
  submit  --orig-out-id X --targets CSV [--config scoring/grader_config_retry800.json] [--resume] [--mock]
  status  --out-id X-retry [--mock]
  collect --out-id X-retry [--mock]    대상이 모두 최종 상태(ok, parse_error, refusal)이면 잠근다.
          다시 잘리거나 파싱에 실패한 건은 그대로 최종(미해결)이다. errored/expired/canceled(api_error) 만
          submit --resume 으로 다시 낼 수 있다(채점 결과가 아니므로 '1회' 에 세지 않음).

키는 환경변수(api_key_env)에서만 읽고 출력·기록하지 않는다. 배치 생성이 402·429·크레딧 부족으로 거부되면 종료 코드 2.
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import semantic_grader_anthropic as g     # noqa: E402
from scoring import semantic_grader_batch as gb        # noqa: E402
from experiments import semantic_issue_classifier as sic   # noqa: E402
from services import llm_wrapper as lw                 # noqa: E402

RETRY_CONFIG = os.path.join(ROOT, "scoring", "grader_config_retry800.json")
TARGETS = os.path.join(ROOT, "results", "revision", "semantic_truncation_targets.csv")
SUFFIX = "-retry"
IGNORED_KEYS = ("max_tokens", "_notes")


def load_targets(path, orig_out_id):
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r["out_id"] == orig_out_id]
    ids = [r["issue_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("targets: duplicate issue_id")
    return ids


def check_targets_truncated(orig_dir, ids):
    last = {}
    for r in gb.read_jsonl(os.path.join(orig_dir, "grades.jsonl")):
        last[r["issue_id"]] = r
    bad = [i for i in ids if i not in last or not last[i].get("truncated")]
    if bad:
        raise SystemExit(f"targets not truncated in original grades (refusing): {bad[:5]}")
    return last


def check_config(orig_cfg, new_cfg):
    keys = (set(orig_cfg) | set(new_cfg)) - set(IGNORED_KEYS)
    diff = {k: (orig_cfg.get(k), new_cfg.get(k)) for k in sorted(keys) if orig_cfg.get(k) != new_cfg.get(k)}
    if diff:
        raise SystemExit(f"retry config differs from original beyond max_tokens: {diff}")


def build_requests(run_id, runs_base, ids, cfg, orig_map, pass_no):
    want = set(ids)
    reqs, cmap, mism = [], {}, []
    for issue_id, src, issue in g.iter_run_issues(run_id, runs_base):
        if issue_id not in want:
            continue
        text = g.build_input(issue, cfg)
        params = g.build_request(text, cfg)
        cid = gb.custom_id(issue_id, pass_no)
        ish, psh = lw.sha256_text(text), lw.sha256_text(params["messages"][0]["content"])
        o = orig_map.get(issue_id)
        if o is None or o["input_sha256"] != ish or o["prompt_sha256"] != psh:
            mism.append(issue_id)
        reqs.append({"custom_id": cid, "params": params})
        cmap[cid] = {"issue_id": issue_id, "source": src, "prompt_sha256": psh, "input_sha256": ish}
    missing = want - {m["issue_id"] for m in cmap.values()}
    if missing:
        raise SystemExit(f"targets not found in run issues: {sorted(missing)[:5]}")
    if mism:
        raise SystemExit(f"input/prompt sha256 differs from the original grading (refusing): {mism[:5]}")
    return reqs, cmap


def cmd_submit(a):
    orig_dir = os.path.join(a.orig_base or a.out_base, a.orig_out_id)
    ometa = json.load(open(os.path.join(orig_dir, "run_meta.json"), encoding="utf-8"))
    cfg = g.load_config(a.config)
    cfg["input_fields"] = list(ometa["input_fields"])
    check_config(ometa["config"], cfg)
    ids = load_targets(a.targets, a.orig_out_id)
    if not ids:
        print(json.dumps({"submitted": 0, "note": "no targets for this out_id"}, ensure_ascii=False))
        return 0
    check_targets_truncated(orig_dir, ids)
    orig_map = {r["issue_id"]: r for r in gb.read_jsonl(os.path.join(orig_dir, "custom_ids.jsonl"))}
    out_id = a.orig_out_id + SUFFIX
    out = os.path.join(a.out_base, out_id)
    reqs, cmap = build_requests(ometa["source_run"], a.runs_base, ids, cfg, orig_map, ometa["pass"])
    if a.resume:
        if not os.path.isdir(out):
            raise SystemExit(f"--resume: folder not found: {out}")
        if os.path.exists(os.path.join(out, "SHA256SUMS")):
            raise SystemExit(f"--resume: already completed and locked: {out}")
        meta = json.load(open(os.path.join(out, "run_meta.json"), encoding="utf-8"))
        if meta["config_sha256"] != lw.sha256_file(a.config) or meta["targets"] != ids:
            raise SystemExit("--resume: config or targets differ from the original retry submission")
        if [b for b, s in gb.batch_state(out).items() if s["collected"] is None]:
            raise SystemExit("--resume: uncollected batches exist, run collect first")
        done, _ = g.load_done(os.path.join(out, "grades.jsonl"))
        keep = {cid for cid, m in cmap.items() if (m["issue_id"], meta["pass"]) not in done}
        reqs = [r for r in reqs if r["custom_id"] in keep]
        cmap = {k: v for k, v in cmap.items() if k in keep}
        if not reqs:
            print(json.dumps({"submitted": 0, "note": "nothing to resubmit"}, ensure_ascii=False))
            return 0
    else:
        out = lw.create_run_dir(a.out_base, out_id)
        meta = {"source_run": ometa["source_run"], "pass": ometa["pass"], "input_fields": cfg["input_fields"],
                "mock": a.mock, "mode": "batch", "out_id": out_id, "retry_of": a.orig_out_id,
                "config_sha256": lw.sha256_file(a.config), "orig_config_sha256": ometa.get("config_sha256"),
                "judge_prompt_sha256": lw.sha256_text(sic.JUDGE_PROMPT), "targets": ids,
                "targets_file": os.path.relpath(a.targets, ROOT).replace(os.sep, "/"),
                "targets_sha256": lw.sha256_file(a.targets), "config": cfg, "started_utc": lw.utc_now()}
        json.dump(meta, open(os.path.join(out, "run_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    client = gb.make_client(cfg, a.mock)
    try:
        b = client.messages.batches.create(requests=reqs)
    except Exception as e:
        stop = bool(g.BILLING_RE.search(str(e)))
        gb.append_jsonl(os.path.join(out, "batches.jsonl"), {"event": "submit_failed", "ts_utc": lw.utc_now(),
                                                             "n_requests": len(reqs), "billing_stop": stop,
                                                             "error": f"{type(e).__name__}: {str(e)[:300]}"})
        print(f"!!! batch create failed ({'billing/rate-limit stop' if stop else 'error'}): {type(e).__name__}: {str(e)[:200]}")
        return 2
    for cid, v in cmap.items():
        gb.append_jsonl(os.path.join(out, "custom_ids.jsonl"), {"batch_id": b.id, "custom_id": cid, **v})
    rec = {"event": "submitted", "batch_id": b.id, "ts_utc": lw.utc_now(), "n_requests": len(reqs), "pass": meta["pass"],
           "issue_ids": [cmap[r["custom_id"]]["issue_id"] for r in reqs],
           "custom_ids_sha256": lw.sha256_text("\n".join(r["custom_id"] for r in reqs)),
           "config_sha256": meta["config_sha256"], "processing_status": getattr(b, "processing_status", None),
           "resume": bool(a.resume)}
    gb.append_jsonl(os.path.join(out, "batches.jsonl"), rec)
    meta.setdefault("sessions", []).append({"ts_utc": rec["ts_utc"], "action": "submit", "batch_id": b.id, "n": len(reqs),
                                            "resume": bool(a.resume)})
    json.dump(meta, open(os.path.join(out, "run_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({"submitted": len(reqs), "batch_id": b.id, "out": out}, ensure_ascii=False))
    return 0


def cmd_status(a):
    return gb.cmd_status(a)


def cmd_collect(a):
    out = os.path.join(a.out_base, a.out_id)
    meta = json.load(open(os.path.join(out, "run_meta.json"), encoding="utf-8"))
    if not meta.get("retry_of"):
        raise SystemExit("this folder was not created by the retry grader")
    cfg = meta["config"]
    client = gb.make_client(cfg, meta.get("mock", False) or a.mock)
    cmap = {r["custom_id"]: r for r in gb.read_jsonl(os.path.join(out, "custom_ids.jsonl"))}
    path = os.path.join(out, "grades.jsonl")
    still, stats = [], {}
    for bid, s in gb.batch_state(out).items():
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
                   "input_fields": cfg["input_fields"], "max_tokens": cfg["max_tokens"], "status": "api_error",
                   "model_version": None, "input_tokens": None, "output_tokens": None, "stop_reason": None, "truncated": None,
                   "fallback_used": None, "raw_response": None, "label": None, "parse_ok": None, "sent_via_extra_body": [],
                   "attempts": 1, "errors": [], "prompt_sha256": m["prompt_sha256"], "input_sha256": m["input_sha256"],
                   "retry_of": meta["retry_of"], "orig_status": "parse_error", "orig_truncated": True}
            rt = res.result.type
            rec["result_type"] = rt
            if rt == "succeeded":
                gb.record_from_message(rec, res.result.message)
            else:
                err = getattr(res.result, "error", None)
                inner = getattr(err, "error", None)
                etype = getattr(inner, "type", None) or getattr(err, "type", None)
                rec["errors"] = [{"type": rt, "error_type": etype, "message": str(getattr(inner, "message", "") or "")[:300]}]
            gb.append_jsonl(path, rec)
            stats[rec["status"]] = stats.get(rec["status"], 0) + 1
            n += 1
        gb.append_jsonl(os.path.join(out, "batches.jsonl"), {"event": "collected", "batch_id": bid, "ts_utc": lw.utc_now(),
                                                             "n_results": n, "status_counts": stats})
    done, total = g.load_done(path)
    complete = not still and all((i, meta["pass"]) in done for i in meta["targets"])
    meta.update(total_records=total, final_issues=len(done), targets_n=len(meta["targets"]), complete=complete,
                finished_utc=lw.utc_now())
    meta.setdefault("sessions", []).append({"ts_utc": lw.utc_now(), "action": "collect", "status_counts": stats,
                                            "still_processing": still})
    json.dump(meta, open(os.path.join(out, "run_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(meta, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if complete:
        lw.lock_run(out)
    print(json.dumps({"collected_status_counts": stats, "still_processing": still, "final_issues": len(done),
                      "targets": len(meta["targets"]), "complete": complete}, ensure_ascii=False))
    errored = stats.get("api_error", 0)
    if stats and errored / max(1, sum(stats.values())) > 0.20:
        print("!!! errored/expired/canceled > 20% of collected results: report before resubmitting")
    return 3 if still else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("submit", "status", "collect"):
        p = sp.add_parser(name)
        p.add_argument("--mock", action="store_true")
        p.add_argument("--out-base", default=g.OUT_BASE)
        if name == "submit":
            p.add_argument("--orig-out-id", required=True)
            p.add_argument("--targets", default=TARGETS)
            p.add_argument("--config", default=RETRY_CONFIG)
            p.add_argument("--orig-base", default=None)
            p.add_argument("--runs-base", default=g.RUNS_BASE)
            p.add_argument("--resume", action="store_true")
        else:
            p.add_argument("--out-id", required=True)
    a = ap.parse_args(argv)
    return {"submit": cmd_submit, "status": cmd_status, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
