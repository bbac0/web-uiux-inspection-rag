"""
E9 사람 평가 축소 시트(정규식 걸린 52건, 평가자 A 1인)와 누출 점검 (API 호출 없음).
규칙: results/revision/analysis_plan_addendum_e9_human_3.md (94503ac). 표본: key/e9_key.csv 중 regex_stratum = hit.

  python experiments/revision/e9_human_hit52.py build   # rater_A_e9_hit52/, key/e9_key_hit52.csv, key/e9_manifest_hit52.json
  python experiments/revision/e9_human_hit52.py leak    # leak_audit_e9_hit52.md, leak_audit_e9_hit52.json

issue_id 는 기존 rater_A_e9 시트와 같다(부분 입력 9건을 옮기기 위해). 스크린샷 파일명은 새 토큰.
열, 뷰어, 지침서는 e9_human_sheets.py 와 같은 함수로 만든다. 기존 파일은 고치지 않는다.
"""
import csv
import hashlib
import json
import os
import random
import re
import shutil
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from experiments.revision import e9_human_sheets as es     # noqa: E402

E9, KEY = es.E9, es.KEY
OUT = f"{E9}/rater_A_e9_hit52"
NAME = "A_e9_hit52"
ORDER_SEED, TOKEN_SEED = 20261207, "e9-hit52-tokens-20261207"
TYPES = ["E9-1", "E9-2", "E9-3", "E9-4"]


def used_tokens():
    """다른 시트(기존 E9 시트 포함)가 쓴 issue_id·스크린샷 토큰."""
    seen = es.existing_tokens()
    for root, _, fs in os.walk(E9):
        for fn in fs:
            if fn.endswith(".png"):
                seen.add(fn[:-4])
    for r in csv.DictReader(open(f"{KEY}/e9_key.csv", encoding="utf-8-sig")):
        seen.add(r["issue_id"])
    return seen


