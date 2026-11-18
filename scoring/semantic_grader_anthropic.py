"""
의미 채점기 (Anthropic). 이슈 한 건을 5개 결함 유형 또는 None 으로 분류한다.

- 범주 정의 프롬프트는 새로 쓰지 않는다: experiments/semantic_issue_classifier.py 의 JUDGE_PROMPT(v1)와
  parse_label/LABELS 를 import 해서 그대로 쓴다 (기존 파일은 수정하지 않음).
- 요청 형태는 기존 Anthropic 경로(make_judge("anthropic"))와 같다: messages=[{"role": "user", "content": JUDGE_PROMPT.replace("<<DESC>>", 입력)}].
  설정(scoring/grader_config.json)의 input_fields=["description"] 이고 나머지가 기존 값이면 기존 경로와 요청 인자가 완전히 같다
  (tests/test_semantic_grader.py 가 확인). 추가 인자(thinking, effort, fallbacks)는 설정값이 null 이면 보내지 않는다.
- 입력: 이슈의 description 과 suggestion 만. description 앞의 "[URL]" 접두어는 파이프라인(merge_results)이 붙인 것이고
  페이지 ID 가 들어 있으므로 지운다. 페이지 ID, 주입 라벨, 조건명은 모델 입력에 절대 넣지 않는다(넣으려 하면 예외).
- 이슈마다 JSONL 한 줄: issue_id, 원 run/page(로그에만), 호출 시각(UTC), 모델 버전 문자열(응답의 model),
  입력/출력 토큰, 원본 응답, 라벨, 파싱 성공 여부, stop_reason, 재시도, 오류, 프롬프트 SHA-256.
- 키는 환경변수(api_key_env)에서만 읽고 출력·기록하지 않는다.

사용법
  python scoring/semantic_grader_anthropic.py --run-id E1-R1 --out-id E1-R1-sem-p1 --pass 1 [--limit N] [--mock]
  python scoring/semantic_grader_anthropic.py --run-id E1-R1 --out-id E1-R1-sem-p2 --pass 2
  python scoring/semantic_grader_anthropic.py --run-id E1-R1 --out-id E1-R1-sem-desc-p1 --pass 1 --input-fields description   (민감도)
출력: results/revision/semantic_scores/{out_id}/grades.jsonl, summary.json (끝나면 잠금)
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from experiments import semantic_issue_classifier as sic   # noqa: E402  JUDGE_PROMPT v1, parse_label, LABELS
from services import llm_wrapper as lw                     # noqa: E402  run 폴더 생성/잠금, 재시도

CONFIG_PATH = os.path.join(ROOT, "scoring", "grader_config.json")
OUT_BASE = os.path.join(ROOT, "results", "revision", "semantic_scores")
RUNS_BASE = os.path.join(ROOT, "results", "revision", "runs")
URL_PREFIX_RE = re.compile(r"^\s*\[(?:https?|file)://[^\]]*\]\s*")
FORBIDDEN_RE = re.compile(r"page_\d{3}|testbed_200|localhost:\d+|\bE[1-4]-|\bpilot-|DEF_(VIS|OPS|TEC)_\d+", re.I)
# 크레딧 소진·요금 한도 오류: 재시도하지 않고 즉시 멈춘다 (402, 429, 400 'credit balance is too low' 등)
BILLING_RE = re.compile(r"(?<!\d)(402|429)(?!\d)|credit balance|insufficient[_ ]?(credit|funds|balance)|billing|rate_limit_error", re.I)
FINAL_STATUSES = ("ok", "parse_error", "refusal")   # --resume 에서 '이미 채점함'으로 보는 상태 (api_error 는 다시 호출)


class BillingStop(RuntimeError):
    """크레딧 소진/429/크레딧 부족 400 — 즉시 중단."""


def call_with_retry_billing_stop(fn, max_retries=3, sleep=time.sleep):
    """lw.call_with_retry 와 같은 백오프로 일시적 오류만 재시도하되, 결제·요금 한도 오류는 재시도 없이 BillingStop 으로 던진다."""
    import random
    errors, attempt = [], 0
    while True:
        attempt += 1
        try:
            return fn(), attempt, errors
        except Exception as e:
            errors.append({"attempt": attempt, "type": type(e).__name__, "message": str(e)[:500]})
            if BILLING_RE.search(str(e)):
                b = BillingStop(str(e)[:500])
                b.attempts, b.errors = attempt, errors
                raise b from e
            if not lw.is_transient(e) or attempt > max_retries:
                e.attempts, e.errors = attempt, errors
                raise
            sleep(min(30, 2 ** attempt) + random.uniform(0, 1))


class LeakError(ValueError):
    """모델 입력에 페이지 ID/조건명/주입 라벨 흔적이 들어가려 할 때."""


def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def strip_url_prefix(desc):
    return URL_PREFIX_RE.sub("", desc or "", count=1)


def build_input(issue, cfg):
    """모델에 들어갈 <<DESC>> 자리 문자열. description(접두어 제거) + 설정에 따라 suggestion."""
    desc = strip_url_prefix(issue.get("description") or "").strip()
    fields = cfg["input_fields"]
    if fields == ["description"]:
        text = desc
    elif fields == ["description", "suggestion"]:
        sug = (issue.get("suggestion") or "").strip()
        text = desc + (cfg.get("suggestion_joiner", "\n제안: ") + sug if sug else "")
    else:
        raise ValueError(f"input_fields must be ['description'] or ['description', 'suggestion'], got {fields}")
    m = FORBIDDEN_RE.search(text)
    if m:
        raise LeakError(f"forbidden token in model input: {m.group(0)!r}")
    return text


def build_request(text, cfg):
    """messages.create 인자. 기존 경로와 같은 순서·값을 쓰고, null 설정은 넣지 않는다."""
    req = {"model": cfg["model"], "max_tokens": cfg["max_tokens"]}
    if cfg.get("temperature") is not None:
        req["temperature"] = cfg["temperature"]
    req["messages"] = [{"role": "user", "content": sic.JUDGE_PROMPT.replace("<<DESC>>", text)}]
    if cfg.get("thinking") is not None:
        req["thinking"] = cfg["thinking"]
    if cfg.get("effort") is not None:
        req["output_config"] = {"effort": cfg["effort"]}
    return req


def response_text(msg):
    """thinking 블록을 건너뛰고 text 블록만 이어 붙인다."""
    out = []
    for b in getattr(msg, "content", []) or []:
        if getattr(b, "type", None) == "text":
            out.append(b.text)
    return "".join(out)


def make_client(cfg, mock=False):
    if mock:
        from scoring.mock_anthropic import FakeAnthropic
        return FakeAnthropic()
    key = os.environ.get(cfg["api_key_env"])
    if not key:
        raise SystemExit(f"환경변수 {cfg['api_key_env']} 가 필요합니다.")
    import anthropic
    return anthropic.Anthropic(api_key=key, max_retries=0)   # 재시도는 lw.call_with_retry 가 맡는다


EXTRA_BODY_FIELDS = ("thinking", "output_config")


def call_model(client, req, cfg):
    """요청을 보낸다. 설치된 SDK 가 thinking/output_config 인자를 모르면(TypeError) 그 필드만 extra_body 로 옮겨 다시 보낸다.
    반환: (응답, extra_body 로 보낸 필드 목록)"""
    if cfg.get("fallbacks") is not None:
        fb = cfg["fallbacks"]
        beta = "server-side-fallback-2026-07-01" if fb == "default" else "server-side-fallback-2026-06-01"
        create, extra = client.beta.messages.create, {"betas": [beta], "fallbacks": fb}
    else:
        create, extra = client.messages.create, {}
    try:
        return create(**req, **extra), []
    except TypeError as e:
        moved = [k for k in EXTRA_BODY_FIELDS if k in req and k in str(e)]
        if not moved:
            raise
        req2 = {k: v for k, v in req.items() if k not in EXTRA_BODY_FIELDS}
        body = {k: req[k] for k in EXTRA_BODY_FIELDS if k in req}
        return create(**req2, **extra, extra_body=body), sorted(body)


def grade_issue(client, issue, cfg, issue_id, source=None, pass_no=1):
    """이슈 한 건 채점 → 로그 레코드."""
    rec = {"issue_id": issue_id, "pass": pass_no, "source": source or {}, "ts_start_utc": lw.utc_now(),
           "provider": cfg["provider"], "model_requested": cfg["model"],
           "judge_prompt_version": cfg.get("judge_prompt_version"), "input_fields": cfg["input_fields"],
           "status": "api_error", "model_version": None, "input_tokens": None, "output_tokens": None,
           "stop_reason": None, "truncated": None, "fallback_used": None, "raw_response": None, "label": None,
           "parse_ok": None, "sent_via_extra_body": [],
           "attempts": 0, "errors": [], "prompt_sha256": None, "input_sha256": None, "latency_sec": None}
    text = build_input(issue, cfg)
    req = build_request(text, cfg)
    rec["prompt_sha256"] = lw.sha256_text(req["messages"][0]["content"])
    rec["input_sha256"] = lw.sha256_text(text)
    t0 = time.time()
    try:
        (msg, via_extra), attempts, errs = call_with_retry_billing_stop(lambda: call_model(client, req, cfg),
                                                                       max_retries=cfg.get("max_retries", 3))
        rec["attempts"], rec["errors"], rec["sent_via_extra_body"] = attempts, errs, via_extra
    except BillingStop as e:
        rec["attempts"], rec["errors"], rec["status"] = e.attempts, e.errors, "billing_stop"
        rec["latency_sec"] = round(time.time() - t0, 4)
        rec["ts_end_utc"] = lw.utc_now()
        return rec
    except Exception as e:
        rec["attempts"] = getattr(e, "attempts", 1)
        rec["errors"] = getattr(e, "errors", [{"type": type(e).__name__, "message": str(e)[:500]}])
        rec["latency_sec"] = round(time.time() - t0, 4)
        rec["ts_end_utc"] = lw.utc_now()
        return rec
    rec["latency_sec"] = round(time.time() - t0, 4)
    rec["ts_end_utc"] = lw.utc_now()
    usage = getattr(msg, "usage", None)
    rec["input_tokens"] = getattr(usage, "input_tokens", None)
    rec["output_tokens"] = getattr(usage, "output_tokens", None)
    rec["model_version"] = getattr(msg, "model", None)
    rec["stop_reason"] = getattr(msg, "stop_reason", None)
    rec["fallback_used"] = any(getattr(b, "type", None) == "fallback" for b in getattr(msg, "content", []) or [])
    raw = response_text(msg)                     # text 블록만 읽는다
    rec["raw_response"] = raw
    rec["truncated"] = rec["stop_reason"] == "max_tokens"
    if rec["stop_reason"] == "refusal":
        rec["label"], rec["parse_ok"], rec["status"] = "refusal", False, "refusal"
        return rec
    label, ok = sic.parse_label(raw)
    if rec["truncated"]:                         # max_tokens 로 끊긴 응답은 내용과 관계없이 파싱 실패로 기록
        rec["label"], rec["parse_ok"], rec["status"] = None, False, "parse_error"
        rec["label_if_parsed"] = label if ok else None
        return rec
    rec["label"], rec["parse_ok"] = (label, True) if ok else (None, False)
    rec["status"] = "ok" if ok else "parse_error"
    return rec


def iter_run_issues(run_id, runs_base=RUNS_BASE):
    """run 의 reports.jsonl 에서 대상 페이지 이슈를 순서대로 꺼낸다 → (issue_id, source, issue)."""
    with open(os.path.join(runs_base, run_id, "reports.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            rep = r.get("report") or {}
            marker = f"testbed_200/{r['page_id']}.html"
            k = 0
            for idx, issue in enumerate(rep.get("issues", []) or []):
                if not isinstance(issue, dict) or marker not in (issue.get("description") or ""):
                    continue
                yield f"{run_id}:{r['page_id']}:{idx:02d}", {"run_id": run_id, "page_id": r["page_id"], "issue_index": idx}, issue
                k += 1


def load_done(path):
    """grades.jsonl 에서 (issue_id, pass) 별 최종 상태가 기록된 것 → 집합."""
    done, n = set(), 0
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                n += 1
                if r.get("status") in FINAL_STATUSES:
                    done.add((r["issue_id"], r.get("pass")))
    return done, n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-id", required=True)
    ap.add_argument("--config", default=CONFIG_PATH)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--pass", dest="pass_no", type=int, choices=[1, 2], required=True,
                    help="1 = 주 결과, 2 = 안정성 확인용 반복 채점")
    ap.add_argument("--input-fields", choices=["description", "description,suggestion"], default=None,
                    help="설정 파일의 input_fields 를 이 run 에 한해 바꾼다 (R1 민감도 채점: description)")
    ap.add_argument("--resume", action="store_true",
                    help="중단된 채점 폴더를 이어서 채점한다. (issue_id, pass) 가 이미 최종 상태로 기록된 이슈는 건너뛴다")
    ap.add_argument("--out-base", default=OUT_BASE)
    ap.add_argument("--runs-base", default=RUNS_BASE)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    if a.input_fields:
        cfg["input_fields"] = a.input_fields.split(",")
    fingerprint = {"source_run": a.run_id, "pass": a.pass_no, "input_fields": cfg["input_fields"], "mock": a.mock,
                   "config_sha256": lw.sha256_file(a.config), "judge_prompt_sha256": lw.sha256_text(sic.JUDGE_PROMPT)}
    out = os.path.join(a.out_base, a.out_id)
    meta_path, path = os.path.join(out, "run_meta.json"), os.path.join(out, "grades.jsonl")
    if a.resume:
        if not os.path.isdir(out):
            raise SystemExit(f"--resume: folder not found: {out}")
        if os.path.exists(os.path.join(out, "SHA256SUMS")):
            raise SystemExit(f"--resume: run already completed and locked: {out}")
        old = json.load(open(meta_path, encoding="utf-8"))
        diff = {k: (old.get(k), v) for k, v in fingerprint.items() if old.get(k) != v}
        if diff:
            raise SystemExit(f"--resume: settings differ from the original run: {diff}")
        meta = old
    else:
        out = lw.create_run_dir(a.out_base, a.out_id)       # 이미 있으면 RunExistsError
        meta = dict(fingerprint, out_id=a.out_id, config=cfg, started_utc=lw.utc_now())
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    client = make_client(cfg, mock=a.mock)
    done, prior = load_done(path)
    issues = list(iter_run_issues(a.run_id, a.runs_base))
    if a.resume:
        ev = {"ts_utc": lw.utc_now(), "prior_records": prior, "already_final": len(done),
              "remaining": sum(1 for i, _, _ in issues if (i, a.pass_no) not in done)}
        with open(os.path.join(out, "resume_log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        print(f"[resume] {ev}")
    n, stats, stop = 0, {}, None
    try:
        for issue_id, src, issue in issues:
            if (issue_id, a.pass_no) in done:
                continue
            if a.limit and n >= a.limit:
                break
            rec = grade_issue(client, issue, cfg, issue_id, src, pass_no=a.pass_no)
            rec["resumed_session"] = bool(a.resume)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            stats[rec["status"]] = stats.get(rec["status"], 0) + 1
            stats["truncated_max_tokens"] = stats.get("truncated_max_tokens", 0) + bool(rec["truncated"])
            stats["refusal_label"] = stats.get("refusal_label", 0) + (rec["label"] == "refusal")
            if rec["status"] == "billing_stop" or any(BILLING_RE.search(e.get("message", "")) for e in rec["errors"]):
                last = (rec["errors"] or [{}])[-1].get("message", "")[:200]
                stop = f"billing/rate-limit error at {issue_id}: {last}"
                break
    except KeyboardInterrupt:
        stop = "KeyboardInterrupt"
    finally:
        done_after, total_records = load_done(path)
        complete = stop is None and not a.limit and all((i, a.pass_no) in done_after for i, _, _ in issues)
        session = {"ts_end_utc": lw.utc_now(), "resume": a.resume, "graded_this_session": n,
                   "status_counts_this_session": stats, "stopped": stop}
        meta.setdefault("sessions", []).append(session)
        meta.update(total_records=total_records, final_issues=len(done_after), issues_in_run=len(issues),
                    complete=complete, stopped=stop, graded=n, status_counts=stats, finished_utc=lw.utc_now())
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        if complete:
            lw.lock_run(out)            # 끝까지 채점했을 때만 잠근다. 중단되면 열어 두고 --resume 으로 잇는다
    print(json.dumps({k: meta[k] for k in ("out_id", "graded", "status_counts", "stopped", "complete")}, ensure_ascii=False))
    return 2 if stop else 0


if __name__ == "__main__":
    sys.exit(main())
