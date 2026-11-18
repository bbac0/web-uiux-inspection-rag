"""E9 동결 대상(정규식 규칙, 판정 프롬프트, 조건 입력, 테스트베드) 점검 (API 호출 없음)."""
import csv
import hashlib
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import e9_rules as r          # noqa: E402
from scoring import e9_judge_prompt as jp  # noqa: E402

I = lambda d, s="": {"description": "[http://localhost:8090/e9_001.html] " + d, "suggestion": s}


class Rules(unittest.TestCase):
    def test_e9_1(self):
        self.assertTrue(r.match_issue(I("공식 배너의 문구가 규정과 다릅니다."))["E9-1"])
        self.assertTrue(r.match_issue(I("상단 배너 텍스트가 변형됨"))["E9-1"])
        self.assertTrue(r.match_issue(I("상단 안내", "이 누리집은 대한민국 공식 전자정부 누리집입니다 로 고치세요"))["E9-1"])
        self.assertFalse(r.match_issue(I("배너 색이 다릅니다"))["E9-1"])
        inj = "이누리집은 대한민국 공식 전자정부 누리집입니다."
        self.assertTrue(r.match_issue(I('"이누리집은 대한민국 공식 전자정부 누리집입니다" 표기'), inj)["E9-1"])
        self.assertFalse(r.match_issue(I('"이누리집은 대한민국 공식 전자정부 누리집입니다" 표기'), None)["E9-1"])

    def test_e9_2(self):
        self.assertTrue(r.match_issue(I("공식배너 글자 크기가 14px 입니다"))["E9-2"])
        self.assertTrue(r.match_issue(I("Footer color is #000000"))["E9-2"])
        self.assertFalse(r.match_issue(I("푸터에 연락처가 없습니다"))["E9-2"])

    def test_e9_3_and_4(self):
        self.assertTrue(r.match_issue(I("로그인 링크가 회원 가입 화면으로 연결됩니다"))["E9-3"])
        self.assertTrue(r.match_issue(I("로그인 링크 href 가 /signup"))["E9-3"])
        self.assertFalse(r.match_issue(I("로그인 버튼이 작습니다"))["E9-3"])
        self.assertTrue(r.match_issue(I("모바일 화면에서 로그인 링크가 숨겨집니다"))["E9-4"])
        self.assertTrue(r.match_issue(I("로그인", "@media max-width 768px display: none 제거"))["E9-4"])
        self.assertFalse(r.match_issue(I("로그인 링크가 숨겨져 있습니다"))["E9-4"])

    def test_url_prefix_not_matched(self):
        # 접두어의 'e9_001' 등은 규칙에 쓰이지 않는다
        self.assertEqual(r.issue_text(I("본문")).startswith("본문"), True)

    def test_page_level(self):
        d = r.page_detections([I("배너 문구 변경"), I("로그인 링크가 signup 으로")])
        self.assertEqual(d, {"E9-1": 1, "E9-2": 0, "E9-3": 1, "E9-4": 0})


class JudgePrompt(unittest.TestCase):
    def test_prompt_equals_approved_draft(self):
        doc = open(os.path.join(ROOT, "docs", "e9_judge_prompt_draft.md"), encoding="utf-8").read()
        block = re.search(r"```text\n(.*?)\n```", doc, re.S).group(1)
        self.assertEqual(jp.PROMPT, block)

    def test_no_leak_tokens(self):
        p = jp.build_prompt(I("배너 문구", ""))
        self.assertNotIn("e9_001", p)
        self.assertNotIn("localhost", p)
        self.assertIn("(없음)", p)
        for bad in ("/signup", "웹사이트입니다", "홈페이지", "14px"):
            self.assertNotIn(bad, jp.PROMPT)

    def test_parse(self):
        ok = '{"banner_text": "아니오", "style_spec": "아니오", "login_destination": "아니오", "login_small_screen": "아니오", "none": true}'
        self.assertEqual(jp.parse(ok)[1], True)
        self.assertEqual(jp.parse(ok.replace("true", "false"))[1], False)        # 모순
        self.assertEqual(jp.parse(ok.replace('"아니오"', '"모름"', 1))[1], False)
        self.assertEqual(jp.parse("no json")[1], False)


class Inputs(unittest.TestCase):
    def test_condition_chunk_files(self):
        meta = json.load(open(os.path.join(ROOT, "testbed_e9", "dataset_metadata_e9.json"), encoding="utf-8"))
        pages = sorted(p["page_id"] for p in meta["pages"])
        sel = [s["chunk_id"] for s in json.load(open(os.path.join(ROOT, "results", "revision", "fixed_long_selection.json"),
                                                     encoding="utf-8"))["selected"]]
        for name, n in (("e9_related_clause_chunks.csv", 6), ("e9_fixed_long_chunks.csv", 9)):
            rows = list(csv.DictReader(open(os.path.join(ROOT, "results", "revision", "e9", name), encoding="utf-8")))
            by = {}
            for x in rows:
                by.setdefault(x["page_id"], []).append(x["chunk_id"])
            self.assertEqual(sorted(by), pages)
            self.assertEqual(len({tuple(v) for v in by.values()}), 1)               # 모든 페이지에 같은 청크·같은 순서
            self.assertEqual(len(next(iter(by.values()))), n)
            if n == 9:
                self.assertEqual(next(iter(by.values())), sel)

    def test_testbed_hashes(self):
        for row in csv.DictReader(open(os.path.join(ROOT, "results", "revision", "e9", "testbed_e9_manifest.csv"), encoding="utf-8")):
            self.assertEqual(hashlib.sha256(open(os.path.join(ROOT, row["file"]), "rb").read()).hexdigest(), row["sha256"])


if __name__ == "__main__":
    unittest.main()
