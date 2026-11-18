"""E9 v3 입력 수정(c1 국기 그림, c2 portal_main 본문 문구)에서 새로 들어간 문자열이 정규식 규칙의 키워드를 건드리지 않는지 (API 없음)."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import e9_rules as r                     # noqa: E402
from experiments.revision import e9_generate as g     # noqa: E402

NEW = ["주요 소식", "main-notice", "대한민국 국기", "/flag.svg"]
WORDS = ["로그인", "헤더", "푸터", "배너", "회원가입"]
PATTERNS = {n: getattr(r, n) for n in dir(r) if isinstance(getattr(r, n), re.Pattern) and n != "URL_PREFIX_RE"}


class NewStrings(unittest.TestCase):
    def test_patterns_cover_all_rules(self):
        self.assertEqual(sorted(PATTERNS), sorted(["E9_1_TOPIC", "E9_1_ASPECT", "E9_2_REGION", "E9_2_PROP", "E9_3_A", "E9_3_B",
                                                   "E9_4_A", "E9_4_B", "E9_4_C"]))

    def test_no_rule_pattern_matches(self):
        for s in NEW:
            for name, p in PATTERNS.items():
                self.assertIsNone(p.search(s), f"{name} matches {s!r}")
            for w in WORDS:
                self.assertNotIn(w, s)
            self.assertNotIn(r.REQUIRED_BANNER, s)

    def test_new_strings_are_in_generated_pages(self):
        tpl = g.load_templates()
        self.assertIn('<div id="main-notice">주요 소식</div>', tpl["portal_main"]["main"])
        self.assertNotIn("배너", tpl["portal_main"]["main"])
        page = g.build_page("t", tpl["portal_main"]["main"], g.BASE_RULES, g.BANNER_TEXT)
        self.assertIn('<img class="flag" src="/flag.svg" alt="대한민국 국기" width="24" height="16">', page)
        self.assertNotIn("#D8D8D8}", g.css([x for x in g.BASE_RULES if x[0] == ".gov-banner .flag"]))

    def test_flag_svg(self):
        svg = g.flag_svg()
        self.assertTrue(svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"'))
        self.assertIn('width="24" height="16"', svg)
        self.assertEqual(svg, g.flag_svg())          # 결정적


if __name__ == "__main__":
    unittest.main()
