"""
사람 평가 시트와 로컬 HTML 뷰어 생성 (API 호출 없음). 동결된 make_eval_sheets.build 를 그대로 호출한 뒤 평가자별 폴더로 나눈다.

  python experiments/revision/build_human_eval.py      # 시드 A 20261112, B 20261113 (analysis_plan.md 10절 4항)

출력: results/revision/human_eval/
  rater_A/  eval_sheet_A.csv, viewer_A.html, shots/{토큰}.png, rater_guidelines.md   ← 평가자 A 에게 준다
  rater_B/  eval_sheet_B.csv, viewer_B.html, shots/{토큰}.png (B 페이지만), rater_guidelines.md ← 평가자 B 에게 준다
  key/      eval_key.csv, sampling_manifest.json, page_html_map.csv   ← 평가자에게 주지 않는다
  README.md 표본 요약 (평가자에게 주지 않는다)

뷰어: 외부 네트워크 없이 열리는 단일 HTML. 행마다 스크린샷, 이슈 설명·제안, 그 페이지의 HTML 원문(testbed_200 원본 파일,
표시만 하고 렌더링하지 않음), 판정 입력. 입력은 브라우저 localStorage 에 저장되고 'CSV 내보내기'로 시트와 같은 열의 CSV 를 받는다.
뷰어에 넣는 데이터 = 시트 행(issue_id, screenshot_path, description, suggestion) + 스크린샷 토큰별 HTML 원문뿐이다.
"""
import csv
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import make_eval_sheets as mes    # noqa: E402

OUT = "results/revision/human_eval"
SEED_A, SEED_B = 20261112, 20261113
RUN = "E1-R1"
GUIDE = "docs/rater_guidelines.md"
VIEW_FIELDS = ["issue_id", "screenshot_path", "description", "suggestion"]
INPUT_FIELDS = ["rater_category", "exists_in_code", "visible_on_screen", "login_link_label_concern", "rater_notes"]
# 평가자 폴더에 나오면 안 되는 문자열 (테스트도 같은 목록을 쓴다)
FORBIDDEN = [r"page_\d{3}", r"testbed_200", r"localhost:\d+", r"\bE[1-9]-", r"\bE9", r"DEF_[A-Z]+_\d+",
             r"Poor Contrast Ratio", r"Mobile Layout Breakage", r"Button Area Clipping", r"Standard Terminology Violation",
             r"Duplicate ID Markup Error", r"nominal", r"effective_", r"stratum", r"in_sheet_B", r"keyword_types",
             r"semantic_pass1", r"string_match", r"injected", r"ground_truth", r"\bcontrol\b"]


