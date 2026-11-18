"""E9 보조 분석 규칙과 주/보조 비교 표 스크립트 점검 (API 호출 없음)."""
import csv
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scoring import e9_rules as primary      # noqa: E402
from scoring import e9_rules_aux as aux      # noqa: E402
from experiments.revision import e9_regex_table as tbl   # noqa: E402

I = lambda pid, d, s="": {"description": f"[http://localhost:8090/{pid}.html] {d}", "suggestion": s}
EXAMPLE = '안내 문장 "대한민국 공식 전자정부 웹사이트입니다" 는 미준수 예시'   # 조항 청크의 미준수 사례 문구 인용


class AuxRule(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(len(aux.VARIANTS), 6)

    def test_difference_only_on_variant_quote_without_topic(self):
        i = I("e9_090", "상단 영역: \"대한민국 공식 전자정부 웹사이트입니다\" 표기 확인 필요")
        self.assertFalse(primary.match_issue(i, None)["E9-1"])      # 대조군: 주 지표는 세지 않음
        self.assertTrue(aux.match_issue(i)["E9-1"])                 # 보조: 모든 페이지에 변형 문구 적용
        j = I("e9_090", "배너 문구가 다릅니다")
        self.assertEqual(primary.match_issue(j, None), aux.match_issue(j))   # 주제어 절은 같음

    def test_other_types_identical(self):
        for d in ("로그인 링크가 회원가입으로 연결", "푸터 글자 크기 15px", "모바일에서 로그인 숨김 768"):
            i = I("e9_001", d)
            p, a = primary.match_issue(i, None), aux.match_issue(i)
            self.assertEqual({k: p[k] for k in ("E9-2", "E9-3", "E9-4")}, {k: a[k] for k in ("E9-2", "E9-3", "E9-4")})


class Table(unittest.TestCase):
    def test_side_by_side(self):
        meta = json.load(open(os.path.join(ROOT, "testbed_e9", "dataset_metadata_e9.json"), encoding="utf-8"))
        pages = {p["page_id"]: p for p in meta["pages"]}
        ctrl = sorted(p for p, m in pages.items() if m["defect_id"] is None)[0]
        e91 = sorted(p for p, m in pages.items() if m["defect_id"] == "E9-1")[0]
        tmp = tempfile.mkdtemp()
        try:
            d = os.path.join(tmp, "runs", "mock-related")
            os.makedirs(d)
            json.dump({"condition": "E9-related"}, open(os.path.join(d, "run_meta.json"), "w", encoding="utf-8"))
            with open(os.path.join(d, "reports.jsonl"), "w", encoding="utf-8") as f:
                for pid in pages:
                    issues = []
                    if pid == ctrl:
                        issues = [I(pid, "상단 표기 " + aux.VARIANTS[0])]
                    if pid == e91:
                        issues = [I(pid, "표기: " + pages[pid]["injected_string"])]
                    f.write(json.dumps({"page_id": pid, "status": "ok", "report": {"issues": issues}}, ensure_ascii=False) + "\n")
            out = os.path.join(tmp, "out")
            self.assertEqual(tbl.main(["--runs-base", os.path.join(tmp, "runs"), "--out", out]), 0)
            rows = list(csv.DictReader(open(os.path.join(out, "e9_regex_primary_vs_aux.csv"), encoding="utf-8")))
            r = {(x["type"], x["rule"]): x for x in rows}
            self.assertEqual(r[("E9-1", "primary")]["detected"], "1")
            self.assertEqual(r[("E9-1", "aux")]["detected"], "1")
            self.assertEqual(r[("E9-1", "primary")]["control_detected"], "0")
            self.assertEqual(r[("E9-1", "aux")]["control_detected"], "1")
            self.assertEqual({x["rule"] for x in rows}, {"primary", "aux"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
