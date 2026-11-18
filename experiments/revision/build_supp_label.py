"""
추가 평가 세트(보충 시트) 생성 (API 호출 없음). 표본은 supp_label/key/sample_selection.csv (커밋 1bf93c8) 그대로.
규칙: results/revision/analysis_plan_addendum_supp_label.md. 기존 rater_A/, rater_B/, pilot_rater/ 는 읽지도 고치지도 않는다
(토큰 충돌 검사를 위해 key/eval_key.csv 만 읽는다).

  python experiments/revision/build_supp_label.py build   # rater_A_supp/, rater_B_supp/, key/ 추가 파일, README.md
  python experiments/revision/build_supp_label.py leak    # 누출 점검 → leak_audit_supp.json, leak_audit_supp.md

- 공통 기준 순서 = sample_selection.csv 의 order (층 섞기 시드 20261122).
- 평가자별 순서: A = random.Random(20261127).shuffle(기준 순서), B = random.Random(20261128).shuffle(기준 순서).
- 토큰: random.Random("supp-tokens-20261122"), 기존 시트 토큰과 겹치지 않게.
- 스크린샷: 대표 이슈 run 의 해당 페이지 스크린샷. E4-mobile(390x844) 대표 이슈는 E1-R1, E1-R2, E1-R3b 중
  같은 페이지·같은 문장 이슈가 있는 첫 run 의 1280x800 스크린샷, 없으면 그 페이지에 이슈가 있는 첫 run 의 스크린샷
  (연구자 지시 2026-11-16; key/screenshot_substitution.csv 에 기록).
"""
import csv
import hashlib
import json
import os
import random
import re
import shutil
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import build_human_eval as bhe       # noqa: E402
from experiments.revision import make_eval_sheets as mes       # noqa: E402
from experiments.revision import supp_label_sample as sls      # noqa: E402

HE = "results/revision/human_eval"
OUT = f"{HE}/supp_label"
KEYD = f"{OUT}/key"
SEED_BASE, SEED_A, SEED_B = 20261122, 20261127, 20261128
TOKEN_SEED = f"supp-tokens-{SEED_BASE}"
GUIDE = "docs/rater_guidelines_v2.md"
SUBST_RUNS = ["E1-R1", "E1-R2", "E1-R3b"]
SIDES = {"A": ("rater_A_supp", "A_supp", SEED_A), "B": ("rater_B_supp", "B_supp", SEED_B)}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def png_size(p):
    w, h = struct.unpack(">II", open(p, "rb").read()[16:24])
    return w, h


def dup_counts():
    """같은 (description, suggestion) 이 모집단 6개 run 에 나온 횟수 → {(desc, sug): Counter(run)}."""
    rows, _ = sls.population()
    out = defaultdict(Counter)
    for r in rows:
        out[(r["_desc"], r["_sug"])][r["run_id"]] += 1
    return out


