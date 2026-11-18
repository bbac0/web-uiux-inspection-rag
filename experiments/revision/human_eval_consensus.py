"""
합의 회의 결과 접수, 사람 최종 판정(human_final), 합의 요약, A 재판정 강건 지표 (API 호출 없음, 검정 없음).

정답 키(key/)와 자동 채점 결과(키워드, string_match, 의미 채점)는 읽지 않는다. 평가자 제출 CSV, rater_*/ 시트·뷰어는 읽기만 한다.
합의 후 평가자 간 일치율은 계산하지 않는다(합의로 일치가 인위적으로 높아지므로). 합의 전 일치도는 agreement_main.md,
agreement_supp.md 를 그대로 쓴다.

  python experiments/revision/human_eval_consensus.py intake    # intake_consensus.md
  python experiments/revision/human_eval_consensus.py final     # human_final_main.csv, human_final_supp.csv
  python experiments/revision/human_eval_consensus.py summary   # consensus_summary.md (채택 집계; 사유 규칙 목록은 손으로 쓴 절)
  python experiments/revision/human_eval_consensus.py retest    # retest_agreement.md
"""
import csv
import os
import re
import stat
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import human_eval_compare_robust as rob    # noqa: E402
from experiments.revision import human_eval_intake_all as ia         # noqa: E402
from experiments.revision import human_eval_retest_compare as rc     # noqa: E402

HE, REL, DATE = ia.HE, ia.REL, "2026-11-18"
ORIG = f"{HE}/consensus/disagreement_for_consensus.csv"
FILLED = f"{HE}/consensus/disagreement_for_consensus_filled.csv"
COL_BY_NAME = {v: k for k, v in rob.JUDGE_COLS}
NO_CONSENSUS = ("합의 불가", "판단 보류")
FINAL_COLS = ["시트 구분", "issue_id", "source", "6분류", "코드 존재", "화면 존재", "로그인 레이블 지적", "판정 출처",
              "합의 열", "합의 불가 열"]
FINAL_NAME = {"rater_category": "6분류", "exists_in_code": "코드 존재", "visible_on_screen": "화면 존재",
              "login_link_label_concern": "로그인 레이블 지적"}


def need_new(p):
    if os.path.exists(p):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {p}")


def load_consensus():
    _, rows = ia.rows_of(FILLED)
    return rows


# 사유 문장과 합의 답이 어긋나 보이는 경우(판단 근거는 사유 문장의 결론 표현뿐). 고치지 않고 표시만 한다.
CONTRA = {
    "코드에 존재": [(r"코드에 있는 것으로", "아니오"), (r"코드에 없는|코드엔 따로 스타일이 명시되어 있지 않", "예")],
    "화면에서 보임": [(r"보이지 않", "예"), (r"보이는 것으로|보임\.?\s*$", "아니오")],
}


def contradictions(r):
    out = []
    for pat, bad in CONTRA.get(r["판정 열"], []):
        if re.search(pat, r["합의 사유"]) and r["합의 답"] == bad:
            out.append(f"사유에 '{re.search(pat, r['합의 사유']).group(0)}' 가 있으나 합의 답이 '{bad}'")
    return out


