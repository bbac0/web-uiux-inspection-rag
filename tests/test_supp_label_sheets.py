"""추가 평가 세트 시트·뷰어 시험 (API 없음). 가림, 순서, 스크린샷 크기, 저장 키, 불러오기 거부."""
import csv
import json
import os
import re
import struct
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import build_human_eval as bhe    # noqa: E402

SL = os.path.join(ROOT, "results", "revision", "human_eval", "supp_label")
SIDES = {"A": "rater_A_supp", "B": "rater_B_supp"}


def sheet(side):
    return list(csv.DictReader(open(os.path.join(SL, SIDES[side], f"eval_sheet_{side}_supp.csv"), encoding="utf-8-sig")))


class SuppSheets(unittest.TestCase):
    def test_same_set_different_order_matches_key(self):
        a, b = sheet("A"), sheet("B")
        self.assertEqual(len(a), 107)
        self.assertEqual({r["issue_id"] for r in a}, {r["issue_id"] for r in b})
        self.assertNotEqual([r["issue_id"] for r in a], [r["issue_id"] for r in b])
        key = {r["issue_id"]: r for r in csv.DictReader(open(os.path.join(SL, "key", "supp_key.csv"), encoding="utf-8-sig"))}
        self.assertEqual([r["issue_id"] for r in a], sorted(key, key=lambda i: int(key[i]["pos_A"])))
        self.assertEqual([r["issue_id"] for r in b], sorted(key, key=lambda i: int(key[i]["pos_B"])))
        self.assertEqual(sorted(key, key=lambda i: int(key[i]["base_order"])),
                         [r["issue_id"] for r in csv.DictReader(open(os.path.join(SL, "key", "supp_key.csv"),
                                                                     encoding="utf-8-sig"))])
        old = {r["issue_id"] for r in csv.DictReader(open(os.path.join(SL, "..", "key", "eval_key.csv"), encoding="utf-8-sig"))}
        self.assertFalse(old & set(key))

    def test_no_forbidden_strings_outside_issue_text(self):
        for side, d in SIDES.items():
            for r in sheet(side):
                for k, v in r.items():
                    if k not in ("description", "suggestion"):
                        for pat in bhe.FORBIDDEN + [r"E4-mobile", r"stratum", r"S[123]\b"]:
                            self.assertIsNone(re.search(pat, v), (k, v))
            html = open(os.path.join(SL, d, f"viewer_{side}_supp.html"), encoding="utf-8").read()
            m_rows = re.search(r"const ROWS = (.*?);\n", html)
            m_src = re.search(r"const SRC = (.*?);\n", html)
            code = html[:m_rows.start()] + html[m_src.end():]
            for pat in bhe.FORBIDDEN:
                self.assertIsNone(re.search(pat, code), pat)
            for r in json.loads(m_rows.group(1).replace("<\\/", "</")):
                self.assertEqual(set(r), set(bhe.VIEW_FIELDS))
            self.assertIn(f'const KEY = "human_eval_{side}_supp"', html)
            self.assertIn("<!-- csv-import v1 -->", html)

    def test_screenshots_and_guidelines(self):
        guide = open(os.path.join(ROOT, "docs", "rater_guidelines_v2.md"), encoding="utf-8").read()
        for side, d in SIDES.items():
            shots = os.listdir(os.path.join(SL, d, "shots"))
            self.assertEqual({f"shots/{s}" for s in shots}, {r["screenshot_path"] for r in sheet(side)})
            for s in shots:
                self.assertRegex(s, r"^P[0-9a-f]{10}\.png$")
                b = open(os.path.join(SL, d, "shots", s), "rb").read(24)
                self.assertEqual(struct.unpack(">II", b[16:24]), (1280, 800))
            self.assertEqual(open(os.path.join(SL, d, "rater_guidelines.md"), encoding="utf-8").read(), guide)

    def test_howto_wording(self):
        t = open(os.path.join(SL, "supp_howto.md"), encoding="utf-8").read()
        for w in ("레이블 관련", "용어", "접속하기", "보충", "E4", "모바일"):
            self.assertNotIn(w, t)
        self.assertIn("추가 평가 세트", t)
        self.assertIn("viewer_howto.md", t)


try:
    from playwright.sync_api import sync_playwright
    HAVE_PW = True
except Exception:
    HAVE_PW = False


@unittest.skipUnless(HAVE_PW, "playwright missing")
class SuppViewerImport(unittest.TestCase):
    def test_rejects_main_sheet_and_other_rater_csv(self):
        with sync_playwright() as pw:
            br = pw.chromium.launch(headless=True)
            page = br.new_page()
            reqs = []
            page.on("request", lambda r: reqs.append(r.url))
            page.goto("file:///" + os.path.join(SL, "rater_A_supp", "viewer_A_supp.html").replace("\\", "/"))
            self.assertIn("1 / 107", page.inner_text("#pos"))
            for p in (os.path.join(SL, "..", "rater_A", "eval_sheet_A.csv"),):
                page.set_input_files("#importFile", p); page.wait_for_timeout(300)
                self.assertIn("거부", page.inner_text("#msg"))
            # 같은 시트 CSV(빈 칸)는 받는다
            page.set_input_files("#importFile", os.path.join(SL, "rater_A_supp", "eval_sheet_A_supp.csv"))
            page.wait_for_timeout(300)
            self.assertIn("불러오기 완료", page.inner_text("#msg"))
            br.close()
            self.assertEqual([u for u in reqs if not u.startswith(("file:", "blob:", "data:"))], [])


if __name__ == "__main__":
    unittest.main()
