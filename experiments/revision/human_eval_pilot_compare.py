"""
두 평가자 CSV 비교: 열별 일치율, Cohen's kappa, 불일치 이슈 목록 (API 호출 없음, 통계 검정 없음).

입력은 평가자가 뷰어에서 내보낸 CSV 두 개뿐이다(열: make_eval_sheets.SHEET_COLS). 정답 키(key/)와 채점 결과는 받지 않는다.

  python experiments/revision/human_eval_pilot_compare.py --a 연습_A.csv --b 연습_B.csv --out results/revision/human_eval/pilot_agreement.md
  # 본 평가: A 444건과 B 204건 중 겹치는 issue_id 만 비교
  python experiments/revision/human_eval_pilot_compare.py --a filled_A.csv --b filled_B.csv --merge overlap --out ...

--merge same    (기본, 시범) 두 CSV 의 issue_id 집합이 같아야 한다. 다르면 멈춘다.
--merge overlap (본 평가) 두 CSV 에 모두 있는 issue_id 만 비교하고, 한쪽에만 있는 건수를 보고한다.
각 열에서 어느 한쪽이라도 비어 있는 행은 그 열의 일치율·kappa 에서 빼고 '빈 칸' 건수로 따로 센다.
"""
import argparse
import csv
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import make_eval_sheets as mes    # noqa: E402

JUDGE_COLS = [("rater_category", "6분류"), ("exists_in_code", "코드에 존재"), ("visible_on_screen", "화면에서 보임"),
              ("login_link_label_concern", "로그인 레이블 지적")]
TEXT_COLS = ("description", "suggestion")


def read(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if not rows or list(rows[0].keys()) != mes.SHEET_COLS:
        raise SystemExit(f"{path}: 열 구성이 평가 시트와 다르다")
    ids = [r["issue_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{path}: issue_id 중복")
    return {r["issue_id"]: r for r in rows}


def cohen_kappa(a, b):
    n = len(a)
    if n == 0:
        return None, None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in set(ca) | set(cb)) / (n * n)
    return po, ((po - pe) / (1 - pe) if pe < 1 else None)


def compare(A, B, merge="same"):
    sa, sb = set(A), set(B)
    if merge == "same" and sa != sb:
        raise SystemExit(f"issue_id 집합이 다르다 (A만 {len(sa - sb)}, B만 {len(sb - sa)}). 본 평가는 --merge overlap")
    ids = sorted(sa & sb)
    for i in ids:
        for c in TEXT_COLS:
            if A[i][c] != B[i][c]:
                raise SystemExit(f"{i}: 두 CSV 의 {c} 가 다르다 (다른 시트의 파일인지 확인)")
    res = {"n_common": len(ids), "only_a": len(sa - sb), "only_b": len(sb - sa), "cols": {}, "disagree": [], "confusion": Counter()}
    for col, name in JUDGE_COLS:
        pairs = [(A[i][col], B[i][col]) for i in ids if A[i][col] and B[i][col]]
        po, k = cohen_kappa([x for x, _ in pairs], [y for _, y in pairs])
        res["cols"][col] = {"name": name, "n": len(pairs), "blank": len(ids) - len(pairs), "agree": sum(x == y for x, y in pairs),
                            "po": po, "kappa": k}
        if col == "rater_category":
            res["confusion"].update(pairs)
    for i in ids:
        diff = [c for c, _ in JUDGE_COLS if A[i][c] and B[i][c] and A[i][c] != B[i][c]]
        if diff:
            res["disagree"].append({"issue_id": i, "cols": diff, "a": {c: A[i][c] for c in diff}, "b": {c: B[i][c] for c in diff},
                                    "notes_a": A[i]["rater_notes"], "notes_b": B[i]["rater_notes"]})
    return res


def fmt(x):
    return "-" if x is None else f"{x:.3f}"


def report(res, a_path, b_path, merge):
    L = ["# 평가자 간 일치 (" + ("시범" if merge == "same" else "본 평가, 겹치는 이슈") + ")", "",
         "작성: `experiments/revision/human_eval_pilot_compare.py` (API 호출 없음, 검정 없음).",
         f"입력 A: `{a_path}`", f"입력 B: `{b_path}`", f"정답 키·채점 결과 미사용. 병합 방식 `{merge}`.",
         f"비교 이슈 {res['n_common']}건 (A 에만 {res['only_a']}, B 에만 {res['only_b']}).", "",
         "## 1. 열별 일치율과 Cohen's kappa", "",
         "| 열 | 비교 건 | 빈 칸(제외) | 일치 | 일치율 | kappa |", "|---|---|---|---|---|---|"]
    for col, _ in JUDGE_COLS:
        c = res["cols"][col]
        L.append(f"| {c['name']} ({col}) | {c['n']} | {c['blank']} | {c['agree']} | {fmt(c['po'])} | {fmt(c['kappa'])} |")
    labels = mes.CATEGORY_CHOICES
    L += ["", "출처: 위 입력 A, B CSV"]
    L += ["", "## 2. 6분류 혼동 행렬 (행 = A, 열 = B)", "", "| A \\ B | " + " | ".join(labels) + " |",
          "|" + "---|" * (len(labels) + 1)]
    for x in labels:
        L.append(f"| {x} | " + " | ".join(str(res["confusion"][(x, y)]) for y in labels) + " |")
    L += ["", "출처: 위 입력 A, B CSV"]
    L += ["", f"## 3. 불일치 이슈 ({len(res['disagree'])}건)", "", "| issue_id | 열 | A | B | A 비고 | B 비고 |", "|---|---|---|---|---|---|"]
    for d in res["disagree"]:
        for c in d["cols"]:
            L.append(f"| {d['issue_id']} | {c} | {d['a'][c]} | {d['b'][c]} | {d['notes_a'].replace('|', '/')[:40]} | "
                     f"{d['notes_b'].replace('|', '/')[:40]} |")
    L += ["", "출처: 위 입력 A, B CSV"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--merge", choices=["same", "overlap"], default="same")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if os.path.exists(a.out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {a.out}")
    res = compare(read(a.a), read(a.b), a.merge)
    open(a.out, "w", encoding="utf-8", newline="\n").write(report(res, a.a, a.b, a.merge))
    print(f"{a.out}: {res['n_common']} issues, disagreements {len(res['disagree'])}")


if __name__ == "__main__":
    sys.exit(main())