def cmd_intake():
    out = f"{HE}/intake_consensus.md"
    need_new(out)
    os.chmod(FILLED, stat.S_IREAD)
    cols, rows = ia.rows_of(FILLED)
    _, orig = ia.rows_of(ORIG)
    P, flags = [], []
    if cols != ia.CONS_COLS:
        P.append(f"열 구성이 원 파일과 다름: {cols}")
    if len(rows) != 37:
        P.append(f"행 수 {len(rows)} (기대 37)")
    O = {r["번호"]: r for r in orig}
    if [r["번호"] for r in rows] != [r["번호"] for r in orig]:
        P.append("번호 목록·순서가 원 파일과 다름")
    for r in rows:
        k = r["번호"]
        o = O.get(k)
        if o is None:
            P.append(f"#{k}: 원 파일에 없는 번호")
            continue
        for c in ia.CONS_COLS:
            if c not in ("합의 답", "합의 사유") and r[c] != o[c]:
                P.append(f"#{k}: '{c}' 가 원 파일과 다름")
        col = COL_BY_NAME.get(r["판정 열"])
        if not r["합의 답"].strip():
            P.append(f"#{k} {r['issue_id']} {r['판정 열']}: 합의 답 빈칸")
        elif r["합의 답"] in NO_CONSENSUS:
            P.append(f"#{k} {r['issue_id']} {r['판정 열']}: 합의 불가로 표시")
        elif col and r["합의 답"] not in rob.ALLOWED[col]:
            P.append(f"#{k} {r['issue_id']} {r['판정 열']}: 합의 답 허용 값 밖 '{r['합의 답']}'")
        if not r["합의 사유"].strip():
            P.append(f"#{k} {r['issue_id']} {r['판정 열']}: 합의 사유 빈칸")
        for x in contradictions(r):
            flags.append((k, r["issue_id"], r["판정 열"], r["합의 답"], x))
    # 원 불일치가 지금의 평가자 제출 CSV 와 같은지(제출 파일이 그 뒤 바뀌지 않았는지)
    src = {"본 평가": (ia.FILES[0][3], ia.FILES[2][3]), "추가 세트": (ia.FILES[1][3], ia.FILES[3][3])}
    R = {s: (rob.read(f"{HE}/{a}"), rob.read(f"{HE}/{b}")) for s, (a, b) in src.items()}
    for r in rows:
        A, B = R[r["시트 구분"]]
        col = COL_BY_NAME[r["판정 열"]]
        if (A[r["issue_id"]][col], B[r["issue_id"]][col]) != (r["A의 답"], r["B의 답"]):
            P.append(f"#{r['번호']}: A·B 답이 지금 제출 CSV 와 다름")
    L = ["# 합의 회의 결과 접수", "",
         f"작성: `experiments/revision/human_eval_consensus.py intake` (API 호출 없음). {DATE}.",
         "정답 키(key/)와 자동 채점 결과는 읽지 않았다.", "",
         f"- 입력: `{REL}/consensus/disagreement_for_consensus_filled.csv`",
         f"  SHA256 `{ia.sha(FILLED)}`",
         f"  크기 {os.path.getsize(FILLED)} 바이트. 접수 시 읽기 전용 속성 설정(내용은 바꾸지 않음), 커밋하지 않음.",
         f"- 원 불일치 파일: `{REL}/consensus/disagreement_for_consensus.csv`", f"  SHA256 `{ia.sha(ORIG)}`", "",
         "## 1. 점검", "", "| 점검 | 결과 |", "|---|---|",
         f"| 행 수 | {len(rows)} (기대 37) |",
         f"| 열 구성 | {'원 파일과 같음' if cols == ia.CONS_COLS else '다름'} |",
         f"| 번호·issue_id·판정 열·본문·A/B 답이 원 파일과 같음 | "
         f"{'예' if not any('원 파일' in x for x in P) else '아니오'} |",
         f"| 합의 답 빈칸 | {sum('합의 답 빈칸' in x for x in P)} |",
         f"| 합의 불가 표시 | {sum('합의 불가' in x for x in P)} |",
         f"| 합의 답 허용 값 밖 | {sum('허용 값 밖' in x for x in P)} |",
         f"| 합의 사유 빈칸 | {sum('합의 사유 빈칸' in x for x in P)} |",
         f"| A·B 답이 지금 제출 CSV 와 같음 | {'예' if not any('제출 CSV' in x for x in P) else '아니오'} |", "",
         "출처: 위 입력과 원 불일치 파일, 평가자 제출 CSV 4개(`intake_all.md`)", ""]
    L += (["**문제 0건.**", ""] if not P else
          ["### 문제 목록 (고치지 않음)", "", "| 문제 |", "|---|"] + [f"| {ia.cell(x, 90)} |" for x in P]
          + ["", "출처: 위와 같음", ""])
    L += ["## 2. 확인 필요: 합의 사유와 합의 답이 어긋나 보이는 행", "",
          "사유 문장의 결론 표현(예: '코드에 있는 것으로', '보이지 않')과 합의 답을 기계적으로 대조했다.",
          "어느 쪽이 맞는지는 판단하지 않았고 고치지 않았다. human_final 에는 합의 답을 그대로 썼다.", "",
          "| 번호 | issue_id | 판정 열 | 합의 답 | 어긋난 점 |", "|---|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in flags] or ["| - | - | - | - | 없음 |"]
    L += ["", "출처: 위 입력의 합의 답·합의 사유 열", ""]
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"{out}: problems {len(P)}, flags {len(flags)}")