def build():
    for d, _, _ in SIDES.values():
        if os.path.exists(f"{OUT}/{d}"):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUT}/{d}")
    sel = list(csv.DictReader(open(f"{KEYD}/sample_selection.csv", encoding="utf-8-sig")))
    sel.sort(key=lambda r: int(r["order"]))
    texts = {run: sls.load_text(run) for run in sls.RUNS + SUBST_RUNS}
    dups = dup_counts()

    # ---- 스크린샷 출처
    subst = []
    for r in sel:
        r["_desc"], r["_sug"] = texts[r["run_id"]][(r["page_id"], int(r["issue_index"]))]
        r["_shot_run"], r["_subst"] = r["run_id"], 0
        if r["run_id"] == "E4-mobile":
            same = [run for run in SUBST_RUNS
                    if any(p == r["page_id"] and v == (r["_desc"], r["_sug"]) for (p, _), v in texts[run].items())]
            has = [run for run in SUBST_RUNS if any(p == r["page_id"] for (p, _) in texts[run])]
            use = (same or has)[0]
            r["_shot_run"], r["_subst"] = use, 1
            shas = {run: sha(f"{sls.RUNS_BASE}/{run}/shots/{r['page_id']}.png") for run in SUBST_RUNS}
            subst.append({"source_issue_id": r["issue_id"], "page_id": r["page_id"], "original_run": "E4-mobile",
                          "original_size": "x".join(map(str, png_size(f"{sls.RUNS_BASE}/E4-mobile/shots/{r['page_id']}.png"))),
                          "used_run": use, "used_size": "x".join(map(str, png_size(f"{sls.RUNS_BASE}/{use}/shots/{r['page_id']}.png"))),
                          "same_text_runs": ";".join(same), "runs_with_issues_on_page": ";".join(has),
                          "rule_applied": "same page and same text" if same else "no same-text issue; first run with issues on page",
                          "e1_shots_identical": int(len(set(shas.values())) == 1), "used_sha256": shas[use]})
        r["_shot_src"] = f"{sls.RUNS_BASE}/{r['_shot_run']}/shots/{r['page_id']}.png"
        if png_size(r["_shot_src"]) != (1280, 800):
            raise SystemExit(f"1280x800 아님: {r['_shot_src']}")

    # ---- 토큰 (페이지별 스크린샷 토큰: 같은 페이지의 출처 스크린샷이 모두 같은 파일 내용일 때만 공유)
    old = list(csv.DictReader(open(f"{HE}/key/eval_key.csv", encoding="utf-8-sig")))
    used = {r["issue_id"] for r in old} | {r["page_token"] for r in old}
    rng = random.Random(TOKEN_SEED)

    def tok(prefix):
        while True:
            t = f"{prefix}{rng.getrandbits(40):010x}"
            if t not in used:
                used.add(t); return t
    by_page = defaultdict(set)
    for r in sel:
        by_page[r["page_id"]].add(sha(r["_shot_src"]))
    shot_tok = {}
    for r in sel:
        k = r["page_id"] if len(by_page[r["page_id"]]) == 1 else (r["page_id"], r["_shot_run"])
        if k not in shot_tok:
            shot_tok[k] = f"shots/{tok('P')}.png"
        r["_shot"] = shot_tok[k]
        r["_tok"] = tok("I")
    for r in sel:
        if mes.LEAK_RE.search(r["_desc"]) or mes.LEAK_RE.search(r["_sug"]):
            raise SystemExit(f"이슈 문장에 페이지 식별자 남음: {r['issue_id']}")

    # ---- 평가자별 순서와 폴더
    pos = {}
    for side, (d, name, seed) in SIDES.items():
        order = list(sel)
        random.Random(seed).shuffle(order)
        pos[side] = {r["_tok"]: i + 1 for i, r in enumerate(order)}
        os.makedirs(f"{OUT}/{d}/shots")
        rows = [{"issue_id": r["_tok"], "screenshot_path": r["_shot"], "description": r["_desc"], "suggestion": r["_sug"],
                 **{c: "" for c in bhe.INPUT_FIELDS}} for r in order]
        with open(f"{OUT}/{d}/eval_sheet_{name}.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=mes.SHEET_COLS); w.writeheader(); w.writerows(rows)
        src_by_shot = {}
        for r in order:
            if not os.path.exists(f"{OUT}/{d}/{r['_shot']}"):
                shutil.copyfile(r["_shot_src"], f"{OUT}/{d}/{r['_shot']}")
            src_by_shot[r["_shot"]] = open(f"testbed_200/{r['page_id']}.html", encoding="utf-8").read()
        open(f"{OUT}/{d}/viewer_{name}.html", "w", encoding="utf-8", newline="\n").write(bhe.make_viewer(name, rows, src_by_shot))
        shutil.copyfile(GUIDE, f"{OUT}/{d}/rater_guidelines.md")

    # ---- key/
    kcols = ["issue_id", "base_order", "pos_A", "pos_B", "stratum", "run_id", "page_id", "issue_index", "source_issue_id",
             "semantic_pass1_merged", "string_match_term", "keyword_types", "screenshot_path", "screenshot_run",
             "screenshot_substituted", "dup_n_total", "dup_by_run"]
    with open(f"{KEYD}/supp_key.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(kcols)
        for r in sel:
            dc = dups[(r["_desc"], r["_sug"])]
            w.writerow([r["_tok"], r["order"], pos["A"][r["_tok"]], pos["B"][r["_tok"]], r["stratum"], r["run_id"], r["page_id"],
                        r["issue_index"], r["issue_id"], r["semantic_pass1_merged"], r["string_match_term"], r["keyword_types"],
                        r["_shot"], r["_shot_run"], r["_subst"], sum(dc.values()),
                        ";".join(f"{k}:{dc[k]}" for k in sls.RUNS if dc[k])])
    with open(f"{KEYD}/screenshot_substitution.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(subst[0])); w.writeheader(); w.writerows(subst)
    man = {"sample_selection": f"{KEYD}/sample_selection.csv", "plan": "results/revision/analysis_plan_addendum_supp_label.md",
           "seeds": {"stratum_shuffle_base_order": SEED_BASE, "order_A": SEED_A, "order_B": SEED_B, "tokens": TOKEN_SEED},
           "order_method": "random.Random(seed).shuffle(기준 순서 목록 사본)", "guidelines": GUIDE,
           "issues": len(sel), "pages": len({r["page_id"] for r in sel}), "screenshot_files": len(set(shot_tok.values())),
           "strata": dict(Counter(r["stratum"] for r in sel)), "screenshot_substituted": len(subst),
           "viewer_storage_keys": {s: f"human_eval_{n}" for s, (_, n, _) in SIDES.items()},
           "sheet_sha256": {s: sha(f"{OUT}/{d}/eval_sheet_{n}.csv") for s, (d, n, _) in SIDES.items()}}
    json.dump(man, open(f"{KEYD}/supp_manifest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: man[k] for k in ("issues", "pages", "screenshot_files", "strata", "screenshot_substituted")},
                     ensure_ascii=False))


# ------------------------------------------------------------------ 누출 점검
EXTRA_TERMS = {"안내 문구": r"레이블 관련|접속하기 중심|보충|용어 위반 중심"}


def leak():
    from experiments.revision import human_eval_prep as hp
    terms = dict(hp.TERMS, **EXTRA_TERMS)
    out, files = [], []

    def hits(text, where, file):
        for cat, pat in terms.items():
            for m in re.finditer(pat, text):
                s = text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ").replace("|", "/")
                out.append({"file": file, "where": where, "category": cat, "match": m.group(0), "context": s})
    targets = [f"{OUT}/{d}" for d, _, _ in SIDES.values()]
    for d in targets:
        for root, _, fs in os.walk(d):
            for fn in fs:
                p = os.path.join(root, fn).replace("\\", "/")
                rel = p[len(OUT) + 1:]
                files.append(rel)
                hits(rel, "파일명·경로", rel)
                if fn.endswith(".csv"):
                    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
                    hits(",".join(rows[0].keys()), "CSV 열 이름", rel)
                    for r in rows:
                        for k, v in r.items():
                            if k not in hp.TEXT_FIELDS:
                                hits(v, f"CSV 값({k})", rel)
                elif fn.endswith(".html"):
                    s = open(p, encoding="utf-8").read()
                    m_rows = re.search(r"const ROWS = (.*?);\n", s)
                    m_src = re.search(r"const SRC = (.*?);\n", s)
                    code = s[:m_rows.start()] + s[m_src.end():]
                    hits(code, "뷰어 코드·마크업", rel)
                    for r in json.loads(m_rows.group(1).replace("<\\/", "</")):
                        for k, v in r.items():
                            if k not in hp.TEXT_FIELDS:
                                hits(v, f"뷰어 데이터({k})", rel)
                    for shot, h in json.loads(m_src.group(1).replace("<\\/", "</")).items():
                        hits(h, f"포함된 페이지 HTML ({shot})", rel)
                elif fn.endswith(".md"):
                    hits(open(p, encoding="utf-8").read(), "지침서 본문", rel)
                elif fn.endswith(".png"):
                    ch = hp.png_text_chunks(p)
                    if ch:
                        out.append({"file": rel, "where": "PNG 메타데이터", "category": "메타데이터 있음", "match": "",
                                    "context": str(ch)[:100]})
                    if png_size(p) != (1280, 800):
                        out.append({"file": rel, "where": "PNG 크기", "category": "1280x800 아님", "match": str(png_size(p)),
                                    "context": ""})
    howto = f"{OUT}/supp_howto.md"
    if os.path.exists(howto):
        files.append("supp_howto.md")
        hits(open(howto, encoding="utf-8").read(), "안내문 본문", "supp_howto.md")
    json.dump({"files": sorted(files), "hits": out}, open(f"{OUT}/leak_audit_supp.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    for h in out:
        if h["where"] == "뷰어 코드·마크업" and h["match"] == "fixed" and "position:fixed" in h["context"]:
            h["where"] = "뷰어 코드·마크업 CSS"
        if h["where"] == "안내문 본문" and h["match"] == "guideline" and "rater_guidelines.md" in h["context"]:
            h["where"] = "안내문 본문 지침서 파일명"
    judge = {"안내문 본문 지침서 파일명": "예상됨: 지침서 파일명 rater_guidelines.md 언급","뷰어 코드·마크업 CSS": "예상됨: CSS position:fixed (조건명 아님)",
             "뷰어 코드·마크업": "예상됨: 6분류 선택지 문구(모든 행에 같음)",
             "지침서 본문": "예상됨: 지침서 v2 의 6분류 정의와 예시(기존 시트와 같은 파일)",
             "파일명·경로": "예상됨: 지침서 파일명 rater_guidelines.md"}
    c = Counter((h["file"].split("/")[0], h["where"].split("(")[0].strip(), h["category"], h["match"]) for h in out)
    leaks = [k for k in c if k[1] not in judge]
    fc = Counter(f.split("/")[0] for f in files)
    L = ["# 추가 평가 세트 정보 누출 점검", "",
         "작성: `experiments/revision/build_supp_label.py leak` (API 호출 없음, 파일은 읽기만 함). 2026-11-16.",
         "방법: 본 시트 점검(`human_eval/leak_audit.md`)과 같은 검색어·위치에 다음을 더했다:",
         "안내문 문구(레이블 관련, 접속하기 중심, 보충, 용어 위반 중심), `supp_howto.md` 본문, PNG 크기(1280x800).",
         "원 검색 결과: `results/revision/human_eval/supp_label/leak_audit_supp.json`.", "",
         f"검사한 파일: rater_A_supp {fc['rater_A_supp']}개, rater_B_supp {fc['rater_B_supp']}개, "
         f"supp_howto.md {fc['supp_howto.md']}개.", "제외: 이슈 설명·제안 본문(모델 출력).", "",
         "## 1. 검색 결과", "", "| 폴더 | 위치 | 분류 | 일치 | 건수 | 판단 |", "|---|---|---|---|---|---|"]
    for (fo, w, cat, m), n in sorted(c.items()):
        L.append(f"| {fo} | {w} | {cat} | {m} | {n} | {judge.get(w, '확인 필요')} |")
    L += ["", "출처: `results/revision/human_eval/supp_label/leak_audit_supp.json`", "",
          f"**누출로 판단한 항목: {len(leaks)}건.**", "",
          "## 2. 알아둘 점", "",
          "- 스크린샷 PNG 는 모두 1280x800 이고 텍스트 메타데이터가 없다(위 표에 'PNG' 행이 없으면 0건).",
          "- 페이지 HTML 원문에는 주입된 CSS·마크업이 그대로 있다(본 시트와 같음).",
          "- 이슈 설명·제안 본문에는 '접속하기', '용어' 같은 단어가 나올 수 있다(모델 출력, 본 시트와 같게 제외).",
          "- 추가 평가 세트의 이슈 일부는 본 시트와 같은 페이지에서 나왔지만 issue_id·스크린샷 토큰은 새로 만들었다.", ""]
    open(f"{OUT}/leak_audit_supp.md", "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(f"files {len(files)}, hits {len(out)}, leaks {len(leaks)}")


if __name__ == "__main__":
    {"build": build, "leak": leak}[sys.argv[1]]()
