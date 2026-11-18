"""
Gemini 호출 래퍼와 실행 로그.

- 모든 Gemini 호출(파일 업로드, 생성)은 call_with_retry 를 거친다.
- 재시도: 일시적 오류(429/rate/quota/503/unavailable/overloaded/deadline)만, 최대 max_retries 회,
  지수 백오프 min(30, 2**attempt) + U(0,1) 초. 프로덕션 generate_with_retry 와 같은 정책이다.
- 실행 로그: results/revision/runs/{run_id}/calls.jsonl 에 호출(페이지 분석)당 한 줄, append 전용.
- API 키는 환경변수에서만 읽고 어디에도 기록하지 않는다.
"""

import datetime
import hashlib
import json
import os
import random
import stat
import threading
import time

SCHEMA_VERSION = 1
PRICE_INPUT_PER_TOKEN = 0.30 / 1_000_000       # cached 를 뺀 나머지 입력
PRICE_CACHED_PER_TOKEN = 0.03 / 1_000_000      # cached 입력
PRICE_OUTPUT_PER_TOKEN = 2.50 / 1_000_000     # 출력 + (derived) 사고 토큰
TRANSIENT_MARKERS = ("429", "rate", "quota", "503", "unavailable", "overloaded", "deadline")

REQUIRED_FIELDS = {
    "schema_version": int, "run_id": str, "condition": str, "page_id": (str, type(None)),
    "template_id": (str, type(None)), "url": str, "ts_start_utc": str, "ts_end_utc": str,
    "status": str, "prompt_date": (str, type(None)), "model_name": str,
    "model_version": (str, type(None)), "prompt_sha256": (str, type(None)),
    "image_sha256": (str, type(None)), "modality": str, "viewport": list, "html_chars_sent": int,
    "rag": dict, "usage": dict, "cost_usd": dict, "latency_sec": dict, "attempts": int,
    "retries": int, "errors": list, "raw_response_text": (str, type(None)),
    "parsed": (dict, type(None)), "parse_error": (str, type(None)), "result": (dict, type(None)),
}
STATUSES = ("ok", "parse_error", "api_error", "rag_empty", "rag_error", "acquisition_error")
RAG_FIELDS = ("enabled", "query_mode", "query", "chroma_path", "n_chunks", "chunks")
USAGE_FIELDS = ("prompt_token_count", "cached_content_token_count", "candidates_token_count",
                "total_token_count", "thoughts_token_count_derived")
LATENCY_FIELDS = ("acquisition", "query_embedding", "vector_search", "upload", "llm", "total")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_transient(exc):
    msg = str(exc).lower()
    return any(k in msg for k in TRANSIENT_MARKERS)


def call_with_retry(fn, max_retries=3, sleep=time.sleep):
    """fn() 을 호출한다. 반환: (결과, 시도 횟수, 오류 목록). 최종 실패 시 예외에 .attempts/.errors 를 붙여 다시 던진다."""
    errors = []
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn(), attempt, errors
        except Exception as e:
            errors.append({"attempt": attempt, "type": type(e).__name__, "message": str(e)[:500]})
            if not is_transient(e) or attempt > max_retries:
                e.attempts, e.errors = attempt, errors
                raise
            sleep(min(30, 2 ** attempt) + random.uniform(0, 1))


def usage_from_response(resp):
    """usage_metadata → 토큰 수. 사고 토큰은 SDK(0.8.6)가 주지 않으므로 total-prompt-candidates-cached 로 계산."""
    um = getattr(resp, "usage_metadata", None)
    g = lambda k: int(getattr(um, k, 0) or 0) if um is not None else None
    u = {k: g(k) for k in ("prompt_token_count", "cached_content_token_count",
                           "candidates_token_count", "total_token_count")}
    if um is None:
        u["thoughts_token_count_derived"] = None
    else:
        u["thoughts_token_count_derived"] = (u["total_token_count"] - u["prompt_token_count"]
                                             - u["candidates_token_count"] - u["cached_content_token_count"])
        # 점검용: Gemini 는 prompt_token_count 에 cached 가 포함되므로 cached>0 이면 위 값과 달라진다
        u["thoughts_check_without_cached_subtraction"] = (u["total_token_count"] - u["prompt_token_count"]
                                                          - u["candidates_token_count"])
    u["thoughts_derivation"] = "total - prompt - candidates - cached"
    return u


def cost_from_usage(u):
    """cached 입력 $0.03/1M, 나머지 입력(prompt - cached) $0.30/1M, 출력+derived 사고 $2.50/1M (음수 사고는 0)."""
    if not u or u.get("prompt_token_count") is None:
        return zero_cost()
    cached = u.get("cached_content_token_count") or 0
    uncached = max(0, u["prompt_token_count"] - cached)
    out_tokens = (u["candidates_token_count"] or 0) + max(0, u["thoughts_token_count_derived"] or 0)
    cu, cc = uncached * PRICE_INPUT_PER_TOKEN, cached * PRICE_CACHED_PER_TOKEN
    co = out_tokens * PRICE_OUTPUT_PER_TOKEN
    return {"input_uncached": round(cu, 8), "input_cached": round(cc, 8), "input": round(cu + cc, 8),
            "output": round(co, 8), "total": round(cu + cc + co, 8),
            "tokens": {"input_uncached": uncached, "input_cached": cached, "output_incl_thinking": out_tokens}}


