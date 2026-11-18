"""E9 사람 평가 비교·매핑 스크립트(가짜 CSV)와 시트 구성 점검. API 없음, 실제 평가 결과 미사용."""
import csv
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import e9_human_compare as ec    # noqa: E402
from experiments.revision import e9_human_sheets as es     # noqa: E402
from experiments.revision import e9_partial9_map as pm     # noqa: E402

E9 = os.path.join(ROOT, "results", "revision", "human_eval", "e9_eval")


def srow(i, b="아니오", s="아니오", l="아니오", note=""):
    return {"issue_id": i, "screenshot_path": f"shots/P{i}.png", "description": f"d{i}", "suggestion": f"s{i}",
            "banner-text": b, "spec-values": s, "login-address": l, "notes": note}


def krow(i, run, stratum, hit, **prim):
    r = {"issue_id": i, "run_id": run, "page_stratum": stratum, "regex_stratum": "hit" if hit else "miss"}
    for t in ("E9-1", "E9-2", "E9-3", "E9-4"):
        r[f"primary_{t}"] = str(prim.get(t.replace("-", "_"), 0))
        r[f"aux_{t}"] = r[f"primary_{t}"]
    return r


class Compare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def w(self, name, rows, cols):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            x = csv.DictWriter(f, fieldnames=cols); x.writeheader(); x.writerows(rows)
        return p

    def test_precision_pairs_hit_only(self):
        A = [srow("I1", b="예"), srow("I2"), srow("I3", b="예", s="아니오"), srow("I4", l="예")]
        K = [krow("I1", "rel", "E9-1", 1, E9_1=1), krow("I2", "rel", "E9-1", 1, E9_1=1),
             krow("I3", "rel", "E9-2", 1, E9_1=1, E9_2=1),           # 두 유형 → 쌍 두 개
             krow("I4", "nor", "control", 1, E9_3=1), krow("I5", "nor", "control", 0)]   # 안 걸림 → 무시
        kcols = list(K[0])
        a, k = self.w("a.csv", A, ec.COLS), self.w("k.csv", K, kcols)
        res = ec.compare(ec.read_sheet(a), ec.read_key(k))
        c, t = res["counts"], res["totals"]
        self.assertEqual((c[("rel", "E9-1", "E9-1")]["n"], c[("rel", "E9-1", "E9-1")]["yes"]), (2, 1))
        self.assertEqual((c[("rel", "E9-2", "E9-1")]["yes"], c[("rel", "E9-2", "E9-2")]["no"]), (1, 1))
        self.assertEqual((t[("rel", "E9-1")]["n"], t[("rel", "E9-1")]["yes"]), (3, 2))
        self.assertEqual(c[("nor", "control", "E9-3")]["yes"], 1)
        self.assertEqual(sorted((d["issue_id"], d["type"]) for d in res["no"]), [("I2", "E9-1"), ("I3", "E9-2")])
        out = os.path.join(self.tmp, "o.md")
        ec.main(["--a", a, "--key", k, "--out", out])
        md = open(out, encoding="utf-8").read()
        self.assertIn("3쌍 중 2쌍", md)
        self.assertNotIn("재평가 일치", md)
        self.assertNotIn("안 걸림", md)
        with self.assertRaises(SystemExit):
            ec.main(["--a", a, "--key", k, "--out", out])
        with self.assertRaises(SystemExit):
            ec.main(["--a", a, "--key", k, "--retest", a, "--out", out + "2"])

    def test_rejects_bad_values_and_mismatch(self):
        a = self.w("a.csv", [srow("I1", b="판단 불가")], ec.COLS)
        with self.assertRaises(SystemExit):
            ec.read_sheet(a)
        a2 = self.w("a2.csv", [srow("I1")], ec.COLS)
        k2 = self.w("k2.csv", [krow("I9", "rel", "E9-2", 1, E9_2=1)], list(krow("I9", "rel", "E9-2", 0)))
        with self.assertRaises(SystemExit):
            ec.compare(ec.read_sheet(a2), ec.read_key(k2))