def read_sheet(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


VIEWER = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>평가 시트 __NAME__</title>
<style>
:root{--bg:#f6f7f9;--fg:#1d1d1d;--card:#fff;--line:#d8dbe0;--accent:#1f5fbf;--muted:#666}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,"Malgun Gothic",sans-serif;font-size:15px}
header{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--line);padding:8px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;z-index:2}
header b{font-size:16px}button{font:inherit;padding:6px 12px;border:1px solid var(--line);border-radius:6px;background:#fff;cursor:pointer}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
main{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:16px;padding:16px}
@media (max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.shot img{max-width:100%;border:1px solid var(--line)}
pre{white-space:pre-wrap;word-break:break-all;background:#f2f2f2;padding:8px;border-radius:6px;max-height:320px;overflow:auto;font-size:12.5px}
.q{margin:10px 0}.q label{margin-right:12px;white-space:nowrap}.q .t{font-weight:600;display:block;margin-bottom:4px}
textarea{width:100%;min-height:60px;font:inherit}select{font:inherit;padding:4px}
.muted{color:var(--muted);font-size:13px}.done{color:#1a7f37}
</style></head><body>
<header><b>평가 시트 __NAME__</b><span id="pos"></span><span id="prog" class="muted"></span>
<button id="prev">◀ 이전</button><button id="next">다음 ▶</button>
<label class="muted">이동 <input id="jump" type="number" min="1" style="width:70px"></label>
<button id="export" class="primary">CSV 내보내기</button></header>
<main>
<section class="card shot"><div class="muted">스크린샷 (1280x800)</div><img id="img" alt="페이지 스크린샷"></section>
<section>
<div class="card"><div class="muted">이슈 ID <span id="iid"></span></div>
<p><b>이슈 설명</b><br><span id="desc"></span></p><p><b>제안</b><br><span id="sug"></span></p></div>
<div class="card" style="margin-top:12px"><div class="muted">페이지 HTML 원문 (표시만, 렌더링하지 않음)</div><pre id="src"></pre></div>
<div class="card" style="margin-top:12px">
<div class="q"><span class="t">1. 분류 (rater_category)</span><select id="rater_category"><option value="">선택</option>__CATS__</select></div>
<div class="q"><span class="t">2. 코드에 존재하는가 (exists_in_code)</span>__R_exists_in_code__</div>
<div class="q"><span class="t">3. 화면에서 보이는가 (visible_on_screen)</span>__R_visible_on_screen__</div>
<div class="q"><span class="t">4. 로그인 링크 레이블 지적 (login_link_label_concern)</span>__R_login_link_label_concern__</div>
<div class="q"><span class="t">비고 (rater_notes)</span><textarea id="rater_notes"></textarea></div>
<div id="saved" class="muted"></div></div>
</section></main>
<script>
const ROWS = __ROWS__;
const SRC = __SRC__;
const COLS = __COLS__;
const KEY = "human_eval___NAME__";
let st = {}; try { st = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { st = {}; }
let i = 0; try { i = +(localStorage.getItem(KEY + "_pos") || 0); } catch (e) {}
const $ = id => document.getElementById(id);
function save(){ try { localStorage.setItem(KEY, JSON.stringify(st)); localStorage.setItem(KEY + "_pos", i); $("saved").textContent = "브라우저에 저장됨"; } catch (e) { $("saved").textContent = "저장 실패: CSV 로 내보내세요"; } }
function cur(){ return st[ROWS[i].issue_id] || (st[ROWS[i].issue_id] = {}); }
function complete(r){ const v = st[r.issue_id] || {}; return v.rater_category && v.exists_in_code && v.visible_on_screen && v.login_link_label_concern; }
function show(){
  const r = ROWS[i], v = cur();
  $("pos").textContent = (i + 1) + " / " + ROWS.length; $("iid").textContent = r.issue_id;
  $("img").src = r.screenshot_path; $("desc").textContent = r.description; $("sug").textContent = r.suggestion;
  $("src").textContent = SRC[r.screenshot_path] || "(HTML 없음)";
  $("rater_category").value = v.rater_category || ""; $("rater_notes").value = v.rater_notes || "";
  for (const k of ["exists_in_code","visible_on_screen","login_link_label_concern"])
    document.querySelectorAll('input[name="'+k+'"]').forEach(e => e.checked = (e.value === v[k]));
  $("prog").textContent = "완료 " + ROWS.filter(complete).length + "건"; $("saved").textContent = "";
}
$("rater_category").onchange = e => { cur().rater_category = e.target.value; save(); show(); };
$("rater_notes").oninput = e => { cur().rater_notes = e.target.value; save(); };
document.querySelectorAll("input[type=radio]").forEach(e => e.onchange = () => { cur()[e.name] = e.value; save(); show(); });
$("prev").onclick = () => { if (i > 0) { i--; save(); show(); } };
$("next").onclick = () => { if (i < ROWS.length - 1) { i++; save(); show(); } };
$("jump").onchange = e => { const n = +e.target.value; if (n >= 1 && n <= ROWS.length) { i = n - 1; save(); show(); } };
function q(s){ s = (s == null ? "" : String(s)); return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
$("export").onclick = () => {
  const lines = [COLS.join(",")];
  for (const r of ROWS) { const v = st[r.issue_id] || {}; lines.push(COLS.map(c => q(c in r ? r[c] : (v[c] || ""))).join(",")); }
  const blob = new Blob(["﻿" + lines.join("\r\n")], {type: "text/csv"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "eval_sheet___NAME___filled.csv"; a.click();
};
show();
</script></body></html>
"""


def radios(name):
    return "".join(f'<label><input type="radio" name="{name}" value="{v}"> {v}</label>'
                   for v in (["예", "아니오"] if name == "login_link_label_concern" else ["예", "아니오", "판단 불가"]))


def make_viewer(name, rows, src_by_shot):
    view_rows = [{k: r[k] for k in VIEW_FIELDS} for r in rows]
    used = {r["screenshot_path"] for r in rows}
    src = {k: v for k, v in src_by_shot.items() if k in used}
    out = VIEWER.replace("__NAME__", name)
    out = out.replace("__CATS__", "".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>'
                                          for c in mes.CATEGORY_CHOICES))
    for k in ("exists_in_code", "visible_on_screen", "login_link_label_concern"):
        out = out.replace(f"__R_{k}__", radios(k))
    js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
    out = out.replace("__ROWS__", js(view_rows)).replace("__SRC__", js(src)).replace("__COLS__", js(mes.SHEET_COLS))
    from experiments.revision import viewer_add_import as vai    # 2026-11-14: CSV 불러오기 (기존 뷰어에도 같은 코드로 추가함)
    return vai.add_import(out)


def main():
    if os.path.exists(OUT) and os.listdir(OUT):
        raise SystemExit(f"output folder not empty: {OUT}")
    build = os.path.join(OUT, "_build")
    m = mes.build(RUN, SEED_A, SEED_B, build, "results/revision/runs", "testbed_200/dataset_metadata.json",
                  "results/revision/ground_truth.csv")
    key = list(csv.DictReader(open(os.path.join(build, "eval_key.csv"), encoding="utf-8")))
    tok2page = {f"shots/{r['page_token']}.png": r["page_id"] for r in key}
    src_by_shot = {}
    for shot, page in tok2page.items():
        src_by_shot[shot] = open(f"testbed_200/{page}.html", encoding="utf-8").read()
    for side in ("A", "B"):
        d = os.path.join(OUT, f"rater_{side}")
        os.makedirs(os.path.join(d, "shots"))
        rows = read_sheet(os.path.join(build, f"eval_sheet_{side}.csv"))
        shutil.move(os.path.join(build, f"eval_sheet_{side}.csv"), os.path.join(d, f"eval_sheet_{side}.csv"))
        for shot in sorted({r["screenshot_path"] for r in rows}):
            shutil.copyfile(os.path.join(build, shot), os.path.join(d, shot))
        open(os.path.join(d, f"viewer_{side}.html"), "w", encoding="utf-8", newline="\n").write(
            make_viewer(side, rows, src_by_shot))
        shutil.copyfile(GUIDE, os.path.join(d, "rater_guidelines.md"))
    kd = os.path.join(OUT, "key")
    os.makedirs(kd)
    for f in ("eval_key.csv", "sampling_manifest.json"):
        shutil.move(os.path.join(build, f), os.path.join(kd, f))
    with open(os.path.join(kd, "page_html_map.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["screenshot_path", "page_id", "html_source"])
        for shot, page in sorted(tok2page.items()):
            w.writerow([shot, page, f"testbed_200/{page}.html"])
    shutil.rmtree(build)
    write_readme(m, key)
    print(json.dumps({k: m[k] for k in ("pages_A", "pages_B", "issues_A", "issues_B")}, ensure_ascii=False))


def write_readme(m, key):
    nom, _, _ = mes.load_labels("testbed_200/dataset_metadata.json", "results/revision/ground_truth.csv")
    a = mes.select_pages_a(nom, m["seed_a"])
    b = mes.select_pages_b(a, m["seed_b"])
    nominal = {p: (";".join(nom[p]), p in b) for p in a}
    types = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping", "Standard Terminology Violation",
             "Duplicate ID Markup Error"]
    sh = {"Poor Contrast Ratio": "명도 대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼 잘림",
          "Standard Terminology Violation": "표준 용어", "Duplicate ID Markup Error": "중복 ID"}
    pages_B = {p for p, (_, b) in nominal.items() if b}
    L = ["# 사람 평가 시트 (E1-R1)", "",
         "작성: `experiments/revision/build_human_eval.py` → 동결된 `make_eval_sheets.build` 호출 (API 호출 없음).",
         f"시드: A 표본·토큰·섞기 {m['seed_a']}, B 표본·섞기 {m['seed_b']} (analysis_plan.md 10절 4항).",
         "**평가자에게는 `rater_A/` 또는 `rater_B/` 폴더만 준다.** `key/` 와 이 README 는 주지 않는다.", "",
         "## 표본 크기", "", "| 시트 | 페이지 | 이슈 | 예상 소요 (행당 2~3분) |", "|---|---|---|---|",
         f"| A | {m['pages_A']} | {m['issues_A']} | {m['issues_A'] * 2 / 60:.1f}~{m['issues_A'] * 3 / 60:.1f}시간 |",
         f"| B | {m['pages_B']} | {m['issues_B']} | {m['issues_B'] * 2 / 60:.1f}~{m['issues_B'] * 3 / 60:.1f}시간 |", "",
         "행당 2~3분은 `docs/rater_guidelines.md` 4절의 목표 시간이다(연습 문항 시간 제외).", "",
         "## 표본 층 (페이지 수)", "", "| 층 | A | B |", "|---|---|---|"]
    for s in mes.STRATA:
        L.append(f"| {s} | {m['strata_A'][s]} | {m['strata_B'].get(s, 0)} |")
    L += ["", "## 주입 유형별 포함 페이지 수 (nominal, 한 페이지에 유형 2개면 둘 다 셈)", "",
          "| 유형 | A | B |", "|---|---|---|"]
    for t in types:
        L.append(f"| {sh[t]} | {sum(1 for p, (n, _) in nominal.items() if t in n.split(';'))} | "
                 f"{sum(1 for p in pages_B if t in nominal[p][0].split(';'))} |")
    L.append(f"| 대조군 (주입 없음) | {sum(1 for p, (n, _) in nominal.items() if not n)} | "
             f"{sum(1 for p in pages_B if not nominal[p][0])} |")
    L += ["", f"이슈가 없는 A 페이지: {len(m['pages_without_issues_A'])}개 (시트에 행이 없음; key/sampling_manifest.json).",
          "위 페이지 수는 이슈가 없는 페이지를 포함한 표본 전체 기준이다(같은 시드로 표본 함수를 다시 호출해 셈).", "",
          "## 가림 확인", "", "- 시트·뷰어에는 issue_id(무작위 토큰), 스크린샷 경로(무작위 토큰), 설명, 제안, 판정 칸만 있다.",
          "- 뷰어의 HTML 원문은 testbed_200 원본 파일 그대로다(페이지 ID·주입 표기 없음, 테스트로 확인).",
          "- 테스트: `tests/test_human_eval_blinding.py`.", "",
          "출처:", "- `results/revision/human_eval/key/sampling_manifest.json`", "- `results/revision/human_eval/key/eval_key.csv`", ""]
    open(os.path.join(OUT, "README.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
