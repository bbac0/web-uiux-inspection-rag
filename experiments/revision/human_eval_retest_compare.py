"""
평가자 자기 일치도: 본 평가 CSV vs 재판정 CSV (API 호출 없음, 통계 검정 없음).

human_eval_pilot_compare.py 를 복사해 고친 파일이다(원 파일은 그대로). 열별 단순 일치율과 Cohen's kappa 를 내고,
두 번의 답을 합쳐 값이 한 가지뿐인 열은 kappa 를 '계산 불가(값 한 가지)'로 적는다.
입력은 평가자가 뷰어에서 내보낸 CSV 두 개(와 선택적으로 retest_sampling.json)뿐이다. 정답 키·채점 결과는 받지 않는다.

  python experiments/revision/human_eval_retest_compare.py \
      --main results/revision/human_eval/rater_A/eval_sheet_A_filled.csv \
      --retest eval_sheet_A_retest_filled.csv \
      --sampling results/revision/human_eval/retest_sampling.json \
      --out results/revision/human_eval/retest_agreement_A.md

- 재판정 CSV 의 issue_id 는 모두 본 평가 CSV 에 있어야 한다. 비교는 재판정 issue_id 만 한다.
- --sampling 을 주면 재판정 issue_id 집합이 표본 목록(issue_ids_sorted)과 같은지 확인한다.
- 설명·제안이 두 CSV 에서 다르면 멈춘다(스크린샷 경로는 재판정에서 새 토큰이라 비교하지 않는다).
- 각 열에서 어느 한쪽이라도 비어 있는 행은 그 열의 지표에서 빼고 '빈 칸' 건수로 따로 센다.
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import make_eval_sheets as mes    # noqa: E402

JUDGE_COLS = [("rater_category", "6분류"), ("exists_in_code", "코드에 존재"), ("visible_on_screen", "화면에서 보임"),
              ("login_link_label_concern", "로그인 레이블 지적")]
TEXT_COLS = ("description", "suggestion")
ONE_VALUE = "계산 불가(값 한 가지)"


def read(path):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows or list(rows[0].keys()) != mes.SHEET_COLS:
        raise SystemExit(f"{path}: 열 구성이 평가 시트와 다르다")
    ids = [r["issue_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{path}: issue_id 중복")
    return {r["issue_id"]: r for r in rows}


def cohen_kappa(a, b):
    """→ (po, kappa). kappa 는 숫자, None(n=0 또는 정의 안 됨) 또는 ONE_VALUE."""
    n = len(a)
    if n == 0:
        return None, None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    vals = set(ca) | set(cb)
    if len(vals) == 1:
        return po, ONE_VALUE
    pe = sum(ca[k] * cb[k] for k in vals) / (n * n)
    return po, ((po - pe) / (1 - pe) if pe < 1 else None)


def compare(M, R, sample_ids=None):
    extra = set(R) - set(M)
    if extra:
        raise SystemExit(f"재판정 issue_id {len(extra)}건이 본 평가 CSV 에 없다 (다른 평가자의 파일인지 확인)")
    if sample_ids is not None and set(R) != set(sample_ids):
        raise SystemExit(f"재판정 issue_id 집합이 표본 목록과 다르다 (표본에만 {len(set(sample_ids) - set(R))}, "
                         f"CSV 에만 {len(set(R) - set(sample_ids))})")
    ids = sorted(R)
    for i in ids:
        for c in TEXT_COLS:
            if M[i][c] != R[i][c]:
                raise SystemExit(f"{i}: 두 CSV 의 {c} 가 다르다")
    res = {"n": len(ids), "n_main": len(M), "cols": {}, "disagree": [], "confusion": Counter()}
    for col, name in JUDGE_COLS:
        pairs = [(M[i][col], R[i][col]) for i in ids if M[i][col] and R[i][col]]
        po, k = cohen_kappa([x for x, _ in pairs], [y for _, y in pairs])
        res["cols"][col] = {"name": name, "n": len(pairs), "blank": len(ids) - len(pairs),
                            "agree": sum(x == y for x, y in pairs), "po": po, "kappa": k,
                            "values": len({v for p in pairs for v in p})}
        if col == "rater_category":
            res["confusion"].update(pairs)
    for i in ids:
        diff = [c for c, _ in JUDGE_COLS if M[i][c] and R[i][c] and M[i][c] != R[i][c]]
        if diff:
            res["disagree"].append({"issue_id": i, "cols": diff, "m": {c: M[i][c] for c in diff},
                                    "r": {c: R[i][c] for c in diff},
                                    "notes_m": M[i]["rater_notes"], "notes_r": R[i]["rater_notes"]})
    return res


def fmt(x):
    if x is None:
        return "-"
    return x if isinstance(x, str) else f"{x:.3f}"


def report(res, m_path, r_path):
    src = "출처: 위 입력 CSV 두 개"
    L = ["# 평가자 자기 일치도 (본 평가 vs 재판정)", "",
         "작성: `experiments/revision/human_eval_retest_compare.py` (API 호출 없음, 검정 없음).",
         f"본 평가: `{m_path}`", f"재판정: `{r_path}`", "정답 키·채점 결과 미사용.",
         f"비교 이슈 {res['n']}건 (본 평가 CSV {res['n_main']}건 중 재판정한 이슈).", "",
         "## 1. 열별 일치", "",
         "| 열 | 비교 건 | 빈 칸(제외) | 일치 | 단순 일치율 | Cohen's kappa | 관찰 값 수 |",
         "|---|---|---|---|---|---|---|"]
    for col, _ in JUDGE_COLS:
        c = res["cols"][col]
        L.append(f"| {c['name']} | {c['n']} | {c['blank']} | {c['agree']} | {fmt(c['po'])} | {fmt(c['kappa'])} | "
                 f"{c['values']} |")
    labels = mes.CATEGORY_CHOICES
    L += ["", src, "", "## 2. 6분류 혼동 행렬 (행 = 본 평가, 열 = 재판정)", "",
          "| 본 \\ 재 | " + " | ".join(labels) + " |", "|" + "---|" * (len(labels) + 1)]
    for x in labels:
        L.append(f"| {x} | " + " | ".join(str(res["confusion"][(x, y)]) for y in labels) + " |")
    L += ["", src, "", f"## 3. 불일치 이슈 ({len(res['disagree'])}건)", "",
          "| issue_id | 열 | 본 평가 | 재판정 | 본 평가 비고 | 재판정 비고 |", "|---|---|---|---|---|---|"]
    for d in res["disagree"]:
        for c in d["cols"]:
            L.append(f"| {d['issue_id']} | {c} | {d['m'][c]} | {d['r'][c]} | {d['notes_m'].replace('|', '/')[:20]} | "
                     f"{d['notes_r'].replace('|', '/')[:20]} |")
    L += ["", src]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", required=True)
    ap.add_argument("--retest", required=True)
    ap.add_argument("--sampling")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if os.path.exists(a.out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {a.out}")
    sample_ids = None
    if a.sampling:
        with open(a.sampling, encoding="utf-8") as f:
            sample_ids = json.load(f)["issue_ids_sorted"]
    res = compare(read(a.main), read(a.retest), sample_ids)
    open(a.out, "w", encoding="utf-8", newline="\n").write(report(res, a.main, a.retest))
    print(f"{a.out}: {res['n']} issues, disagreements {len(res['disagree'])}")


if __name__ == "__main__":
    sys.exit(main())
