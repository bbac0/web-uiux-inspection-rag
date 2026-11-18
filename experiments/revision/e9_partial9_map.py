"""
평가자 A 가 기존 E9 시트(rater_A_e9, 138건)에 입력한 부분 답(9건)을 52건 시트로 옮긴다 (API 호출 없음).
규칙: results/revision/analysis_plan_addendum_e9_human_3.md (94503ac) 3절. 생성만 하고 아직 실행하지 않았다.

  python experiments/revision/e9_partial9_map.py --partial <경로>/rater_A_e9_partial9.csv

입력: 기존 뷰어에서 내보낸 CSV(열은 E9 시트와 같음; 138행이든 입력한 행만이든 됨). 읽기만 하고 고치지 않는다.
출력(results/revision/human_eval/e9_eval/partial9/, 이미 있으면 거부):
- eval_sheet_A_e9_hit52_prefill.csv  52건 시트와 같은 열·행 순서. 52건에 드는 이슈의 답만 옮김(값 그대로).
                                     평가자가 52건 뷰어의 'CSV 불러오기' 로 넣는다.
- partial9_excluded_nonhit.csv       52건에 들지 않는 이슈의 답. 분석에 쓰지 않고 보관만 한다.
- partial9_mapping.md                건수, issue_id 목록, 입력 파일 SHA-256.
평가자 답이 든 앞의 두 CSV 는 커밋하지 않는다.
답이 하나라도 있는 행(세 판정 열 또는 notes)을 '입력한 행'으로 본다.
"""
import argparse
import csv
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import e9_human_sheets as es     # noqa: E402

E9 = es.E9
HIT52 = f"{E9}/rater_A_e9_hit52/eval_sheet_A_e9_hit52.csv"
A138 = f"{E9}/rater_A_e9/eval_sheet_A_e9.csv"
INPUT = es.JUDGE + ["notes"]


def read(p):
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    if not rows or list(rows[0]) != es.SHEET_COLS:
        raise SystemExit(f"{p}: 열 구성이 E9 시트와 다르다")
    ids = [r["issue_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{p}: issue_id 중복")
    return rows


def mapping(partial, hit52, a138):
    base = {r["issue_id"]: r for r in a138}
    for r in partial:
        b = base.get(r["issue_id"])
        if b is None:
            raise SystemExit(f"{r['issue_id']}: 기존 138건 시트에 없는 issue_id")
        if (r["description"], r["suggestion"]) != (b["description"], b["suggestion"]):
            raise SystemExit(f"{r['issue_id']}: 기존 시트와 이슈 문장이 다르다")
        for c in es.JUDGE:
            if r[c] not in ("", "예", "아니오"):
                raise SystemExit(f"{r['issue_id']} {c}: 허용되지 않은 값 '{r[c]}'")
    entered = [r for r in partial if any(r[c] for c in INPUT)]
    in52 = {r["issue_id"] for r in hit52}
    carried = {r["issue_id"]: r for r in entered if r["issue_id"] in in52}
    excluded = [r for r in entered if r["issue_id"] not in in52]
    prefill = [{**h, **{c: carried[h["issue_id"]][c] for c in INPUT}} if h["issue_id"] in carried else dict(h)
               for h in hit52]
    incomplete = sorted(i for i, r in carried.items() if not all(r[c] for c in es.JUDGE))
    return entered, carried, excluded, prefill, incomplete


def write_csv(p, rows):
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=es.SHEET_COLS)
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--partial", required=True)
    ap.add_argument("--out", default=f"{E9}/partial9")
    a = ap.parse_args(argv)
    if os.path.exists(a.out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {a.out}")
    partial, hit52, a138 = read(a.partial), read(HIT52), read(A138)
    if any(r[c] for r in hit52 for c in INPUT):
        raise SystemExit(f"{HIT52}: 빈 시트가 아니다")
    entered, carried, excluded, prefill, incomplete = mapping(partial, hit52, a138)
    os.makedirs(a.out)
    write_csv(f"{a.out}/eval_sheet_A_e9_hit52_prefill.csv", prefill)
    write_csv(f"{a.out}/partial9_excluded_nonhit.csv", excluded)
    sha = hashlib.sha256(open(a.partial, "rb").read()).hexdigest()
    L = ["# 평가자 A 부분 입력의 52건 시트 매핑", "",
         "작성: `experiments/revision/e9_partial9_map.py` (API 호출 없음). 규칙: 부록 3 (94503ac) 3절.",
         f"입력: `{os.path.relpath(a.partial, ROOT).replace(os.sep, '/')}` (SHA-256 `{sha}`), 읽기만 함.", "",
         "| 항목 | 건수 |", "|---|---|",
         f"| 입력 파일 행 | {len(partial)} |", f"| 답이 있는 행 | {len(entered)} |",
         f"| 52건 시트로 옮김 | {len(carried)} |", f"| 옮긴 행 중 판정 열이 다 차지 않은 행 | {len(incomplete)} |",
         f"| 52건에 들지 않아 분석 제외(보관만) | {len(excluded)} |", "",
         "출처: 위 입력 파일, `rater_A_e9_hit52/eval_sheet_A_e9_hit52.csv`", "",
         "| issue_id | 처리 |", "|---|---|"]
    L += [f"| {i} | 옮김{' (판정 열 일부 빈 칸)' if i in incomplete else ''} |" for i in sorted(carried)]
    L += [f"| {r['issue_id']} | 제외(52건 밖) |" for r in sorted(excluded, key=lambda r: r["issue_id"])]
    L += ["", "출처: 위와 같음", "",
          "평가자 답이 든 `eval_sheet_A_e9_hit52_prefill.csv`, `partial9_excluded_nonhit.csv` 는 커밋하지 않는다.", ""]
    open(f"{a.out}/partial9_mapping.md", "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"{a.out}: entered {len(entered)}, carried {len(carried)}, excluded {len(excluded)}, "
          f"incomplete {len(incomplete)}")


if __name__ == "__main__":
    sys.exit(main())
