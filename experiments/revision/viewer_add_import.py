"""
평가 뷰어에 'CSV 불러오기' 추가 (2026-11-14 연구자 지시, API 호출 없음).

- 기존 뷰어의 데이터(ROWS, SRC, COLS), 저장 키(KEY = human_eval_{이름}), 저장 구조(st[issue_id] = {열: 값}),
  자동 저장과 CSV 내보내기는 그대로 둔다. 버튼·대화상자 마크업과 불러오기 스크립트만 끼워 넣는다.
- 불러오기: 이 뷰어에서 내보낸 CSV(열 구성이 COLS 와 정확히 같고, issue_id 집합이 이 시트와 정확히 같음)만 받는다.
  다른 시트(issue_id 집합이 다름)나 열이 다른 파일, 허용되지 않은 값이 있는 파일은 거부한다.
  비어 있는 칸은 CSV 값으로 채우고, 이미 입력된 값과 다르면 대화상자에서 묻는다(기본 = 덮어쓰지 않음).
  CSV 의 빈 칸은 기존 입력을 지우지 않는다.

  python experiments/revision/viewer_add_import.py            # rater_A, rater_B, pilot_rater 뷰어를 고침 (이미 고친 파일은 건너뜀)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HE = os.path.join(ROOT, "results", "revision", "human_eval")
TARGETS = [("rater_A", "viewer_A.html"), ("rater_B", "viewer_B.html"), ("pilot_rater", "viewer_pilot.html")]
MARK = "<!-- csv-import v1 -->"

BUTTONS = ('<button id="importBtn">CSV 불러오기</button><input id="importFile" type="file" accept=".csv,text/csv" '
           'style="display:none"><span id="msg" class="muted"></span>')
MODAL = """<div id="modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:5">
<div class="card" style="max-width:560px;margin:15vh auto;background:#fff"><p id="modalText"></p>
<button id="keepBtn" class="primary">덮어쓰지 않음 (기존 입력 유지)</button> <button id="overBtn">CSV 값으로 덮어쓰기</button></div></div>
""" + MARK
IMPORT_JS = r"""
/* csv-import v1: 이 뷰어에서 내보낸 CSV 로 입력 되살리기. 저장 키와 저장 구조는 그대로. */
const INPUTS = ["rater_category","exists_in_code","visible_on_screen","login_link_label_concern","rater_notes"];
const VALID = {rater_category: Array.from($("rater_category").options).map(o => o.value).filter(Boolean),
  exists_in_code: ["예","아니오","판단 불가"], visible_on_screen: ["예","아니오","판단 불가"], login_link_label_concern: ["예","아니오"]};
