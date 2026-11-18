"""강건판 평가자 비교 스크립트 시험 (가짜 CSV, API 없음, 실제 평가 결과 미사용). 기대값은 손으로 계산했다."""
import csv
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import human_eval_compare_robust as hr    # noqa: E402
from experiments.revision import make_eval_sheets as mes             # noqa: E402


def row(i, cat="해당 없음", ex="예", vis="예", login="아니오", note=""):
    return {"issue_id": i, "screenshot_path": f"shots/P{i}.png", "description": f"d{i}", "suggestion": f"s{i}",
            "rater_category": cat, "exists_in_code": ex, "visible_on_screen": vis, "login_link_label_concern": login,
            "rater_notes": note}


class RobustTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, rows):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=mes.SHEET_COLS); w.writeheader(); w.writerows(rows)
        return p

    def run_cmp(self, A, B, **kw):
        return hr.compare(hr.read(self.write("a.csv", A)), hr.read(self.write("b.csv", B)), **kw)

    def test_rare_value_binary(self):
        # 로그인 열: A 예 1 / 아니오 19, B 아니오 20 → po .95, pe .95 → kappa 0, PABAK .9, AC1 = (.95-.04875)/.95125
        A = [row(f"I{k}", login="예" if k == 0 else "아니오") for k in range(20)]
        B = [row(f"I{k}") for k in range(20)]
        c = self.run_cmp(A, B)["cols"]["login_link_label_concern"]
        self.assertAlmostEqual(c["po"], 0.95)
        self.assertAlmostEqual(c["kappa"], 0.0)
        self.assertAlmostEqual(c["pabak"], 0.9)
        self.assertAlmostEqual(c["ac1"], (0.95 - 0.04875) / (1 - 0.04875))
        self.assertEqual(c["values"], 2)

    def test_single_value_column_marked(self):
        A = [row(f"I{k}") for k in range(10)]
        res = self.run_cmp(A, [dict(r) for r in A])
        c = res["cols"]["login_link_label_concern"]
        self.assertEqual(c["kappa"], hr.ONE_VALUE)
        self.assertAlmostEqual(c["po"], 1.0)
        self.assertAlmostEqual(c["pabak"], 1.0)
        self.assertAlmostEqual(c["ac1"], 1.0)
        self.assertIn(hr.ONE_VALUE, hr.report(res, "a.csv", "b.csv", "same"))

    def test_three_category_values(self):
        # A 예,예,아니오,판단 불가 / B 예,아니오,아니오,판단 불가
        A = [row("I1", ex="예"), row("I2", ex="예"), row("I3", ex="아니오"), row("I4", ex="판단 불가")]
        B = [row("I1", ex="예"), row("I2", ex="아니오"), row("I3", ex="아니오"), row("I4", ex="판단 불가")]
        c = self.run_cmp(A, B)["cols"]["exists_in_code"]
        self.assertAlmostEqual(c["po"], 0.75)
        self.assertAlmostEqual(c["kappa"], (0.75 - 0.3125) / 0.6875)
        self.assertAlmostEqual(c["pabak"], 0.625)                      # q = 3
        self.assertAlmostEqual(c["ac1"], (0.75 - 0.328125) / 0.671875)

    def test_category_uses_q6_and_blanks_excluded(self):
        A = [row("I1", cat="중복 ID"), row("I2", cat="해당 없음"), row("I3", cat="")]
        B = [row("I1", cat="중복 ID"), row("I2", cat="중복 ID"), row("I3", cat="해당 없음")]
        c = self.run_cmp(A, B)["cols"]["rater_category"]
        self.assertEqual((c["n"], c["blank"]), (2, 1))
        self.assertAlmostEqual(c["pabak"], (6 * 0.5 - 1) / 5)

    def test_groups_and_rejects(self):
        A = [row(f"I{k}", vis="예" if k < 2 else "아니오") for k in range(4)]
        B = [row(f"I{k}", vis="아니오") for k in range(4)]
        g = os.path.join(self.tmp, "g.csv")
        with open(g, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["issue_id", "group"]); w.writerows([["I0", "x"], ["I1", "x"], ["I2", "y"], ["I3", "y"]])
        out = os.path.join(self.tmp, "o.md")
        hr.main(["--a", self.write("a.csv", A), "--b", self.write("b.csv", B), "--groups", g, "--out", out])
        md = open(out, encoding="utf-8").read()
        self.assertIn("### 묶음 x (2건)", md)
        self.assertIn("### 묶음 y (2건)", md)
        self.assertTrue(all(len(l) <= 120 for l in md.splitlines()))
        with self.assertRaises(SystemExit):                              # 덮어쓰기 거부
            hr.main(["--a", self.write("a.csv", A), "--b", self.write("b.csv", B), "--out", out])
        with self.assertRaises(SystemExit):                              # 허용되지 않은 값
            hr.read(self.write("bad.csv", [row("I1", login="판단 불가")]))
        with self.assertRaises(SystemExit):                              # 집합이 다름 (same)
            self.run_cmp(A, B[:3])
        self.assertEqual(self.run_cmp(A, B[:3], merge="overlap")["n_common"], 3)

    def test_original_pilot_script_untouched(self):
        import subprocess
        r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "experiments/revision/human_eval_pilot_compare.py"], cwd=ROOT)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
