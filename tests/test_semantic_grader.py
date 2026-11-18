"""
의미 채점기(scoring/semantic_grader_anthropic.py) 단위 테스트. API 호출 없음 (가짜 클라이언트).

  python -m unittest tests.test_semantic_grader -v
"""
import json
import os
import shutil
import stat
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scoring import semantic_grader_anthropic as g     # noqa: E402
from scoring.mock_anthropic import FakeAnthropic        # noqa: E402
from experiments import semantic_issue_classifier as sic  # noqa: E402
from services import llm_wrapper as lw                   # noqa: E402

PILOT = "pilot-02"
SAMPLE = {"category": "기술",
          "description": "[http://localhost:8080/testbed_200/page_081.html] HTML 문서 내 `id` 속성 값 (`main-banner`)이 중복 사용되었습니다.",
          "suggestion": "중복된 id 를 고유한 값으로 바꾸세요.", "source_file": "gov_guide.pdf", "page_number": [9]}


def cfg_with(**kw):
    c = g.load_config()
    c.update(kw)
    return c


class TestConfig(unittest.TestCase):
    def test_config_values(self):
        c = g.load_config()
        self.assertEqual((c["provider"], c["model"], c["temperature"], c["api_key_env"]),
                         ("anthropic", "claude-sonnet-5-5", None, "ANTHROPIC_API_KEY"))
        self.assertEqual((c["thinking"], c["effort"], c["max_tokens"], c["fallbacks"]),
                         ({"type": "between_tools"}, "high", 100, None))
        self.assertEqual(c["input_fields"], ["description", "suggestion"])
        req = g.build_request("x", c)
        self.assertNotIn("temperature", req)
        self.assertEqual(req["thinking"], {"type": "between_tools"})
        self.assertEqual(req["output_config"], {"effort": "high"})
        self.assertEqual(c["judge_prompt_version"], sic.PROMPT_VERSION)


class TestInput(unittest.TestCase):
    def test_url_prefix_removed_and_suggestion_appended(self):
        t = g.build_input(SAMPLE, cfg_with(input_fields=["description", "suggestion"]))
        self.assertTrue(t.startswith("HTML 문서 내"))
        self.assertIn("\n제안: 중복된 id 를 고유한 값으로 바꾸세요.", t)
        self.assertNotIn("page_081", t)
        self.assertNotIn("testbed", t)

    def test_description_only(self):
        t = g.build_input(SAMPLE, cfg_with(input_fields=["description"]))
        self.assertNotIn("제안", t)

    def test_leak_guard(self):
        bad = dict(SAMPLE, suggestion="page_081 의 id 를 고치세요")
        with self.assertRaises(g.LeakError):
            g.build_input(bad, cfg_with(input_fields=["description", "suggestion"]))
        bad2 = dict(SAMPLE, description="조건 E1-R1 에서 발견")
        with self.assertRaises(g.LeakError):
            g.build_input(bad2, cfg_with(input_fields=["description"]))

    def test_other_fields_never_used(self):
        with self.assertRaises(ValueError):
            g.build_input(SAMPLE, cfg_with(input_fields=["description", "source_file"]))

    def test_real_pilot_issues_are_blinded(self):
        n = 0
        for issue_id, src, issue in g.iter_run_issues(PILOT):
            for fields in (["description"], ["description", "suggestion"]):
                t = g.build_input(issue, cfg_with(input_fields=fields))
                self.assertNotIn(src["page_id"], t)
                req = g.build_request(t, g.load_config())
                self.assertEqual(req["messages"][0]["content"], sic.JUDGE_PROMPT.replace("<<DESC>>", t))
            n += 1
        self.assertGreater(n, 0)


class TestSameRequestAsExistingPath(unittest.TestCase):
    """기존 semantic_issue_classifier.make_judge('anthropic') 와 요청 인자가 같은지 (같은 입력 문자열 기준)."""

    def test_kwargs_identical(self):
        recorded = []

        class _Client:
            def __init__(self, *a, **k):
                self.messages = types.SimpleNamespace(create=self._create)

            def _create(self, **kw):
                recorded.append(kw)
                return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text='{"label": "None"}')])

        fake_mod = types.ModuleType("anthropic")
        fake_mod.Anthropic = _Client
        old = sys.modules.get("anthropic")
        sys.modules["anthropic"] = fake_mod
        env = {k: os.environ.get(k) for k in ("JUDGE_MODEL", "ANTHROPIC_API_KEY")}
        os.environ["JUDGE_MODEL"] = "claude-sonnet-5-5"
        os.environ["ANTHROPIC_API_KEY"] = "dummy-not-a-key"
        try:
            legacy = cfg_with(input_fields=["description"], temperature=0, thinking=None, effort=None)
            text = g.build_input(SAMPLE, legacy)
            sic.make_judge("anthropic", False)(text)
            new_req = g.build_request(text, legacy)     # 기존 인자로 되돌리면 요청이 완전히 같다 (메시지 구성 동일성 확인)
            self.assertEqual(recorded[0], new_req)
        finally:
            if old is None:
                sys.modules.pop("anthropic", None)
            else:
                sys.modules["anthropic"] = old
            for k, v in env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_optional_params_omitted_when_null(self):
        req = g.build_request("x", cfg_with(temperature=None, thinking=None, effort=None))
        self.assertEqual(set(req), {"model", "max_tokens", "messages"})
        req2 = g.build_request("x", cfg_with(thinking={"type": "between_tools"}, effort="low"))
        self.assertEqual(req2["thinking"], {"type": "between_tools"})
        self.assertEqual(req2["output_config"], {"effort": "low"})


