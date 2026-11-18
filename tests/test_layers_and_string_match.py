"""
라벨 층 로더, string_match 채점기, 이슈 단위 통합 표 테스트 (API 호출 없음).

  python -m unittest tests.test_layers_and_string_match -v
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import string_match, issue_table          # noqa: E402
from experiments.revision import label_layers as ll   # noqa: E402


class TestStringMatch(unittest.TestCase):
    def test_rule(self):
        self.assertTrue(string_match.match({"description": "'접속하기' 링크는 비표준", "suggestion": ""}))
        self.assertTrue(string_match.match({"description": "링크 문구", "suggestion": "'접속하기'를 '로그인'으로"}))
        self.assertFalse(string_match.match({"description": "접속 하기", "suggestion": "로그인"}))   # 정규화하지 않음
        self.assertFalse(string_match.match({"description": None, "suggestion": None}))
        self.assertEqual(string_match.RULE_STRING, "접속하기")


class TestIssueTable(unittest.TestCase):
    def test_pilot_rows(self):
        rows = issue_table.build_rows("pilot-02")
        self.assertEqual(len(rows), 32)
        self.assertEqual(list(rows[0].keys()), issue_table.COLUMNS)
        ids = [r["issue_id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        p077 = [r for r in rows if r["page_id"] == "page_077"]              # 용어 위반 페이지
        self.assertTrue(any(r["string_match_term"] == 1 for r in p077))
        self.assertTrue(all(r["semantic_pass1"] == "" for r in rows))       # 의미 채점 결과가 없으면 빈 칸


class TestLayers(unittest.TestCase):
    def test_counts(self):
        nom, _ = ll.load_labels("nominal")
        eff, _ = ll.load_labels("effective")
        self.assertEqual(len(nom), 1000)
        self.assertEqual(sum(nom.values()), 231)
        self.assertEqual(sum(eff.values()), 202)          # 버튼 26, 용어 3 차이
        gg, pending = ll.load_labels("guideline_grounded")
        self.assertTrue(all(v is None for (p, t), v in gg.items() if t == "Standard Terminology Violation"))
        self.assertNotIn("Standard Terminology Violation", pending)
        with self.assertRaises(ll.PendingDecisionError):
            if pending:
                ll.load_labels("guideline_grounded", strict=True)
            else:
                raise ll.PendingDecisionError("none pending")


if __name__ == "__main__":
    unittest.main()
