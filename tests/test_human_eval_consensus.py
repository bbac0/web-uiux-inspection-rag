"""합의 접수·human_final 시험 (실제 산출물 점검, API 없음)."""
import csv
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import human_eval_consensus as hc     # noqa: E402
from experiments.revision import human_eval_compare_robust as rob    # noqa: E402

HE = os.path.join(ROOT, "results", "revision", "human_eval")


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


class Final(unittest.TestCase):
    def test_contradiction_rule(self):
        r = {"판정 열": "코드에 존재", "합의 사유": "부재형이므로 코드에 있는 것으로 결정.", "합의 답": "아니오"}
        self.assertEqual(len(hc.contradictions(r)), 1)
        r["합의 답"] = "예"
        self.assertEqual(hc.contradictions(r), [])

    @unittest.skipUnless(os.path.exists(os.path.join(HE, "human_final_main.csv")), "산출물 없음")
    def test_human_final_matches_rule(self):
        cons = {(r["시트 구분"], r["issue_id"], hc.COL_BY_NAME[r["판정 열"]]): r["합의 답"]
                for r in rows(os.path.join(HE, "consensus", "disagreement_for_consensus_filled.csv"))}
        for st, fa, fb, out, n in (("본 평가", "rater_A/eval_sheet_A_filled.csv", "rater_B/eval_sheet_B_filled.csv",
                                    "human_final_main.csv", 444),
                                   ("추가 세트", "supp_label/rater_A_supp/eval_sheet_A_supp_filled.csv",
                                    "supp_label/rater_B_supp/eval_sheet_B_supp_filled.csv", "human_final_supp.csv", 107)):
            A, B = rob.read(os.path.join(HE, fa)), rob.read(os.path.join(HE, fb))
            F = rows(os.path.join(HE, out))
            self.assertEqual(len(F), n)
            self.assertEqual(list(F[0]), hc.FINAL_COLS)
            for f in F:
                i = f["issue_id"]
                self.assertEqual(f["source"], "A_B_consensus" if i in B else "A_only")
                for c, name in hc.FINAL_NAME.items():
                    want = A[i][c] if i not in B or A[i][c] == B[i][c] else cons[(st, i, c)]
                    self.assertEqual(f[name], want)
            self.assertEqual(sum(f["source"] == "A_only" for f in F), 240 if n == 444 else 0)

    def test_no_key_or_scoring_inputs(self):
        src = open(hc.__file__, encoding="utf-8").read()
        for s in ("eval_key", "supp_key", "semantic_scores", "issue_table", "}/key", "/key/"):
            self.assertNotIn(s, src)


if __name__ == "__main__":
    unittest.main()
