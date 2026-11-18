"""
두 평가자 CSV 비교 (강건판): 열별 단순 일치율, Cohen's kappa, PABAK, Gwet AC1, 불일치 목록 (API 호출 없음, 검정 없음).

human_eval_pilot_compare.py 를 복사해 고친 파일이다(원 파일은 그대로). 한쪽 값이 극히 드문 열에서도 보고할 수 있게
PABAK 과 AC1 을 kappa 와 함께 낸다. 두 평가자가 고른 값이 합쳐서 한 가지뿐인 열은 kappa 를 '계산 불가(값 한 가지)'로 적는다.

  python experiments/revision/human_eval_compare_robust.py --a A.csv --b B.csv --out report.md [--merge same|overlap]
         [--groups groups.csv]      # 열: issue_id,group → 묶음별 표를 추가로 낸다(예: 층). 없으면 전체만.

지표 (q = 그 열에서 허용된 값의 수: 6분류 6, 코드·화면 3, 로그인 레이블 2. 관찰된 값 수가 아니다):
  일치율 po = 같은 답 비율
  Cohen's kappa = (po - pe) / (1 - pe), pe = Σ_k pA_k pB_k
  PABAK = (q po - 1) / (q - 1)                         (q = 2 이면 2 po - 1)
  Gwet AC1 = (po - pe1) / (1 - pe1), pe1 = Σ_k π_k (1 - π_k) / (q - 1), π_k = (pA_k + pB_k) / 2
각 열에서 어느 한쪽이라도 비어 있는 행은 그 열의 지표에서 빼고 '빈 칸' 건수로 따로 센다.
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
ALLOWED = {"rater_category": list(mes.CATEGORY_CHOICES), "exists_in_code": ["예", "아니오", "판단 불가"],
           "visible_on_screen": ["예", "아니오", "판단 불가"], "login_link_label_concern": ["예", "아니오"]}
TEXT_COLS = ("description", "suggestion")
ONE_VALUE = "계산 불가(값 한 가지)"


def read(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if not rows or list(rows[0].keys()) != mes.SHEET_COLS:
        raise SystemExit(f"{path}: 열 구성이 평가 시트와 다르다")
    ids = [r["issue_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{path}: issue_id 중복")
    for r in rows:
        for c, allowed in ALLOWED.items():
            if r[c] and r[c] not in allowed:
                raise SystemExit(f"{path}: {r['issue_id']} 의 {c} 값 '{r[c]}' 은 허용되지 않음")
    return {r["issue_id"]: r for r in rows}


def agreement(a, b, q):
    """→ dict(n, po, kappa, pabak, ac1, values). kappa 는 숫자, None(n=0) 또는 ONE_VALUE."""
    n = len(a)
    if n == 0:
        return {"n": 0, "po": None, "kappa": None, "pabak": None, "ac1": None, "values": 0}
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    vals = set(ca) | set(cb)
    pe = sum(ca[k] * cb[k] for k in vals) / (n * n)
    if len(vals) == 1:
        kappa = ONE_VALUE
    elif pe >= 1:
        kappa = None
    else:
        kappa = (po - pe) / (1 - pe)
    pabak = (q * po - 1) / (q - 1)
    pe1 = sum(((ca[k] + cb[k]) / (2 * n)) * (1 - (ca[k] + cb[k]) / (2 * n)) for k in vals) / (q - 1)
    ac1 = (po - pe1) / (1 - pe1) if pe1 < 1 else None
    return {"n": n, "po": po, "kappa": kappa, "pabak": pabak, "ac1": ac1, "values": len(vals)}


def compare(A, B, merge="same", ids=None):
    sa, sb = set(A), set(B)
    if merge == "same" and sa != sb:
        raise SystemExit(f"issue_id 집합이 다르다 (A만 {len(sa - sb)}, B만 {len(sb - sa)}). 본 평가는 --merge overlap")
    common = sorted(sa & sb)
    for i in common:
        for c in TEXT_COLS:
            if A[i][c] != B[i][c]:
                raise SystemExit(f"{i}: 두 CSV 의 {c} 가 다르다 (다른 시트의 파일인지 확인)")
    use = common if ids is None else [i for i in common if i in ids]
    res = {"n_common": len(use), "only_a": len(sa - sb), "only_b": len(sb - sa), "cols": {}, "disagree": [],
           "confusion": Counter()}
    for col, name in JUDGE_COLS:
        pairs = [(A[i][col], B[i][col]) for i in use if A[i][col] and B[i][col]]
        m = agreement([x for x, _ in pairs], [y for _, y in pairs], len(ALLOWED[col]))
        m.update(name=name, blank=len(use) - len(pairs), agree=sum(x == y for x, y in pairs),
                 dist_a=Counter(x for x, _ in pairs), dist_b=Counter(y for _, y in pairs))
        res["cols"][col] = m
        if col == "rater_category":
            res["confusion"].update(pairs)
    for i in use:
        diff = [c for c, _ in JUDGE_COLS if A[i][c] and B[i][c] and A[i][c] != B[i][c]]
        if diff:
            res["disagree"].append({"issue_id": i, "cols": diff, "a": {c: A[i][c] for c in diff},
                                    "b": {c: B[i][c] for c in diff},
                                    "notes_a": A[i]["rater_notes"], "notes_b": B[i]["rater_notes"]})
    return res


def fmt(x):
    if x is None:
        return "-"
    return x if isinstance(x, str) else f"{x:.3f}"


def metric_table(res):
    L = ["| 열 | 비교 건 | 빈 칸(제외) | 일치 | 일치율 | kappa | PABAK | AC1 | 관찰 값 수 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for col, _ in JUDGE_COLS:
        c = res["cols"][col]
        L.append(f"| {c['name']} | {c['n']} | {c['blank']} | {c['agree']} | {fmt(c['po'])} | {fmt(c['kappa'])} | "
                 f"{fmt(c['pabak'])} | {fmt(c['ac1'])} | {c['values']} |")
    return L


def dist_table(res):
    L = ["| 열 | 값 | A | B |", "|---|---|---|---|"]
    for col, _ in JUDGE_COLS:
        c = res["cols"][col]
        for v in ALLOWED[col]:
            if c["dist_a"][v] or c["dist_b"][v]:
                L.append(f"| {c['name']} | {v} | {c['dist_a'][v]} | {c['dist_b'][v]} |")
    return L


def report(res, a_path, b_path, merge, groups=None):
    src = "출처: 위 입력 A, B CSV"
    L = ["# 평가자 간 일치 (강건판)", "",
         "작성: `experiments/revision/human_eval_compare_robust.py` (API 호출 없음, 검정 없음).",
         f"입력 A: `{a_path}`", f"입력 B: `{b_path}`", f"병합 방식 `{merge}`.",
         f"비교 이슈 {res['n_common']}건 (A 에만 {res['only_a']}, B 에만 {res['only_b']}).",
         "PABAK·AC1 의 q 는 허용 값 수(6분류 6, 코드·화면 3, 로그인 레이블 2).", "",
         "## 1. 열별 일치 지표", ""] + metric_table(res) + ["", src, "",
         "## 2. 열별 답 분포 (빈 칸 제외 쌍 기준)", ""] + dist_table(res) + ["", src]
    sec = 3
    if groups:
        L += ["", f"## {sec}. 묶음별 일치 지표", ""]
        for g, gres in groups:
            L += [f"### 묶음 {g} ({gres['n_common']}건)", ""] + metric_table(gres) + ["", src + ", 묶음 파일", ""]
        sec += 1
    labels = mes.CATEGORY_CHOICES
    L += ["", f"## {sec}. 6분류 혼동 행렬 (행 = A, 열 = B)", "", "| A \\ B | " + " | ".join(labels) + " |",
          "|" + "---|" * (len(labels) + 1)]
    for x in labels:
        L.append(f"| {x} | " + " | ".join(str(res["confusion"][(x, y)]) for y in labels) + " |")
    L += ["", src, "", f"## {sec + 1}. 불일치 이슈 ({len(res['disagree'])}건)", "",
          "| issue_id | 열 | A | B | A 비고 | B 비고 |", "|---|---|---|---|---|---|"]
    for d in res["disagree"]:
        for c in d["cols"]:
            L.append(f"| {d['issue_id']} | {c} | {d['a'][c]} | {d['b'][c]} | {d['notes_a'].replace('|', '/')[:30]} | "
                     f"{d['notes_b'].replace('|', '/')[:30]} |")
    L += ["", src]
    return "\n".join(L) + "\n"


def read_groups(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if not rows or not {"issue_id", "group"} <= set(rows[0]):
        raise SystemExit(f"{path}: issue_id, group 열이 필요하다")
    out = {}
    for r in rows:
        out.setdefault(r["group"], set()).add(r["issue_id"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--merge", choices=["same", "overlap"], default="same")
    ap.add_argument("--groups")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if os.path.exists(a.out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {a.out}")
    A, B = read(a.a), read(a.b)
    res = compare(A, B, a.merge)
    groups = None
    if a.groups:
        groups = [(g, compare(A, B, a.merge, ids)) for g, ids in sorted(read_groups(a.groups).items())]
    open(a.out, "w", encoding="utf-8", newline="\n").write(report(res, a.a, a.b, a.merge, groups))
    print(f"{a.out}: {res['n_common']} issues, disagreements {len(res['disagree'])}")


if __name__ == "__main__":
    sys.exit(main())