def cmd_final():
    outs = {"main": f"{HE}/human_final_main.csv", "supp": f"{HE}/human_final_supp.csv"}
    for p in outs.values():
        need_new(p)
    cons = defaultdict(dict)
    for r in load_consensus():
        cons[(r["시트 구분"], r["issue_id"])][COL_BY_NAME[r["판정 열"]]] = r["합의 답"].strip()
    for st, (ia_, ib) in (("main", (0, 2)), ("supp", (1, 3))):
        name = ia.SET_NAME[st]
        A, B = rob.read(f"{HE}/{ia.FILES[ia_][3]}"), rob.read(f"{HE}/{ia.FILES[ib][3]}")
        rows = []
        for i in [r["issue_id"] for r in ia.rows_of(f"{HE}/{ia.FILES[ia_][4]}")[1]]:   # A 시트 순서
            o = {"시트 구분": name, "issue_id": i}
            if i not in B:
                o.update({FINAL_NAME[c]: A[i][c] for c in ia.JUDGE})
                o.update({"source": "A_only", "판정 출처": "A_only", "합의 열": "", "합의 불가 열": ""})
                rows.append(o)
                continue
            used, fail = [], []
            for c in ia.JUDGE:
                if A[i][c] == B[i][c]:
                    o[FINAL_NAME[c]] = A[i][c]
                    continue
                v = cons.get((name, i), {}).get(c, "")
                if v not in rob.ALLOWED[c]:          # 빈칸·합의 불가·허용 밖 → 최종 답 비움
                    o[FINAL_NAME[c]] = ""
                    fail.append(FINAL_NAME[c])
                else:
                    o[FINAL_NAME[c]] = v
                    used.append(FINAL_NAME[c])
            o.update({"source": "A_B_consensus", "판정 출처": "합의" if used or fail else "일치",
                      "합의 열": ";".join(used), "합의 불가 열": ";".join(fail)})
            rows.append(o)
        missing = [k for k in cons if k[0] == name and (k[1] not in A or k[1] not in B)]
        if missing:
            raise SystemExit(f"합의 파일의 issue_id 가 A·B 공통 이슈가 아님: {missing}")
        with open(outs[st], "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FINAL_COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        c = Counter((r["source"], r["판정 출처"]) for r in rows)
        print(f"{outs[st]}: {len(rows)} rows; " + ", ".join(f"{a}/{b} {n}" for (a, b), n in sorted(c.items()))
              + f"; no-consensus cells {sum(bool(r['합의 불가 열']) for r in rows)}")


def cmd_summary():
    out = f"{HE}/consensus_summary.md"
    need_new(out)
    rows = load_consensus()
    cnt = Counter()
    for r in rows:
        v = r["합의 답"].strip()
        k = ("A 채택" if v == r["A의 답"] else "B 채택" if v == r["B의 답"] else
             "합의 불가·빈칸" if v in ("",) + NO_CONSENSUS else "제3의 답")
        cnt[(r["시트 구분"], r["판정 열"], k)] += 1
    kinds = ["A 채택", "B 채택", "제3의 답", "합의 불가·빈칸"]
    L = ["# 합의 회의 요약", "",
         f"작성: `experiments/revision/human_eval_consensus.py summary` (API 호출 없음). {DATE}.",
         f"입력: `{REL}/consensus/disagreement_for_consensus_filled.csv`", "(접수: `intake_consensus.md`).",
         "정답 키·자동 채점 결과 미사용. 평가자 간 일치도는 합의 전 원 답 기준(`agreement_main.md`,",
         "`agreement_supp.md`)을 그대로 쓰고, 합의 후 일치율은 계산하지 않는다.", "",
         "## 1. 어느 쪽 답이 채택됐는가 (열별)", "",
         "| 시트 | 판정 열 | 불일치 | " + " | ".join(kinds) + " |", "|---|---|---|" + "---|" * len(kinds)]
    tot = Counter()
    for st in ("본 평가", "추가 세트"):
        for _, name in rob.JUDGE_COLS:
            n = sum(cnt[(st, name, k)] for k in kinds)
            if n:
                L.append(f"| {st} | {name} | {n} | " + " | ".join(str(cnt[(st, name, k)]) for k in kinds) + " |")
            for k in kinds:
                tot[(st, k)] += cnt[(st, name, k)]
        L.append(f"| {st} | 합계 | {sum(tot[(st, k)] for k in kinds)} | "
                 + " | ".join(str(tot[(st, k)]) for k in kinds) + " |")
    L += ["", "출처: 위 입력의 A의 답, B의 답, 합의 답 열", "",
          "- 사유에 '실수'라고 적힌 행: " + ", ".join(
              f"{w} {sum(f'{w}의 실수' in r['합의 사유'] for r in rows)}건" for w in ("A", "B")) + ".", "",
          "## 2. 합의 사유에서 반복해서 나온 판정 규칙", "", "@@RULES@@", ""]
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"{out}: rows {len(rows)}")


