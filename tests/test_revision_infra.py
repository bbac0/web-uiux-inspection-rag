"""
재실험 인프라 단위 테스트 (API 호출 없음).

  python -m unittest tests.test_revision_infra -v      (저장소 루트에서, venv 파이썬)

검사 항목: 로그 스키마, run_id 중복 방지, 읽기 전용 잠금, 재시도/비용/사고 토큰 계산,
프롬프트가 원본 커밋(6bee028)의 프롬프트와 바이트 단위로 같은지, 동결 상수, page 질의 규칙.
"""

import ast
import datetime
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("GEMINI_API_KEY", "mock-not-a-key")

from services import llm_wrapper as lw                      # noqa: E402
from services import exp_config as ec                       # noqa: E402
from services import analyzer                               # noqa: E402
from experiments.revision import mock_llm                   # noqa: E402

BASE_COMMIT = "6bee028c0a33eb9588d593a9f04f0aa8d86620ee"     # 재실험 전 프로덕션 코드
mock_llm.install(analyzer)


def old_prompt_template():
    """원본 커밋의 analyze_with_gemini 안 prompt f-string 을 AST 로 꺼내 컴파일한다."""
    src = subprocess.run(["git", "show", f"{BASE_COMMIT}:services/analyzer.py"], cwd=ROOT,
                         capture_output=True, encoding="utf-8").stdout
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "analyze_with_gemini")
    node = next(n for n in ast.walk(fn) if isinstance(n, ast.Assign)
                and getattr(n.targets[0], "id", None) == "prompt")
    return compile(ast.Expression(node.value), "<old_prompt>", "eval")


OLD_PROMPT = old_prompt_template()
HTML = "<html><body>" + ("가나다라 " * 2000) + "</body></html>"     # 5,000자를 넘는 HTML


