"""
사람 평가 결과 접수와 평가자 간 일치도, 합의 회의용 불일치 목록 (API 호출 없음, 검정 없음).

정답 키(key/)와 자동 채점 결과(키워드, string_match, 의미 채점)는 읽지 않는다. A·B 시트는 같은 issue_id 를 쓰므로
(평가자용 시트끼리 issue_id·설명·제안·스크린샷 경로가 모두 같음을 접수 단계에서 확인) 대응표가 필요 없다.
기존 rater_*/ 시트·뷰어는 읽기만 한다. 입력 CSV 는 읽기 전용 속성만 바꾸고 내용은 바꾸지 않는다.

  python experiments/revision/human_eval_intake_all.py intake      # intake_all.md (점검 + 분포)
  python experiments/revision/human_eval_intake_all.py agree       # agreement_main.md, agreement_supp.md
  python experiments/revision/human_eval_intake_all.py consensus   # consensus/ (CSV, HTML, shots/)
  python experiments/revision/human_eval_intake_all.py leak        # consensus/ 누출 점검
"""
import csv
import hashlib
import html
import json
import os
import random
import re
import shutil
import stat
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import make_eval_sheets as mes             # noqa: E402
from experiments.revision import human_eval_compare_robust as rob    # noqa: E402

HE = os.path.join(ROOT, "results", "revision", "human_eval").replace("\\", "/")
REL = "results/revision/human_eval"
DATE = "2026-11-18"
JUDGE = [c for c, _ in rob.JUDGE_COLS]
NAME = dict(rob.JUDGE_COLS)
FILES = [  # (라벨, 평가자, 세트, 제출 파일, 대조 시트, 기대 행 수)
    ("A 본 평가", "A", "main", "rater_A/eval_sheet_A_filled.csv", "rater_A/eval_sheet_A.csv", 444),
    ("A 추가 세트", "A", "supp", "supp_label/rater_A_supp/eval_sheet_A_supp_filled.csv",
     "supp_label/rater_A_supp/eval_sheet_A_supp.csv", 107),
    ("B 본 평가", "B", "main", "rater_B/eval_sheet_B_filled.csv", "rater_B/eval_sheet_B.csv", 204),
    ("B 추가 세트", "B", "supp", "supp_label/rater_B_supp/eval_sheet_B_supp_filled.csv",
     "supp_label/rater_B_supp/eval_sheet_B_supp.csv", 107),
]
SET_NAME = {"main": "본 평가", "supp": "추가 세트"}
BOOT_N, BOOT_SEED = 2000, 20261118
CONS = f"{HE}/consensus"
CONS_COLS = ["번호", "시트 구분", "issue_id", "판정 열", "이슈 설명", "제안", "A의 답", "B의 답", "A의 비고", "B의 비고",
             "합의 답", "합의 사유", "스크린샷"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def rows_of(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def cell(s, n=60):
    s = (s or "").replace("|", "/").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


# ------------------------------------------------------------------ intake
def check(filled, sheet, expected):
    """→ (problems 목록, rows). 고치지 않고 목록만 만든다."""
    P = []
    cols, rows = rows_of(filled)
    scols, srows = rows_of(sheet)
    if cols != mes.SHEET_COLS:
        P.append(f"열 구성이 시트와 다름: {cols}")
    if len(rows) != expected:
        P.append(f"행 수 {len(rows)} (기대 {expected})")
    if len(rows) != len(srows):
        P.append(f"행 수 {len(rows)} ≠ 시트 {len(srows)}")
    ids = [r.get("issue_id", "") for r in rows]
    for i, k in Counter(ids).items():
        if k > 1:
            P.append(f"중복 issue_id {i} ({k}회)")
    S = {r["issue_id"]: r for r in srows}
    for i in sorted(set(ids) - set(S)):
        P.append(f"시트에 없는 issue_id {i}")
    for i in sorted(set(S) - set(ids)):
        P.append(f"제출에 빠진 issue_id {i}")
    if not P and ids != [r["issue_id"] for r in srows]:
        P.append("issue_id 순서가 시트와 다름(집합은 같음)")
    for r in rows:
        i = r.get("issue_id", "")
        if i in S:
            for c in ("screenshot_path", "description", "suggestion"):
                if r.get(c) != S[i][c]:
                    P.append(f"{i}: {c} 가 시트와 다름")
        for c in JUDGE:
            v = r.get(c, "")
            if v == "":
                P.append(f"{i}: {c} 빈칸")
            elif v not in rob.ALLOWED[c]:
                P.append(f"{i}: {c} 허용 값 밖 '{v}'")
    return P, rows


def dist_lines(rows_by_set):
    sets = list(rows_by_set)
    L = ["| 열 | 값 | " + " | ".join(SET_NAME[s] for s in sets) + " |", "|---|---|" + "---|" * len(sets)]
    for c in JUDGE:
        for v in rob.ALLOWED[c]:
            L.append(f"| {NAME[c]} | {v} | " + " | ".join(str(sum(r[c] == v for r in rows_by_set[s])) for s in sets)
                     + " |")
    L.append("| 비고 | 적은 행 | " + " | ".join(str(sum(bool(r["rater_notes"].strip()) for r in rows_by_set[s]))
                                         for s in sets) + " |")
    return L


def notes_lines(rows):
    c = Counter(r["rater_notes"].strip() for r in rows if r["rater_notes"].strip())
    L = ["| 순위 | 비고(앞 60자) | 건수 |", "|---|---|---|"]
    for k, (t, n) in enumerate(c.most_common(20), 1):
        L.append(f"| {k} | {cell(t)} | {n} |")
    return L, len(c)


def cmd_intake():
    out = f"{HE}/intake_all.md"
    if os.path.exists(out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {out}")
    meta, probs, data = [], {}, {}
    for lab, rater, st, f, s, n in FILES:
        p = f"{HE}/{f}"
        os.chmod(p, stat.S_IREAD)                       # 읽기 전용 속성만 (내용 그대로)
        P, rows = check(p, f"{HE}/{s}", n)
        probs[lab], data[(rater, st)] = P, rows
        meta.append((lab, f, s, sha(p), os.path.getsize(p), sha(f"{HE}/{s}"), len(rows), n,
                     not os.access(p, os.W_OK)))
    # 시트끼리 대응 (평가자용 시트만)
    _, sa = rows_of(f"{HE}/{FILES[0][4]}")
    _, sb = rows_of(f"{HE}/{FILES[2][4]}")
    _, saa = rows_of(f"{HE}/{FILES[1][4]}")
    _, sbb = rows_of(f"{HE}/{FILES[3][4]}")
    corr = []
    for lab, x, y in (("본 평가 A 시트 ↔ B 시트", sa, sb), ("추가 세트 A 시트 ↔ B 시트", saa, sbb)):
        dx = {r["issue_id"]: r for r in x}
        dy = {r["issue_id"]: r for r in y}
        com = set(dx) & set(dy)
        same = sum(all(dx[i][c] == dy[i][c] for c in ("description", "suggestion", "screenshot_path")) for i in com)
        corr.append((lab, len(x), len(y), len(com), same))
    total = sum(len(v) for v in probs.values())
    L = ["# 사람 평가 결과 접수 (평가자 A, B: 본 평가와 추가 세트)", "",
         f"작성: `experiments/revision/human_eval_intake_all.py intake` (API 호출 없음). {DATE}.",
         "정답 키(key/)와 자동 채점 결과(키워드, string_match, 의미 채점)는 읽지 않았다.",
         "입력은 평가자 제출 CSV 4개와 평가자에게 준 원 시트 CSV 4개뿐이다.", "",
         "- 제출 파일 위치: 지시문의 `results_A/`, `results_B/` 폴더는 없었다. 평가자가 각 시트 폴더에",
         "  내보낸 파일을 그대로 접수했다(아래 경로). 파일은 옮기지 않았다.",
         "- 접수 시 읽기 전용 속성을 설정했다(내용은 바꾸지 않음). 제출 CSV 는 커밋하지 않는다.",
         "- `rater_A_retest/eval_sheet_A_retest_filled.csv` 도 폴더에 있으나 이번 작업 범위가 아니어서 열지 않았다.", "",
         "## 1. 접수 파일", ""]
    for lab, f, s, h, size, sh, nr, n, ro in meta:
        L += [f"- {lab}: `{REL}/{f}`", f"  SHA256 `{h}`",
              f"  크기 {size} 바이트, 행 {nr} (기대 {n}), 읽기 전용 {'예' if ro else '아니오'}",
              f"  대조 시트 `{REL}/{s}`", f"  시트 SHA256 `{sh}`"]
    L += ["", "## 2. 점검 결과", "",
          "| 파일 | 행 수 | 기대 | 열 구성 | issue_id·순서·본문 | 중복 | 빈칸(판정 4열) | 허용 값 밖 | 문제 수 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for lab, f, s, h, size, sh, nr, n, ro in meta:
        P = probs[lab]
        k = lambda pat: sum(bool(re.search(pat, x)) for x in P)    # noqa: E731
        L.append(f"| {lab} | {nr} | {n} | {'다름' if k('열 구성') else '같음'} | "
                 f"{k('시트에 없는|빠진|순서|시트와 다름') or '일치'} | {k('중복') or 0} | {k('빈칸')} | "
                 f"{k('허용 값 밖')} | {len(P)} |")
    L += ["", "출처: 위 1절의 제출 CSV 와 대조 시트", "",
          "- 필수 열은 판정 4열(6분류, 코드에 존재, 화면에서 보임, 로그인 레이블 지적)이다. 비고는 선택이다.",
          "- 허용 값: 6분류 6개 선택지, 코드·화면 예/아니오/판단 불가, 로그인 레이블 예/아니오.", ""]
    if total:
        L += ["### 문제 목록 (고치지 않음)", "", "| 파일 | 문제 |", "|---|---|"]
        for lab, P in probs.items():
            L += [f"| {lab} | {cell(x, 80)} |" for x in P]
        L += ["", "출처: 위와 같음", ""]
    else:
        L += ["**문제 0건.** 고친 것 없음.", ""]
    L += ["## 3. A·B 시트 대응 방법", "",
          "| 비교 | A 시트 | B 시트 | 같은 issue_id | 그중 설명·제안·스크린샷 경로까지 같음 |", "|---|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in corr]
    L += ["", "출처: 1절의 대조 시트 4개", "",
          "- 평가자용 시트끼리 issue_id 가 같고 본문도 같아서 issue_id 로 바로 대응시켰다. key/ 는 열지 않았다.",
          "- B 본 평가 204건은 모두 A 본 평가 444건 안에 있다.", "",
          "## 4. 답 분포 (평가자별)", ""]
    sec = 1
    for rater in ("A", "B"):
        by = {st: data[(rater, st)] for st in ("main", "supp")}
        L += [f"### 4.{sec} 평가자 {rater} 열별 값 분포 (본 평가 {len(by['main'])}건, 추가 세트 {len(by['supp'])}건)",
              ""] + dist_lines(by) + ["", f"출처: 1절의 평가자 {rater} 제출 CSV 2개", ""]
        sec += 1
        for st in ("main", "supp"):
            nl, nd = notes_lines(by[st])
            L += [f"### 4.{sec} 평가자 {rater} {SET_NAME[st]} 비고 빈도 상위 20 (서로 다른 비고 {nd}종)", "",
                  "같은 문자열(앞뒤 공백 제거)끼리 센다.", ""] + nl + [
                  "", f"출처: `{REL}/{[f for _, r, s, f, *_ in FILES if r == rater and s == st][0]}`", ""]
            sec += 1
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"{out}: problems {total}")
    return total


# ------------------------------------------------------------------ agree
def quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def bootstrap(A, B, ids, n=BOOT_N, seed=BOOT_SEED):
    """이슈 단위 재표집(복원). 열마다 po, kappa, PABAK, AC1 의 2.5·97.5 백분위. kappa 가 정의되지 않은 회차는 뺀다."""
    rng = random.Random(seed)
    acc = {c: {m: [] for m in ("po", "kappa", "pabak", "ac1")} for c in JUDGE}
    skip = Counter()
    for _ in range(n):
        s = [ids[rng.randrange(len(ids))] for _ in ids]
        for c in JUDGE:
            pr = [(A[i][c], B[i][c]) for i in s if A[i][c] and B[i][c]]
            m = rob.agreement([x for x, _ in pr], [y for _, y in pr], len(rob.ALLOWED[c]))
            for k in acc[c]:
                if isinstance(m[k], float):
                    acc[c][k].append(m[k])
                elif k == "kappa":
                    skip[c] += 1
    return {c: {k: (quantile(v, .025), quantile(v, .975), len(v)) for k, v in acc[c].items()} for c in JUDGE}, skip


def extra_sections(res, A, B, ids):
    ci, skip = bootstrap(A, B, ids)
    f = rob.fmt
    L = ["", "## 부록 1. 부트스트랩 95% 구간 (이슈 단위)", "",
         f"비교 이슈 {len(ids)}건을 복원 추출로 {BOOT_N}회 다시 뽑아(시드 {BOOT_SEED}) 백분위 2.5, 97.5 를 적었다.",
         "kappa 가 값 한 가지로 정의되지 않은 회차는 그 열 kappa 구간에서 뺐다(유효 회차 열).",
         "기술 통계용 구간이며 검정이 아니다.", "",
         "| 열 | 일치율 | 일치율 구간 | kappa | kappa 구간 | kappa 유효 회차 | PABAK 구간 | AC1 구간 |",
         "|---|---|---|---|---|---|---|---|"]
    for c in JUDGE:
        m, b = res["cols"][c], ci[c]
        iv = lambda k: "-" if b[k][0] is None else f"{b[k][0]:.3f}–{b[k][1]:.3f}"    # noqa: E731
        L.append(f"| {NAME[c]} | {f(m['po'])} | {iv('po')} | {f(m['kappa'])} | {iv('kappa')} | {b['kappa'][2]} | "
                 f"{iv('pabak')} | {iv('ac1')} |")
    L += ["", "출처: 본문 입력 A, B CSV (재표집은 이 스크립트)", "",
          "## 부록 2. 나머지 열 혼동 행렬 (행 = A, 열 = B)", ""]
    for c in JUDGE[1:]:
        vals = rob.ALLOWED[c]
        cnt = Counter((A[i][c], B[i][c]) for i in ids if A[i][c] and B[i][c])
        L += [f"### {NAME[c]}", "", "| A \\ B | " + " | ".join(vals) + " |", "|" + "---|" * (len(vals) + 1)]
        L += [f"| {x} | " + " | ".join(str(cnt[(x, y)]) for y in vals) + " |" for x in vals]
        L += ["", "출처: 본문 입력 A, B CSV", ""]
    return L


def run_agree(a_rel, b_rel, merge, out, title_note):
    if os.path.exists(out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {out}")
    A, B = rob.read(f"{HE}/{a_rel}"), rob.read(f"{HE}/{b_rel}")
    res = rob.compare(A, B, merge)
    ids = sorted(set(A) & set(B))
    md = rob.report(res, f"{REL}/{a_rel}", f"{REL}/{b_rel}", merge).rstrip("\n").split("\n")
    md[0] += f" — {title_note}"
    md.insert(2, f"{DATE}. 접수 점검: `{REL}/intake_all.md`. 정답 키·자동 채점 결과·층 정보 미사용.")
    md += extra_sections(res, A, B, ids)
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(md).rstrip("\n") + "\n")
    print(f"{out}: {res['n_common']} issues, disagreements {len(res['disagree'])}")


def cmd_agree():
    run_agree(FILES[0][3], FILES[2][3], "overlap", f"{HE}/agreement_main.md", "본 평가 (B 시트 204건)")
    run_agree(FILES[1][3], FILES[3][3], "same", f"{HE}/agreement_supp.md", "추가 세트 (107건, 층 구분 없음)")


# ------------------------------------------------------------------ consensus
def viewer_src(path):
    s = open(path, encoding="utf-8").read()
    return json.loads(re.search(r"const SRC = (.*?);\n", s).group(1).replace("<\\/", "</"))


def build_rows():
    out = []
    for st, (ia, ib) in (("main", (0, 2)), ("supp", (1, 3))):
        A, B = rob.read(f"{HE}/{FILES[ia][3]}"), rob.read(f"{HE}/{FILES[ib][3]}")
        ids = sorted(set(A) & set(B))
        for c in JUDGE:
            for i in ids:
                if A[i][c] != B[i][c]:
                    out.append({"시트 구분": SET_NAME[st], "issue_id": i, "판정 열": NAME[c],
                                "이슈 설명": A[i]["description"], "제안": A[i]["suggestion"], "A의 답": A[i][c],
                                "B의 답": B[i][c], "A의 비고": A[i]["rater_notes"], "B의 비고": B[i]["rater_notes"],
                                "합의 답": "", "합의 사유": "", "스크린샷": A[i]["screenshot_path"], "_st": st})
    for k, r in enumerate(out, 1):
        r["번호"] = k
    return out


PAGE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>합의 회의 시트</title>
<style>
:root{--bg:#fafaf8;--fg:#1d1d1b;--mute:#6b6b66;--card:#fff;--line:#deded8;--a:#1f5fa8;--b:#a8521f;--ok:#2e7d32}
@media (prefers-color-scheme:dark){:root{--bg:#18181a;--fg:#ececea;--mute:#a3a39e;--card:#232326;--line:#3a3a3e;
--a:#7fb0ea;--b:#eaa77f;--ok:#7fcf84}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;
display:flex;flex-wrap:wrap;gap:8px;align-items:center}
header h1{font-size:17px;margin:0 12px 0 0}header .sp{flex:1}
select,button,textarea{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:6px}
button,select{padding:4px 10px;cursor:pointer}main{max-width:1100px;margin:0 auto;padding:12px 16px 60px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:12px 0}
.card.done{border-left:5px solid var(--ok)}.meta{color:var(--mute);font-size:13px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:8px 0}.ans{padding:8px;border-radius:6px;
border:1px solid var(--line)}.ans b{display:block;font-size:13px}.A b{color:var(--a)}.B b{color:var(--b)}
.txt{white-space:pre-wrap;margin:4px 0}.lbl{font-size:13px;color:var(--mute)}
textarea{width:100%;min-height:52px;padding:6px}img{max-width:100%;border:1px solid var(--line);margin-top:6px}
pre{max-height:360px;overflow:auto;background:var(--bg);border:1px solid var(--line);padding:8px;font-size:12px;
white-space:pre-wrap;word-break:break-all}details{margin-top:6px}
@media (max-width:640px){.grid{grid-template-columns:1fr}}
</style></head><body>
<header><h1>합의 회의 시트</h1><label>시트 <select id="fs"><option value="">전체</option></select></label>
<label>판정 열 <select id="fc"><option value="">전체</option></select></label>
<label>상태 <select id="fd"><option value="">전체</option><option value="todo">합의 전</option>
<option value="done">합의 완료</option></select></label><span class="sp"></span><span id="prog"></span>
<button id="ex">CSV 내보내기</button><label><button id="imb">CSV 불러오기</button>
<input id="im" type="file" accept=".csv" hidden></label></header>
<main id="list"></main>
<script>
const ROWS = __ROWS__;
const SRC = __SRC__;
const CHOICES = __CHOICES__;
const COLS = __COLS__;
const KEY = "human_eval_consensus_v1";
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { state = {}; }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} prog(); }
function k(r){ return r["번호"] + "|" + r["issue_id"] + "|" + r["판정 열"]; }
function el(t, cls, txt){ const e = document.createElement(t); if (cls) e.className = cls;
  if (txt !== undefined) e.textContent = txt; return e; }
function prog(){ const d = ROWS.filter(r => (state[k(r)] || {}).ans).length;
  document.getElementById("prog").textContent = "합의 " + d + " / " + ROWS.length; }
function fill(id, vals){ const s = document.getElementById(id);
  [...new Set(vals)].forEach(v => { const o = el("option", "", v); o.value = v; s.appendChild(o); });
  s.onchange = render; }
fill("fs", ROWS.map(r => r["시트 구분"])); fill("fc", ROWS.map(r => r["판정 열"]));
document.getElementById("fd").onchange = render;
function render(){
  const fs = document.getElementById("fs").value, fc = document.getElementById("fc").value,
        fd = document.getElementById("fd").value, L = document.getElementById("list");
  L.textContent = "";
  ROWS.forEach(r => {
    const st = state[k(r)] || {};
    if (fs && r["시트 구분"] !== fs) return; if (fc && r["판정 열"] !== fc) return;
    if (fd === "done" && !st.ans) return; if (fd === "todo" && st.ans) return;
    const c = el("div", "card" + (st.ans ? " done" : ""));
    c.appendChild(el("div", "meta", "#" + r["번호"] + " · " + r["시트 구분"] + " · " + r["issue_id"] +
      " · 판정 열: " + r["판정 열"]));
    c.appendChild(el("div", "lbl", "이슈 설명")); c.appendChild(el("div", "txt", r["이슈 설명"]));
    c.appendChild(el("div", "lbl", "제안")); c.appendChild(el("div", "txt", r["제안"]));
    const g = el("div", "grid");
    [["A", "A의 답", "A의 비고"], ["B", "B의 답", "B의 비고"]].forEach(([w, a, n]) => {
      const box = el("div", "ans " + w); box.appendChild(el("b", "", "평가자 " + w + ": " + r[a]));
      box.appendChild(el("div", "txt", r[n] ? "비고: " + r[n] : "비고 없음")); g.appendChild(box); });
    c.appendChild(g);
    const sel = el("select"); sel.appendChild(el("option", "", "합의 답 선택"));
    sel.firstChild.value = "";
    CHOICES[r["판정 열"]].forEach(v => { const o = el("option", "", v); o.value = v; sel.appendChild(o); });
    sel.value = st.ans || "";
    sel.onchange = () => { state[k(r)] = Object.assign(state[k(r)] || {}, {ans: sel.value}); save();
      c.className = "card" + (sel.value ? " done" : ""); };
    const ta = el("textarea"); ta.placeholder = "합의 사유"; ta.value = st.why || "";
    ta.oninput = () => { state[k(r)] = Object.assign(state[k(r)] || {}, {why: ta.value}); save(); };
    const lab = el("div", "lbl", "합의 답"); c.appendChild(lab); c.appendChild(sel);
    c.appendChild(el("div", "lbl", "합의 사유")); c.appendChild(ta);
    const d1 = el("details"); d1.appendChild(el("summary", "", "스크린샷"));
    d1.ontoggle = () => { if (d1.open && !d1.querySelector("img")) { const im = el("img");
      im.src = r["스크린샷"]; im.alt = "스크린샷"; d1.appendChild(im); } };
    c.appendChild(d1);
    if (SRC[r["스크린샷"]]) { const d2 = el("details"); d2.appendChild(el("summary", "", "페이지 코드"));
      d2.ontoggle = () => { if (d2.open && !d2.querySelector("pre")) d2.appendChild(el("pre", "", SRC[r["스크린샷"]])); };
      c.appendChild(d2); }
    L.appendChild(c);
  });
  prog();
}
function q(v){ v = String(v == null ? "" : v); return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
document.getElementById("ex").onclick = () => {
  const lines = [COLS.map(q).join(",")];
  ROWS.forEach(r => { const st = state[k(r)] || {};
    lines.push(COLS.map(c => q(c === "합의 답" ? (st.ans || "") : c === "합의 사유" ? (st.why || "") : r[c])).join(",")); });
  const b = new Blob(["﻿" + lines.join("\r\n") + "\r\n"], {type: "text/csv;charset=utf-8"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(b);
  a.download = "disagreement_for_consensus_filled.csv"; document.body.appendChild(a); a.click(); a.remove();
};
function parse(t){ const out = []; let row = [], f = "", i = 0, inq = false;
  for (; i < t.length; i++) { const ch = t[i];
    if (inq) { if (ch === '"') { if (t[i + 1] === '"') { f += '"'; i++; } else inq = false; } else f += ch; }
    else if (ch === '"') inq = true; else if (ch === ",") { row.push(f); f = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && t[i + 1] === "\n") i++; row.push(f); out.push(row);
      row = []; f = ""; } else f += ch; }
  if (f !== "" || row.length) { row.push(f); out.push(row); } return out; }
document.getElementById("imb").onclick = () => document.getElementById("im").click();
document.getElementById("im").onchange = ev => { const file = ev.target.files[0]; if (!file) return;
  file.text().then(t => { const R = parse(t.replace(/^﻿/, "")), h = R.shift() || [];
    if (h.join(",") !== COLS.join(",")) { document.getElementById("prog").textContent =
      "불러오기 거부: 이 시트에서 내보낸 CSV 가 아님"; return; }
    const byKey = {}; ROWS.forEach(r => byKey[k(r)] = r); let n = 0, bad = 0;
    R.forEach(v => { if (v.length !== COLS.length) return; const o = {}; COLS.forEach((c, j) => o[c] = v[j]);
      const key = o["번호"] + "|" + o["issue_id"] + "|" + o["판정 열"];
      if (!byKey[key]) { bad++; return; }
      if (o["합의 답"] && !CHOICES[o["판정 열"]].includes(o["합의 답"])) { bad++; return; }
      state[key] = {ans: o["합의 답"], why: o["합의 사유"]}; n++; });
    save(); render(); document.getElementById("prog").textContent += " (불러옴 " + n + ", 거부 " + bad + ")"; });
  ev.target.value = ""; };
render();
</script></body></html>
"""


def js(o):
    return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")


def cmd_consensus():
    if os.path.exists(CONS):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {CONS}")
    rows = build_rows()
    src_main = viewer_src(f"{HE}/rater_A/viewer_A.html")
    src_supp = viewer_src(f"{HE}/supp_label/rater_A_supp/viewer_A_supp.html")
    shot_dir = {"main": f"{HE}/rater_A", "supp": f"{HE}/supp_label/rater_A_supp"}
    os.makedirs(f"{CONS}/shots")
    src, seen = {}, {}
    for r in rows:
        s = r["스크린샷"]
        if s in seen and seen[s] != r["_st"]:
            raise SystemExit(f"스크린샷 이름 충돌: {s}")
        seen[s] = r["_st"]
        if not os.path.exists(f"{CONS}/{s}"):
            shutil.copyfile(f"{shot_dir[r['_st']]}/{s}", f"{CONS}/{s}")
        sm = src_main if r["_st"] == "main" else src_supp
        if s in sm:
            src[s] = sm[s]
    with open(f"{CONS}/disagreement_for_consensus.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CONS_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    view = [{c: r[c] for c in CONS_COLS if c not in ("합의 답", "합의 사유")} for r in rows]
    choices = {NAME[c]: rob.ALLOWED[c] for c in JUDGE}
    page = (PAGE.replace("__ROWS__", js(view)).replace("__SRC__", js(src)).replace("__CHOICES__", js(choices))
            .replace("__COLS__", js(CONS_COLS)))
    open(f"{CONS}/consensus_viewer.html", "w", encoding="utf-8", newline="\n").write(page)
    c = Counter((r["시트 구분"], r["판정 열"]) for r in rows)
    print(f"{CONS}: {len(rows)} rows, shots {len(seen)}, src {len(src)}; " +
          ", ".join(f"{a}/{b} {n}" for (a, b), n in sorted(c.items())))


# ------------------------------------------------------------------ leak
TERMS = {
    "결함 유형(영문)": r"Poor Contrast|Mobile Layout|Button Area|Terminology|Duplicate ID",
    "페이지 ID": r"page_\d+|e9_\d+",
    "런 이름": r"E\d-[A-Za-z0-9]|E5b|\bE\d\b",
    "주입 식별자": r"DEF_",
    "조건명": r"\bRAG\b|oracle|\bfixed\b|baseline|nominal|effective",
    "채점기": r"string_match|semantic|키워드|keyword|채점|grader|ground.?truth|정답",
    "층 정보": r"\bS[123]\b|stratum|strata|층",
    "키 경로": r"key/|_key|supp_key|sample_selection",
}


def cmd_leak():
    hits, files = [], []
    nonblank = 0

    def scan(text, where, file):
        for cat, pat in TERMS.items():
            for m in re.finditer(pat, text):
                ctx = text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ").replace("|", "/")
                hits.append({"file": file, "where": where, "category": cat, "match": m.group(0), "context": ctx})

    for root, _, fs in os.walk(CONS):
        for fn in sorted(fs):
            p = os.path.join(root, fn).replace("\\", "/")
            rel = p[len(HE) + 1:]
            files.append(rel)
            scan(rel, "파일명", rel)
            if fn.endswith(".csv"):
                cols, rows = rows_of(p)
                scan(",".join(cols), "CSV 열 이름", rel)
                if cols != CONS_COLS:
                    hits.append({"file": rel, "where": "CSV 열 구성", "category": "열 다름", "match": str(cols),
                                 "context": ""})
                for r in rows:
                    nonblank += bool(r["합의 답"]) + bool(r["합의 사유"])
                    for c, v in r.items():
                        if c not in ("이슈 설명", "제안"):
                            scan(v, f"CSV 값({c})", rel)
            elif fn.endswith(".html"):
                s = open(p, encoding="utf-8").read()
                m_rows = re.search(r"const ROWS = (.*?);\n", s)
                m_src = re.search(r"const SRC = (.*?);\n", s)
                scan(s[:m_rows.start()] + s[m_src.end():], "뷰어 코드·마크업", rel)
                for r in json.loads(m_rows.group(1).replace("<\\/", "</")):
                    for c, v in r.items():
                        if c not in ("이슈 설명", "제안"):
                            scan(str(v), f"뷰어 데이터({c})", rel)
                for shot, h in json.loads(m_src.group(1).replace("<\\/", "</")).items():
                    scan(h, "포함된 페이지 HTML", rel)
            elif fn.endswith(".png"):
                from experiments.revision import human_eval_prep as hp
                if hp.png_text_chunks(p):
                    hits.append({"file": rel, "where": "PNG 메타데이터", "category": "메타데이터 있음", "match": "",
                                 "context": ""})
    # 판단: 평가자 본인이 쓴 비고·답은 평가자 입력이라 누출이 아니다(내용은 표에 남긴다).
    judge = {"CSV 값(A의 비고)": "평가자 A 본인 비고", "CSV 값(B의 비고)": "평가자 B 본인 비고",
             "뷰어 데이터(A의 비고)": "평가자 A 본인 비고", "뷰어 데이터(B의 비고)": "평가자 B 본인 비고",
             "CSV 값(A의 답)": "평가자 답(6분류 선택지)", "CSV 값(B의 답)": "평가자 답(6분류 선택지)",
             "뷰어 데이터(A의 답)": "평가자 답(6분류 선택지)", "뷰어 데이터(B의 답)": "평가자 답(6분류 선택지)"}
    for h in hits:
        if h["where"] == "뷰어 코드·마크업" and h["match"] == "fixed" and "position:fixed" in h["context"]:
            h["judge"] = "CSS position:fixed"
        else:
            h["judge"] = judge.get(h["where"], "확인 필요")
    json.dump({"files": files, "hits": hits, "nonblank_consensus_cells": nonblank},
              open(f"{HE}/leak_audit_consensus.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = Counter((h["file"], h["where"], h["category"], h["match"], h["judge"]) for h in hits)
    leaks = [x for x in c if x[4] == "확인 필요"]
    L = ["# 합의 회의 시트 정보 누출 점검", "",
         f"작성: `experiments/revision/human_eval_intake_all.py leak` (API 호출 없음). {DATE}.",
         "검사 대상: `results/revision/human_eval/consensus/` 의 모든 파일. 이슈 설명·제안 본문은 평가자가 이미 본",
         "LLM 문장이라 제외했다. 검색어: 결함 유형 영문명, 페이지 ID, 런 이름, 주입 식별자, 조건명, 채점기, 층 정보,",
         "키 경로. 원 결과: `results/revision/human_eval/leak_audit_consensus.json`.", "",
         f"검사한 파일 {len(files)}개.", "", "## 1. 검색 결과", "",
         "| 파일 | 위치 | 분류 | 일치 | 건수 | 판단 |", "|---|---|---|---|---|---|"]
    for (fi, w, cat, m, j), k in sorted(c.items()):
        L.append(f"| {cell(fi, 30)} | {w} | {cat} | {m} | {k} | {j} |")
    if not c:
        L.append("| - | - | - | - | 0 | - |")
    L += ["", "출처: `results/revision/human_eval/leak_audit_consensus.json`", "",
          "## 2. 추가 점검", "", "| 점검 | 결과 |", "|---|---|",
          f"| CSV 의 합의 답·합의 사유 칸 중 값이 있는 칸 | {nonblank} |",
          "| CSV 열에 채점기 결과·정답 키·실험 조건·층 열 | 없음(열 구성 고정) |", "", "출처: 위와 같음", "",
          f"**누출로 판단한 항목: {len(leaks) + (1 if nonblank else 0)}건.**", ""]
    out = f"{HE}/leak_audit_consensus.md"
    if os.path.exists(out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {out}")
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"{out}: hits {len(hits)}, leaks {len(leaks)}, nonblank {nonblank}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"intake": cmd_intake, "agree": cmd_agree, "consensus": cmd_consensus, "leak": cmd_leak}.get(
        cmd, lambda: sys.exit(__doc__))()