def zero_cost():
    return {"input_uncached": 0.0, "input_cached": 0.0, "input": 0.0, "output": 0.0, "total": 0.0,
            "tokens": {"input_uncached": 0, "input_cached": 0, "output_incl_thinking": 0}}


def model_version_of(resp):
    try:
        v = getattr(resp, "model_version", None)
        return v or None
    except Exception:
        return None


def empty_record(run_id, condition, url, page_id=None, template_id=None):
    return {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "condition": condition,
        "page_id": page_id, "template_id": template_id, "url": url,
        "ts_start_utc": utc_now(), "ts_end_utc": "", "status": "api_error",
        "prompt_date": None, "model_name": "", "model_version": None,
        "prompt_sha256": None, "image_sha256": None, "modality": "both", "viewport": [],
        "html_chars_sent": 0,
        "rag": {k: None for k in RAG_FIELDS},
        "usage": {k: None for k in USAGE_FIELDS},
        "cost_usd": zero_cost(),
        "latency_sec": {k: None for k in LATENCY_FIELDS},
        "attempts": 0, "retries": 0, "errors": [], "raw_response_text": None,
        "parsed": None, "parse_error": None, "result": None,
    }


def validate_record(rec):
    """로그 스키마 검증. 문제 목록을 돌려준다 (빈 목록이면 통과)."""
    problems = []
    for k, typ in REQUIRED_FIELDS.items():
        if k not in rec:
            problems.append(f"missing {k}")
        elif not isinstance(rec[k], typ):
            problems.append(f"bad type {k}: {type(rec[k]).__name__}")
    if rec.get("status") not in STATUSES:
        problems.append(f"bad status {rec.get('status')}")
    for sub, keys in (("rag", RAG_FIELDS), ("usage", USAGE_FIELDS), ("latency_sec", LATENCY_FIELDS)):
        for k in keys:
            if k not in (rec.get(sub) or {}):
                problems.append(f"missing {sub}.{k}")
    if rec.get("status") == "ok":
        if rec.get("parsed") is None:
            problems.append("ok without parsed")
        if (rec.get("usage") or {}).get("prompt_token_count") is None:
            problems.append("ok without usage")
    return problems


class RunExistsError(RuntimeError):
    pass


def create_run_dir(base, run_id):
    """run 폴더를 새로 만든다. 이미 있으면 RunExistsError (덮어쓰기 금지)."""
    if not run_id or any(c in run_id for c in '\\/:*?"<>| '):
        raise ValueError(f"invalid run_id: {run_id!r}")
    path = os.path.join(base, run_id)
    if os.path.exists(path):
        raise RunExistsError(f"run_id already exists: {path}")
    os.makedirs(path)
    return path


class RunLogger:
    """append 전용 JSONL 로거. 같은 프로세스의 여러 스레드에서 써도 된다."""

    def __init__(self, run_dir, run_id):
        self.run_dir = run_dir
        self.run_id = run_id
        self.path = os.path.join(run_dir, "calls.jsonl")
        if os.path.exists(self.path):
            raise RunExistsError(f"log already exists: {self.path}")
        self._lock = threading.Lock()
        self.status_by_page = {}
        self.records_written = 0

    def write(self, rec):
        rec = dict(rec)
        prompt_text = rec.pop("_prompt_text", None)
        if prompt_text is not None and rec.get("prompt_sha256"):
            pdir = os.path.join(self.run_dir, "prompts")
            os.makedirs(pdir, exist_ok=True)
            ppath = os.path.join(pdir, f"{rec['prompt_sha256']}.txt")
            if not os.path.exists(ppath):
                with open(ppath, "w", encoding="utf-8", newline="") as f:
                    f.write(prompt_text)
        problems = validate_record(rec)
        if problems:
            rec = dict(rec, schema_problems=problems)
        line = json.dumps(rec, ensure_ascii=False)
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
            self.records_written += 1
            self.status_by_page.setdefault(rec.get("page_id") or rec.get("url"), []).append(rec["status"])
        return problems


def lock_run(run_dir):
    """SHA256SUMS 를 쓰고 run 폴더 전체를 읽기 전용으로 만든다 (chmod -R a-w 에 해당)."""
    sums = []
    for root, _, files in os.walk(run_dir):
        for fn in sorted(files):
            if fn == "SHA256SUMS":
                continue
            p = os.path.join(root, fn)
            sums.append(f"{sha256_file(p)}  {os.path.relpath(p, run_dir).replace(os.sep, '/')}")
    with open(os.path.join(run_dir, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sorted(sums, key=lambda s: s.split("  ", 1)[1])) + "\n")
    ro = ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    for root, dirs, files in os.walk(run_dir, topdown=False):
        for fn in files:
            p = os.path.join(root, fn)
            os.chmod(p, os.stat(p).st_mode & ro)
        os.chmod(root, os.stat(root).st_mode & ro)   # POSIX 에서는 폴더도 잠김. Windows 는 파일만 읽기 전용 속성.


def verify_run(run_dir):
    """SHA256SUMS 와 현재 파일을 대조. 불일치 목록을 돌려준다."""
    bad = []
    with open(os.path.join(run_dir, "SHA256SUMS"), encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            h, rel = line.rstrip("\n").split("  ", 1)
            p = os.path.join(run_dir, rel)
            if not os.path.exists(p) or sha256_file(p) != h:
                bad.append(rel)
    return bad