def cmd_build():
    for p in (OUT, f"{KEY}/e9_key_hit52.csv", f"{KEY}/e9_manifest_hit52.json"):
        if os.path.exists(p):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {p}")
    key = list(csv.DictReader(open(f"{KEY}/e9_key.csv", encoding="utf-8-sig")))
    sheet = {r["issue_id"]: r for r in csv.DictReader(open(f"{E9}/rater_A_e9/eval_sheet_A_e9.csv",
                                                            encoding="utf-8-sig"))}
    hit = [r for r in key if r["regex_stratum"] == "hit"]
    if len(hit) != 52:
        raise SystemExit(f"걸린 이슈 {len(hit)}건 (52건이 아님)")
    rng = random.Random(TOKEN_SEED)
    shot_keys = sorted({(r["run_id"], r["page_id"]) for r in hit})
    shots = dict(zip(shot_keys, es.tokens(rng, "P", len(shot_keys), used_tokens())))
    rows = [{**r, "description": sheet[r["issue_id"]]["description"], "suggestion": sheet[r["issue_id"]]["suggestion"],
             "screenshot_path": f"shots/{shots[(r['run_id'], r['page_id'])]}.png"} for r in hit]
    src_page = {p: open(f"{ROOT}/testbed_e9/{p}.html", encoding="utf-8").read() for _, p in shot_keys}
    src = {f"shots/{shots[k]}.png": src_page[k[1]] for k in shot_keys}
    order = rows[:]
    random.Random(ORDER_SEED).shuffle(order)
    es.write_sheet(OUT, NAME, order, src)
    for (run, page), t in shots.items():
        shutil.copyfile(f"{ROOT}/results/revision/runs_e9/{run}/shots/{page}.png", f"{OUT}/shots/{t}.png")
    pos = {r["issue_id"]: k + 1 for k, r in enumerate(order)}
    kcols = ["issue_id", "pos_hit52", "screenshot_path_hit52"] + [c for c in key[0] if c not in
                                                                   ("pos_A", "in_retest", "pos_retest",
                                                                    "screenshot_path_retest")]
    kcols = [c if c != "screenshot_path" else "screenshot_path_A_e9" for c in kcols]
    with open(f"{KEY}/e9_key_hit52.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kcols, extrasaction="ignore")
        w.writeheader()
        for r0, r in zip(hit, rows):
            w.writerow({**r0, "pos_hit52": pos[r["issue_id"]], "screenshot_path_hit52": r["screenshot_path"],
                        "screenshot_path_A_e9": r0["screenshot_path"]})
    strata = Counter((r["run_id"], r["page_stratum"], "+".join(t for t in TYPES if r[f"primary_{t}"] == "1"))
                     for r in hit)
    man = {"date": "2026-11-18", "rules": ["ca021ba", "c737a9c", "94503ac"], "sample": "93f2542 (regex_stratum = hit)",
           "seeds": {"order": ORDER_SEED, "tokens": TOKEN_SEED}, "issue_id": "rater_A_e9 시트와 같음",
           "n_issues": len(rows), "n_shots": len(shots),
           "n_pairs": sum(r[f"primary_{t}"] == "1" for r in hit for t in TYPES),
           "strata_run_page_types": {"|".join(k): n for k, n in sorted(strata.items())},
           "screenshots": {"source": "results/revision/runs_e9/{run}/shots/{page}.png", "size": "1280x800",
                           "sha256": {t: hashlib.sha256(open(f"{OUT}/shots/{t}.png", "rb").read()).hexdigest()
                                      for t in shots.values()}}}
    json.dump(man, open(f"{KEY}/e9_manifest_hit52.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{OUT}: {len(rows)} issues, {len(shots)} shots, {man['n_pairs']} pairs")


def cmd_leak():
    out, files, nonblank = [], [], 0

    def hits(text, rel, where):
        for cat, pat in es.TERMS.items():
            for m in re.finditer(pat, text, re.I):
                ctx = text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ").replace("|", "/")
                out.append({"file": rel, "where": where, "category": cat, "match": m.group(0), "context": ctx})

    for root, _, fs in os.walk(OUT):
        for fn in sorted(fs):
            p = os.path.join(root, fn).replace("\\", "/")
            rel = p[len(E9) + 1:]
            files.append(rel)
            hits(rel, rel, "파일명")
            if fn.endswith(".csv"):
                rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
                hits(",".join(rows[0].keys()), rel, "CSV 열 이름")
                for r in rows:
                    nonblank += sum(1 for c in es.JUDGE + ["notes"] if r[c])
                    for k, v in r.items():
                        hits(v, rel, "CSV 본문(이슈 문장)" if k in ("description", "suggestion") else f"CSV 값({k})")
            elif fn.endswith(".html"):
                s = open(p, encoding="utf-8").read()
                mr, ms = re.search(r"const ROWS = (.*?);\n", s), re.search(r"const SRC = (.*?);\n", s)
                hits(s[:mr.start()] + s[ms.end():], rel, "뷰어 코드·마크업")
                for r in json.loads(mr.group(1).replace("<\\/", "</")):
                    if set(r) != set(es.SHEET_COLS[:4]):
                        out.append({"file": rel, "where": "뷰어 데이터 열", "category": "열 다름", "match": str(r.keys()),
                                    "context": ""})
                    for k, v in r.items():
                        hits(v, rel, "뷰어 본문(이슈 문장)" if k in ("description", "suggestion") else f"뷰어 데이터({k})")
                for _, h in json.loads(ms.group(1).replace("<\\/", "</")).items():
                    hits(h, rel, "포함된 페이지 HTML")
            elif fn.endswith(".md"):
                hits(open(p, encoding="utf-8").read(), rel, "지침서 본문")
            elif fn.endswith(".png"):
                from experiments.revision import human_eval_prep as hp
                if hp.png_text_chunks(p):
                    out.append({"file": rel, "where": "PNG 메타데이터", "category": "메타데이터", "match": "", "context": ""})
    files.append("e9_howto.md")
    hits(open(f"{E9}/e9_howto.md", encoding="utf-8").read(), "e9_howto.md", "안내문 본문")
    expected = {"CSV 본문(이슈 문장)": "평가 대상(이슈 문장)", "뷰어 본문(이슈 문장)": "평가 대상(이슈 문장)",
                "포함된 페이지 HTML": "평가 대상(페이지 원문)"}
    for h in out:
        h["judge"] = expected.get(h["where"], "확인 필요")
        if h["judge"] == "확인 필요" and h["where"] == "뷰어 코드·마크업" and h["match"].lower() == "fixed" \
                and "position:fixed" in h["context"]:
            h["judge"] = "CSS position:fixed"
        if h["judge"] == "확인 필요" and h["match"].lower() == "e9" and h["where"] in ("파일명", "안내문 본문") \
                and re.search(r"e9_rater_guidelines|e9_eval/|rater_A_e9|A_e9", h["context"]):
            h["judge"] = "연구자가 지정한 파일·폴더 이름(e9)"
    leaks = [h for h in out if h["judge"] == "확인 필요"]
    mine = set(os.listdir(f"{OUT}/shots"))
    others = set()
    for d in ("rater_A_e9", "rater_A_e9_retest"):
        others |= set(os.listdir(f"{E9}/{d}/shots"))
    reused = sorted(mine & others)
    json.dump({"files": files, "hits": out, "nonblank_input_cells": nonblank, "reused_screenshot_names": reused},
              open(f"{E9}/leak_audit_e9_hit52.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = Counter((h["file"].split("/")[0], h["where"], h["category"], h["judge"]) for h in out)
    n_leak = len(leaks) + (1 if nonblank else 0) + (1 if reused else 0)
    L = ["# E9 축소 시트(52건) 정보 누출 점검", "",
         "작성: `experiments/revision/e9_human_hit52.py leak` (API 호출 없음). 2026-11-18.",
         "검사 대상: `rater_A_e9_hit52/` 의 모든 파일과 `e9_howto.md`. 원 결과: `leak_audit_e9_hit52.json`.",
         "검색어는 `leak_audit_e9.md` 와 같다(조건·run, 페이지 ID·경로, 결함 유형, 정규식·층, 주입 문구·값).",
         "이슈 문장과 페이지 HTML 원문은 평가 대상 그 자체라 일치해도 누출로 보지 않고 건수만 적는다.", "",
         f"검사한 파일 {len(files)}개.", "", "## 1. 검색 결과 (묶음별 건수)", "",
         "| 폴더 | 위치 | 분류 | 판단 | 건수 |", "|---|---|---|---|---|"]
    L += [f"| {a} | {b} | {cat} | {j} | {n} |" for (a, b, cat, j), n in sorted(c.items())] or ["| - | - | - | - | 0 |"]
    L += ["", "출처: `results/revision/human_eval/e9_eval/leak_audit_e9_hit52.json`", "",
          "## 2. 추가 점검", "", "| 점검 | 결과 |", "|---|---|",
          f"| 시트 입력 칸 중 값이 있는 칸 | {nonblank} |",
          f"| 기존 E9 시트(본·재평가)와 같은 스크린샷 파일명 | {len(reused)} |", "", "출처: 위와 같음", "",
          f"**누출로 판단한 항목: {n_leak}건.**", ""]
    open(f"{E9}/leak_audit_e9_hit52.md", "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"leak hits {len(out)}, leaks {len(leaks)}, nonblank {nonblank}, reused {len(reused)}")
    for h in leaks[:20]:
        print("  ", h["file"], h["where"], h["category"], h["match"], "|", h["context"][:80])


if __name__ == "__main__":
    {"build": cmd_build, "leak": cmd_leak}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
