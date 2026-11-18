"""평가자 간 비교 스크립트 시험 (가짜 CSV, API 없음, 실제 평가 결과 미사용)."""
import csv
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import human_eval_pilot_compare as hc    # noqa: E402
from experiments.revision import make_eval_sheets as mes             # noqa: E402


def row(i, cat="", ex="", vis="", login="", note=""):
    return {"issue_id": i, "screenshot_path": f"shots/P{i}.png", "description": f"d{i}", "suggestion": f"s{i}",
            "rater_category": cat, "exists_in_code": ex, "visible_on_screen": vis, "login_link_label_concern": login,
            "rater_notes": note}


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, rows, cols=None):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols or mes.SHEET_COLS); w.writeheader(); w.writerows(rows)
        return p

    def test_perfect_and_partial_agreement(self):
        A = [row("I1", "중복 ID", "예", "아니오", "아니오"), row("I2", "해당 없음", "아니오", "아니오", "아니오"),
             row("I3", "표준 용어 위반", "예", "예", "예"), row("I4", "명도 대비 부족", "예", "예", "아니오")]
        B = [row("I1", "중복 ID", "예", "아니오", "아니오"), row("I2", "해당 없음", "판단 불가", "아니오", "아니오", "부재형"),
             row("I3", "해당 없음", "예", "예", "예"), row("I4", "명도 대비 부족", "예", "예", "아니오")]
        res = hc.compare(hc.read(self.write("a.csv", A)), hc.read(self.write("b.csv", B)))
        c = res["cols"]
        self.assertEqual((c["rater_category"]["agree"], c["rater_category"]["n"]), (3, 4))
        self.assertAlmostEqual(c["login_link_label_concern"]["po"], 1.0)
        self.assertAlmostEqual(c["login_link_label_concern"]["kappa"], 1.0)
        # 6분류 kappa 수기 계산: po=0.75, A {중복1,해당없음1,용어1,대비1}, B {중복1,해당없음2,대비1} → pe=(1+2+0+1)/16=0.25
        self.assertAlmostEqual(c["rater_category"]["kappa"], (0.75 - 0.25) / 0.75)
        self.assertEqual({d["issue_id"] for d in res["disagree"]}, {"I2", "I3"})
        self.assertEqual(res["confusion"][("표준 용어 위반", "해당 없음")], 1)
        md = hc.report(res, "a.csv", "b.csv", "same")
        self.assertIn("I3", md)

    def test_blank_cells_excluded(self):
        A = [row("I1", "중복 ID", "예", "", "아니오"), row("I2", "해당 없음", "아니오", "아니오", "")]
        B = [row("I1", "중복 ID", "예", "아니오", "아니오"), row("I2", "", "아니오", "아니오", "아니오")]
        res = hc.compare(hc.read(self.write("a.csv", A)), hc.read(self.write("b.csv", B)))
        self.assertEqual((res["cols"]["rater_category"]["n"], res["cols"]["rater_category"]["blank"]), (1, 1))
        self.assertEqual(res["cols"]["visible_on_screen"]["n"], 1)

    def test_same_mode_rejects_different_sets_overlap_mode_merges(self):
        A = [row(f"I{k}", "해당 없음", "예", "예", "아니오") for k in range(1, 7)]       # A 6건
        B = [row(f"I{k}", "해당 없음", "예", "아니오", "아니오") for k in (2, 4, 6)]     # B 3건 (부분집합)
        a, b = hc.read(self.write("a.csv", A)), hc.read(self.write("b.csv", B))
        with self.assertRaises(SystemExit):
            hc.compare(a, b, "same")
        res = hc.compare(a, b, "overlap")
        self.assertEqual((res["n_common"], res["only_a"], res["only_b"]), (3, 3, 0))
        self.assertEqual(res["cols"]["visible_on_screen"]["agree"], 0)

    def test_rejects_wrong_columns_and_mismatched_text(self):
        with self.assertRaises(SystemExit):
            hc.read(self.write("bad.csv", [{"issue_id": "I1", "x": "1"}], ["issue_id", "x"]))
        A = [row("I1", "중복 ID", "예", "예", "아니오")]
        B = [dict(row("I1", "중복 ID", "예", "예", "아니오"), description="다른 문장")]
        with self.assertRaises(SystemExit):
            hc.compare(hc.read(self.write("a.csv", A)), hc.read(self.write("b.csv", B)))

    def test_main_writes_file_and_refuses_overwrite(self):
        A = [row("I1", "중복 ID", "예", "예", "아니오")]
        a, b = self.write("a.csv", A), self.write("b.csv", A)
        out = os.path.join(self.tmp, "out.md")
        hc.main(["--a", a, "--b", b, "--out", out])
        self.assertTrue(os.path.exists(out))
        with self.assertRaises(SystemExit):
            hc.main(["--a", a, "--b", b, "--out", out])

    def test_no_key_or_scoring_inputs(self):
        src = open(hc.__file__, encoding="utf-8").read()
        for s in ("eval_key", "semantic_scores", "issue_table", "ground_truth", "keyword"):
            self.assertNotIn(s, src)


if __name__ == "__main__":
    unittest.main()