def capture_inputs():
    seen = []
    orig = mock_llm.FakeModel.generate_content

    def spy(self, inputs):
        seen.append(inputs)
        return orig(self, inputs)
    mock_llm.FakeModel.generate_content = spy
    return seen, lambda: setattr(mock_llm.FakeModel, "generate_content", orig)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.shot = os.path.join(self.tmp, "shot.png")
        with open(self.shot, "wb") as f:
            f.write(b"\x89PNG fake")
        mock_llm.FakeModel.fail_times = 0
        mock_llm.FakeModel.bad_json = False
        analyzer.get_vector_store = lambda persist_directory="./chroma_db": mock_llm.FakeStore(4)

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp):
            for n in dirs + files:
                os.chmod(os.path.join(root, n), stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cfg(self, run_id="t1", **kw):
        run_dir = lw.create_run_dir(self.tmp, run_id)
        logger = lw.RunLogger(run_dir, run_id)
        c = ec.ExperimentConfig(run_id=run_id, condition="test", max_pages=1, chroma_path="x",
                                prompt_date="2026-11-12", require_rag_chunks=True, logger=logger,
                                page_id="page_001", template_id="portal_main", **kw).validate()
        return c, run_dir

    def records(self, run_dir):
        with open(os.path.join(run_dir, "calls.jsonl"), encoding="utf-8") as f:
            return [json.loads(l) for l in f]

    def run_one(self, c):
        return analyzer.analyze_with_gemini(HTML, self.shot, [], config=c,
                                            page_ctx={"url": "http://x/page_001.html", "page_id": "page_001",
                                                      "template_id": "portal_main", "acquisition_sec": 1.0})


class TestLoggingSchema(Base):
    def test_ok_record_is_valid(self):
        c, d = self.cfg()
        self.run_one(c)
        [r] = self.records(d)
        self.assertEqual(lw.validate_record(r), [])
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["rag"]["n_chunks"], 4)
        self.assertEqual([x["id"] for x in r["rag"]["chunks"]], ["mock-0", "mock-1", "mock-2", "mock-3"])
        self.assertEqual(r["model_version"], "mock-model-0")
        self.assertEqual(r["usage"]["thoughts_token_count_derived"], 300)
        self.assertAlmostEqual(r["cost_usd"]["total"], 1000 * 0.30e-6 + 500 * 2.50e-6, places=9)
        self.assertEqual(r["html_chars_sent"], 5000)
        self.assertNotIn("_prompt_text", r)
        self.assertTrue(os.path.exists(os.path.join(d, "prompts", r["prompt_sha256"] + ".txt")))
        for k in ("acquisition", "query_embedding", "vector_search", "upload", "llm", "total"):
            self.assertIsNotNone(r["latency_sec"][k], k)
        datetime.datetime.fromisoformat(r["ts_start_utc"])

    def test_missing_field_detected(self):
        r = lw.empty_record("r", "c", "u")
        del r["usage"]
        self.assertTrue(any("usage" in p for p in lw.validate_record(r)))

    def test_parse_error_recorded(self):
        mock_llm.FakeModel.bad_json = True
        c, d = self.cfg()
        res = self.run_one(c)
        [r] = self.records(d)
        self.assertEqual(res["status"], "error")
        self.assertEqual(r["status"], "parse_error")
        self.assertEqual(r["raw_response_text"], "not json")
        self.assertEqual(lw.validate_record(r), [])

    def test_retry_then_success(self):
        mock_llm.FakeModel.fail_times = 2
        c, d = self.cfg()
        orig = lw.time.sleep
        lw.time.sleep = lambda s: None
        try:
            self.run_one(c)
        finally:
            lw.time.sleep = orig
        [r] = self.records(d)
        self.assertEqual((r["status"], r["attempts"], r["retries"], len(r["errors"])), ("ok", 3, 2, 2))

    def test_retry_exhausted_is_api_error(self):
        mock_llm.FakeModel.fail_times = 10
        c, d = self.cfg()
        orig = lw.time.sleep
        lw.time.sleep = lambda s: None
        try:
            with self.assertRaises(Exception):
                self.run_one(c)
        finally:
            lw.time.sleep = orig
        [r] = self.records(d)
        self.assertEqual((r["status"], r["attempts"]), ("api_error", 4))   # 최초 1회 + 재시도 3회
        self.assertEqual(lw.validate_record(r), [])

    def test_rag_empty_is_error(self):
        analyzer.get_vector_store = lambda persist_directory="./chroma_db": mock_llm.FakeStore(0)
        c, d = self.cfg()
        with self.assertRaises(analyzer.AnalysisStageError):
            self.run_one(c)
        [r] = self.records(d)
        self.assertEqual(r["status"], "rag_empty")

    def test_no_api_key_in_log(self):
        os.environ["GEMINI_API_KEY"] = "SENTINEL-KEY-123"
        try:
            c, d = self.cfg()
            self.run_one(c)
            for root, _, files in os.walk(d):
                for fn in files:
                    with open(os.path.join(root, fn), "rb") as f:
                        self.assertNotIn(b"SENTINEL-KEY-123", f.read())
        finally:
            os.environ["GEMINI_API_KEY"] = "mock-not-a-key"

    def test_derived_thoughts_negative_is_kept(self):
        resp = mock_llm.FakeResponse("{}", prompt_tokens=10, cand_tokens=5, thoughts=0)
        resp.usage_metadata.total_token_count = 12
        u = lw.usage_from_response(resp)
        self.assertEqual(u["thoughts_token_count_derived"], -3)      # 음수는 숨기지 않고 기록 (비용 계산에서만 0 처리)
        self.assertAlmostEqual(lw.cost_from_usage(u)["output"], 5 * 2.5e-6)

    def test_cached_pricing(self):
        resp = mock_llm.FakeResponse("{}", prompt_tokens=1000, cand_tokens=100, thoughts=200, cached=0)
        resp.usage_metadata.cached_content_token_count = 400       # prompt 1000 중 400 cached
        resp.usage_metadata.total_token_count = 1000 + 100 + 200
        u = lw.usage_from_response(resp)
        c = lw.cost_from_usage(u)
        self.assertAlmostEqual(c["input_cached"], 400 * 0.03e-6)
        self.assertAlmostEqual(c["input_uncached"], 600 * 0.30e-6)
        self.assertEqual(c["tokens"]["input_cached"], 400)
        self.assertEqual(u["thoughts_check_without_cached_subtraction"], 200)