def cmd_retest():
    out = f"{HE}/retest_agreement.md"
    need_new(out)
    m_rel, r_rel = "rater_A/eval_sheet_A_filled.csv", "rater_A_retest/eval_sheet_A_retest_filled.csv"
    rp = f"{HE}/{r_rel}"
    os.chmod(rp, stat.S_IREAD)
    P, rows = ia.check(rp, f"{HE}/rater_A_retest/eval_sheet_A_retest.csv", 40)
    import json
    sample = json.load(open(f"{HE}/retest_sampling.json", encoding="utf-8"))["issue_ids_sorted"]
    M, R = rc.read(f"{HE}/{m_rel}"), rc.read(rp)
    res = rc.compare(M, R, sample)
    ids = sorted(R)
    L = ["# 평가자 A 자기 일치도 (본 평가 vs 재판정, 강건 지표 포함)", "",
         f"작성: `experiments/revision/human_eval_consensus.py retest` (API 호출 없음, 검정 없음). {DATE}.",
         "비교·불일치 목록은 `human_eval_retest_compare.py` 의 read/compare, PABAK·AC1 은",
         "`human_eval_compare_robust.agreement` 로 계산했다. 정답 키·채점 결과 미사용.",
         "같은 입력의 kappa 까지 보고는 `retest_agreement_A.md`(55eed97) 에 있고, 이 파일은 PABAK·AC1 을 더한 판이다.", "",
         "## 0. 접수 점검", "",
         f"- 재판정: `{REL}/{r_rel}`", f"  SHA256 `{ia.sha(rp)}`, 읽기 전용 "
         f"{'예' if not os.access(rp, os.W_OK) else '아니오'}, 커밋하지 않음.",
         f"- 본 평가: `{REL}/{m_rel}`", f"  SHA256 `{ia.sha(f'{HE}/{m_rel}')}`",
         f"- 점검: 행 {len(rows)} (기대 40), 열 구성·issue_id·순서·본문, 중복, 판정 4열 빈칸, 허용 값 밖 → 문제 {len(P)}건.",
         "- issue_id 집합이 `retest_sampling.json` 표본 40건과 같음.", ""]
    L += [f"  - {x}" for x in P]
    L += ["## 1. 열별 일치", "",
          "| 열 | 비교 건 | 일치 | 일치율 | kappa | PABAK | AC1 | 관찰 값 수 |", "|---|---|---|---|---|---|---|---|"]
    for col, name in rob.JUDGE_COLS:
        pr = [(M[i][col], R[i][col]) for i in ids if M[i][col] and R[i][col]]
        m = rob.agreement([x for x, _ in pr], [y for _, y in pr], len(rob.ALLOWED[col]))
        L.append(f"| {name} | {m['n']} | {sum(x == y for x, y in pr)} | {rob.fmt(m['po'])} | {rob.fmt(m['kappa'])} | "
                 f"{rob.fmt(m['pabak'])} | {rob.fmt(m['ac1'])} | {m['values']} |")
    L += ["", "출처: 0절의 두 CSV. PABAK·AC1 의 q 는 허용 값 수(6분류 6, 코드·화면 3, 로그인 레이블 2).", "",
          f"## 2. 불일치 목록 ({len(res['disagree'])}건)", "",
          "| issue_id | 열 | 본 평가 | 재판정 | 본 평가 비고 | 재판정 비고 |", "|---|---|---|---|---|---|"]
    for d in res["disagree"]:
        for c in d["cols"]:
            L.append(f"| {d['issue_id']} | {dict(rob.JUDGE_COLS)[c]} | "
                     f"{d['m'][c]} | {d['r'][c]} | {ia.cell(d['notes_m'], 20)} | {ia.cell(d['notes_r'], 20)} |")
    L += ["", "출처: 0절의 두 CSV", ""]
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"{out}: {res['n']} issues, disagreements {len(res['disagree'])}, problems {len(P)}")


if __name__ == "__main__":
    {"intake": cmd_intake, "final": cmd_final, "summary": cmd_summary, "retest": cmd_retest}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
