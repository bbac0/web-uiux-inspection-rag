"""사람 평가 시트·뷰어 가림 테스트 (API 없음). 생성물이 없으면 생성물 검사는 건너뛰고 뷰어 생성 함수만 시험한다."""
import csv
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import build_human_eval as bhe     # noqa: E402
from experiments.revision import make_eval_sheets as mes     # noqa: E402

OUT = os.path.join(ROOT, "results", "revision", "human_eval")
FORB = re.compile("|".join(bhe.FORBIDDEN))
HAVE = os.path.isdir(os.path.join(OUT, "rater_A"))


def viewer_data(path):
    s = open(path, encoding="utf-8").read()
    rows = json.loads(re.search(r"const ROWS = (.*?);\n", s).group(1).replace("<\\/", "</"))
    src = json.loads(re.search(r"const SRC = (.*?);\n", s).group(1).replace("<\\/", "</"))
    return s, rows, src


class ViewerUnit(unittest.TestCase):
    def test_viewer_only_view_fields_and_no_network(self):
        rows = [{"issue_id": "Iabc", "screenshot_path": "shots/Pxyz.png", "description": "d </script> x", "suggestion": "s",
                 "rater_category": "", "_page": "page_001", "stratum": "terminology"}]
        out = bhe.make_viewer("T", rows, {"shots/Pxyz.png": "<html>ok</html>", "shots/Pother.png": "<b>x</b>"})
        self.assertNotIn("page_001", out)
        self.assertNotIn("terminology", out)
        self.assertNotIn("Pother", out)                                 # 다른 페이지 HTML 은 넣지 않음
        self.assertNotIn("</script> x", out)                            # 스크립트 탈출 방지
        self.assertIsNone(re.search(r"(https?:)?//[a-z0-9.-]+\.[a-z]{2,}", out.replace("http://www.w3.org", "")))
        self.assertNotRegex(out, r"<(script|link|img)[^>]+(src|href)=\"https?:")


@unittest.skipUnless(HAVE, "human_eval not generated")
class GeneratedBlinding(unittest.TestCase):
    def files(self, side):
        d = os.path.join(OUT, f"rater_{side}")
        return d, sorted(os.listdir(d))

    def test_rater_folders_have_only_allowed_files(self):
        for side in ("A", "B"):
            d, names = self.files(side)
            self.assertEqual(names, sorted([f"eval_sheet_{side}.csv", f"viewer_{side}.html", "rater_guidelines.md", "shots"]))
            self.assertTrue(all(re.fullmatch(r"P[0-9a-f]{10}\.png", f) for f in os.listdir(os.path.join(d, "shots"))))

    def test_sheet_columns_and_empty_inputs(self):
        for side in ("A", "B"):
            rows = list(csv.DictReader(open(os.path.join(OUT, f"rater_{side}", f"eval_sheet_{side}.csv"), encoding="utf-8-sig")))
            self.assertEqual(list(rows[0].keys()), mes.SHEET_COLS)
            for r in rows:
                self.assertRegex(r["issue_id"], r"^I[0-9a-f]{10}$")
                self.assertRegex(r["screenshot_path"], r"^shots/P[0-9a-f]{10}\.png$")
                self.assertTrue(all(r[k] == "" for k in bhe.INPUT_FIELDS))
                self.assertTrue(os.path.exists(os.path.join(OUT, f"rater_{side}", r["screenshot_path"])))

    def test_no_forbidden_strings_in_sheets_and_viewers(self):
        for side in ("A", "B"):
            for f in (f"eval_sheet_{side}.csv", f"viewer_{side}.html"):
                text = open(os.path.join(OUT, f"rater_{side}", f), encoding="utf-8-sig").read()
                m = FORB.search(text)
                self.assertIsNone(m, f"{f}: {m.group(0) if m else ''}")

    def test_viewer_rows_match_sheet_and_carry_only_view_fields(self):
        for side in ("A", "B"):
            _, rows, src = viewer_data(os.path.join(OUT, f"rater_{side}", f"viewer_{side}.html"))
            sheet = list(csv.DictReader(open(os.path.join(OUT, f"rater_{side}", f"eval_sheet_{side}.csv"), encoding="utf-8-sig")))
            self.assertEqual([r["issue_id"] for r in rows], [r["issue_id"] for r in sheet])
            self.assertTrue(all(set(r) == set(bhe.VIEW_FIELDS) for r in rows))
            self.assertEqual(set(src), {r["screenshot_path"] for r in rows})

    def test_b_subset_of_a_and_orders_differ(self):
        a = [r["issue_id"] for r in csv.DictReader(open(os.path.join(OUT, "rater_A", "eval_sheet_A.csv"), encoding="utf-8-sig"))]
        b = [r["issue_id"] for r in csv.DictReader(open(os.path.join(OUT, "rater_B", "eval_sheet_B.csv"), encoding="utf-8-sig"))]
        self.assertTrue(set(b) < set(a))
        self.assertNotEqual(b, [x for x in a if x in set(b)])         # 서로 다른 시드로 섞임

    def test_key_separate_and_complete(self):
        key = list(csv.DictReader(open(os.path.join(OUT, "key", "eval_key.csv"), encoding="utf-8")))
        a = {r["issue_id"] for r in csv.DictReader(open(os.path.join(OUT, "rater_A", "eval_sheet_A.csv"), encoding="utf-8-sig"))}
        self.assertEqual({r["issue_id"] for r in key}, a)
        for side in ("A", "B"):
            self.assertFalse(any("key" in f.lower() or "manifest" in f.lower() for f in os.listdir(os.path.join(OUT, f"rater_{side}"))))

    def test_sampling_uses_only_labels_and_seeds(self):
        m = json.load(open(os.path.join(OUT, "key", "sampling_manifest.json"), encoding="utf-8"))
        self.assertEqual((m["seed_a"], m["seed_b"]), (20261112, 20261113))
        nom, _, _ = mes.load_labels(os.path.join(ROOT, "testbed_200", "dataset_metadata.json"),
                                    os.path.join(ROOT, "results", "revision", "ground_truth.csv"))
        a = mes.select_pages_a(nom, 20261112)
        b = mes.select_pages_b(a, 20261113)
        self.assertEqual((len(a), len(b)), (m["pages_A"], m["pages_B"]))
        key = list(csv.DictReader(open(os.path.join(OUT, "key", "eval_key.csv"), encoding="utf-8")))
        self.assertEqual({r["page_id"] for r in key if r["in_sheet_B"] == "1"}, {p for p in b if any(r["page_id"] == p for r in key)})


if __name__ == "__main__":
    unittest.main()
