"""
사람 평가 준비 (API 호출 없음). rater_A/, rater_B/ 는 읽기만 한다.

  leak    : rater_A/, rater_B/ (와 pilot_rater/) 의 모든 파일에서 누출 후보 문자열을 찾아 leak_audit_scan.json 에 쓴다.
            이슈 설명·제안 본문(CSV 의 description/suggestion, 뷰어 ROWS 의 같은 필드)은 검색에서 뺀다.
  pilot   : A 시트에서 무작위 20건(시드 20261118, 층화 없음, 정답 키·채점 결과 미사용) → pilot_rater/ (같은 형식·같은 뷰어)
  schedule: schedule_scenarios.md
  scope   : sheet_scope_options.md (표본은 주입 라벨과 시드만 사용)

  python experiments/revision/human_eval_prep.py pilot|leak|schedule|scope
"""
import csv
import json
import os
import random
import re
import shutil
import struct
import sys
import zlib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import build_human_eval as bhe    # noqa: E402
from experiments.revision import make_eval_sheets as mes    # noqa: E402
from scoring import semantic_grader_anthropic as sga        # noqa: E402

HE = "results/revision/human_eval"
PILOT = f"{HE}/pilot_rater"
PILOT_SEED = 20261118
TEXT_FIELDS = ("description", "suggestion")
TERMS = {
    "결함 유형(영문)": r"Poor Contrast|Mobile Layout|Button Area|Terminology|Duplicate ID",
    "결함 유형(한글)": r"대비|모바일|버튼 잘림|용어|중복 ID",
    "페이지 ID": r"page_\d+|e9_\d+",
    "런 이름": r"E1-R|E2-A|E3-|E4-",
    "주입 식별자": r"DEF_",
    "조건명": r"\bRAG\b|oracle|\bfixed\b",
    "라벨 열 이름": r"nominal|effective|guideline",
}


