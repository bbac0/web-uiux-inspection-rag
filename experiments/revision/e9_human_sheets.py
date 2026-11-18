"""
E9 사람 평가 시트(평가자 A 1인)와 재평가 시트, 누출 점검 (API 호출 없음).
규칙: results/revision/analysis_plan_addendum_e9_human.md (ca021ba), _2.md (c737a9c). 표본: e9_eval/key/sample_selection.csv (93f2542).

  python experiments/revision/e9_human_sheets.py build   # rater_A_e9/, rater_A_e9_retest/, key/e9_key.csv, key/e9_manifest.json
  python experiments/revision/e9_human_sheets.py leak    # leak_audit_e9.md, leak_audit_e9.json

평가자 폴더: 시트 CSV, 뷰어 HTML(CSV 불러오기 포함), shots/{토큰}.png, e9_rater_guidelines.md.
조건명, run 이름, 페이지 결함 유형, 주입 정보, 정규식 결과, 층은 key/ 에만 둔다.
"""
import csv
import hashlib
import html
import json
import os
import random
import re
import shutil
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import build_human_eval as bhe       # noqa: E402
from experiments.revision import make_eval_sheets as mes       # noqa: E402
from experiments.revision import viewer_add_import as vai      # noqa: E402

REL = "results/revision/human_eval/e9_eval"
E9 = f"{ROOT}/{REL}"
KEY = f"{E9}/key"
GUIDE = f"{E9}/e9_rater_guidelines.md"
JUDGE = ["banner-text", "spec-values", "login-address"]
SHEET_COLS = ["issue_id", "screenshot_path", "description", "suggestion"] + JUDGE + ["notes"]
TOKEN_SEED, ORDER_SEED_A, RETEST_SEED, ORDER_SEED_RT = "e9-tokens-20261203", 20261205, 20261204, 20261206
PAGE_STRATA = ["E9-1", "E9-2", "E9-3", "control"]
LABEL = {"banner-text": "배너 문구 지적", "spec-values": "규격값 지적", "login-address": "로그인 주소 지적"}


def existing_tokens():
    """다른 시트들이 이미 쓴 issue_id·스크린샷 토큰 (겹치지 않게)."""
    seen = set()
    he = f"{ROOT}/results/revision/human_eval"
    for root, _, fs in os.walk(he):
        if root.startswith(E9.replace("/", os.sep)) or "/e9_eval" in root.replace("\\", "/"):
            continue
        for fn in fs:
            if fn.endswith(".png"):
                seen.add(fn[:-4])
            elif fn.startswith("eval_sheet") and fn.endswith(".csv"):
                for r in csv.DictReader(open(os.path.join(root, fn), encoding="utf-8-sig")):
                    seen.add(r.get("issue_id", ""))
    return seen


def tokens(rng, prefix, n, used):
    out = []
    while len(out) < n:
        t = prefix + "%010x" % rng.getrandbits(40)
        if t not in used:
            used.add(t)
            out.append(t)
    return out


VIEW_Q = """<div class="q"><span class="t">1. 배너 문구 지적 (banner-text)</span>__R_banner-text__</div>
<div class="q"><span class="t">2. 규격값 지적 (spec-values)</span>__R_spec-values__</div>
<div class="q"><span class="t">3. 로그인 주소 지적 (login-address)</span>__R_login-address__</div>
<div class="q"><span class="t">비고 (notes)</span><textarea id="notes"></textarea></div>"""


