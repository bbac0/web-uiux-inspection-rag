"""
재실험 배치 러너. 페이지 목록을 프로덕션 파이프라인(services.analyzer.run_analysis_flow)으로 분석하고
results/revision/runs/{run_id}/ 에 append 전용 로그를 남긴 뒤 요약표를 내고 폴더를 잠근다.

출력 (results/revision/runs/{run_id}/)
  run_meta.json     실행 인자, git 커밋/태그, 환경, 시작 시각 (실행 시작 시 1회 기록)
  calls.jsonl       LLM 호출(페이지 분석)당 1줄 (services/llm_wrapper.py 스키마)
  reports.jsonl     페이지당 1줄: 프로덕션과 같은 형태의 병합 리포트 (채점 입력)
  summary.json/.md  요약표 (성공/실패, 토큰, 비용, 지연시간)
  SHA256SUMS        잠금 시점의 전체 파일 해시
  shots/, prompts/  스크린샷과 프롬프트 원문 (커밋하지 않음, 해시만 SHA256SUMS 에 남음)

예시
  python -m http.server 8080      # 저장소 루트, 별도 터미널
  python experiments/revision/run_experiment.py --run-id E1-R1 --condition E1 --pages all \
      --max-pages 1 --chroma-path services/chroma_db --prompt-date 2026-11-12 --concurrency 1

오류율 중단: 완료 페이지가 10개 이상이고 (api_error + rag_empty + rag_error + acquisition_error) / 완료 > 0.2
이면 남은 페이지를 취소하고 aborted=true 로 요약·잠금한다. parse_error 는 오류율에 넣지 않고 따로 집계한다.
"""

import argparse
import asyncio
import copy
import csv
import datetime
import json
import os
import platform
import re
import shutil
import tempfile
import statistics
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from services import exp_config as ec          # noqa: E402
from services import llm_wrapper as lw         # noqa: E402

RUNS_BASE = os.path.join("results", "revision", "runs")
METADATA = os.path.join("testbed_200", "dataset_metadata.json")
FAIL_STATUSES = {"api_error", "rag_empty", "rag_error", "acquisition_error"}
ERROR_RATE_LIMIT = 0.20
ERROR_RATE_MIN_PAGES = 10
# 크레딧 소진/요금 한도 오류는 오류율과 별개로 즉시 중단한다 (페이지 단위로 확인, 재시도는 래퍼 정책 그대로)
BILLING_ERROR_RE = re.compile(r"(?<!\d)(402|429)(?!\d)|resource_exhausted|credits are depleted|prepayment", re.I)


