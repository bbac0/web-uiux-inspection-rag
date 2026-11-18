"""접수 점검·부트스트랩·합의 시트 시험 (가짜 CSV, API 없음)."""
import csv
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import human_eval_intake_all as ia     # noqa: E402
from experiments.revision import make_eval_sheets as mes         # noqa: E402


def row(i, cat="해당 없음", ex="예", vis="아니오", login="아니오", note=""):
    return {"issue_id": i, "screenshot_path": f"shots/P{i}.png", "description": f"d{i}", "suggestion": f"s{i}",
            "rater_category": cat, "exists_in_code": ex, "visible_on_screen": vis, "login_link_label_concern": login,
            "rater_notes": note}


class Intake(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, rows):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=mes.SHEET_COLS); w.writeheader(); w.writerows(rows)
        return p

    def test_check_lists_problems_without_fixing(self):
        sheet = self.write("s.csv", [row(f"I{k}", cat="", ex="", vis="", login="") for k in range(4)])
        bad = [row("I0"), row("I1", ex=""), row("I1"), dict(row("I3", cat="기타"), description="x")]
        p = self.write("f.csv", bad)
        before = open(p, "rb").read()
        P, _ = ia.check(p, sheet, 4)
        txt = "\n".join(P)
        for s in ("중복 issue_id I1", "제출에 빠진 issue_id I2", "I1: exists_in_code 빈칸", "허용 값 밖 '기타'",
                  "I3: description 가 시트와 다름"):
            self.assertIn(s, txt)
        self.assertEqual(open(p, "rb").read(), before)
        ok = self.write("ok.csv", [row(f"I{k}") for k in range(4)])
        self.assertEqual(ia.check(ok, sheet, 4)[0], [])

    def test_bootstrap_deterministic_and_bounds(self):
        A = {f"I{k}": row(f"I{k}", ex="예" if k % 3 else "아니오") for k in range(30)}
        B = {f"I{k}": row(f"I{k}", ex="예" if k % 4 else "아니오") for k in range(30)}
        ids = sorted(A)
        c1, s1 = ia.bootstrap(A, B, ids, n=200, seed=1)
        c2, _ = ia.bootstrap(A, B, ids, n=200, seed=1)
        self.assertEqual(c1, c2)
        lo, hi, n = c1["exists_in_code"]["po"]
        self.assertTrue(0 <= lo <= hi <= 1 and n == 200)
        self.assertEqual(c1["login_link_label_concern"]["kappa"][2], 0)    # 모든 회차가 값 한 가지 → 유효 0
        self.assertEqual(s1["login_link_label_concern"], 200)

    def test_leak_terms_catch_forbidden(self):
        for s in ("E1-R1", "E3-oracle", "string_match", "semantic", "S2", "supp_key", "page_12", "Terminology"):
            self.assertTrue(any(re.search(p, s) for p in ia.TERMS.values()), s)

    def test_consensus_columns(self):
        self.assertEqual(ia.CONS_COLS[-3:], ["합의 답", "합의 사유", "스크린샷"])
        for c in ia.CONS_COLS:
            self.assertFalse(re.search(r"층|채점|정답|조건|run|label", c), c)
        src = open(ia.__file__, encoding="utf-8").read()
        for s in ("eval_key", "semantic_scores", "issue_table", "sample_selection.csv\"", "open(f\"{HE}/key"):
            self.assertNotIn(s, src)


if __name__ == "__main__":
    unittest.main()