class TestRunIdAndLock(Base):
    def test_duplicate_run_id_rejected(self):
        lw.create_run_dir(self.tmp, "dup")
        with self.assertRaises(lw.RunExistsError):
            lw.create_run_dir(self.tmp, "dup")

    def test_existing_log_rejected(self):
        d = lw.create_run_dir(self.tmp, "r2")
        open(os.path.join(d, "calls.jsonl"), "w").close()
        with self.assertRaises(lw.RunExistsError):
            lw.RunLogger(d, "r2")

    def test_invalid_run_id(self):
        for bad in ("", "a/b", "..\\x", "a b"):
            with self.assertRaises(ValueError):
                lw.create_run_dir(self.tmp, bad)

    def test_append_only(self):
        c, d = self.cfg()
        self.run_one(c)
        self.run_one(c)
        self.assertEqual(len(self.records(d)), 2)

    def test_lock_read_only_and_verify(self):
        c, d = self.cfg()
        self.run_one(c)
        lw.lock_run(d)
        self.assertEqual(lw.verify_run(d), [])
        with self.assertRaises(PermissionError):
            open(os.path.join(d, "calls.jsonl"), "a").write("x")
        p = os.path.join(d, "calls.jsonl")                    # 강제로 풀고 변조하면 검증에서 잡힌다
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        with open(p, "a") as f:
            f.write("tamper\n")
        self.assertEqual(lw.verify_run(d), ["calls.jsonl"])


class TestPromptIdentity(Base):
    """원본 프롬프트 문구가 바뀌지 않았음을 보장한다."""

    def expected(self, retrieved_context, today, html):
        # eval 대상은 이 저장소 원본 커밋의 f-string 하나를 AST 로 꺼내 컴파일한 것뿐이다 (외부 입력 아님).
        return eval(OLD_PROMPT, {}, {"retrieved_context": retrieved_context, "user_custom_context": "",
                                     "today": today, "html_content": html})

    def ctx4(self):
        return analyzer._format_context(mock_llm.FakeStore(4).similarity_search(None))

    def test_production_path_unchanged(self):
        seen, restore = capture_inputs()
        try:
            analyzer.analyze_with_gemini(HTML, self.shot, [])
        finally:
            restore()
        today = datetime.datetime.now().strftime("%Y년 %m월 %d일")
        self.assertEqual(len(seen[0]), 2)
        self.assertEqual(seen[0][1], self.expected(self.ctx4(), today, HTML))

    def test_experiment_both_equals_production_text(self):
        seen, restore = capture_inputs()
        try:
            c, _ = self.cfg()
            self.run_one(c)
        finally:
            restore()
        self.assertEqual(seen[0][1], self.expected(self.ctx4(), "2026년 11월 12일", HTML))

    def test_no_rag_keeps_section_title_empty_content(self):
        seen, restore = capture_inputs()
        try:
            c, _ = self.cfg(rag=False)
            self.run_one(c)
        finally:
            restore()
        self.assertEqual(seen[0][1], self.expected("", "2026년 11월 12일", HTML))
        self.assertIn("[1. 정부 표준 가이드라인 (기본 지침)]", seen[0][1])

    def test_modality_screenshot_empties_html_block(self):
        seen, restore = capture_inputs()
        try:
            c, d = self.cfg(modality="screenshot")
            self.run_one(c)
        finally:
            restore()
        self.assertEqual(len(seen[0]), 2)
        self.assertEqual(seen[0][1], self.expected(self.ctx4(), "2026년 11월 12일", ""))
        self.assertEqual(self.records(d)[0]["html_chars_sent"], 0)

    def test_modality_html_drops_image(self):
        seen, restore = capture_inputs()
        try:
            c, d = self.cfg(modality="html")
            self.run_one(c)
        finally:
            restore()
        self.assertEqual(len(seen[0]), 1)
        self.assertEqual(seen[0][0], self.expected(self.ctx4(), "2026년 11월 12일", HTML))
        self.assertIsNone(self.records(d)[0]["image_sha256"])

    def test_oracle_uses_given_chunks(self):
        c, d = self.cfg(query_mode="oracle", oracle_chunks={"page_001": ["c-9", "c-3"]})
        self.run_one(c)
        r = self.records(d)[0]
        self.assertEqual([x["id"] for x in r["rag"]["chunks"]], ["c-9", "c-3"])
        self.assertIsNone(r["rag"]["query"])


