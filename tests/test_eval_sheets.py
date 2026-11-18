"""
사람 평가 시트 생성 스크립트 단위 테스트 (가짜 run 데이터, API 호출 없음).

  python -m unittest tests.test_eval_sheets -v
"""
import csv
import json
import os
import random
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.revision import make_eval_sheets as m   # noqa: E402

META = os.path.join(ROOT, "testbed_200", "dataset_metadata.json")
GT = os.path.join(ROOT, "results", "revision", "ground_truth.csv")


def fake_run(base, run_id="FAKE-R1", seed=7):
    """200페이지 가짜 reports.jsonl + 스크린샷. 페이지마다 대상 이슈 0~4개와 /login 이슈 1개."""
    d = os.path.join(base, run_id)
    os.makedirs(os.path.join(d, "shots"))
    rng = random.Random(seed)
    meta = json.load(open(META, encoding="utf-8"))
    with open(os.path.join(d, "reports.jsonl"), "w", encoding="utf-8") as f:
        for p in meta:
            pid = p["page_id"][:-5]
            url = f"http://localhost:8080/testbed_200/{pid}.html"
            issues = [{"category": "기술", "description": f"[{url}] 가짜 이슈 {k}: 버튼 높이가 2px 입니다.",
                       "suggestion": "높이를 늘리세요.", "source_file": "gov_guide.pdf", "page_number": [15]}
                      for k in range(rng.randint(0, 4))]
            issues.append({"category": "운영", "description": "[http://localhost:8080/login] 404 페이지", "suggestion": "-"})
            f.write(json.dumps({"page_id": pid, "status": "ok", "report": {"issues": issues}}, ensure_ascii=False) + "\n")
            open(os.path.join(d, "shots", f"{pid}.png"), "wb").write(b"png")
    return run_id


class TestEvalSheets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.runs = os.path.join(self.tmp, "runs")
        self.run_id = fake_run(self.runs)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, out="out", a=101, b=202):
        o = os.path.join(self.tmp, out)
        man = m.build(self.run_id, a, b, o, self.runs, META, GT)
        read = lambda n: list(csv.DictReader(open(os.path.join(o, n), encoding="utf-8-sig")))
        return o, man, read("eval_sheet_A.csv"), read("eval_sheet_B.csv"), read("eval_key.csv")

    def test_sample_composition(self):
        o, man, A, B, key = self.build()
        self.assertEqual(man["strata_A"]["control"], 39)
        self.assertEqual(man["strata_A"]["terminology"], 45)
        for t in m.OTHER:
            self.assertEqual(man["strata_A"][t], 12)
            self.assertGreaterEqual(man["type_coverage_A"][t], 12)
        self.assertEqual(man["pages_A"], 132)
        self.assertEqual(man["pages_B"], 60)
        self.assertTrue(all(man["strata_B"][s] >= 1 for s in m.STRATA))
        self.assertGreater(man["strata_B"]["terminology"], 0)
        self.assertGreater(man["strata_B"]["control"], 0)

    def test_b_subset_of_a_and_key_complete(self):
        o, man, A, B, key = self.build()
        ids_a, ids_b = {r["issue_id"] for r in A}, {r["issue_id"] for r in B}
        self.assertTrue(ids_b <= ids_a)
        self.assertEqual({r["issue_id"] for r in key}, ids_a)
        self.assertEqual({r["issue_id"] for r in key if r["in_sheet_B"] == "1"}, ids_b)
        self.assertEqual(len(ids_a), len(A))     # issue_id 고유

    def test_columns_and_blinding(self):
        o, man, A, B, key = self.build()
        self.assertEqual(list(A[0].keys()), m.SHEET_COLS)
        raw = open(os.path.join(o, "eval_sheet_A.csv"), encoding="utf-8-sig").read() + \
              open(os.path.join(o, "eval_sheet_B.csv"), encoding="utf-8-sig").read()
        for bad in ("page_", "testbed", "localhost", "FAKE-R1", "E1", "Terminology", "Contrast", "control", "/login", "404 페이지"):
            self.assertNotIn(bad, raw, bad)
        for r in A:
            self.assertTrue(os.path.exists(os.path.join(o, r["screenshot_path"])))
            self.assertEqual((r["rater_category"], r["exists_in_code"], r["visible_on_screen"],
                              r["login_link_label_concern"], r["rater_notes"]), ("", "", "", "", ""))

    def test_seeds(self):
        _, man1, A1, B1, _ = self.build("o1", 101, 202)
        _, man2, A2, B2, _ = self.build("o2", 101, 202)
        self.assertEqual([r["issue_id"] for r in A1], [r["issue_id"] for r in A2])      # 같은 시드 → 같은 결과
        self.assertEqual([r["issue_id"] for r in B1], [r["issue_id"] for r in B2])
        common = [r["issue_id"] for r in A1 if r["issue_id"] in {x["issue_id"] for x in B1}]
        self.assertNotEqual(common, [r["issue_id"] for r in B1])                         # A 와 B 순서가 다름
        _, man3, _, B3, _ = self.build("o3", 101, 303)
        self.assertNotEqual({r["issue_id"] for r in B1}, {r["issue_id"] for r in B3})   # B 시드가 표본을 바꿈
        with self.assertRaises(ValueError):
            self.build("o4", 5, 5)

    def test_sampling_ignores_scores(self):
        """표본 추출 함수는 라벨(nominal)과 시드만 입력으로 받는다."""
        import inspect
        self.assertEqual(list(inspect.signature(m.select_pages_a).parameters), ["nominal", "seed_a"])
        self.assertEqual(list(inspect.signature(m.select_pages_b).parameters), ["a_strata", "seed_b", "target"])

    def test_leak_guard(self):
        p = os.path.join(self.runs, self.run_id, "reports.jsonl")
        lines = open(p, encoding="utf-8").read().splitlines()
        ctrl = next(q["page_id"][:-5] for q in json.load(open(META, encoding="utf-8")) if not q["has_defect"])  # 대조군은 항상 A 에 포함
        i = next(k for k, l in enumerate(lines) if json.loads(l)["page_id"] == ctrl)
        r = json.loads(lines[i])
        r["report"]["issues"].insert(0, {"description": f"[http://localhost:8080/testbed_200/{ctrl}.html] {ctrl} 문제",
                                         "suggestion": ""})
        lines[i] = json.dumps(r, ensure_ascii=False)
        open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        with self.assertRaises(m.LeakError):
            m.build(self.run_id, 1, 2, os.path.join(self.tmp, "o5"), self.runs, META, GT)


if __name__ == "__main__":
    unittest.main()
