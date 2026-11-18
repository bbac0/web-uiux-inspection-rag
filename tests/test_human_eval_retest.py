"""재판정 시트와 자기 일치도 비교 스크립트 시험 (가짜 CSV, API 없음, 실제 평가 결과 미사용)."""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import human_eval_retest_compare as rc    # noqa: E402
from experiments.revision import make_eval_sheets as mes             # noqa: E402

HE = os.path.join(ROOT, "results", "revision", "human_eval")


def row(i, cat="해당 없음", ex="예", vis="아니오", login="아니오", note="", shot=None):
    return {"issue_id": i, "screenshot_path": shot or f"shots/P{i}.png", "description": f"d{i}", "suggestion": f"s{i}",
            "rater_category": cat, "exists_in_code": ex, "visible_on_screen": vis, "login_link_label_concern": login,
            "rater_notes": note}


class RetestCompare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, rows):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=mes.SHEET_COLS); w.writeheader(); w.writerows(rows)
        return p

    def test_subset_compare_and_kappa(self):
        M = [row(f"I{k}", ex="예" if k % 2 else "아니오") for k in range(10)]           # 본 평가 10건
        R = [row(f"I{k}", ex="예", shot=f"shots/Q{k}.png") for k in (1, 2, 3, 4)]       # 재판정 4건, 새 스크린샷 토큰
        res = rc.compare(rc.read(self.write("m.csv", M)), rc.read(self.write("r.csv", R)))
        c = res["cols"]["exists_in_code"]
        self.assertEqual((res["n"], c["agree"]), (4, 2))
        self.assertAlmostEqual(c["po"], 0.5)
        # 본: 예,아니오,예,아니오 / 재: 예,예,예,예 → pe = (2*4 + 2*0)/16 = .5 → kappa 0
        self.assertAlmostEqual(c["kappa"], 0.0)
        self.assertEqual(res["cols"]["login_link_label_concern"]["kappa"], rc.ONE_VALUE)
        self.assertEqual({d["issue_id"] for d in res["disagree"]}, {"I2", "I4"})
        md = rc.report(res, "m.csv", "r.csv")
        self.assertIn(rc.ONE_VALUE, md)
        self.assertIn("단순 일치율", md)

    def test_known_kappa_and_blanks(self):
        M = [row("I1", cat="중복 ID"), row("I2", cat="해당 없음"), row("I3", cat="명도 대비 부족"), row("I4", cat="해당 없음")]
        R = [row("I1", cat="중복 ID"), row("I2", cat="해당 없음"), row("I3", cat="해당 없음"), row("I4", cat="")]
        c = rc.compare(rc.read(self.write("m.csv", M)), rc.read(self.write("r.csv", R)))["cols"]["rater_category"]
        self.assertEqual((c["n"], c["blank"]), (3, 1))
        # 본 {중복1,해당1,대비1} 재 {중복1,해당2} → po 2/3, pe (1+2+0)/9 = 1/3 → kappa .5
        self.assertAlmostEqual(c["kappa"], 0.5)

    def test_rejects(self):
        M = [row(f"I{k}") for k in range(3)]
        m = self.write("m.csv", M)
        with self.assertRaises(SystemExit):                          # 본 평가에 없는 issue_id
            rc.compare(rc.read(m), rc.read(self.write("r.csv", [row("X9")])))
        with self.assertRaises(SystemExit):                          # 설명이 다름
            rc.compare(rc.read(m), rc.read(self.write("r2.csv", [dict(row("I1"), description="다른")])))
        with self.assertRaises(SystemExit):                          # 표본 목록과 다름
            rc.compare(rc.read(m), rc.read(self.write("r3.csv", [row("I1")])), ["I1", "I2"])
        s = os.path.join(self.tmp, "s.json")
        json.dump({"issue_ids_sorted": ["I1"]}, open(s, "w", encoding="utf-8"))
        out = os.path.join(self.tmp, "o.md")
        rc.main(["--main", m, "--retest", self.write("r4.csv", [row("I1")]), "--sampling", s, "--out", out])
        with self.assertRaises(SystemExit):                          # 덮어쓰기 거부
            rc.main(["--main", m, "--retest", self.write("r5.csv", [row("I1")]), "--out", out])

    def test_no_key_or_scoring_inputs_and_original_untouched(self):
        src = open(rc.__file__, encoding="utf-8").read()
        for s in ("eval_key", "semantic_scores", "issue_table", "ground_truth", "keyword"):
            self.assertNotIn(s, src)
        r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "experiments/revision/human_eval_pilot_compare.py"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


class RetestSheet(unittest.TestCase):
    def test_sheet_matches_sampling_blank_inputs_new_tokens(self):
        s = json.load(open(os.path.join(HE, "retest_sampling.json"), encoding="utf-8"))
        rows = list(csv.DictReader(open(os.path.join(HE, "rater_A_retest", "eval_sheet_A_retest.csv"), encoding="utf-8-sig")))
        self.assertEqual(len(rows), 40)
        self.assertEqual([r["issue_id"] for r in rows], s["sheet_order"])
        self.assertEqual(sorted(s["sheet_order"]), s["issue_ids_sorted"])
        self.assertEqual((s["seed_sample"], s["seed_order"]), (20261125, 20261126))
        for r in rows:
            for c in ("rater_category", "exists_in_code", "visible_on_screen", "login_link_label_concern", "rater_notes"):
                self.assertEqual(r[c], "")
        a_shots = set(os.listdir(os.path.join(HE, "rater_A", "shots")))
        r_shots = set(os.listdir(os.path.join(HE, "rater_A_retest", "shots")))
        self.assertFalse(a_shots & r_shots)
        self.assertEqual({f"shots/{x}" for x in r_shots}, {r["screenshot_path"] for r in rows})
        html = open(os.path.join(HE, "rater_A_retest", "viewer_A_retest.html"), encoding="utf-8").read()
        self.assertIn('const KEY = "human_eval_A_retest"', html)
        self.assertIn("<!-- csv-import v1 -->", html)
        data = json.loads(re.search(r"const ROWS = (.*?);\n", html).group(1).replace("<\\/", "</"))
        self.assertEqual({k for d in data for k in d}, {"issue_id", "screenshot_path", "description", "suggestion"})


if __name__ == "__main__":
    unittest.main()
