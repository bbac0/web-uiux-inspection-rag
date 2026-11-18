"""배치 채점 경로 단위 테스트 (API 호출 없음)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import semantic_grader_anthropic as g          # noqa: E402
from scoring import semantic_grader_batch as gb             # noqa: E402
from scoring import mock_anthropic_batch as mb              # noqa: E402
from scoring.mock_anthropic import FakeAnthropic            # noqa: E402
from services import llm_wrapper as lw                      # noqa: E402

RUN = "E1-R1"


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["MOCK_BATCH_STORE"] = os.path.join(self.tmp, "store.json")
        mb.reset()
        self.base = os.path.join(self.tmp, "out")

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp):
            for f in files:
                os.chmod(os.path.join(root, f), 0o666)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sub(self, *args):
        return gb.main(list(args) + ["--mock", "--out-base", self.base])

    def grades(self, oid):
        return [json.loads(l) for l in open(os.path.join(self.base, oid, "grades.jsonl"), encoding="utf-8")]

    def test_custom_id_format(self):
        self.assertEqual(gb.custom_id("E1-R1:page_001:00", 1), "E1-R1__page_001__00__p1")
        with self.assertRaises(ValueError):
            gb.custom_id("E1 R1:page:00", 1)

    def test_request_body_same_as_standard(self):
        cfg = g.load_config()
        issue_id, src, issue = next(g.iter_run_issues(RUN))
        text = g.build_input(issue, cfg)
        self.assertEqual(g.build_request(text, cfg)["thinking"], {"type": "between_tools"})
        self.assertEqual(g.build_request(text, cfg)["output_config"], {"effort": "high"})
        self.assertNotIn("temperature", g.build_request(text, cfg))

    def test_submit_collect_lock_and_equivalence(self):
        self.assertEqual(self.sub("submit", "--run-id", RUN, "--out-id", "b1", "--pass", "1", "--limit", "15"), 0)
        self.assertEqual(self.sub("collect", "--out-id", "b1"), 0)
        recs = self.grades("b1")
        self.assertEqual(len(recs), 15)
        self.assertTrue(all(r["mode"] == "batch" and r["pricing"] == "batch" for r in recs))
        # 같은 이슈를 표준 경로(가짜 클라이언트)로 채점한 라벨·상태와 같아야 한다
        cfg = g.load_config()
        fake = FakeAnthropic()
        std = {}
        for issue_id, src, issue in list(g.iter_run_issues(RUN))[:15]:
            r = g.grade_issue(fake, issue, cfg, issue_id, src, pass_no=1)
            std[issue_id] = (r["label"], r["status"], r["prompt_sha256"])
        for r in recs:
            self.assertEqual((r["label"], r["status"], r["prompt_sha256"]), std[r["issue_id"]])
        self.assertFalse(os.path.exists(os.path.join(self.base, "b1", "SHA256SUMS")))   # 아직 전체가 아님 → 잠그지 않음

    def test_resume_full_run_locks(self):
        self.sub("submit", "--run-id", RUN, "--out-id", "b2", "--pass", "1", "--limit", "20")
        self.sub("collect", "--out-id", "b2")
        self.assertEqual(self.sub("submit", "--run-id", RUN, "--out-id", "b2", "--pass", "1", "--resume"), 0)
        self.assertEqual(self.sub("collect", "--out-id", "b2"), 0)
        n_issues = len(list(g.iter_run_issues(RUN)))
        recs = self.grades("b2")
        self.assertEqual(len({r["issue_id"] for r in recs}), n_issues)
        self.assertEqual(len(recs), n_issues)                         # 중복 채점 없음
        self.assertTrue(os.path.exists(os.path.join(self.base, "b2", "SHA256SUMS")))
        self.assertEqual(lw.verify_run(os.path.join(self.base, "b2")), [])

    def test_errored_resubmitted_on_resume(self):
        self.sub("submit", "--run-id", RUN, "--out-id", "b3", "--pass", "1", "--limit", "5")
        cids = [json.loads(l)["custom_id"] for l in open(os.path.join(self.base, "b3", "custom_ids.jsonl"), encoding="utf-8")]
        mb.set_controls(errored_custom_ids=[cids[0]], expired_custom_ids=[cids[1]])
        self.sub("collect", "--out-id", "b3")
        st = [r["status"] for r in self.grades("b3")]
        self.assertEqual(st.count("api_error"), 2)
        mb.set_controls(errored_custom_ids=[], expired_custom_ids=[])
        self.sub("submit", "--run-id", RUN, "--out-id", "b3", "--pass", "1", "--resume", "--limit", "2")
        sub2 = [json.loads(l) for l in open(os.path.join(self.base, "b3", "batches.jsonl"), encoding="utf-8")
                if json.loads(l)["event"] == "submitted"][-1]
        self.assertEqual(len(sub2["issue_ids"]), 2)                   # 실패한 두 이슈만 다시 제출
        self.assertEqual(set(sub2["issue_ids"]), {gb.custom_id(i, 1)[:0] + i for i in sub2["issue_ids"]})

    def test_resume_refuses_uncollected_and_mode_change(self):
        self.sub("submit", "--run-id", RUN, "--out-id", "b4", "--pass", "1", "--limit", "3")
        with self.assertRaises(SystemExit):
            self.sub("submit", "--run-id", RUN, "--out-id", "b4", "--pass", "1", "--resume")
        with self.assertRaises(SystemExit):
            self.sub("submit", "--run-id", RUN, "--out-id", "b4", "--pass", "2", "--resume")

    def test_processing_then_ended(self):
        mb.set_controls(processing_polls=1)
        self.sub("submit", "--run-id", RUN, "--out-id", "b5", "--pass", "1", "--limit", "3")
        self.assertEqual(self.sub("collect", "--out-id", "b5"), 3)     # 아직 처리 중
        self.assertFalse(os.path.exists(os.path.join(self.base, "b5", "grades.jsonl")))
        self.assertEqual(self.sub("collect", "--out-id", "b5"), 0)

    def test_billing_error_on_create_stops(self):
        mb.set_controls(create_error="Error code: 400 - credit balance is too low")
        self.assertEqual(self.sub("submit", "--run-id", RUN, "--out-id", "b6", "--pass", "1", "--limit", "3"), 2)
        ev = [json.loads(l) for l in open(os.path.join(self.base, "b6", "batches.jsonl"), encoding="utf-8")]
        self.assertTrue(ev[-1]["billing_stop"])

    def test_max_tokens_is_parse_error(self):
        mb.set_controls(stop_reason="max_tokens")
        self.sub("submit", "--run-id", RUN, "--out-id", "b7", "--pass", "1", "--limit", "3")
        self.sub("collect", "--out-id", "b7")
        self.assertTrue(all(r["status"] == "parse_error" and r["truncated"] for r in self.grades("b7")))


if __name__ == "__main__":
    unittest.main()
