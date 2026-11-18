"""평가 뷰어 CSV 불러오기 기능 시험 (실제 Chromium, 헤드리스, 로컬 파일만, API 없음).

- 변경 전 뷰어(백업)로 입력 → 같은 자리의 파일을 변경 후 뷰어로 바꿈 → 입력이 그대로 보임 (세 뷰어 모두)
- 내보내기 → 저장소 삭제 → 불러오기로 복원
- 충돌: 기본(덮어쓰지 않음) / 덮어쓰기
- 거부: 다른 시트 CSV, 열 구성이 다른 CSV, 허용되지 않은 값
- 외부 네트워크 요청 없음
"""
import csv
import io
import json
import os
import shutil
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HE = os.path.join(ROOT, "results", "revision", "human_eval")
BACKUP = os.path.join(HE, "viewer_backup_before_import")
SIDES = {"pilot": ("pilot_rater", "viewer_pilot.html", "eval_sheet_pilot.csv"),
         "A": ("rater_A", "viewer_A.html", "eval_sheet_A.csv"),
         "B": ("rater_B", "viewer_B.html", "eval_sheet_B.csv")}

try:
    from playwright.sync_api import sync_playwright
    HAVE = os.path.isdir(BACKUP)
except Exception:
    HAVE = False


@unittest.skipUnless(HAVE, "playwright or backup missing")
class ViewerImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.br = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.br.close(); cls.pw.stop()

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ctx = self.br.new_context(accept_downloads=True)
        self.page = self.ctx.new_page()
        self.reqs = []
        self.page.on("request", lambda r: self.reqs.append(r.url))

    def tearDown(self):
        self.ctx.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.assertEqual([u for u in self.reqs if not u.startswith(("file:", "blob:", "data:"))], [])

    # ------------------------------------------------ helpers
    def place(self, src):
        dst = os.path.join(self.tmp, "viewer.html")
        shutil.copyfile(src, dst)
        return "file:///" + dst.replace("\\", "/")

    def store(self, side):
        return json.loads(self.page.evaluate(f"() => localStorage.getItem('human_eval_{side}') || '{{}}'"))

    def enter(self, n, cat, ex, vis, login, note=""):
        p = self.page
        p.fill("#jump", str(n)); p.dispatch_event("#jump", "change")
        p.select_option("#rater_category", cat)
        p.check(f'input[name=exists_in_code][value="{ex}"]')
        p.check(f'input[name=visible_on_screen][value="{vis}"]')
        p.check(f'input[name=login_link_label_concern][value="{login}"]')
        if note:
            p.fill("#rater_notes", note)

    def export(self):
        with self.page.expect_download() as d:
            self.page.click("#export")
        path = os.path.join(self.tmp, d.value.suggested_filename)
        d.value.save_as(path)
        return path

    def do_import(self, path):
        self.page.set_input_files("#importFile", path)
        self.page.wait_for_timeout(300)
        return self.page.inner_text("#msg")

    # ------------------------------------------------ tests
    def test_old_inputs_survive_upgrade_all_viewers(self):
        for side, (d, fn, _) in SIDES.items():
            url = self.place(os.path.join(BACKUP, fn))
            self.page.goto(url)
            self.enter(1, "표준 용어 위반", "예", "아니오", "예", "메모 \"따옴표\", 쉼표")
            self.enter(2, "해당 없음", "판단 불가", "예", "아니오")
            before = self.store(side)
            self.assertEqual(self.page.evaluate("() => document.getElementById('importBtn')"), None)   # 변경 전 뷰어
            self.place(os.path.join(HE, d, fn))                                                         # 같은 자리 교체
            self.page.reload()
            self.assertIsNotNone(self.page.query_selector("#importBtn"))
            self.assertEqual(self.store(side), before)
            self.page.fill("#jump", "1"); self.page.dispatch_event("#jump", "change")
            self.assertEqual(self.page.input_value("#rater_category"), "표준 용어 위반")
            self.assertTrue(self.page.is_checked('input[name=exists_in_code][value="예"]'))
            self.assertEqual(self.page.input_value("#rater_notes"), "메모 \"따옴표\", 쉼표")
            self.assertIn("완료 2건", self.page.inner_text("#prog"))
            self.page.evaluate("() => localStorage.clear()")

    def test_export_clear_import_restores(self):
        self.page.goto(self.place(os.path.join(HE, "pilot_rater", "viewer_pilot.html")))
        self.enter(3, "명도 대비 부족", "예", "예", "아니오", "줄\n바꿈 메모")
        self.enter(5, "중복 ID", "예", "아니오", "아니오")
        before = {k: v for k, v in self.store("pilot").items() if v}
        path = self.export()
        self.page.evaluate("() => localStorage.clear()"); self.page.reload()
        self.assertEqual({k: v for k, v in self.store("pilot").items() if v}, {})
        m = self.do_import(path)
        self.assertIn("불러오기 완료", m)
        self.assertEqual({k: v for k, v in self.store("pilot").items() if v}, before)
        self.assertIn("완료 2건", self.page.inner_text("#prog"))

    def test_conflict_default_keeps_then_overwrite(self):
        self.page.goto(self.place(os.path.join(HE, "pilot_rater", "viewer_pilot.html")))
        self.enter(1, "버튼 영역 잘림", "예", "예", "아니오")
        path = self.export()
        iid = self.page.inner_text("#iid")
        self.enter(1, "해당 없음", "예", "예", "아니오")                        # CSV 와 다르게 바꿈
        self.do_import(path)
        self.assertTrue(self.page.is_visible("#modal"))
        self.assertEqual(self.page.evaluate("() => document.activeElement.id"), "keepBtn")   # 기본 = 덮어쓰지 않음
        self.page.click("#keepBtn")
        self.assertEqual(self.store("pilot")[iid]["rater_category"], "해당 없음")
        self.assertIn("기존 유지 1", self.page.inner_text("#msg"))
        self.do_import(path)
        self.page.click("#overBtn")
        self.assertEqual(self.store("pilot")[iid]["rater_category"], "버튼 영역 잘림")

    def test_rejects_other_sheet_columns_and_values(self):
        self.page.goto(self.place(os.path.join(HE, "pilot_rater", "viewer_pilot.html")))
        self.enter(1, "중복 ID", "예", "아니오", "아니오")
        before = self.store("pilot")
        # 다른 시트(B 시트 CSV, 같은 열 구성)
        m = self.do_import(os.path.join(HE, "rater_B", "eval_sheet_B.csv"))
        self.assertIn("거부", m); self.assertEqual(self.store("pilot"), before)
        # A 시트 CSV (pilot 이슈를 모두 포함하지만 집합이 다름)
        m = self.do_import(os.path.join(HE, "rater_A", "eval_sheet_A.csv"))
        self.assertIn("거부", m); self.assertEqual(self.store("pilot"), before)
        # 열 구성이 다른 파일
        rows = list(csv.DictReader(open(os.path.join(HE, "pilot_rater", "eval_sheet_pilot.csv"), encoding="utf-8-sig")))
        bad = os.path.join(self.tmp, "bad_cols.csv")
        with open(bad, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["issue_id", "rater_category"]); [w.writerow([r["issue_id"], ""]) for r in rows]
        self.assertIn("열 구성", self.do_import(bad)); self.assertEqual(self.store("pilot"), before)
        # 허용되지 않은 값
        path = self.export()
        txt = open(path, encoding="utf-8-sig").read().replace(",예,", ",maybe,", 1)
        badv = os.path.join(self.tmp, "bad_val.csv")
        open(badv, "w", encoding="utf-8").write(txt)
        self.assertIn("허용되지 않은 값", self.do_import(badv)); self.assertEqual(self.store("pilot"), before)

    def test_key_and_data_unchanged_vs_backup(self):
        from experiments.revision import viewer_add_import as vai
        for side, (d, fn, _) in SIDES.items():
            old = open(os.path.join(BACKUP, fn), encoding="utf-8").read()
            new = open(os.path.join(HE, d, fn), encoding="utf-8").read()
            self.assertEqual(vai.invariant(old), vai.invariant(new))
            self.assertIn(f'const KEY = "human_eval_{side}"', new)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ROOT)
    unittest.main()