class TestFrozenSettings(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(analyzer.RAG_QUERY, ec.RAG_QUERY)
        self.assertEqual(analyzer.RAG_K, ec.RAG_K)
        src = open(os.path.join(ROOT, "services", "analyzer.py"), encoding="utf-8").read()
        self.assertIn('model_name="models/gemini-2.5-flash"', src)
        self.assertIn("temperature=0.0", src)
        self.assertEqual(ec.HTML_CHAR_LIMIT, 5000)
        self.assertEqual(ec.DEFAULT_VIEWPORT, (1280, 800))
        idx = open(os.path.join(ROOT, "services", "indexer.py"), encoding="utf-8").read()
        self.assertIn("chunk_size=1000, chunk_overlap=100", idx)

    def test_defaults_equal_production(self):
        c = ec.ExperimentConfig()
        self.assertEqual((c.max_pages, c.rag, c.modality, c.viewport, c.query_mode, c.chroma_path,
                          c.prompt_date, c.concurrency, c.require_rag_chunks),
                         (5, True, "both", (1280, 800), "fixed", "./chroma_db", None, None, False))


class TestPageQuery(unittest.TestCase):
    def test_rule(self):
        q, fb = analyzer.build_page_query({"title": " 로그인 - 대한민국 정부 ", "headings": ["로그인"],
                                           "buttons": ["로그인", "  제출\n하기 "]})
        self.assertEqual((q, fb), ("로그인 - 대한민국 정부 로그인 제출 하기", False))

    def test_fallback(self):
        self.assertEqual(analyzer.build_page_query({}), (ec.RAG_QUERY, True))




class TestRunnerCleanupAndBillingStop(unittest.TestCase):
    """러너 변경(exp-freeze-v3): Chroma 복사본 닫고 삭제, 402/429 즉시 중단 감지."""

    def test_real_chroma_copy_closed_and_deleted(self):
        from experiments.revision import run_experiment as rx
        from langchain_chroma import Chroma
        meta = rx.copy_chroma(os.path.join(ROOT, "services", "chroma_db"), "unittest")
        store = Chroma(persist_directory=meta["copy_path"], embedding_function=None)
        self.assertEqual(store._collection.count(), 1020)          # 실제로 열어서 파일 핸들을 잡게 한다 (API 호출 없음)
        analyzer._VECTOR_STORES[meta["copy_path"]] = store
        res = rx.close_and_remove_chroma_copy(meta, analyzer)
        self.assertTrue(res["deleted"], res)
        self.assertFalse(os.path.exists(os.path.dirname(meta["copy_path"])))
        self.assertEqual(analyzer._VECTOR_STORES, {})

    def test_delete_failure_only_warns(self):
        from experiments.revision import run_experiment as rx
        orig = rx.shutil.rmtree
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "chroma_db"); os.makedirs(p)
        rx.shutil.rmtree = lambda *a, **k: None                    # 삭제 실패 흉내
        try:
            res = rx.close_and_remove_chroma_copy({"copy_path": p}, analyzer)
        finally:
            rx.shutil.rmtree = orig
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertFalse(res["deleted"])
        self.assertIn("copy not deleted", res["warning"])

    def test_billing_error_detection(self):
        from experiments.revision import run_experiment as rx
        tmp = tempfile.mkdtemp()
        try:
            lg = rx.WatchingLogger(lw.create_run_dir(tmp, "b1"), "b1")
            r = lw.empty_record("b1", "c", "u", "page_001")
            r["errors"].append({"attempt": 1, "type": "X", "message": "page 4029 timeout"})
            lg.write(r)
            self.assertIsNone(lg.billing_error)
            r2 = lw.empty_record("b1", "c", "u", "page_002")
            r2["rag"]["embedding_errors"] = [{"attempt": 1, "message": "402 RESOURCE_EXHAUSTED credits are depleted"}]
            lg.write(r2)
            self.assertTrue(lg.billing_error.startswith("page_002"))
            lg3 = rx.WatchingLogger(lw.create_run_dir(tmp, "b2"), "b2")
            r3 = lw.empty_record("b2", "c", "u", "page_003")
            r3["errors"].append({"attempt": 1, "message": "429 Too Many Requests"})
            lg3.write(r3)
            self.assertIsNotNone(lg3.billing_error)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