def make_viewer(name, rows, src):
    v = bhe.VIEWER
    start = v.index('<div class="q"><span class="t">1. 분류')
    end = v.index('<div id="saved"')
    v = v[:start] + VIEW_Q + "\n" + v[end:]
    rep = [
        ('function complete(r){ const v = st[r.issue_id] || {}; return v.rater_category && v.exists_in_code && '
         'v.visible_on_screen && v.login_link_label_concern; }',
         'function complete(r){ const v = st[r.issue_id] || {}; return v["banner-text"] && v["spec-values"] && '
         'v["login-address"]; }'),
        ('  $("rater_category").value = v.rater_category || ""; $("rater_notes").value = v.rater_notes || "";\n'
         '  for (const k of ["exists_in_code","visible_on_screen","login_link_label_concern"])',
         '  $("notes").value = v.notes || "";\n  for (const k of ["banner-text","spec-values","login-address"])'),
        ('$("rater_category").onchange = e => { cur().rater_category = e.target.value; save(); show(); };\n'
         '$("rater_notes").oninput = e => { cur().rater_notes = e.target.value; save(); };',
         '$("notes").oninput = e => { cur().notes = e.target.value; save(); };'),
    ]
    for a, b in rep:
        assert v.count(a) == 1, a[:40]
        v = v.replace(a, b)
    for k in JUDGE:
        v = v.replace(f"__R_{k}__", "".join(f'<label><input type="radio" name="{k}" value="{x}"> {x}</label>'
                                            for x in ("예", "아니오")))
    js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")    # noqa: E731
    used = {r["screenshot_path"] for r in rows}
    v = (v.replace("__NAME__", name).replace("__ROWS__", js([{k: r[k] for k in SHEET_COLS[:4]} for r in rows]))
         .replace("__SRC__", js({k: s for k, s in src.items() if k in used})).replace("__COLS__", js(SHEET_COLS)))
    v = vai.add_import(v)
    a = ('const INPUTS = ["rater_category","exists_in_code","visible_on_screen","login_link_label_concern","rater_notes"];\n'
         'const VALID = {rater_category: Array.from($("rater_category").options).map(o => o.value).filter(Boolean),\n'
         '  exists_in_code: ["예","아니오","판단 불가"], visible_on_screen: ["예","아니오","판단 불가"], '
         'login_link_label_concern: ["예","아니오"]};')
    assert v.count(a) == 1
    v = v.replace(a, 'const INPUTS = ["banner-text","spec-values","login-address","notes"];\n'
                     'const VALID = {"banner-text": ["예","아니오"], "spec-values": ["예","아니오"], '
                     '"login-address": ["예","아니오"]};')
    return v


