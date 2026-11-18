"""E5b 지표 함수 시험 (가짜 자료, API 없음)."""
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import e5b_run as e5    # noqa: E402


def rec(i, hcat, sem, kw=(), tpl="t1"):
    return {"issue_id": i, "template": tpl, "mapped": True, "hcat": hcat, "sem": sem, "kw": set(kw), "sm": 0,
            "code": "예", "vis": "아니오", "login": "아니오"}


class Metrics(unittest.TestCase):
    def test_m2x2(self):
        p, r, k = (float(x) for x in e5.m2x2(np.array([8, 2, 2, 8])))
        self.assertAlmostEqual(p, 0.8)
        self.assertAlmostEqual(r, 0.8)
        self.assertAlmostEqual(k, 0.6)
        p, r, k = e5.m2x2(np.array([0, 0, 0, 5]))
        self.assertTrue(np.isnan(p) and np.isnan(r) and np.isnan(k))

    def test_kappa6_perfect_and_chance(self):
        c = np.zeros(36)
        for j in range(6):
            c[j * 6 + j] = 3
        self.assertAlmostEqual(float(e5.kappa_k(c)), 1.0)

    def test_binrow_counts_and_ci_bounds(self):
        C = e5.CONTRAST
        recs = [rec(f"I{k}", C if k < 6 else "None", C if k < 5 or k == 9 else "None", tpl=f"t{k % 3}")
                for k in range(20)]
        row = e5.binrow(recs, [C], lambda r, t: r["hcat"] == t, lambda r, t: r["sem"] == t, lambda r: True,
                        stats=False)
        self.assertEqual((row["TP"], row["FP"], row["FN"], row["TN"]), (5, 1, 1, 13))
        self.assertTrue(row["precision_cluster_lo"] <= row["precision"] <= row["precision_cluster_hi"])
        self.assertEqual(row["precision_small"], 1)

    def test_outputs_only_under_e5b_and_no_overwrite(self):
        self.assertTrue(e5.OUT.endswith("results/revision/human_eval/e5b"))
        src = open(e5.__file__, encoding="utf-8").read()
        self.assertIn("if os.path.exists(OUT):", src)
        for line in src.splitlines():                      # 쓰기 모드로 여는 파일은 모두 OUT 아래
            if '"w"' in line and "open(" in line:
                self.assertIn("{OUT}/", line)


if __name__ == "__main__":
    unittest.main()
