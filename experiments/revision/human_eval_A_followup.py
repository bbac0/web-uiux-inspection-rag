"""
평가자 A 본 평가 접수와 자기 일치도 재판정 시트 (API 호출 없음). 정답 키(key/)와 채점 결과는 읽지 않는다.
rater_A/ 의 시트·뷰어·입력 파일은 읽기만 한다.

  python experiments/revision/human_eval_A_followup.py intake   # → human_eval/intake_A.md
  python experiments/revision/human_eval_A_followup.py retest   # → human_eval/rater_A_retest/, retest_sampling.json
  python experiments/revision/human_eval_A_followup.py leak     # → human_eval/leak_audit_retest.json, .md

재판정 표본: random.Random(20261125).sample(eval_sheet_A.csv 의 issue_id 를 정렬한 목록, 40)
행 순서:     random.Random(20261126).shuffle(표본을 issue_id 순으로 정렬한 목록)
스크린샷 토큰: random.Random("retest-tokens-20261125"), rater_A/ 와 supp_label/ 의 기존 토큰과 겹치지 않게.
issue_id 는 본 시트와 같은 값을 쓴다(비교 스크립트가 issue_id 로 맞춘다).
페이지 HTML 원문은 rater_A/viewer_A.html 에 들어 있는 것을 그대로 옮긴다(key/ 를 읽지 않기 위해).
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
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import build_human_eval as bhe    # noqa: E402
from experiments.revision import make_eval_sheets as mes    # noqa: E402

HE = "results/revision/human_eval"
SHEET = f"{HE}/rater_A/eval_sheet_A.csv"
FILLED = f"{HE}/rater_A/eval_sheet_A_filled.csv"
RT = f"{HE}/rater_A_retest"
SEED_SAMPLE, SEED_ORDER = 20261125, 20261126
TOKEN_SEED = f"retest-tokens-{SEED_SAMPLE}"
N_RETEST = 40
REQUIRED = ["rater_category", "exists_in_code", "visible_on_screen", "login_link_label_concern"]
ALLOWED = {"rater_category": list(mes.CATEGORY_CHOICES), "exists_in_code": ["예", "아니오", "판단 불가"],
           "visible_on_screen": ["예", "아니오", "판단 불가"], "login_link_label_concern": ["예", "아니오"]}
NAMES = {"rater_category": "6분류", "exists_in_code": "코드에 존재", "visible_on_screen": "화면에서 보임",
         "login_link_label_concern": "로그인 레이블 지적"}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def read_csv(p):
    with open(p, encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


# ------------------------------------------------------------------ 1, 2. 접수와 기술 요약
def intake():
    out = f"{HE}/intake_A.md"
    if os.path.exists(out):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {out}")
    _, sheet = read_csv(SHEET)
    cols, rows = read_csv(FILLED)
    sid = [r["issue_id"] for r in sheet]
    fid = [r["issue_id"] for r in rows]
    dup = [i for i, n in Counter(fid).items() if n > 1]
    blank = {c: [r["issue_id"] for r in rows if not r[c]] for c in REQUIRED}
    bad = {c: [(r["issue_id"], r[c]) for r in rows if r[c] and r[c] not in ALLOWED[c]] for c in REQUIRED}
    sheet_by = {r["issue_id"]: r for r in sheet}
    text_diff = [r["issue_id"] for r in rows if r["issue_id"] in sheet_by and any(
        r[c] != sheet_by[r["issue_id"]][c] for c in ("screenshot_path", "description", "suggestion"))]
    checks = [
        ("열 구성이 시트와 같음", cols == mes.SHEET_COLS, ", ".join(cols or [])[:60] if cols != mes.SHEET_COLS else ""),
        ("행 수 444", len(rows) == 444, str(len(rows))),
        ("issue_id 집합이 eval_sheet_A.csv 와 같음", set(fid) == set(sid),
         f"시트에만 {len(set(sid) - set(fid))}, 입력에만 {len(set(fid) - set(sid))}"),
        ("issue_id 순서가 시트와 같음", fid == sid, ""),
        ("중복 issue_id 없음", not dup, ", ".join(dup[:5])),
        ("스크린샷 경로·설명·제안이 시트와 같음", not text_diff, ", ".join(text_diff[:5])),
    ]
    for c in REQUIRED:
        checks.append((f"{c} 빈칸 없음", not blank[c], f"{len(blank[c])}건 " + ", ".join(blank[c][:5])))
        checks.append((f"{c} 허용 값만", not bad[c], ", ".join(f"{i}={v}" for i, v in bad[c][:5])))
    os.makedirs(HE, exist_ok=True)
    L = ["# 평가자 A 본 평가 접수", "",
         "작성: `experiments/revision/human_eval_A_followup.py intake` (API 호출 없음). 2026-11-16.",
         "정답 키(key/)와 채점 결과는 읽지 않았다. 입력은 아래 두 파일뿐이다.", "",
         f"- 입력: `{FILLED}`",
         f"  SHA256 `{sha(FILLED)}`",
         f"  크기 {os.path.getsize(FILLED)} 바이트. 접수 시 읽기 전용 속성 설정(파일 내용은 바꾸지 않음), 커밋하지 않음.",
         f"- 대조 시트: `{SHEET}`",
         f"  SHA256 `{sha(SHEET)}`", "",
         "## 1. 점검", "", "| 점검 | 결과 | 비고 |", "|---|---|---|"]
    for name, ok, note in checks:
        L.append(f"| {name} | {'통과' if ok else '실패'} | {note if not ok else ''} |")
    L += ["", f"출처: `{FILLED}`,", f"`{SHEET}`", ""]

    L += ["## 2. 열별 값 분포 (A 의 답만)", "", "| 열 | 값 | 건수 | 비율 |", "|---|---|---|---|"]
    n = len(rows)
    for c in REQUIRED:
        cnt = Counter(r[c] for r in rows)
        for v in ALLOWED[c] + sorted(k for k in cnt if k not in ALLOWED[c]):
            if cnt[v] or v in ALLOWED[c]:
                L.append(f"| {NAMES[c]} | {v or '(빈칸)'} | {cnt[v]} | {cnt[v] / n:.3f} |")
    L += ["", f"출처: `{FILLED}`", "",
          "## 3. 코드 존재 × 화면에서 보임 (A 의 답만)", "",
          "| 코드에 존재 \\ 화면에서 보임 | " + " | ".join(ALLOWED["visible_on_screen"]) + " |", "|---|---|---|---|"]
    ct = Counter((r["exists_in_code"], r["visible_on_screen"]) for r in rows)
    for x in ALLOWED["exists_in_code"]:
        L.append(f"| {x} | " + " | ".join(str(ct[(x, y)]) for y in ALLOWED["visible_on_screen"]) + " |")
    notes = [r["rater_notes"].strip() for r in rows]
    L += ["", f"출처: `{FILLED}`", "",
          "## 4. 비고", "",
          "| 항목 | 건수 |", "|---|---|",
          f"| 비고가 있는 행 | {sum(1 for x in notes if x)} |",
          f"| '부재형' 포함 | {sum('부재형' in x for x in notes)} |",
          f"| '기준 비교형' 포함 | {sum('기준 비교형' in x for x in notes)} |",
          f"| 둘 다 포함 | {sum('부재형' in x and '기준 비교형' in x for x in notes)} |", "",
          f"출처: `{FILLED}` (부분 문자열 일치)", "",
          "### 비고 빈도 상위 20개 (비고 전체 문자열, 앞뒤 공백 제거, 빈 비고 제외)", "",
          "| 순위 | 비고 | 건수 |", "|---|---|---|"]
    top = Counter(x for x in notes if x).most_common()
    top.sort(key=lambda kv: (-kv[1], kv[0]))
    for k, (v, c) in enumerate(top[:20], 1):
        s = v.replace("|", "/").replace("\n", " ")
        L.append(f"| {k} | {s[:60]}{'…' if len(s) > 60 else ''} | {c} |")
    L += ["", f"서로 다른 비고 {len(top)}종. 동률은 비고 문자열 순.", f"출처: `{FILLED}`", ""]
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(out, "fails:", [c[0] for c in checks if not c[1]])


# ------------------------------------------------------------------ 3. 재판정 시트
def viewer_src(path):
    s = open(path, encoding="utf-8").read()
    return json.loads(re.search(r"const SRC = (.*?);\n", s).group(1).replace("<\\/", "</"))


def existing_tokens():
    used = set()
    for root, _, fs in os.walk(HE):
        for fn in fs:
            m = re.match(r"(P[0-9a-f]{10})\.png$", fn)
            if m:
                used.add(m.group(1))
    _, sheet = read_csv(SHEET)
    used |= {r["issue_id"] for r in sheet}
    return used


def retest():
    samp = f"{HE}/retest_sampling.json"
    for p in (RT, samp):
        if os.path.exists(p):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {p}")
    _, sheet = read_csv(SHEET)
    by = {r["issue_id"]: r for r in sheet}
    pick = random.Random(SEED_SAMPLE).sample(sorted(by), N_RETEST)
    order = sorted(pick)
    random.Random(SEED_ORDER).shuffle(order)
    used, rng, new_shot = existing_tokens(), random.Random(TOKEN_SEED), {}
    for i in order:
        old = by[i]["screenshot_path"]
        if old not in new_shot:
            while True:
                t = f"P{rng.getrandbits(40):010x}"
                if t not in used:
                    used.add(t); break
            new_shot[old] = f"shots/{t}.png"
    src_old = viewer_src(f"{HE}/rater_A/viewer_A.html")
    os.makedirs(f"{RT}/shots")
    rows = [{"issue_id": i, "screenshot_path": new_shot[by[i]["screenshot_path"]], "description": by[i]["description"],
             "suggestion": by[i]["suggestion"], **{c: "" for c in bhe.INPUT_FIELDS}} for i in order]
    with open(f"{RT}/eval_sheet_A_retest.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=mes.SHEET_COLS); w.writeheader(); w.writerows(rows)
    src = {}
    for old, new in new_shot.items():
        shutil.copyfile(f"{HE}/rater_A/{old}", f"{RT}/{new}")
        src[new] = src_old[old]
    open(f"{RT}/viewer_A_retest.html", "w", encoding="utf-8", newline="\n").write(bhe.make_viewer("A_retest", rows, src))
    shutil.copyfile("docs/rater_guidelines_v2.md", f"{RT}/rater_guidelines.md")
    json.dump({"created": "2026-11-16", "source_sheet": SHEET, "source_sheet_sha256": sha(SHEET),
               "seed_sample": SEED_SAMPLE, "seed_order": SEED_ORDER, "screenshot_token_seed": TOKEN_SEED,
               "method": {"sample": "random.Random(20261125).sample(sorted(eval_sheet_A.csv 의 issue_id), 40)",
                          "order": "random.Random(20261126).shuffle(sorted(표본 issue_id))"},
                          "inputs_not_used": "정답 키(key/), 채점 결과, 평가자 A 의 본 평가 답",
               "issue_ids_sorted": sorted(pick), "sheet_order": order, "pages": len(new_shot),
               "screenshot_map_note": "재판정 스크린샷은 rater_A/shots 의 같은 파일을 새 토큰 이름으로 복사(내용 같음)",
               "screenshot_map": {new: old for old, new in sorted(new_shot.items())},
               "viewer_storage_key": "human_eval_A_retest", "guidelines": "docs/rater_guidelines_v2.md",
               "sheet_sha256": sha(f"{RT}/eval_sheet_A_retest.csv")},
              open(samp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{RT}: {len(rows)} issues, {len(new_shot)} screenshots")


# ------------------------------------------------------------------ 누출 점검
def leak():
    from experiments.revision import human_eval_prep as hp
    terms = dict(hp.TERMS, **{"이전 답": r"_filled|이전 답|본 평가 답"})
    out, files = [], []

    def hits(text, where, file):
        for cat, pat in terms.items():
            for m in re.finditer(pat, text):
                s = text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ").replace("|", "/")
                out.append({"file": file, "where": where, "category": cat, "match": m.group(0), "context": s})
    nonblank = 0
    for root, _, fs in os.walk(RT):
        for fn in fs:
            p = os.path.join(root, fn).replace("\\", "/")
            rel = p[len(HE) + 1:]
            files.append(rel)
            hits(rel, "파일명·경로", rel)
            if fn.endswith(".csv"):
                _, rows = read_csv(p)
                hits(",".join(rows[0].keys()), "CSV 열 이름", rel)
                for r in rows:
                    nonblank += sum(1 for c in bhe.INPUT_FIELDS if r[c])
                    for k, v in r.items():
                        if k not in hp.TEXT_FIELDS:
                            hits(v, f"CSV 값({k})", rel)
            elif fn.endswith(".html"):
                s = open(p, encoding="utf-8").read()
                m_rows = re.search(r"const ROWS = (.*?);\n", s)
                m_src = re.search(r"const SRC = (.*?);\n", s)
                hits(s[:m_rows.start()] + s[m_src.end():], "뷰어 코드·마크업", rel)
                for r in json.loads(m_rows.group(1).replace("<\\/", "</")):
                    if set(r) != set(bhe.VIEW_FIELDS):
                        out.append({"file": rel, "where": "뷰어 데이터 열", "category": "입력 열 포함", "match": str(sorted(r)),
                                    "context": ""})
                    for k, v in r.items():
                        if k not in hp.TEXT_FIELDS:
                            hits(v, f"뷰어 데이터({k})", rel)
                for shot, h in json.loads(m_src.group(1).replace("<\\/", "</")).items():
                    hits(h, f"포함된 페이지 HTML ({shot})", rel)
            elif fn.endswith(".md"):
                hits(open(p, encoding="utf-8").read(), "지침서 본문", rel)
            elif fn.endswith(".png") and hp.png_text_chunks(p):
                out.append({"file": rel, "where": "PNG 메타데이터", "category": "메타데이터 있음", "match": "", "context": ""})
    if os.path.exists(f"{HE}/retest_howto.md"):
        files.append("retest_howto.md")
        hits(open(f"{HE}/retest_howto.md", encoding="utf-8").read(), "안내문 본문", "retest_howto.md")
    # 재판정 스크린샷 파일명이 본 시트 토큰과 겹치지 않는지
    a_tokens = set(os.listdir(f"{HE}/rater_A/shots"))
    reused = sorted(set(os.listdir(f"{RT}/shots")) & a_tokens)
    for h in out:
        if h["where"] == "뷰어 코드·마크업" and h["match"] == "fixed" and "position:fixed" in h["context"]:
            h["where"] = "뷰어 코드·마크업 CSS"
        if h["where"] == "안내문 본문" and h["match"] == "guideline" and "rater_guidelines.md" in h["context"]:
            h["where"] = "안내문 본문 지침서 파일명"
        if h["where"] == "안내문 본문" and h["category"] == "이전 답" and (
                "retest_filled.csv" in h["context"] or "열어 보지 마세요" in h["context"] or "보지 마세요" in h["context"]):
            h["where"] = "안내문 본문 안내 문구"
    judge = {"안내문 본문 안내 문구": "예상됨: 내보낼 파일 이름·찾아보지 말라는 안내","뷰어 코드·마크업 CSS": "예상됨: CSS position:fixed (조건명 아님)",
             "뷰어 코드·마크업": "예상됨: 6분류 선택지 문구(모든 행에 같음)",
             "지침서 본문": "예상됨: 지침서 v2 의 6분류 정의와 예시",
             "파일명·경로": "예상됨: 지침서 파일명 rater_guidelines.md",
             "안내문 본문 지침서 파일명": "예상됨: 지침서 파일명 언급"}
    json.dump({"files": sorted(files), "hits": out, "nonblank_input_cells": nonblank, "reused_screenshot_names": reused},
              open(f"{HE}/leak_audit_retest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = Counter((h["file"].split("/")[0], h["where"].split("(")[0].strip(), h["category"], h["match"]) for h in out)
    leaks = [k for k in c if k[1] not in judge]
    L = ["# 재판정 시트 정보 누출 점검", "",
         "작성: `experiments/revision/human_eval_A_followup.py leak` (API 호출 없음). 2026-11-16.",
         "방법: 본 시트 점검(`leak_audit.md`)과 같은 검색어·위치에, 이전 답 흔적('_filled', '이전 답', '본 평가 답'),",
         "입력 칸이 비었는지, 스크린샷 파일명이 본 시트와 겹치는지를 더했다. `retest_howto.md` 본문도 검사했다.",
         "원 검색 결과: `results/revision/human_eval/leak_audit_retest.json`.", "",
         f"검사한 파일 {len(files)}개 (rater_A_retest/ 와 retest_howto.md). 제외: 이슈 설명·제안 본문.", "",
         "## 1. 검색 결과", "", "| 폴더 | 위치 | 분류 | 일치 | 건수 | 판단 |", "|---|---|---|---|---|---|"]
    for (fo, w, cat, m), k in sorted(c.items()):
        L.append(f"| {fo} | {w} | {cat} | {m} | {k} | {judge.get(w, '확인 필요')} |")
    L += ["", "출처: `results/revision/human_eval/leak_audit_retest.json`", "",
          "## 2. 추가 점검", "", "| 점검 | 결과 |", "|---|---|",
          f"| 시트 입력 칸(5개 열 × 40행) 중 값이 있는 칸 | {nonblank} |",
          f"| 본 시트와 이름이 같은 스크린샷 파일 | {len(reused)} |", "",
          "출처: 위와 같음", "",
          f"**누출로 판단한 항목: {len(leaks) + (1 if nonblank else 0) + (1 if reused else 0)}건.**", "",
          "## 3. 알아둘 점", "",
          "- issue_id 는 본 시트와 같다(비교 스크립트가 issue_id 로 맞추기 때문). 평가자가 자기 본 평가 CSV 를 열어",
          "  issue_id 로 찾으면 이전 답을 볼 수 있다. retest_howto.md 에서 찾아보지 말라고 안내했다.",
          "- 스크린샷 그림 내용은 본 시트와 같은 파일이다(이름만 새 토큰).", ""]
    open(f"{HE}/leak_audit_retest.md", "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"files {len(files)}, hits {len(out)}, leaks {len(leaks)}, nonblank {nonblank}, reused {len(reused)}")


if __name__ == "__main__":
    {"intake": intake, "retest": retest, "leak": leak}[sys.argv[1]]()