@unittest.skipUnless(os.path.exists(os.path.join(E9, "rater_A_e9")), "시트 없음")
class Sheets(unittest.TestCase):
    def test_sheet_blank_and_no_key_columns(self):
        rows = list(csv.DictReader(open(os.path.join(E9, "rater_A_e9", "eval_sheet_A_e9.csv"), encoding="utf-8-sig")))
        self.assertEqual(len(rows), 138)
        self.assertEqual(list(rows[0]), es.SHEET_COLS)
        self.assertTrue(all(r[c] == "" for r in rows for c in es.JUDGE + ["notes"]))
        rt = list(csv.DictReader(open(os.path.join(E9, "rater_A_e9_retest", "eval_sheet_A_e9_retest.csv"),
                                      encoding="utf-8-sig")))
        self.assertEqual(len(rt), 20)
        self.assertTrue({r["issue_id"] for r in rt} <= {r["issue_id"] for r in rows})
        self.assertFalse(set(os.listdir(os.path.join(E9, "rater_A_e9", "shots"))) &
                         set(os.listdir(os.path.join(E9, "rater_A_e9_retest", "shots"))))
        for name in ("rater_A_e9", "rater_A_e9_retest"):
            self.assertEqual(sorted(os.listdir(os.path.join(E9, name)))[:2], ["e9_rater_guidelines.md", "eval_sheet_" +
                                                                             name.replace("rater_", "") + ".csv"])
            html = open(os.path.join(E9, name, f"viewer_{name.replace('rater_', '')}.html"), encoding="utf-8").read()
            self.assertIn('const KEY = "human_eval_' + name.replace("rater_", "") + '"', html)
            data = json.loads(re.search(r"const ROWS = (.*?);\n", html).group(1).replace("<\\/", "</"))
            self.assertEqual({k for d in data for k in d}, set(es.SHEET_COLS[:4]))
            self.assertNotRegex(html, r"e9_\d{3}|localhost|related|norag|primary_|page_stratum")

    def test_leak_audit_zero(self):
        self.assertIn("누출로 판단한 항목: 0건", open(os.path.join(E9, "leak_audit_e9.md"), encoding="utf-8").read())


class Partial9(unittest.TestCase):
    def test_mapping_carries_hit_and_excludes_rest(self):
        a138 = [srow(f"I{i}") for i in range(1, 7)]
        hit52 = [{**srow(i, b="", s="", l=""), "screenshot_path": "shots/Pnew.png"} for i in ("I5", "I2", "I4")]
        part = [srow("I2", b="예", s="아니오", l="아니오", note="x"), srow("I3", b="아니오"),
                srow("I4", b="", s="예", l=""), srow("I6", b="", s="", l="")]
        entered, carried, excluded, prefill, incomplete = pm.mapping(part, hit52, a138)
        self.assertEqual(len(entered), 3)
        self.assertEqual(sorted(carried), ["I2", "I4"])
        self.assertEqual([r["issue_id"] for r in excluded], ["I3"])
        self.assertEqual([r["issue_id"] for r in prefill], ["I5", "I2", "I4"])
        self.assertEqual((prefill[1]["banner-text"], prefill[1]["notes"], prefill[1]["screenshot_path"]),
                         ("예", "x", "shots/Pnew.png"))
        self.assertEqual(prefill[0]["banner-text"], "")
        self.assertEqual(incomplete, ["I4"])
        with self.assertRaises(SystemExit):
            pm.mapping([{**srow("I2"), "description": "다른 문장"}], hit52, a138)
        with self.assertRaises(SystemExit):
            pm.mapping([srow("I99")], hit52, a138)


@unittest.skipUnless(os.path.exists(os.path.join(E9, "rater_A_e9_hit52")), "시트 없음")
class Hit52(unittest.TestCase):
    def test_hit52_sheet(self):
        d = os.path.join(E9, "rater_A_e9_hit52")
        rows = list(csv.DictReader(open(os.path.join(d, "eval_sheet_A_e9_hit52.csv"), encoding="utf-8-sig")))
        self.assertEqual(len(rows), 52)
        self.assertEqual(list(rows[0]), es.SHEET_COLS)
        self.assertTrue(all(r[c] == "" for r in rows for c in es.JUDGE + ["notes"]))
        key = list(csv.DictReader(open(os.path.join(E9, "key", "e9_key.csv"), encoding="utf-8-sig")))
        self.assertEqual({r["issue_id"] for r in rows}, {r["issue_id"] for r in key if r["regex_stratum"] == "hit"})
        old = set()
        for n in ("rater_A_e9", "rater_A_e9_retest"):
            old |= set(os.listdir(os.path.join(E9, n, "shots")))
        self.assertFalse(old & set(os.listdir(os.path.join(d, "shots"))))
        html = open(os.path.join(d, "viewer_A_e9_hit52.html"), encoding="utf-8").read()
        self.assertIn('const KEY = "human_eval_A_e9_hit52"', html)
        self.assertNotRegex(html, r"e9_\d{3}|localhost|related|norag|primary_|page_stratum")
        self.assertIn("누출로 판단한 항목: 0건", open(os.path.join(E9, "leak_audit_e9_hit52.md"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