class TestGrading(unittest.TestCase):
    def test_record_fields(self):
        c = FakeAnthropic()
        rec = g.grade_issue(c, SAMPLE, g.load_config(), "x:1", {"run_id": "r", "page_id": "page_081"})
        self.assertEqual(rec["status"], "ok")
        self.assertEqual(rec["label"], "Duplicate ID Markup Error")
        self.assertEqual(rec["model_version"], "mock-claude-0")
        self.assertIsNotNone(rec["input_tokens"]); self.assertIsNotNone(rec["output_tokens"])
        self.assertTrue(rec["raw_response"].startswith("{"))
        import datetime
        datetime.datetime.fromisoformat(rec["ts_start_utc"])
        self.assertNotIn("page_081", json.dumps(c.calls, ensure_ascii=False))   # 요청에는 페이지 ID 없음

    def test_retry(self):
        c = FakeAnthropic(); c.fail_times = 2
        orig = lw.time.sleep; lw.time.sleep = lambda s: None
        try:
            rec = g.grade_issue(c, SAMPLE, g.load_config(), "x:2")
        finally:
            lw.time.sleep = orig
        self.assertEqual((rec["status"], rec["attempts"], len(rec["errors"])), ("ok", 3, 2))

    def test_fallback_uses_beta_path(self):
        c = FakeAnthropic()
        g.grade_issue(c, SAMPLE, cfg_with(fallbacks="default"), "x:3")
        self.assertEqual(c.calls[0]["betas"], ["server-side-fallback-2026-07-01"])
        self.assertEqual(c.calls[0]["fallbacks"], "default")


class TestDecisions20261112(unittest.TestCase):
    def test_extra_body_when_sdk_lacks_fields(self):
        from scoring.mock_anthropic import StrictOldSDK
        c = StrictOldSDK()
        rec = g.grade_issue(c, SAMPLE, g.load_config(), "x:e")
        self.assertEqual(rec["status"], "ok")
        self.assertEqual(rec["sent_via_extra_body"], ["output_config", "thinking"])
        self.assertEqual(c.calls[-1]["extra_body"], {"thinking": {"type": "between_tools"}, "output_config": {"effort": "high"}})

    def test_max_tokens_is_parse_error(self):
        c = FakeAnthropic(); c.stop_reason = "max_tokens"
        rec = g.grade_issue(c, SAMPLE, g.load_config(), "x:t")
        self.assertEqual((rec["status"], rec["truncated"], rec["label"], rec["parse_ok"]), ("parse_error", True, None, False))

    def test_refusal_label(self):
        c = FakeAnthropic(); c.stop_reason = "refusal"
        rec = g.grade_issue(c, SAMPLE, g.load_config(), "x:r")
        self.assertEqual((rec["status"], rec["label"]), ("refusal", "refusal"))

    def test_pass_and_input_override_recorded(self):
        tmp = tempfile.mkdtemp()
        try:
            g.main(["--run-id", PILOT, "--out-id", "p2", "--pass", "2", "--mock", "--out-base", tmp])
            g.main(["--run-id", PILOT, "--out-id", "d1", "--pass", "1", "--input-fields", "description", "--mock", "--out-base", tmp])
            r2 = json.loads(open(os.path.join(tmp, "p2", "grades.jsonl"), encoding="utf-8").readline())
            s1 = json.load(open(os.path.join(tmp, "d1", "summary.json"), encoding="utf-8"))
            self.assertEqual(r2["pass"], 2)
            self.assertEqual(s1["input_fields"], ["description"])
            self.assertIn("truncated_max_tokens", s1["status_counts"])
        finally:
            for root, dirs, files in os.walk(tmp):
                for n in dirs + files:
                    os.chmod(os.path.join(root, n), stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            shutil.rmtree(tmp, ignore_errors=True)


class TestMockRun(unittest.TestCase):
    def test_end_to_end_mock(self):
        tmp = tempfile.mkdtemp()
        os.environ["ANTHROPIC_API_KEY"] = "SENTINEL-ANTH-KEY"
        try:
            rc = g.main(["--run-id", PILOT, "--out-id", "t-mock", "--pass", "1", "--mock", "--out-base", tmp])
            self.assertEqual(rc, 0)
            d = os.path.join(tmp, "t-mock")
            recs = [json.loads(l) for l in open(os.path.join(d, "grades.jsonl"), encoding="utf-8")]
            n_issues = sum(1 for _ in g.iter_run_issues(PILOT))
            self.assertEqual(len(recs), n_issues)
            self.assertEqual(lw.verify_run(d), [])
            with self.assertRaises(PermissionError):
                open(os.path.join(d, "grades.jsonl"), "a")
            for root, _, files in os.walk(d):
                for fn in files:
                    self.assertNotIn(b"SENTINEL-ANTH-KEY", open(os.path.join(root, fn), "rb").read())
            with self.assertRaises(lw.RunExistsError):
                g.main(["--run-id", PILOT, "--out-id", "t-mock", "--pass", "1", "--mock", "--out-base", tmp])
        finally:
            os.environ.pop("ANTHROPIC_API_KEY", None)
            for root, dirs, files in os.walk(tmp):
                for n in dirs + files:
                    os.chmod(os.path.join(root, n), stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
