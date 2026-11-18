"""잘림 재채점기·병합 통합 표 단위 테스트 (mock 만, API 호출 없음)."""
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import semantic_grader_batch as gb             # noqa: E402
from scoring import semantic_grader_retry as gr             # noqa: E402
from scoring import issue_table_merged as itm               # noqa: E402
from scoring import mock_anthropic_batch as mb              # noqa: E402
from services import llm_wrapper as lw                      # noqa: E402

RUN = "E1-R1"
ORIG = "orig-p1"


def tree_hash(d):
    h = {}
    for root, _, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            h[os.path.relpath(p, d)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return h


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["MOCK_BATCH_STORE"] = os.path.join(self.tmp, "store.json")
        mb.reset()
        self.base = os.path.join(self.tmp, "out")
        # 원 채점: 10건 모두 max_tokens 로 잘림 (원 설정 max_tokens 100)
        mb.set_controls(stop_reason="max_tokens")
        gb.main(["submit", "--run-id", RUN, "--out-id", ORIG, "--pass", "1", "--limit", "10", "--mock", "--out-base", self.base])
        gb.main(["collect", "--out-id", ORIG, "--mock", "--out-base", self.base])
        mb.set_controls(stop_reason="end_turn")
        self.orig_dir = os.path.join(self.base, ORIG)
        self.orig_grades = [json.loads(l) for l in open(os.path.join(self.orig_dir, "grades.jsonl"), encoding="utf-8")]
        assert all(r["truncated"] for r in self.orig_grades)
        self.targets_ids = [r["issue_id"] for r in self.orig_grades][:4]
        self.targets = self.write_targets(self.targets_ids)

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp):
            for f in files:
                os.chmod(os.path.join(root, f), 0o666)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_targets(self, ids, out_id=ORIG, name="targets.csv"):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["out_id", "retry_out_id", "source_run", "pass", "input_fields", "issue_id", "orig_input_tokens"])
            for i in ids:
                w.writerow([out_id, out_id + "-retry", RUN, 1, "description+suggestion", i, 0])
        return p

    def retry(self, *args):
        return gr.main(list(args) + ["--mock", "--out-base", self.base])

    def submit(self, targets=None):
        return self.retry("submit", "--orig-out-id", ORIG, "--targets", targets or self.targets)

    def store_requests(self):
        s = json.load(open(os.environ["MOCK_BATCH_STORE"], encoding="utf-8"))
        return [r for b in s["batches"].values() for r in b["requests"]]

    def test_only_targets_submitted_with_max_tokens_800(self):
        n_before = len(self.store_requests())
        self.assertEqual(self.submit(), 0)
        new = self.store_requests()[n_before:]
        self.assertEqual(sorted(r["custom_id"] for r in new), sorted(gb.custom_id(i, 1) for i in self.targets_ids))
        self.assertTrue(all(r["params"]["max_tokens"] == 800 for r in new))
        self.assertTrue(all(r["params"]["thinking"] == {"type": "between_tools"} for r in new))
        self.assertTrue(all(r["params"]["output_config"] == {"effort": "high"} for r in new))
        meta = json.load(open(os.path.join(self.base, ORIG + "-retry", "run_meta.json"), encoding="utf-8"))
        self.assertEqual(meta["retry_of"], ORIG)
        self.assertEqual(meta["targets"], self.targets_ids)

    def test_input_sha_mismatch_refused_and_no_folder(self):
        p = os.path.join(self.orig_dir, "custom_ids.jsonl")
        rows = [json.loads(l) for l in open(p, encoding="utf-8")]
        rows[0]["input_sha256"] = "0" * 64
        os.chmod(p, 0o666)
        with open(p, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        targets = self.write_targets([rows[0]["issue_id"]], name="t1.csv")
        with self.assertRaises(SystemExit) as cm:
            self.submit(targets)
        self.assertIn("sha256", str(cm.exception))
        self.assertFalse(os.path.exists(os.path.join(self.base, ORIG + "-retry")))

    def test_non_truncated_target_refused(self):
        gb.main(["submit", "--run-id", RUN, "--out-id", "okrun", "--pass", "1", "--limit", "3", "--mock", "--out-base", self.base])
        gb.main(["collect", "--out-id", "okrun", "--mock", "--out-base", self.base])
        ok_ids = [json.loads(l)["issue_id"] for l in open(os.path.join(self.base, "okrun", "grades.jsonl"), encoding="utf-8")]
        t = self.write_targets(ok_ids, out_id="okrun", name="t2.csv")
        with self.assertRaises(SystemExit):
            self.retry("submit", "--orig-out-id", "okrun", "--targets", t)

    def test_config_difference_beyond_max_tokens_refused(self):
        cfg = json.load(open(gr.RETRY_CONFIG, encoding="utf-8"))
        cfg["effort"] = "low"
        p = os.path.join(self.tmp, "bad_cfg.json")
        json.dump(cfg, open(p, "w", encoding="utf-8"))
        with self.assertRaises(SystemExit):
            self.retry("submit", "--orig-out-id", ORIG, "--targets", self.targets, "--config", p)

    def test_original_folder_unchanged_and_lock_on_completion(self):
        before = tree_hash(self.orig_dir)
        self.assertEqual(self.submit(), 0)
        self.assertEqual(self.retry("collect", "--out-id", ORIG + "-retry"), 0)
        self.assertEqual(tree_hash(self.orig_dir), before)
        out = os.path.join(self.base, ORIG + "-retry")
        self.assertTrue(os.path.exists(os.path.join(out, "SHA256SUMS")))
        self.assertEqual(lw.verify_run(out), [])
        recs = [json.loads(l) for l in open(os.path.join(out, "grades.jsonl"), encoding="utf-8")]
        self.assertEqual(sorted(r["issue_id"] for r in recs), sorted(self.targets_ids))
        self.assertTrue(all(r["retry_of"] == ORIG and r["orig_truncated"] and r["max_tokens"] == 800 for r in recs))
        self.assertTrue(all(r["status"] == "ok" for r in recs))
        with self.assertRaises(lw.RunExistsError):          # 같은 out_id 재사용 금지
            self.submit()

    def test_not_locked_while_processing(self):
        self.submit()
        mb.set_controls(processing_polls=5)
        self.assertEqual(self.retry("collect", "--out-id", ORIG + "-retry"), 3)
        self.assertFalse(os.path.exists(os.path.join(self.base, ORIG + "-retry", "SHA256SUMS")))

    def test_retruncated_is_final_unresolved_and_merged_table(self):
        self.submit()
        mb.set_controls(stop_reason="max_tokens")            # 재채점에서도 잘림 → 최종(미해결), 다시 내지 않음
        self.retry("collect", "--out-id", ORIG + "-retry")
        out = os.path.join(self.base, ORIG + "-retry")
        self.assertTrue(os.path.exists(os.path.join(out, "SHA256SUMS")))
        rows = {r["issue_id"]: r for r in itm.build_rows(RUN, ORIG, sem_base=self.base)}
        for i in self.targets_ids:
            self.assertEqual(rows[i]["semantic_pass1_source"], "unresolved")
            self.assertEqual(rows[i]["semantic_retry_status"], "parse_error")
            self.assertEqual(rows[i]["semantic_pass1_filled_by_retry"], 0)

    def test_merged_table_fills_from_retry(self):
        self.submit()
        self.retry("collect", "--out-id", ORIG + "-retry")
        rows = {r["issue_id"]: r for r in itm.build_rows(RUN, ORIG, sem_base=self.base)}
        retry = {json.loads(l)["issue_id"]: json.loads(l)
                 for l in open(os.path.join(self.base, ORIG + "-retry", "grades.jsonl"), encoding="utf-8")}
        for i in self.targets_ids:
            self.assertEqual(rows[i]["semantic_pass1_source"], "retry")
            self.assertEqual(rows[i]["semantic_pass1_filled_by_retry"], 1)
            self.assertEqual(rows[i]["semantic_pass1_merged"], retry[i]["label"])
            self.assertEqual(rows[i]["semantic_pass1"], "")             # 원 열은 그대로 (빈 칸)
        others = [i for i in rows if i in {r["issue_id"] for r in self.orig_grades} and i not in self.targets_ids]
        for i in others:
            self.assertEqual(rows[i]["semantic_pass1_source"], "unresolved")
            self.assertEqual(rows[i]["semantic_retry_status"], "")


if __name__ == "__main__":
    unittest.main()
