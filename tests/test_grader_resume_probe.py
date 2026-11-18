"""
채점기 --resume, 결제 오류 즉시 중단, 시험 호출(probe) 테스트. API 호출 없음.

  python -m unittest tests.test_grader_resume_probe -v
"""
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import semantic_grader_anthropic as g, probe_tokens   # noqa: E402
from scoring import mock_anthropic as ma                          # noqa: E402
from services import llm_wrapper as lw                            # noqa: E402

PILOT = "pilot-02"


def rmtree_force(p):
    for root, dirs, files in os.walk(p):
        for n in dirs + files:
            os.chmod(os.path.join(root, n), stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
    shutil.rmtree(p, ignore_errors=True)


class TestResumeAndBilling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.orig_make = g.make_client
        self.orig_sleep = lw.time.sleep

    def tearDown(self):
        g.make_client = self.orig_make
        rmtree_force(self.tmp)

    def run_main(self, *extra):
        return g.main(["--run-id", PILOT, "--out-id", "r", "--pass", "1", "--mock", "--out-base", self.tmp, *extra])

    def test_billing_stop_then_resume(self):
        n_issues = sum(1 for _ in g.iter_run_issues(PILOT))
        failing = ma.FailingAfter(10, "Error code: 400 - Your credit balance is too low to access the Anthropic API.")
        g.make_client = lambda cfg, mock=False: failing
        rc = self.run_main()
        self.assertEqual(rc, 2)
        self.assertEqual(len(failing.calls), 11)          # 10건 정상 + 1건 실패 후 재시도 없이 멈춤
        d = os.path.join(self.tmp, "r")
        self.assertFalse(os.path.exists(os.path.join(d, "SHA256SUMS")))   # 중단되면 잠그지 않는다
        recs = [json.loads(l) for l in open(os.path.join(d, "grades.jsonl"), encoding="utf-8")]
        self.assertEqual([r["status"] for r in recs].count("billing_stop"), 1)
        self.assertEqual(recs[-1]["attempts"], 1)
        s = json.load(open(os.path.join(d, "summary.json"), encoding="utf-8"))
        self.assertFalse(s["complete"]); self.assertIn("credit balance", s["stopped"])

        ok_client = ma.FakeAnthropic()
        g.make_client = lambda cfg, mock=False: ok_client
        rc = self.run_main("--resume")
        self.assertEqual(rc, 0)
        self.assertEqual(len(ok_client.calls), n_issues - 10)    # 이미 채점한 10건은 건너뜀, 실패한 1건은 다시 호출
        self.assertTrue(os.path.exists(os.path.join(d, "SHA256SUMS")))
        ev = [json.loads(l) for l in open(os.path.join(d, "resume_log.jsonl"), encoding="utf-8")]
        self.assertEqual((ev[0]["already_final"], ev[0]["remaining"]), (10, n_issues - 10))
        recs = [json.loads(l) for l in open(os.path.join(d, "grades.jsonl"), encoding="utf-8")]
        final = {r["issue_id"] for r in recs if r["status"] in g.FINAL_STATUSES}
        self.assertEqual(len(final), n_issues)
        self.assertTrue(all(r["resumed_session"] for r in recs[11:]))
        with self.assertRaises(SystemExit):                       # 완료·잠금된 폴더는 다시 이을 수 없다
            self.run_main("--resume")

    def test_429_not_retried(self):
        c = ma.FailingAfter(0, "Error code: 429 - rate_limit_error")
        g.make_client = lambda cfg, mock=False: c
        self.assertEqual(self.run_main(), 2)
        self.assertEqual(len(c.calls), 1)

    def test_transient_still_retried(self):
        c = ma.FakeAnthropic(); c.fail_times = 2               # 529 overloaded 는 일시적 오류 → 재시도
        g.make_client = lambda cfg, mock=False: c
        lw.time.sleep = lambda s: None
        try:
            rec = g.grade_issue(c, {"description": "id 가 중복", "suggestion": ""}, g.load_config(), "x")
        finally:
            lw.time.sleep = self.orig_sleep
        self.assertEqual((rec["status"], rec["attempts"]), ("ok", 3))

    def test_resume_refuses_changed_settings(self):
        failing = ma.FailingAfter(3, "402 payment required")
        g.make_client = lambda cfg, mock=False: failing
        self.run_main()
        with self.assertRaises(SystemExit):
            g.main(["--run-id", PILOT, "--out-id", "r", "--pass", "2", "--mock", "--out-base", self.tmp, "--resume"])
        with self.assertRaises(SystemExit):
            g.main(["--run-id", PILOT, "--out-id", "r", "--pass", "1", "--mock", "--out-base", self.tmp, "--resume",
                    "--input-fields", "description"])

    def test_resume_requires_existing(self):
        with self.assertRaises(SystemExit):
            self.run_main("--resume")


class TestProbe(unittest.TestCase):
    def test_probe_blinded(self):
        tmp = tempfile.mkdtemp()
        try:
            rc = probe_tokens.main(["--run-id", PILOT, "--out-id", "p", "--n", "20", "--mock", "--out-base", tmp])
            self.assertEqual(rc, 0)
            d = os.path.join(tmp, "p")
            raw = open(os.path.join(d, "probe.jsonl"), encoding="utf-8").read()
            for bad in ('"label"', '"raw_response"', '"parse_ok"', "Duplicate ID", "Poor Contrast", '"status"'):
                self.assertNotIn(bad, raw)
            s = json.load(open(os.path.join(d, "summary.json"), encoding="utf-8"))
            self.assertEqual(s["n_called"], 20)
            self.assertEqual(s["input_tokens"]["n"], 20)
            self.assertEqual(s["seed"], probe_tokens.DEFAULT_SEED)
            self.assertEqual(lw.verify_run(d), [])
        finally:
            rmtree_force(tmp)


if __name__ == "__main__":
    unittest.main()
