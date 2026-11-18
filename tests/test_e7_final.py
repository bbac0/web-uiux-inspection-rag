"""E7 최종 산출물 점검: 키워드·string_match 가 기존 E7 과 같은지 (API 없음)."""
import csv
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E7 = os.path.join(ROOT, "results", "revision", "e7")
FIN = os.path.join(ROOT, "results", "revision", "e7_final")


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


@unittest.skipUnless(os.path.exists(FIN), "e7_final 없음")
class E7Final(unittest.TestCase):
    def test_keyword_reproduces_e7(self):
        old = {(r["run"], r["scorer"], r["label"], r["type"]): r for r in rows(os.path.join(E7, "cell_metrics.csv"))}
        new = {(r["run"], r["scorer"], r["label"], r["type"]): r for r in rows(os.path.join(FIN, "cell_metrics.csv"))}
        for k, r in old.items():
            for c in ("TP", "FP", "FN", "TN", "mcc", "mcc_ci_lo", "mcc_ci_hi"):
                self.assertEqual(new[k][c], r[c], (k, c))

    def test_pairs_reproduce_e7(self):
        old = rows(os.path.join(E7, "paired_cluster_bootstrap.csv"))
        new = {(r["comparison"], r["scorer"], r["label"], r["type"]): r
               for r in rows(os.path.join(FIN, "paired_cluster_bootstrap.csv"))}
        for r in old:
            n = new[(r["comparison"], r["scorer"], r["label"], r["type"])]
            for m in ("mcc", "precision", "recall", "specificity"):
                self.assertEqual((n[f"{m}_diff"], n[f"{m}_diff_ci_lo"], n[f"{m}_diff_ci_hi"]),
                                 (r[f"{m}_diff"], r[f"{m}_diff_ci_lo"], r[f"{m}_diff_ci_hi"]))

    def test_meta_zero_mismatch_and_semantic_present(self):
        m = json.load(open(os.path.join(FIN, "e7_final_meta.json"), encoding="utf-8"))
        self.assertTrue(all(v["keyword"] == 0 and v["string_match"] == 0
                            for v in m["keyword_string_match_vs_e7_mismatch_cells"].values()))
        self.assertTrue(all(m["has_semantic"].values()))
        scorers = {r["scorer"] for r in rows(os.path.join(FIN, "cell_metrics.csv"))}
        self.assertEqual(scorers, {"sem_merged", "sem_orig", "keyword", "string_match"})
        mod = rows(os.path.join(FIN, "modality_keyword_reference.csv"))
        self.assertEqual({r["scorer"] for r in mod}, {"keyword", "string_match"})
        self.assertTrue(all("참고용" in r["note"] for r in mod))


if __name__ == "__main__":
    unittest.main()