function parseCSV(t){
  t = t.replace(/^﻿/, ""); const out = []; let row = [], f = "", q = false;
  for (let k = 0; k < t.length; k++){
    const ch = t[k];
    if (q){ if (ch === '"'){ if (t[k+1] === '"'){ f += '"'; k++; } else q = false; } else f += ch; }
    else if (ch === '"') q = true;
    else if (ch === ","){ row.push(f); f = ""; }
    else if (ch === "\n" || ch === "\r"){ if (ch === "\r" && t[k+1] === "\n") k++; row.push(f); out.push(row); row = []; f = ""; }
    else f += ch;
  }
  if (f !== "" || row.length){ row.push(f); out.push(row); }
  return out.filter(r => !(r.length === 1 && r[0] === ""));
}
function msg(s){ $("msg").textContent = s; }
function importText(text){
  const rows = parseCSV(text);
  if (!rows.length || rows[0].join("\u0001") !== COLS.join("\u0001")) { msg("불러오기 거부: 열 구성이 이 시트와 다릅니다."); return false; }
  const data = rows.slice(1), ids = data.map(r => r[0]), mine = new Set(ROWS.map(r => r.issue_id));
  if (data.some(r => r.length !== COLS.length)) { msg("불러오기 거부: 열 개수가 맞지 않는 행이 있습니다."); return false; }
  if (new Set(ids).size !== ids.length || ids.length !== mine.size || !ids.every(i => mine.has(i))) {
    msg("불러오기 거부: 이 시트에서 내보낸 CSV 가 아닙니다 (이슈 " + ids.filter(i => mine.has(i)).length + "/" + mine.size + "건 일치)."); return false; }
  const inc = {};
  for (const r of data) {
    const v = {};
    for (const c of INPUTS) { const x = r[COLS.indexOf(c)];
      if (x === "") continue;
      if (VALID[c] && !VALID[c].includes(x)) { msg("불러오기 거부: 허용되지 않은 값 '" + x + "' (" + c + ")."); return false; }
      v[c] = x; }
    if (Object.keys(v).length) inc[r[0]] = v;
  }
  const conflicts = Object.keys(inc).filter(id => INPUTS.some(c => inc[id][c] !== undefined && st[id] && st[id][c] && st[id][c] !== inc[id][c]));
  const apply = (over) => {
    let filled = 0, replaced = 0, kept = 0;
    for (const id in inc) { const s = st[id] || (st[id] = {});
      for (const c in inc[id]) {
        if (!s[c]) { s[c] = inc[id][c]; filled++; }
        else if (s[c] !== inc[id][c]) { if (over) { s[c] = inc[id][c]; replaced++; } else kept++; } } }
    save(); show(); msg("불러오기 완료: 빈 칸 채움 " + filled + ", 덮어씀 " + replaced + ", 기존 유지 " + kept);
  };
  if (conflicts.length) {
    $("modalText").textContent = conflicts.length + "개 행에서 이미 입력한 값과 CSV 값이 다릅니다. 어떻게 할까요? (다른 행의 빈 칸은 어느 쪽이든 채웁니다)";
    $("modal").style.display = "block"; $("keepBtn").focus();
    $("keepBtn").onclick = () => { $("modal").style.display = "none"; apply(false); };
    $("overBtn").onclick = () => { $("modal").style.display = "none"; apply(true); };
  } else apply(false);
  return true;
}
$("importBtn").onclick = () => $("importFile").click();
$("importFile").onchange = e => { const f = e.target.files[0]; if (!f) return;
  const rd = new FileReader(); rd.onload = () => { importText(rd.result); e.target.value = ""; }; rd.readAsText(f, "utf-8"); };
"""


def add_import(html_text):
    if MARK in html_text:
        return html_text
    exp = '<button id="export" class="primary">CSV 내보내기</button>'
    assert html_text.count(exp) == 1 and html_text.count("\nshow();\n</script>") == 1
    out = html_text.replace(exp, exp + BUTTONS)
    out = out.replace("</header>", "</header>\n" + MODAL, 1)
    out = out.replace("\nshow();\n</script>", "\n" + IMPORT_JS + "show();\n</script>")
    return out


def invariant(html_text):
    """저장 키, 데이터, 열, 기존 함수(save/cur/complete/내보내기)가 같은지 비교할 부분."""
    keys = [r"const KEY = .*?;", r"const ROWS = .*?;\n", r"const SRC = .*?;\n", r"const COLS = .*?;\n",
            r"function save\(\)\{.*?\n", r"function cur\(\)\{.*?\n", r"\$\(\"export\"\)\.onclick = .*?\n\};"]
    return [re.search(k, html_text, re.S).group(0) for k in keys]


def main():
    for d, fn in TARGETS:
        p = os.path.join(HE, d, fn)
        old = open(p, encoding="utf-8").read()
        new = add_import(old)
        if new == old:
            print(f"{d}/{fn}: 이미 적용됨"); continue
        if invariant(old) != invariant(new):
            raise SystemExit(f"{fn}: 저장 키·데이터·기존 함수가 바뀜 → 쓰지 않음")
        open(p, "w", encoding="utf-8", newline="\n").write(new)
        print(f"{d}/{fn}: 불러오기 추가")


if __name__ == "__main__":
    sys.exit(main())