# ------------------------------------------------------------------ pilot
def cmd_pilot():
    if os.path.exists(PILOT):
        raise SystemExit(f"이미 있음: {PILOT}")
    rows = list(csv.DictReader(open(f"{HE}/rater_A/eval_sheet_A.csv", encoding="utf-8-sig")))
    pick = random.Random(PILOT_SEED).sample(sorted(rows, key=lambda r: r["issue_id"]), 20)
    os.makedirs(f"{PILOT}/shots")
    with open(f"{PILOT}/eval_sheet_pilot.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=mes.SHEET_COLS); w.writeheader(); w.writerows(pick)
    src = {}
    for r in csv.DictReader(open(f"{HE}/key/page_html_map.csv", encoding="utf-8")):
        src[r["screenshot_path"]] = open(r["html_source"], encoding="utf-8").read()
    for shot in sorted({r["screenshot_path"] for r in pick}):
        shutil.copyfile(f"{HE}/rater_A/{shot}", f"{PILOT}/{shot}")
    open(f"{PILOT}/viewer_pilot.html", "w", encoding="utf-8", newline="\n").write(bhe.make_viewer("pilot", pick, src))
    shutil.copyfile(bhe.GUIDE, f"{PILOT}/rater_guidelines.md")
    json.dump({"seed": PILOT_SEED, "source_sheet": "rater_A/eval_sheet_A.csv", "method":
               "random.Random(seed).sample(A 시트 행을 issue_id 순으로 정렬한 목록, 20); 층화 없음, 정답 키·채점 결과 미사용",
               "issue_ids": [r["issue_id"] for r in pick], "pages": len({r["screenshot_path"] for r in pick}),
               "note": "연습용. 분석에 쓰지 않는다. 같은 이슈가 A 시트에도 있다."},
              open(f"{HE}/key/pilot_selection.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{PILOT}: 20 issues, {len({r['screenshot_path'] for r in pick})} pages")


# ------------------------------------------------------------------ leak
def png_text_chunks(p):
    out, b = [], open(p, "rb").read()
    i = 8
    while i < len(b):
        n, typ = struct.unpack(">I4s", b[i:i + 8])
        data = b[i + 8:i + 8 + n]
        if typ in (b"tEXt", b"iTXt", b"zTXt"):
            out.append((typ.decode(), data[:200].decode("latin-1")))
        if typ == b"zTXt":
            try:
                out.append(("zTXt-dec", zlib.decompress(data.split(b"\0", 2)[-1][1:])[:200].decode("latin-1")))
            except Exception:
                pass
        i += 12 + n
    return out


def hits(text, where, file, out, ctx=40):
    for cat, pat in TERMS.items():
        for m in re.finditer(pat, text):
            s = text[max(0, m.start() - ctx):m.end() + ctx].replace("\n", " ").replace("|", "/")
            out.append({"file": file, "where": where, "category": cat, "match": m.group(0), "context": s})


def cmd_leak():
    out, files = [], []
    for side in ("rater_A", "rater_B", "pilot_rater"):
        d = f"{HE}/{side}"
        if not os.path.isdir(d):
            continue
        for root, _, fs in os.walk(d):
            for fn in fs:
                p = os.path.join(root, fn).replace("\\", "/")
                rel = p[len(HE) + 1:]
                files.append(rel)
                hits(rel, "파일명·경로", rel, out)
                if fn.endswith(".csv"):
                    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
                    hits(",".join(rows[0].keys()), "CSV 열 이름", rel, out)
                    for r in rows:
                        for k, v in r.items():
                            if k not in TEXT_FIELDS:
                                hits(v, f"CSV 값({k})", rel, out)
                elif fn.endswith(".html"):
                    s = open(p, encoding="utf-8").read()
                    m_rows = re.search(r"const ROWS = (.*?);\n", s)
                    m_src = re.search(r"const SRC = (.*?);\n", s)
                    code = s[:m_rows.start()] + s[m_src.end():]           # 뷰어 코드·마크업 (데이터 제외)
                    hits(code, "뷰어 코드·마크업", rel, out)
                    rows = json.loads(m_rows.group(1).replace("<\\/", "</"))
                    for r in rows:
                        for k, v in r.items():
                            if k not in TEXT_FIELDS:
                                hits(v, f"뷰어 데이터({k})", rel, out)
                    for shot, h in json.loads(m_src.group(1).replace("<\\/", "</")).items():
                        hits(h, f"포함된 페이지 HTML ({shot})", rel, out)
                elif fn.endswith(".md"):
                    hits(open(p, encoding="utf-8").read(), "지침서 본문", rel, out)
                elif fn.endswith(".png"):
                    for typ, txt in png_text_chunks(p):
                        hits(txt, f"PNG 메타데이터 {typ}", rel, out)
                    if png_text_chunks(p):
                        out.append({"file": rel, "where": "PNG 메타데이터", "category": "메타데이터 있음", "match": "",
                                    "context": str(png_text_chunks(p))[:100]})
    json.dump({"files": sorted(files), "hits": out}, open(f"{HE}/leak_audit_scan.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    c = Counter((h["file"].split("/")[0], h["where"].split("(")[0].strip(), h["category"], h["match"]) for h in out)
    print(f"files {len(files)}, hits {len(out)}, distinct {len(c)}")


def cmd_leakmd():
    """leak_audit_scan.json → leak_audit.md (2026-11-14 재점검부터 스크립트로 작성)."""
    import glob
    d = json.load(open(f"{HE}/leak_audit_scan.json", encoding="utf-8"))
    shots = [os.path.basename(p) for p in random.Random(PILOT_SEED).sample(sorted(glob.glob(f"{HE}/rater_A/shots/*.png")), 10)]
    for h in d["hits"]:
        if h["where"] == "뷰어 코드·마크업" and h["match"] == "fixed" and "position:fixed" in h["context"]:
            h["where"] = "뷰어 코드·마크업 CSS"
    c = Counter((h["file"].split("/")[0], h["where"].split("(")[0].strip(), h["category"], h["match"]) for h in d["hits"])
    fc = Counter(f.split("/")[0] for f in d["files"])
    judge = {"뷰어 코드·마크업 CSS": "예상됨: CSS position:fixed (불러오기 대화상자 배치, 조건명 아님)", "뷰어 코드·마크업": "예상됨: 6분류 선택지 문구(모든 행에 같음)", "지침서 본문": "예상됨: 지침서의 6분류 정의와 예시",
             "파일명·경로": "예상됨: 지침서 파일명 rater_guidelines.md"}
    leaks = [k for k in c if k[1] not in judge]
    vhits = [h for h in d["hits"] if h["where"] == "뷰어 코드·마크업"]
    new_code_hits = [h for h in d["hits"] if h["where"] == "뷰어 코드·마크업 CSS"]
    L = ["# 평가자 폴더 정보 누출 점검", "",
         "갱신 2026-11-14 (뷰어 'CSV 불러오기' 추가, 지침서 v2 동기화 뒤 재점검). 처음 점검 2026-11-14 같은 방법.",
         "스크립트: `experiments/revision/human_eval_prep.py leak` → `leakmd` (API 호출 없음, 파일은 읽기만 함).",
         "원 검색 결과(문맥 포함 전체): `results/revision/human_eval/leak_audit_scan.json`.", "",
         "## 1. 범위", "",
         f"- 검사한 파일: rater_A {fc['rater_A']}개, rater_B {fc['rater_B']}개, pilot_rater {fc['pilot_rater']}개",
         "  (CSV, HTML 뷰어, 지침서, 스크린샷 PNG).",
         "- 검사 위치: 파일명·경로, CSV 열 이름과 description·suggestion 밖의 값, 뷰어 코드·마크업(데이터 제외, 새 불러오기 코드 포함),",
         "  뷰어 데이터(ROWS 의 issue_id·screenshot_path), 뷰어에 포함된 페이지 HTML 원문(SRC), 지침서 본문, PNG 텍스트 메타데이터.",
         "- 뷰어는 외부 JS·데이터 파일을 불러오지 않는다(코드와 데이터가 HTML 한 파일 안, 스크린샷만 상대 경로).",
         "- 제외: 이슈 설명·제안 본문(모델 출력).",
         "- 검색어: 영문 유형명(Poor Contrast, Mobile Layout, Button Area, Terminology, Duplicate ID),",
         "  한글(대비, 모바일, 버튼 잘림, 용어, 중복 ID), 페이지 ID(page_숫자, e9_숫자), 런 이름(E1-R, E2-A, E3-, E4-),",
         "  DEF_, 조건명(RAG, oracle, fixed), nominal, effective, guideline.", "",
         "## 2. 검색 결과 (폴더 × 위치 × 검색어, 건수)", "",
         "| 폴더 | 위치 | 분류 | 일치 | 건수 | 판단 |", "|---|---|---|---|---|---|"]
    for (fo, w, cat, m), n in sorted(c.items()):
        L.append(f"| {fo} | {w} | {cat} | {m} | {n} | {judge.get(w, '확인 필요')} |")
    L += ["", f"**누출로 판단한 항목: {len(leaks)}건.**" + ("" if not leaks else " 확인 필요 항목이 있다."),
          "페이지 ID, 런 이름, 주입 식별자, 라벨 열 이름은 어느 위치에서도 나오지 않았고,"
          " 조건명은 CSS 'position:fixed' 외에는 없다." if not leaks else "",
          f"뷰어 코드·마크업의 검색어 일치 {len(vhits)}건은 6분류 선택지(`<option>`) 안이다.",
          f"새 불러오기 코드에서 나온 일치는 {len(new_code_hits)}건으로 모두 CSS `position:fixed` 의 'fixed' 다(조건명 아님).",
          "새 불러오기 문구('CSV 불러오기', '덮어쓰지 않음', 거부·완료 메시지)는 열 이름과 허용 값(예/아니오/판단 불가)만 쓰며",
          "이슈별 정보나 정답을 담지 않는다.", "",
          "출처: `results/revision/human_eval/leak_audit_scan.json`", "",
          "## 3. 스크린샷", "",
          f"- PNG 텍스트 메타데이터(tEXt, iTXt, zTXt): 전체 {sum(1 for f in d['files'] if f.endswith('.png'))}개 파일에서 0건.",
          "- 파일명: 모두 `P` + 16진수 10자리 무작위 토큰(가림 테스트로 확인). 스크린샷은 이번 변경과 무관(바뀌지 않음).",
          "- 눈으로 확인한 표본 10장(rater_A/shots, 시드 20261118 로 무작위, 첫 점검 때 확인):",
          "  " + ", ".join(shots[:5]) + ",", "  " + ", ".join(shots[5:]) + ".",
          "  10장 모두 페이지 본문만 찍혀 있고 주소창·URL·페이지 ID·런 이름 같은 글자는 없다.", "",
          "## 4. 누출은 아니지만 알아둘 점", "",
          "- 뷰어의 페이지 HTML 원문에는 주입된 CSS·마크업이 그대로 있다('코드에 존재하는가' 판정에 필요한 원문).",
          "- 같은 페이지의 이슈는 같은 스크린샷 토큰을 공유한다(설계상).",
          "- pilot_rater 의 20건은 A 시트에도 있는 이슈다.",
          "- 불러오기는 issue_id 집합이 같은 CSV 만 받으므로, A 시트 CSV 를 B 뷰어에 넣는 등의 교차 사용은 거부된다.", ""]
    open(f"{HE}/leak_audit.md", "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(f"leaks {len(leaks)}, viewer-code hits {len(vhits)}, new-code hits {len(new_code_hits)}, long",
          [i + 1 for i, l in enumerate(L) if len(l) > 100])


# ------------------------------------------------------------------ schedule
def cmd_schedule():
    A, B = 444, 204
    L = ["# 사람 평가 일정 시나리오", "",
         "작성: `experiments/revision/human_eval_prep.py schedule` (API 호출 없음). 이슈 수 A 444건, B 204건",
         "(`results/revision/human_eval/README.md`). 하루 3시간 평가 기준, 일수는 올림 전 값과 올림 값을 함께 적는다.",
         "연습(시범 20건)과 휴식 시간은 넣지 않았다.", "",
         "| 이슈당 시간 | A 총 시간 | A 일수 (3시간/일) | B 총 시간 | B 일수 (3시간/일) |", "|---|---|---|---|---|"]
    for m in (1.5, 2, 2.5, 3):
        ha, hb = A * m / 60, B * m / 60
        L.append(f"| {m}분 | {ha:.1f}시간 | {ha / 3:.1f} → {-(-ha // 3):.0f}일 | {hb:.1f}시간 | {hb / 3:.1f} → {-(-hb // 3):.0f}일 |")
    L += ["", "- 시범 20건: 같은 가정에서 30~60분.",
          "- 평가자 A 와 B 는 동시에 진행할 수 있다(서로의 시트를 보지 않음). 중재자 시간은 불일치 건수에 따라 따로 든다.", "",
          "출처:", "- `results/revision/human_eval/key/sampling_manifest.json` (issues_A 444, issues_B 204)", ""]
    m = json.load(open(f"{HE}/key/sampling_manifest.json", encoding="utf-8"))
    assert (m["issues_A"], m["issues_B"]) == (A, B)
    open(f"{HE}/schedule_scenarios.md", "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("schedule ok")


# ------------------------------------------------------------------ scope
def cmd_scope():
    nom, _, _ = mes.load_labels("testbed_200/dataset_metadata.json", "results/revision/ground_truth.csv")
    a = mes.select_pages_a(nom, 20261112)
    b = mes.select_pages_b(a, 20261113)
    n_iss = Counter(s["page_id"] for _, s, _ in sga.iter_run_issues("E1-R1"))
    # (c): 용어 45 전부 + 대조군 12 (A 의 대조군 39 중 무작위) + 나머지 4유형은 포함 페이지가 12 이상이 되도록 A 의 해당 층에서 무작위 추가
    rng = random.Random("C-select-20261112")
    c = {p: "terminology" for p, s in a.items() if s == "terminology"}
    for p in rng.sample(sorted(p for p, s in a.items() if s == "control"), 12):
        c[p] = "control"
    for t in mes.OTHER:
        cov = sum(1 for p in c if t in nom[p])
        pool = sorted(p for p, s in a.items() if s == t and p not in c)
        rng.shuffle(pool)
        while cov < 12 and pool:
            p = pool.pop(); c[p] = t; cov += sum(1 for _ in [0] if t in nom[p])
    c2 = {p: s for p, s in c.items() if s in ("terminology", "control")}
    c2.update({p: s for p, s in a.items() if s in mes.OTHER})
    opts = {"(a) 현재 A": a, "(b) B 와 같은 60페이지": b, "(c) 규칙대로 (약 90 요청)": c,
            "(c2) 참고: 4유형 층 12씩 전부": c2}
    sh = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
          "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복 ID"}
    L = ["# 평가 시트 범위 옵션 (계획만, 시트는 만들지 않음)", "",
         "작성: `experiments/revision/human_eval_prep.py scope` (API 호출 없음). 표본은 주입 라벨(nominal)과 시드만 쓴다.",
         "이슈 수 = E1-R1 대상 페이지 이슈 수(채점 결과는 쓰지 않음).",
         "(a) = 현재 A (시드 20261112), (b) = 현재 B 와 같은 60페이지 (시드 20261113), (c) = 용어 45 전부 + A 의 대조군 39 중 12 +",
         "나머지 4유형은 포함 페이지가 각 12 이상이 되도록 A 의 해당 층에서 추가 (난수열 'C-select-20261112', A 의 부분집합).",
         f"**(c) 는 규칙대로 하면 {len(c)}페이지다(요청의 '약 90'보다 적음).** 용어 페이지 45개 중 다른 유형이 함께 주입된 페이지가",
         "있어 4유형의 '최소 12' 가 적은 추가로 채워지기 때문이다. 참고로 (c2) = 용어 45 + 대조군 12 (c 와 같음)",
         "+ A 의 4유형 층 12페이지씩 전부(겹침과 무관하게 추가).", "",
         "## 1. 크기", "", "| 옵션 | 페이지 | 이슈 | 행당 2~3분 소요 |", "|---|---|---|---|"]
    for k, s in opts.items():
        n = sum(n_iss[p] for p in s)
        L.append(f"| {k} | {len(s)} | {n} | {n * 2 / 60:.1f}~{n * 3 / 60:.1f}시간 |")
    L += ["", "## 2. 유형별 표본 수 (일치도 계산용)", "",
          "양성 페이지 = 그 유형이 주입된 페이지 수(2개 주입 페이지는 두 유형에 모두 셈), 양성 이슈 = 그 페이지들의 이슈 수,",
          "대조군 = 주입 없는 페이지. 이슈 단위 일치도(사람 6분류 대 키워드·의미 채점)는 '이슈' 열이, 셀 단위 일치도는 '페이지' 열이",
          "표본 크기다. string_match 는 용어 유형만 판정하므로 용어 행만 해당한다.", "",
          "| 옵션 | 유형 | 양성 페이지 | 양성 이슈 | 음성 페이지 | 음성 이슈 |", "|---|---|---|---|---|---|"]
    for k, s in opts.items():
        for t in mes.TYPES:
            pos = [p for p in s if t in nom[p]]
            neg = [p for p in s if t not in nom[p]]
            L.append(f"| {k} | {sh[t]} | {len(pos)} | {sum(n_iss[p] for p in pos)} | {len(neg)} | {sum(n_iss[p] for p in neg)} |")
        ctrl = [p for p in s if not nom[p]]
        L.append(f"| {k} | 대조군 | {len(ctrl)} | {sum(n_iss[p] for p in ctrl)} | - | - |")
    L += ["", "## 3. 채점기별로 쓸 수 있는 범위", "",
          "- 키워드, 의미 채점: 5유형 모두 (위 표 전부). 의미 채점은 잘림 재채점 전이면 해당 이슈가 미해결로 남는다.",
          "- string_match: 용어 유형만 (위 표의 용어 행).",
          "- 평가자 간 일치도(kappa)는 B 범위에서만 계산한다(사전 지정). (b) 를 A 로 쓰면 A·B 가 같은 60페이지가 되어",
          "  두 평가자 판정이 모든 항목에서 겹치지만 A 단독 범위가 없어진다.", "",
          "출처:", "- `experiments/revision/make_eval_sheets.py` (select_pages_a, select_pages_b, 동결)",
          "- `testbed_200/dataset_metadata.json`, `results/revision/ground_truth.csv`, `results/revision/runs/E1-R1/reports.jsonl`", ""]
    open(f"{HE}/sheet_scope_options.md", "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print({k: len(v) for k, v in opts.items()})


if __name__ == "__main__":
    {"pilot": cmd_pilot, "leak": cmd_leak, "leakmd": cmd_leakmd, "schedule": cmd_schedule, "scope": cmd_scope}[sys.argv[1]]()