def write_sheet(folder, name, rows, src):
    os.makedirs(f"{folder}/shots")
    with open(f"{folder}/eval_sheet_{name}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**{k: r[k] for k in SHEET_COLS[:4]}, **{k: "" for k in JUDGE + ["notes"]}})
    open(f"{folder}/viewer_{name}.html", "w", encoding="utf-8", newline="\n").write(make_viewer(name, rows, src))
    shutil.copyfile(GUIDE, f"{folder}/e9_rater_guidelines.md")


def allocate(sizes, total):
    """최대 나머지 비례 배분, 비어 있지 않은 층 최소 1, 넘치면 큰 층부터 1씩 뺀다."""
    n = sum(sizes.values())
    raw = {k: total * v / n for k, v in sizes.items()}
    a = {k: int(raw[k]) for k in sizes}
    for k in sorted(sizes, key=lambda k: -(raw[k] - a[k]))[: total - sum(a.values())]:
        a[k] += 1
    for k in sizes:
        if sizes[k] and a[k] == 0:
            a[k] = 1
    while sum(a.values()) > total:
        k = max(a, key=lambda k: (a[k], sizes[k]))
        a[k] -= 1
    return a


def cmd_build():
    A, RT = f"{E9}/rater_A_e9", f"{E9}/rater_A_e9_retest"
    for p in (A, RT, f"{KEY}/e9_key.csv"):
        if os.path.exists(p):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {p}")
    sel = list(csv.DictReader(open(f"{KEY}/sample_selection.csv", encoding="utf-8-sig")))
    used = existing_tokens()
    rng = random.Random(TOKEN_SEED)
    ids = tokens(rng, "I", len(sel), used)
    shot_keys = sorted({(r["run_id"], r["page_id"]) for r in sel})
    shots = dict(zip(shot_keys, tokens(rng, "P", len(shot_keys), used)))
    rows = []
    for r, i in zip(sel, ids):
        rows.append({**r, "issue_id": i, "screenshot_path": f"shots/{shots[(r['run_id'], r['page_id'])]}.png",
                     "description": mes.clean_text(r["description"]), "suggestion": (r["suggestion"] or "").strip()})
    src_page = {p: open(f"{ROOT}/testbed_e9/{p}.html", encoding="utf-8").read() for _, p in shot_keys}
    src = {f"shots/{shots[k]}.png": src_page[k[1]] for k in shot_keys}
    # 본 평가 시트
    order_a = rows[:]
    random.Random(ORDER_SEED_A).shuffle(order_a)
    write_sheet(A, "A_e9", order_a, src)
    for (run, page), t in shots.items():
        shutil.copyfile(f"{ROOT}/results/revision/runs_e9/{run}/shots/{page}.png", f"{A}/shots/{t}.png")
    # 재평가 20건
    strata = defaultdict(list)
    for r in rows:
        strata[(r["page_stratum"], r["regex_stratum"])].append(r["issue_id"])
    order = [(s, h) for s in PAGE_STRATA for h in ("hit", "miss")]
    alloc = allocate({k: len(strata[k]) for k in order}, 20)
    rr = random.Random(RETEST_SEED)
    pick = []
    for k in order:
        pick += rr.sample(sorted(strata[k]), alloc[k]) if strata[k] else []
    by_id = {r["issue_id"]: r for r in rows}
    rt_shot_keys = sorted({(by_id[i]["run_id"], by_id[i]["page_id"]) for i in pick})
    rt_shots = dict(zip(rt_shot_keys, tokens(rng, "P", len(rt_shot_keys), used)))
    rt_rows = [{**by_id[i], "screenshot_path": f"shots/{rt_shots[(by_id[i]['run_id'], by_id[i]['page_id'])]}.png"}
               for i in pick]
    random.Random(ORDER_SEED_RT).shuffle(rt_rows)
    rt_src = {f"shots/{rt_shots[k]}.png": src_page[k[1]] for k in rt_shot_keys}
    write_sheet(RT, "A_e9_retest", rt_rows, rt_src)
    for (run, page), t in rt_shots.items():
        shutil.copyfile(f"{ROOT}/results/revision/runs_e9/{run}/shots/{page}.png", f"{RT}/shots/{t}.png")
    # key
    pos_a = {r["issue_id"]: k + 1 for k, r in enumerate(order_a)}
    pos_rt = {r["issue_id"]: k + 1 for k, r in enumerate(rt_rows)}
    rt_shot_of = {r["issue_id"]: r["screenshot_path"] for r in rt_rows}
    meta = {p["page_id"]: p for p in json.load(open(f"{ROOT}/testbed_e9/dataset_metadata_e9.json",
                                                    encoding="utf-8"))["pages"]}
    kcols = ["issue_id", "pos_A", "in_retest", "pos_retest", "screenshot_path", "screenshot_path_retest", "run_id",
             "page_id", "page_stratum", "subtype", "variant", "injected_string", "issue_index", "regex_stratum"] + \
        [c for c in sel[0] if c.startswith(("primary_", "aux_"))] + ["dup_n_in_sample"]
    with open(f"{KEY}/e9_key.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kcols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            p = meta[r["page_id"]]
            w.writerow({**r, "pos_A": pos_a[r["issue_id"]], "in_retest": int(r["issue_id"] in pos_rt),
                        "pos_retest": pos_rt.get(r["issue_id"], ""), "screenshot_path_retest": rt_shot_of.get(r["issue_id"], ""),
                        "variant": p["variant"] or "", "injected_string": p["injected_string"] or ""})
    man = {"date": "2026-11-18", "rules": ["ca021ba", "c737a9c"], "sample": "93f2542",
           "seeds": {"tokens": TOKEN_SEED, "order_A": ORDER_SEED_A, "retest_sample": RETEST_SEED,
                     "order_retest": ORDER_SEED_RT},
           "n_issues": len(rows), "n_shots": len(shots), "retest": {"n": len(pick), "n_shots": len(rt_shots),
                                                                     "allocation": {f"{a}|{b}": alloc[(a, b)] for a, b in order},
                                                                     "stratum_sizes": {f"{a}|{b}": len(strata[(a, b)]) for a, b in order}},
           "screenshots": {"source": "results/revision/runs_e9/{run}/shots/{page}.png", "size": "1280x800",
                           "sha256": {t: hashlib.sha256(open(f"{A}/shots/{t}.png", "rb").read()).hexdigest()
                                      for t in shots.values()}}}
    json.dump(man, open(f"{KEY}/e9_manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{A}: {len(rows)} issues, {len(shots)} shots; {RT}: {len(pick)} issues, {len(rt_shots)} shots; "
          f"alloc {man['retest']['allocation']}")


# ------------------------------------------------------------------ leak
TERMS = {
    "조건·run": r"related|norag|no[-_ ]?rag|\bRAG\b|fixed|e9-main|\br[123]\b",
    "페이지 ID·경로": r"e9_\d{3}|testbed|localhost|:8090",
    "결함 유형 표기": r"\bE9|E9-\d|subtype|defect|inject|주입|결함 유형",
    "정규식·층": r"regex|정규식|primary_|aux_|hit\b|miss\b|stratum|층\b|control|대조군",
    "주입 문구": r"공식전자정부|이누리집|전자정부누리집|홈페이지입니다|웹사이트입니다|대한민국 전자정부 누리집|/signup|"
             r"font-size:14px|padding:10px|#000000|max-width: 768px",
}


def cmd_leak():
    out = []
    files = []
    nonblank = 0
    targets = [f"{E9}/rater_A_e9", f"{E9}/rater_A_e9_retest"]
    for t in targets:
        for root, _, fs in os.walk(t):
            for fn in sorted(fs):
                p = os.path.join(root, fn).replace("\\", "/")
                rel = p[len(E9) + 1:]
                files.append(rel)

                def hits(text, where):
                    for cat, pat in TERMS.items():
                        for m in re.finditer(pat, text, re.I):
                            ctx = text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ").replace("|", "/")
                            out.append({"file": rel, "where": where, "category": cat, "match": m.group(0), "context": ctx})
                hits(rel, "파일명")
                if fn.endswith(".csv"):
                    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
                    hits(",".join(rows[0].keys()), "CSV 열 이름")
                    for r in rows:
                        nonblank += sum(1 for c in JUDGE + ["notes"] if r[c])
                        for k, v in r.items():
                            hits(v, "CSV 본문(이슈 문장)" if k in ("description", "suggestion") else f"CSV 값({k})")
                elif fn.endswith(".html"):
                    s = open(p, encoding="utf-8").read()
                    mr, ms = re.search(r"const ROWS = (.*?);\n", s), re.search(r"const SRC = (.*?);\n", s)
                    hits(s[:mr.start()] + s[ms.end():], "뷰어 코드·마크업")
                    for r in json.loads(mr.group(1).replace("<\\/", "</")):
                        if set(r) != set(SHEET_COLS[:4]):
                            out.append({"file": rel, "where": "뷰어 데이터 열", "category": "열 다름", "match": str(r.keys()),
                                        "context": ""})
                        for k, v in r.items():
                            hits(v, "뷰어 본문(이슈 문장)" if k in ("description", "suggestion") else f"뷰어 데이터({k})")
                    for k, h in json.loads(ms.group(1).replace("<\\/", "</")).items():
                        hits(h, "포함된 페이지 HTML")
                elif fn.endswith(".md"):
                    hits(open(p, encoding="utf-8").read(), "지침서 본문")
                elif fn.endswith(".png"):
                    from experiments.revision import human_eval_prep as hp
                    if hp.png_text_chunks(p):
                        out.append({"file": rel, "where": "PNG 메타데이터", "category": "메타데이터", "match": "", "context": ""})
    for extra in ("e9_howto.md",):
        p = f"{E9}/{extra}"
        if os.path.exists(p):
            files.append(extra)
            s = open(p, encoding="utf-8").read()
            for cat, pat in TERMS.items():
                for m in re.finditer(pat, s, re.I):
                    out.append({"file": extra, "where": "안내문 본문", "category": cat, "match": m.group(0),
                                "context": s[max(0, m.start() - 30):m.end() + 30].replace("\n", " ").replace("|", "/")})
    # 판단: 이슈 문장(LLM 출력)과 페이지 HTML(평가 대상 그 자체)에 나온 말은 평가자가 판단해야 할 내용이라 누출로 보지 않는다
    expected = {"CSV 본문(이슈 문장)": "평가 대상(이슈 문장)", "뷰어 본문(이슈 문장)": "평가 대상(이슈 문장)",
                "포함된 페이지 HTML": "평가 대상(페이지 원문)"}
    for h in out:
        h["judge"] = expected.get(h["where"], "확인 필요")
        if h["judge"] == "확인 필요" and h["where"] == "뷰어 코드·마크업" and h["match"].lower() == "fixed" \
                and "position:fixed" in h["context"]:
            h["judge"] = "CSS position:fixed"
        if h["judge"] == "확인 필요" and h["match"].lower() == "e9" and h["where"] in ("파일명", "안내문 본문") \
                and re.search(r"e9_rater_guidelines|e9_eval/|rater_A_e9", h["context"]):
            h["judge"] = "연구자가 지정한 파일·폴더 이름(e9)"
    leaks = [h for h in out if h["judge"] == "확인 필요"]
    a_shots = set(os.listdir(f"{E9}/rater_A_e9/shots"))
    reused = sorted(a_shots & set(os.listdir(f"{E9}/rater_A_e9_retest/shots")))
    json.dump({"files": files, "hits": out, "nonblank_input_cells": nonblank, "reused_screenshot_names": reused},
              open(f"{E9}/leak_audit_e9.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = Counter((h["file"].split("/")[0], h["where"], h["category"], h["judge"]) for h in out)
    L = ["# E9 평가 시트 정보 누출 점검", "",
         "작성: `experiments/revision/e9_human_sheets.py leak` (API 호출 없음). 2026-11-18.",
         "검사 대상: `rater_A_e9/`, `rater_A_e9_retest/` 의 모든 파일과 `e9_howto.md`.",
         "검색어: 조건·run 이름, 페이지 ID·경로, 결함 유형 표기, 정규식·층 표기, 실제 주입 문구·값. 원 결과: `leak_audit_e9.json`.",
         "이슈 문장(점검 도구 출력)과 페이지 HTML 원문은 평가 대상 그 자체라 일치해도 누출로 보지 않고 건수만 적는다.", "",
         f"검사한 파일 {len(files)}개.", "", "## 1. 검색 결과 (묶음별 건수)", "",
         "| 폴더 | 위치 | 분류 | 판단 | 건수 |", "|---|---|---|---|---|"]
    L += [f"| {a} | {b} | {cat} | {j} | {n} |" for (a, b, cat, j), n in sorted(c.items())] or ["| - | - | - | - | 0 |"]
    L += ["", "출처: `results/revision/human_eval/e9_eval/leak_audit_e9.json`", "",
          "## 2. 추가 점검", "", "| 점검 | 결과 |", "|---|---|",
          f"| 시트 입력 칸 중 값이 있는 칸 | {nonblank} |",
          f"| 본 시트와 재평가 시트의 같은 스크린샷 파일명 | {len(reused)} |", "", "출처: 위와 같음", "",
          f"**누출로 판단한 항목: {len(leaks) + (1 if nonblank else 0) + (1 if reused else 0)}건.**", ""]
    open(f"{E9}/leak_audit_e9.md", "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"leak hits {len(out)}, leaks {len(leaks)}, nonblank {nonblank}, reused {len(reused)}")
    for h in leaks[:20]:
        print("  ", h["file"], h["where"], h["category"], h["match"], "|", h["context"][:80])


if __name__ == "__main__":
    {"build": cmd_build, "leak": cmd_leak}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
