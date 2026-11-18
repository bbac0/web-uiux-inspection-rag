"""
E6 axe-core 보고서 (API 호출 없음, 검정 없음). 사전 지정: results/revision/analysis_plan_addendum_e6.md.
입력: results/revision/e6/scan_{A,B}_{1280,390}.json, run_log.json, results/revision/ground_truth.csv,
      LLM 비교: results/revision/runs/{E1-R1,E2-A1-1}/reports.jsonl, semantic_scores/{run}-sem-p1/grades.jsonl
출력: results/revision/reports/e6_axe_report.md, results/revision/e6/README.md
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import issue_table as it        # noqa: E402

D = "results/revision/e6"
GT = "results/revision/ground_truth.csv"
OUT = "results/revision/reports/e6_axe_report.md"
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
SH = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
      "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복ID", "control": "대조군"}
MAP = {"Poor Contrast Ratio": ["color-contrast"], "Mobile Layout Breakage": [], "Button Area Clipping": ["target-size"],
       "Standard Terminology Violation": [], "Duplicate ID Markup Error": ["duplicate-id", "duplicate-id-active", "duplicate-id-aria"]}
MAPPED = {r for v in MAP.values() for r in v}
SCANS = [("A", "1280"), ("B", "1280"), ("A", "390"), ("B", "390")]


def src(*p):
    return ["", "출처:"] + [f"- `{x}`" for x in p] + [""]


def tab(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def main():
    scans = {(c, v): json.load(open(f"{D}/scan_{c}_{v}.json", encoding="utf-8"))["pages"] for c, v in SCANS}
    log = json.load(open(f"{D}/run_log.json", encoding="utf-8"))
    lab = defaultdict(dict)
    for r in csv.DictReader(open(GT, encoding="utf-8")):
        lab["nominal"][(r["page_id"], r["defect_type"])] = int(r["nominal_injected"])
        lab["effective_1280"][(r["page_id"], r["defect_type"])] = int(r["effective_1280"])
        lab["effective_390"][(r["page_id"], r["defect_type"])] = int(r["effective_390"])
    pages = sorted({p for p, _ in lab["nominal"]})
    ptype = {p: [t for t in TYPES if lab["nominal"][(p, t)]] for p in pages}
    controls = [p for p in pages if not ptype[p]]
    viol = {k: {p: {v["id"]: len(v["nodes"]) for v in d[p]["violations"]} for p in d} for k, d in scans.items()}
    inc = {k: {p: {v["id"] for v in d[p]["incomplete"]} for p in d} for k, d in scans.items()}
    ran = {k: {p: ({x["id"] for x in d[p]["passes"]} | set(d[p]["inapplicable"]) | set(viol[k][p]) | inc[k][p]) for p in d}
           for k, d in scans.items()}

    L = ["# E6 axe-core 스캔 보고서", "",
         "작성: `experiments/revision/e6_axe_report.py` (API 호출 없음, 기술 집계만, 검정 없음).",
         "사전 지정: `results/revision/analysis_plan_addendum_e6.md` (스캔 전 커밋 133a1a6).",
         f"axe-core {next(iter(scans[('A', '1280')].values()))['version']}, Chromium {log.get('chromium_version')}, "
         f"대기 {log['wait']}.",
         f"스캔 오류 {len(log['errors'])}건. 대응 규칙: 대비 color-contrast, 중복 ID duplicate-id·duplicate-id-active·duplicate-id-aria,",
         "버튼 target-size(두 설정 모두 꺼짐), 모바일·용어 없음.", ""]

    # (1)
    L += ["## 1. 스캔 4회 요약", ""]
    rows = []
    for k in SCANS:
        d = scans[k]
        rows.append([f"{k[0]} / {k[1]}", len(d), sum(1 for p in d if viol[k][p]), sum(1 for p in d if inc[k][p]),
                     sum(len(viol[k][p]) for p in d), sum(sum(viol[k][p].values()) for p in d),
                     sum(1 for p in d if "target-size" in ran[k][p])])
    L += tab(["설정 / 뷰포트", "페이지", "위반 있는 페이지", "incomplete 있는 페이지", "위반 (규칙×페이지)", "위반 노드",
              "target-size 실행 페이지"], rows)
    L += src(f"{D}/scan_{{A,B}}_{{1280,390}}.json", f"{D}/run_log.json")
    L += ["### 1.1 규칙 ID별 위반 페이지 수 (상위 15, 4개 스캔)", ""]
    allr = Counter()
    for k in SCANS:
        for p in scans[k]:
            allr.update(viol[k][p].keys())
    top = [r for r, _ in allr.most_common(15)]
    L += tab(["규칙"] + [f"{c}/{v}" for c, v in SCANS] + ["대응 규칙"],
             [[r] + [sum(1 for p in scans[k] if r in viol[k][p]) for k in SCANS] + ["예" if r in MAPPED else "아니오"] for r in top])
    L += src(f"{D}/scan_{{A,B}}_{{1280,390}}.json")

    # (2)
    L += ["## 2. 유형별 TP·FP 페이지 수", "",
          "칸 = TP / FP. 양성 = 그 라벨의 양성 페이지 수. inc = 대응 규칙이 incomplete 로만 보고된 페이지(위반으로 세지 않음).",
          "effective 는 스캔 뷰포트와 같은 뷰포트 라벨(1280 스캔 → effective_1280, 390 스캔 → effective_390).", ""]
    for k in SCANS:
        for lname in ("nominal", f"effective_{k[1]}"):
            rows = []
            for t in TYPES:
                L_ = lab[lname]
                det = {p: any(r in viol[k][p] for r in MAP[t]) for p in pages}
                incp = sum(1 for p in pages if not det[p] and any(r in inc[k][p] for r in MAP[t]))
                rows.append([SH[t], sum(L_[(p, t)] for p in pages), sum(1 for p in pages if det[p] and L_[(p, t)]),
                             sum(1 for p in pages if det[p] and not L_[(p, t)]), incp,
                             ", ".join(MAP[t]) or "없음"])
            L += [f"### 2.{SCANS.index(k) + 1} 설정 {k[0]}, {k[1]}, 라벨 {lname}", ""]
            L += tab(["유형", "양성", "TP", "FP", "inc", "대응 규칙"], rows) + [""]
    L += src(f"{D}/scan_{{A,B}}_{{1280,390}}.json", GT)

    # (3)
    L += ["## 3. 대조군 39페이지의 위반 규칙 (자연 발생 이슈)", "",
          "칸 = 위반 페이지 수 (위반 노드 수 합계).", ""]
    rr = sorted({r for k in SCANS for p in controls for r in viol[k][p]})
    L += tab(["규칙"] + [f"{c}/{v}" for c, v in SCANS],
             [[r] + [f"{sum(1 for p in controls if r in viol[k][p])} ({sum(viol[k][p].get(r, 0) for p in controls)})"
                     for k in SCANS] for r in rr])
    L += ["", "대조군 중 위반이 하나도 없는 페이지: " +
          ", ".join(f"{c}/{v} {sum(1 for p in controls if not viol[(c, v)][p])}" for c, v in SCANS) + "."]
    L += src(f"{D}/scan_{{A,B}}_{{1280,390}}.json", GT)

    # (4)
    L += ["## 4. 대응 규칙 밖의 위반 (규칙 × 페이지 주입 유형, 위반 페이지 수)", "",
          "페이지 유형 = nominal 주입 유형(2개면 둘 다 셈), 대조군 = 주입 없음.", ""]
    groups = TYPES + ["control"]
    for k in SCANS:
        rs = sorted({r for p in pages for r in viol[k][p] if r not in MAPPED})
        rows = []
        for r in rs:
            cnt = Counter()
            for p in pages:
                if r in viol[k][p]:
                    for g in (ptype[p] or ["control"]):
                        cnt[g] += 1
            rows.append([r] + [cnt[g] for g in groups] + [sum(1 for p in pages if r in viol[k][p])])
        L += [f"### 4.{SCANS.index(k) + 1} 설정 {k[0]}, {k[1]}", ""]
        L += tab(["규칙"] + [SH[g] for g in groups] + ["전체"], rows) + [""]
    L += src(f"{D}/scan_{{A,B}}_{{1280,390}}.json", GT)

    # (5)
    L += ["## 5. 기존 LLM 결과와 비교 (nominal, 1280, 유형별 TP / FP 페이지 수, 검정 없음)", "",
          "LLM 열: 키워드 채점과 의미 채점 pass1(원 규칙, 잘림 = 음성; 재채점 전), string_match(용어만).", ""]
    llm = {}
    for rid in ("E1-R1", "E2-A1-1"):
        sem = {}
        for l in open(f"results/revision/semantic_scores/{rid}-sem-p1/grades.jsonl", encoding="utf-8"):
            x = json.loads(l)
            sem[x["issue_id"]] = x["label"] if x["status"] == "ok" else None
        kw, sm_, se = defaultdict(set), defaultdict(set), defaultdict(set)
        for r in it.build_rows(rid):
            for t in filter(None, r["keyword_types"].split(";")):
                kw[r["page_id"]].add(t)
            if r["string_match_term"]:
                sm_[r["page_id"]].add("Standard Terminology Violation")
            if sem.get(r["issue_id"]) in TYPES:
                se[r["page_id"]].add(sem[r["issue_id"]])
        llm[rid] = (kw, se, sm_)
    rows = []
    N = lab["nominal"]
    for t in TYPES:
        def c(pred):
            return f"{sum(1 for p in pages if pred(p) and N[(p, t)])} / {sum(1 for p in pages if pred(p) and not N[(p, t)])}"
        row = [SH[t], sum(N[(p, t)] for p in pages)]
        for k in (("A", "1280"), ("B", "1280")):
            row.append(c(lambda p, k=k: any(r in viol[k][p] for r in MAP[t])))
        for rid in ("E1-R1", "E2-A1-1"):
            kw, se, sm_ = llm[rid]
            row += [c(lambda p: t in kw[p]), c(lambda p: t in se[p])]
        row += [c(lambda p: t in llm["E1-R1"][2][p]) if t == "Standard Terminology Violation" else "-"]
        rows.append(row)
    L += tab(["유형", "양성", "axe A", "axe B", "R1 키워드", "R1 의미", "A1-1 키워드", "A1-1 의미", "R1 sm"], rows)
    L += ["", "R1 = E1-R1(RAG 켬), A1-1 = E2-A1-1(RAG 끔). LLM 의 실패 페이지는 음성."]
    L += src(f"{D}/scan_A_1280.json", f"{D}/scan_B_1280.json", "results/revision/runs/{E1-R1,E2-A1-1}/reports.jsonl",
             "results/revision/semantic_scores/{E1-R1,E2-A1-1}-sem-p1/grades.jsonl", GT)

    # (6)
    L += ["## 6. 한계", "",
          "- 규칙 매핑: 모바일 레이아웃 깨짐(리플로)과 표준 용어(레이블 문구 적절성)는 axe-core 에 대응 규칙이 없어 구조적으로 0이다.",
          "  버튼 잘림의 대응 규칙 target-size 는 4.14.0 에서 기본 꺼짐이라 사전 지정된 두 설정 모두에서 실행되지 않았다.",
          "  따라서 axe 와 LLM 의 비교는 대비와 중복 ID 두 유형에서만 의미가 있다.",
          "- 대응 규칙 밖 위반(4절)은 자동 탐지 범위 밖의 '자연 발생' 접근성 문제로, 주입 결함의 탐지로 세지 않았다.",
          "- 렌더링 시점: networkidle 후 3초에 한 번 스캔했다. 지연 로드나 상호작용 후 상태는 보지 않는다.",
          "  설정 A, B 는 같은 렌더링에서 차례로 실행했다(axe 는 DOM 을 바꾸지 않는다).",
          "- color-contrast 는 계산할 수 없는 경우(배경 이미지, 겹침 등) incomplete 로 보고하며 위반으로 세지 않았다(2절 inc 열).",
          "- duplicate-id 계열 중 duplicate-id, duplicate-id-active 는 4.14.0 에서 deprecated 다.",
          "- 페이지 단위 기술 집계이며 CI·검정은 하지 않았다. LLM 의미 채점은 재채점 전 값이다.", ""]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")

    R = ["# E6 axe-core 스캔 결과 폴더", "",
         "사전 지정: `results/revision/analysis_plan_addendum_e6.md`. 스크립트: `experiments/revision/e6_axe_scan.py`.", "",
         "## 실행 방식", "",
         f"- 도구: Playwright Chromium {log.get('chromium_version')} (Python),",
         f"  저장소 루트 `axe.min.js` (axe-core 4.14.0, SHA-256 {log['axe_sha256'][:16]}…)",
         "  를 `page.add_script_tag(content=...)` 로 주입 후 `axe.run(document, options)`.",
         "- 서버: `python -m http.server 8080 --bind 127.0.0.1 --directory <저장소 루트>`,",
         "  URL `http://localhost:8080/testbed_200/page_XXX.html`.",
         f"- 대기: {log['wait']} (기존 파이프라인과 같음). UA 는 프로덕션과 같음.",
         "- 뷰포트: 1280x800, 390x844 각각 새 브라우저 컨텍스트.",
         "- 규칙 활성화: 설정 A 는 옵션 없음(기본).",
         "  설정 B 는 `{rules: {duplicate-id, duplicate-id-active, duplicate-id-aria: {enabled: true}}}`.",
         "  한 번 렌더링한 페이지에서 A, B 를 차례로 실행.",
         "- 저장: 페이지별 violations·incomplete 전체, passes 는 규칙 ID 와 노드 수, inapplicable 은 규칙 ID.", "",
         "## 파일", "", "- `scan_A_1280.json`, `scan_B_1280.json`, `scan_A_390.json`, `scan_B_390.json`",
         "- `run_log.json` (시작·끝 시각, 설정, 오류)", "- `SHA256SUMS` (위 5개 파일)",
         f"- 스캔 시각 {log['started_utc']} ~ {log['finished_utc']}, 오류 {len(log['errors'])}건.", ""]
    open(f"{D}/README.md", "w", encoding="utf-8", newline="\n").write("\n".join(R) + "\n")
    print(OUT, "long:", [i + 1 for i, l in enumerate(L) if len(l) > 100], "readme long:", [i + 1 for i, l in enumerate(R) if len(l) > 100])


if __name__ == "__main__":
    main()