class WatchingLogger(lw.RunLogger):
    """RunLogger 와 똑같이 기록하고, 기록된 오류에 402/429/크레딧 소진이 있으면 표시만 해 둔다."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.billing_error = None

    def write(self, rec):
        problems = super().write(rec)
        msgs = [e.get("message", "") for e in rec.get("errors", [])]
        msgs += [e.get("message", "") for e in (rec.get("rag") or {}).get("embedding_errors") or []]
        msgs += [e.get("message", "") for e in rec.get("upload_errors") or []]
        for m in msgs:
            if m and BILLING_ERROR_RE.search(m) and not self.billing_error:
                self.billing_error = f"{rec.get('page_id')}: {m[:200]}"
        return problems


# ---------------------------------------------------------------- 페이지 집합
def load_meta():
    with open(METADATA, encoding="utf-8") as f:
        return {p["page_id"].replace(".html", ""): p for p in json.load(f)}


def select_pages(meta, spec):
    ids = sorted(meta)
    types = lambda p: {d["type"] for d in meta[p]["defects"]}
    ctrl = [p for p in ids if not meta[p]["has_defect"]]
    if spec == "all":
        return ids
    if spec == "terminology+controls":
        return sorted([p for p in ids if "Standard Terminology Violation" in types(p)] + ctrl)
    if spec == "mobile+controls":
        return sorted([p for p in ids if "Mobile Layout Breakage" in types(p)] + ctrl)
    if spec.startswith("file:"):
        with open(spec[5:], encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if spec.startswith("list:"):
        return [s.strip() for s in spec[5:].split(",") if s.strip()]
    raise SystemExit(f"unknown --pages spec: {spec}")


def load_oracle(path):
    out = {}
    if path:
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("page_id") and r.get("chunk_id"):
                    out.setdefault(r["page_id"].strip(), []).append(r["chunk_id"].strip())
    return out


# ---------------------------------------------------------------- 환경 기록
def git(*a):
    try:
        return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    except Exception:
        return None


def env_info():
    pkgs = {}
    try:
        from importlib.metadata import version
        for n in ("google-generativeai", "google-ai-generativelanguage", "langchain-google-genai",
                  "langchain-chroma", "chromadb", "playwright"):
            try:
                pkgs[n] = version(n)
            except Exception:
                pkgs[n] = None
    except Exception:
        pass
    return {"python": sys.version.split()[0], "platform": platform.platform(), "packages": pkgs,
            "git_head": git("rev-parse", "HEAD"), "git_describe": git("describe", "--tags", "--always", "--dirty"),
            "git_dirty_files": [l for l in (git("status", "--porcelain") or "").splitlines()
                                if not l[3:].startswith("results/")],
            "freeze_tag_commit": git("rev-list", "-n", "1", "exp-freeze-v1") or None}


# ---------------------------------------------------------------- 요약
def pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    f, c = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[f] + (xs[c] - xs[f]) * (k - f), 4)


def stats(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0, "mean": None, "median": None, "p95": None}
    return {"n": len(xs), "mean": round(statistics.mean(xs), 4), "median": round(statistics.median(xs), 4),
            "p95": pct(xs, 0.95)}


def summarize(run_dir, meta_info, pages, aborted, abort_reason):
    recs = []
    with open(os.path.join(run_dir, "calls.jsonl"), encoding="utf-8") as f:
        for line in f:
            recs.append(json.loads(line))
    target = [r for r in recs if r.get("page_id") and "#linked:" not in r["page_id"]]
    by_status = {}
    for r in recs:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    u = lambda k: [r["usage"].get(k) for r in recs if r["usage"].get(k) is not None]
    neg_thoughts = [r["page_id"] for r in recs if (r["usage"].get("thoughts_token_count_derived") or 0) < 0]
    cached_pos = [r["page_id"] for r in recs if (r["usage"].get("cached_content_token_count") or 0) > 0]
    lat = {k: stats([r["latency_sec"].get(k) for r in recs]) for k in lw.LATENCY_FIELDS}
    pages_done = sorted({r["page_id"] for r in target})
    s = {
        "run_id": meta_info["run_id"], "condition": meta_info["condition"],
        "started_utc": meta_info["started_utc"], "finished_utc": lw.utc_now(),
        "aborted": aborted, "abort_reason": abort_reason,
        "pages_requested": len(pages), "pages_with_record": len(pages_done),
        "pages_missing_record": sorted(set(pages) - set(pages_done)),
        "records": len(recs), "status_counts": by_status,
        "failed_pages": sorted({r["page_id"] for r in target if r["status"] in FAIL_STATUSES}),
        "parse_error_pages": sorted({r["page_id"] for r in target if r["status"] == "parse_error"}),
        "tokens_total": {k: sum(u(k)) for k in lw.USAGE_FIELDS},
        "tokens_mean": {k: (round(statistics.mean(u(k)), 1) if u(k) else None) for k in lw.USAGE_FIELDS},
        "cost_usd_total": round(sum(r["cost_usd"]["total"] for r in recs), 6),
        "cost_usd_mean_per_call": (round(statistics.mean([r["cost_usd"]["total"] for r in recs if r["status"] in ("ok", "parse_error")]), 6)
                                   if any(r["status"] in ("ok", "parse_error") for r in recs) else None),
        "latency_sec": lat,
        "retries_total": sum(r.get("retries", 0) for r in recs),
        "model_versions": sorted({r["model_version"] for r in recs if r.get("model_version")}),
        "prompt_sha256_distinct": len({r["prompt_sha256"] for r in recs if r.get("prompt_sha256")}),
        "negative_derived_thoughts": neg_thoughts, "cached_tokens_positive": cached_pos,
        "rag_n_chunks_counts": {str(k): v for k, v in sorted(
            {n: sum(1 for r in recs if r["rag"].get("n_chunks") == n) for n in {r["rag"].get("n_chunks") for r in recs}}.items(),
            key=lambda kv: str(kv[0]))},
        "schema_problem_records": sum(1 for r in recs if r.get("schema_problems")),
        "cost_usd_breakdown": {k: round(sum(r["cost_usd"].get(k, 0.0) for r in recs), 6)
                               for k in ("input_uncached", "input_cached", "output")},
        "thoughts_check_mismatch": [r["page_id"] for r in recs
                                    if r["usage"].get("thoughts_check_without_cached_subtraction") is not None
                                    and r["usage"]["thoughts_check_without_cached_subtraction"] != r["usage"]["thoughts_token_count_derived"]],
        "chroma": meta_info.get("chroma"),
        "prices": {"input_uncached_per_1M": 0.30, "input_cached_per_1M": 0.03, "output_incl_thinking_per_1M": 2.50},
    }
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    L = [f"# Run {s['run_id']} ({s['condition']})", "",
         f"- 기간(UTC): {s['started_utc']} → {s['finished_utc']}" + (f"  **중단됨: {abort_reason}**" if aborted else ""),
         f"- 페이지: 요청 {s['pages_requested']}, 기록 {s['pages_with_record']}, 기록 없음 {len(s['pages_missing_record'])}",
         f"- 상태: " + ", ".join(f"{k} {v}" for k, v in sorted(by_status.items())),
         f"- 실패 페이지 {len(s['failed_pages'])}개, 파싱 실패 {len(s['parse_error_pages'])}개, 재시도 합계 {s['retries_total']}",
         f"- 모델 버전: {', '.join(s['model_versions']) or '-'}; 서로 다른 프롬프트 해시 {s['prompt_sha256_distinct']}",
         f"- 총 비용 ${s['cost_usd_total']:.4f} (호출당 평균 ${s['cost_usd_mean_per_call'] or 0:.5f}); "
         f"구성: 입력(비캐시) ${s['cost_usd_breakdown']['input_uncached']:.4f}, 입력(cached) ${s['cost_usd_breakdown']['input_cached']:.4f}, "
         f"출력+사고 ${s['cost_usd_breakdown']['output']:.4f}", "",
         "| 토큰 | 합계 | 평균 |", "|---|---:|---:|"]
    for k in lw.USAGE_FIELDS:
        L.append(f"| {k} | {s['tokens_total'][k]} | {s['tokens_mean'][k]} |")
    L += ["", "| 지연시간(초) | n | 평균 | 중앙값 | P95 |", "|---|---:|---:|---:|---:|"]
    for k, v in lat.items():
        L.append(f"| {k} | {v['n']} | {v['mean']} | {v['median']} | {v['p95']} |")
    L += ["", f"- RAG 청크 수 분포: {s['rag_n_chunks_counts']}",
          f"- derived 사고 토큰 음수: {len(neg_thoughts)}건, cached>0: {len(cached_pos)}건, 스키마 문제 레코드: {s['schema_problem_records']}건"]
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    return s


# ---------------------------------------------------------------- 실행
async def run_pages(args, pages, meta, run_dir, logger, analyzer):
    base = ec.ExperimentConfig(
        run_id=args.run_id, condition=args.condition, max_pages=args.max_pages, rag=not args.no_rag,
        modality=args.modality,
        viewport=ec.MOBILE_VIEWPORT if args.viewport_extra == "mobile" else ec.DEFAULT_VIEWPORT,
        query_mode=args.query_mode, oracle_chunks=load_oracle(args.oracle_chunks),
        chroma_path=args.chroma_path, prompt_date=args.prompt_date, concurrency=None,
        require_rag_chunks=True, max_retries=3, logger=logger,
        shots_dir=os.path.join(run_dir, "shots")).validate()
    sem = asyncio.Semaphore(args.concurrency)
    reports_path = os.path.join(run_dir, "reports.jsonl")
    state = {"done": 0, "fail": 0, "abort": None}
    lock = asyncio.Lock()

    async def one(pid):
        async with sem:
            if state["abort"]:
                return
            cfg = copy.copy(base)
            cfg.page_id, cfg.template_id = pid, meta[pid]["base_template"]
            url = args.base_url.rstrip("/") + f"/{pid}.html"
            final, err = None, None
            try:
                async for step in analyzer.run_analysis_flow(url, [], [], config=cfg):
                    if "result" in step:
                        final = step["result"]
                    elif step.get("progress", 0) < 0:
                        err = step.get("text")
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
            statuses = logger.status_by_page.get(pid, [])
            st = statuses[-1] if statuses else "acquisition_error"
            if not statuses:      # 브라우저 단계에서 죽어 레코드가 없는 경우도 오류로 남긴다
                rec = lw.empty_record(args.run_id, args.condition, url, pid, cfg.template_id)
                rec.update(status="acquisition_error", ts_end_utc=lw.utc_now(), prompt_date=cfg.prompt_date,
                           model_name=ec.MODEL_NAME, modality=cfg.modality, viewport=list(cfg.viewport))
                rec["errors"].append({"attempt": None, "type": "FlowError", "message": str(err)[:500]})
                logger.write(rec)
            async with lock:
                with open(reports_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"page_id": pid, "status": st, "flow_error": err, "report": final},
                                       ensure_ascii=False) + "\n")
                state["done"] += 1
                state["fail"] += st in FAIL_STATUSES
                rate = state["fail"] / state["done"]
                print(f"[{state['done']}/{len(pages)}] {pid} {st} (오류율 {rate:.1%})", flush=True)
                if logger.billing_error and not state["abort"]:
                    state["abort"] = f"billing/rate-limit error (402/429): {logger.billing_error}"
                    print(f"!!! 즉시 중단: {state['abort']}", flush=True)
                if state["done"] >= ERROR_RATE_MIN_PAGES and rate > ERROR_RATE_LIMIT and not state["abort"]:
                    state["abort"] = f"error rate {state['fail']}/{state['done']} > {ERROR_RATE_LIMIT:.0%}"
                    print(f"!!! 중단: {state['abort']}", flush=True)

    await asyncio.gather(*(one(p) for p in pages))
    return state["abort"]


def dir_hashes(path):
    out = {}
    for root, _, files in os.walk(path):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            out[os.path.relpath(p, path).replace(os.sep, "/")] = lw.sha256_file(p)
    return dict(sorted(out.items()))


def copy_chroma(src, run_id):
    """원본 벡터 DB 를 직접 열지 않도록 run 마다 임시 폴더로 복사한다. 복사 전후 해시를 남긴다."""
    before = dir_hashes(src)
    dst = os.path.join(tempfile.mkdtemp(prefix=f"chroma_{run_id}_"), "chroma_db")
    shutil.copytree(src, dst)
    copied = dir_hashes(dst)
    if copied != before:
        raise SystemExit("chroma copy hash mismatch")
    return {"source": src, "copied_at_utc": lw.utc_now(), "copy_path": dst,
            "source_sha256": before,
            "source_combined_sha256": lw.sha256_text(json.dumps(before, sort_keys=True))}


def close_and_remove_chroma_copy(chroma_meta, analyzer):
    """Chroma 클라이언트를 명시적으로 닫은 뒤 임시 복사본을 지운다. 실패하면 경고만 하고 계속한다.
    반환: {"deleted": bool, "warning": str|None}"""
    warning = None
    try:
        for store in list(getattr(analyzer, "_VECTOR_STORES", {}).values()):
            client = getattr(store, "_client", None)
            try:
                if client is not None and hasattr(client, "close"):
                    client.close()
                elif client is not None:
                    client._system.stop()
            except Exception as e:
                warning = f"chroma client close failed: {e}"
        analyzer._VECTOR_STORES.clear()
        try:
            from chromadb.api.client import SharedSystemClient
            SharedSystemClient.clear_system_cache()
        except Exception as e:
            warning = warning or f"chroma cache clear failed: {e}"
        import gc
        gc.collect()
    except Exception as e:
        warning = f"chroma close error: {e}"
    path = chroma_meta["copy_path"]
    shutil.rmtree(os.path.dirname(path), ignore_errors=True)
    deleted = not os.path.exists(path)
    if not deleted:
        warning = (warning + "; " if warning else "") + f"copy not deleted: {path}"
    if warning:
        print(f"[경고] {warning}", flush=True)
    return {"deleted": deleted, "warning": warning}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--condition", required=True, help="조건 이름 (예: E1, E2-A1, E3-page, E4-mobile, pilot)")
    ap.add_argument("--pages", default="all", help="all | terminology+controls | mobile+controls | file:PATH | list:a,b")
    ap.add_argument("--max-pages", type=int, default=ec.DEFAULT_MAX_PAGES)
    ap.add_argument("--no-rag", action="store_true")
    ap.add_argument("--modality", choices=ec.MODALITIES, default="both")
    ap.add_argument("--viewport-extra", choices=["mobile"], default=None)
    ap.add_argument("--query-mode", choices=ec.QUERY_MODES, default="fixed")
    ap.add_argument("--oracle-chunks", default=None)
    ap.add_argument("--chroma-path", default=ec.DEFAULT_CHROMA_PATH)
    ap.add_argument("--prompt-date", required=True, help="모든 run 에 같은 날짜 (YYYY-MM-DD)")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--base-url", default="http://localhost:8080/testbed_200")
    ap.add_argument("--runs-base", default=RUNS_BASE)
    ap.add_argument("--mock-llm", action="store_true", help="API 없이 점검 (가짜 LLM/벡터 DB). 결과는 실험에 쓰지 않는다")
    args = ap.parse_args(argv)

    if args.concurrency < 1 or args.concurrency > 4:
        raise SystemExit("--concurrency must be 1..4")
    if not args.mock_llm:
        if not os.environ.get("GEMINI_API_KEY"):
            raise SystemExit("환경변수 GEMINI_API_KEY 가 필요합니다 (.env 는 읽지 않음).")
        if not args.no_rag and not os.path.exists(os.path.join(args.chroma_path, "chroma.sqlite3")):
            raise SystemExit(f"vector DB not found: {args.chroma_path}")
    else:
        os.environ.setdefault("GEMINI_API_KEY", "mock-not-a-key")

    meta = load_meta()
    pages = select_pages(meta, args.pages)
    unknown = [p for p in pages if p not in meta]
    if unknown:
        raise SystemExit(f"unknown page ids: {unknown}")

    run_dir = lw.create_run_dir(args.runs_base, args.run_id)      # 이미 있으면 RunExistsError
    logger = WatchingLogger(run_dir, args.run_id)
    meta_info = {"run_id": args.run_id, "condition": args.condition, "started_utc": lw.utc_now(),
                 "argv": sys.argv if argv is None else argv, "args": vars(args), "pages": pages,
                 "mock": args.mock_llm, "env": env_info(),
                 "frozen_settings": {"model": ec.MODEL_NAME, "temperature": ec.TEMPERATURE, "rag_query": ec.RAG_QUERY,
                                     "rag_k": ec.RAG_K, "html_char_limit": ec.HTML_CHAR_LIMIT,
                                     "chunk_size": 1000, "chunk_overlap": 100}}
    if not args.no_rag and not args.mock_llm:
        meta_info["chroma"] = copy_chroma(args.chroma_path, args.run_id)
        args.chroma_path = meta_info["chroma"]["copy_path"]
    with open(os.path.join(run_dir, "run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=2)

    from services import analyzer
    if args.mock_llm:
        from experiments.revision import mock_llm
        mock_llm.install(analyzer)

    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    abort = None
    try:
        abort = asyncio.run(run_pages(args, pages, meta, run_dir, logger, analyzer))
    except KeyboardInterrupt:
        abort = "KeyboardInterrupt"
    finally:
        if meta_info.get("chroma"):
            meta_info["chroma"]["cleanup"] = close_and_remove_chroma_copy(meta_info["chroma"], analyzer)
            print("chroma 복사본 삭제: " + ("완료" if meta_info["chroma"]["cleanup"]["deleted"] else "실패(경고 기록)"))
        s = summarize(run_dir, meta_info, pages, bool(abort), abort)
        lw.lock_run(run_dir)
        print(f"\n잠금 완료: {run_dir}")
    return 2 if abort else 0


if __name__ == "__main__":
    sys.exit(main())
