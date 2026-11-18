"""
E9 사람 평가(평가자 A 1인) 대 정규식: 정규식 정밀도만 (API 호출 없음, 검정 없음). 생성만 하고 실제 결과에는 아직 쓰지 않았다.
규칙: results/revision/analysis_plan_addendum_e9_human.md (ca021ba), _2.md (c737a9c), _3.md (94503ac).

  python experiments/revision/e9_human_compare.py \
      --a results/revision/human_eval/e9_eval/rater_A_e9_hit52/eval_sheet_A_e9_hit52_filled.csv \
      --key results/revision/human_eval/e9_eval/key/e9_key_hit52.csv \
      --out results/revision/human_eval/e9_eval/e9_compare_hit52.md

- 부록 3: 정규식에 걸린 52건만 평가했다. 재현 누락(안 걸린 이슈)과 재평가 항목은 건너뛴다(입력도 받지 않는다).
- 단위: (이슈, 정규식 주 지표가 잡은 유형) 쌍. 그 유형의 열(E9-1 → banner-text, E9-2 → spec-values,
  E9-3 → login-address)이 '예'면 A 가 실제 결함으로 본 쌍.
- 층: 조건 run × 페이지 결함 유형 × 잡은 유형, "n쌍 중 m쌍". 걸린 이슈는 전수라 조건 run × 잡은 유형 합계도 낸다.
  신뢰구간 없음. 빈 칸 쌍은 분모에서 빼고 따로 센다. 보조 규칙(aux_*)은 쓰지 않는다.
"""
import argparse
import csv
import os
import sys
from collections import Counter, defaultdict

JUDGE = ["banner-text", "spec-values", "login-address"]
COLS = ["issue_id", "screenshot_path", "description", "suggestion"] + JUDGE + ["notes"]
TYPE_COL = {"E9-1": "banner-text", "E9-2": "spec-values", "E9-3": "login-address"}
STRATA = ["E9-1", "E9-2", "E9-3", "control"]


def read_sheet(p):
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    if not rows or list(rows[0]) != COLS:
        raise SystemExit(f"{p}: 열 구성이 E9 시트와 다르다")
    ids = [r["issue_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{p}: issue_id 중복")
    for r in rows:
        for c in JUDGE:
            if r[c] not in ("", "예", "아니오"):
                raise SystemExit(f"{p}: {r['issue_id']} {c} 값 '{r[c]}' 허용 안 됨")
    return {r["issue_id"]: r for r in rows}


def read_key(p):
    """걸린 이슈만 남긴다(부록 3)."""
    return {r["issue_id"]: r for r in csv.DictReader(open(p, encoding="utf-8-sig")) if r["regex_stratum"] == "hit"}


def fired(k):
    return [t for t in TYPE_COL if k.get(f"primary_{t}") == "1"]


def compare(A, K):
    if set(A) != set(K):
        raise SystemExit(f"issue_id 가 key 의 걸린 이슈와 다르다 (시트만 {len(set(A) - set(K))}, key만 {len(set(K) - set(A))})")
    cnt, tot = defaultdict(Counter), defaultdict(Counter)
    no = []
    for i, k in K.items():
        ts = fired(k)
        if not ts:
            raise SystemExit(f"{i}: 걸린 이슈인데 E9-1~3 주 지표가 없다")
        for t in ts:
            v = A[i][TYPE_COL[t]]
            for c in (cnt[(k["run_id"], k["page_stratum"], t)], tot[(k["run_id"], t)]):
                c["n"] += 1
                c["blank" if v == "" else ("yes" if v == "예" else "no")] += 1
            if v == "아니오":
                no.append({"issue_id": i, "run": k["run_id"], "page": k["page_stratum"], "type": t,
                           "answers": {c: A[i][c] for c in JUDGE}, "notes": A[i]["notes"]})
    return {"counts": cnt, "totals": tot, "no": no}


def frac(c):
    d = c["yes"] + c["no"]
    return f"{d}쌍 중 {c['yes']}쌍" if d else "-"


def report(res, a_path, key_path):
    L = ["# E9 사람 평가(평가자 A) 대 정규식: 정밀도", "",
         "작성: `experiments/revision/e9_human_compare.py` (API 호출 없음, 검정 없음).",
         f"평가자 A: `{a_path}`, key: `{key_path}`",
         "부록 3 (94503ac): 정규식에 걸린 52건만 평가했다. 사람 기준은 평가자 A 1인이고 재평가는 없다.",
         "단위는 (이슈, 잡은 유형) 쌍. 신뢰구간과 층을 넘는 검정은 내지 않는다.", "",
         "## 1. 층별 (조건 run × 페이지 결함 유형 × 잡은 유형)", "",
         "| 조건 run | 페이지 층 | 잡은 유형 | 쌍 | A '예' | A '아니오' | 빈 칸 | 정밀도(건수) |",
         "|---|---|---|---|---|---|---|---|"]
    for (run, s, t), c in sorted(res["counts"].items(), key=lambda x: (x[0][0], STRATA.index(x[0][1]), x[0][2])):
        L.append(f"| {run} | {s} | {t} | {c['n']} | {c['yes']} | {c['no']} | {c['blank']} | {frac(c)} |")
    L += ["", "출처: 위 입력 CSV 와 key", "", "## 2. 조건 run × 잡은 유형 합계 (걸린 이슈 전수)", "",
          "| 조건 run | 잡은 유형 | 쌍 | A '예' | A '아니오' | 빈 칸 | 정밀도(건수) |", "|---|---|---|---|---|---|---|"]
    for (run, t), c in sorted(res["totals"].items()):
        L.append(f"| {run} | {t} | {c['n']} | {c['yes']} | {c['no']} | {c['blank']} | {frac(c)} |")
    L += ["", "출처: 위와 같음", "", f"## 3. A 가 '아니오'로 본 쌍 ({len(res['no'])}건)", "",
          "| issue_id | 조건 run | 페이지 층 | 잡은 유형 | banner/spec/login | 비고 |", "|---|---|---|---|---|---|"]
    for d in res["no"]:
        a = d["answers"]
        L.append(f"| {d['issue_id']} | {d['run']} | {d['page']} | {d['type']} | "
                 f"{a['banner-text']}/{a['spec-values']}/{a['login-address']} | {d['notes'].replace('|', '/')[:20]} |")
    L += ["", "출처: 위와 같음", "", "## 4. 한계", "",
          "- 재현 누락(정규식이 놓친 실제 결함)은 사람이 검증하지 않았다(부록 3 5절).",
          "- 평가자 1인, 재평가 없음. 일부 층은 1~3쌍이라 건수로만 읽는다.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if os.path.exists(a.out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {a.out}")
    res = compare(read_sheet(a.a), read_key(a.key))
    open(a.out, "w", encoding="utf-8", newline="\n").write(report(res, a.a, a.key))
    print(f"{a.out}: pairs {sum(c['n'] for c in res['totals'].values())}; A '아니오' {len(res['no'])}")


if __name__ == "__main__":
    sys.exit(main())
