"""
E6b axe-core 보고서 (API 호출 없음, 기술 집계만). 사전 지정: results/revision/analysis_plan_addendum_e6b.md.
입력: results/revision/e6b/scan_C_{1280,390}.json, run_log.json, results/revision/ground_truth.csv,
      비교용 results/revision/e6/scan_B_{1280,390}.json (E6 설정 B).
출력: results/revision/reports/q7_e6b_axe_wcag22.md (덮어쓰지 않음)
표 형식은 E6 보고서(results/revision/reports/e6_axe_report.md) 2절과 같다.
"""
import csv
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e6_axe_report as e6r     # noqa: E402  (TYPES, SH, MAP)

D = "results/revision/e6b"
OUT = "results/revision/reports/q7_e6b_axe_wcag22.md"
GT = "results/revision/ground_truth.csv"
VP = ["1280", "390"]


def tab(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def load(path):
    d = json.load(open(path, encoding="utf-8"))["pages"]
    viol = {p: {v["id"]: len(v["nodes"]) for v in d[p]["violations"]} for p in d}
    inc = {p: {v["id"] for v in d[p]["incomplete"]} for p in d}
    ran = {p: ({x["id"] for x in d[p]["passes"]} | set(d[p]["inapplicable"]) | set(viol[p]) | inc[p]) for p in d}
    return d, viol, inc, ran


def main():
    if os.path.exists(OUT):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUT}")
    log = json.load(open(f"{D}/run_log.json", encoding="utf-8"))
    lab = defaultdict(dict)
    for r in csv.DictReader(open(GT, encoding="utf-8")):
        for k in ("nominal", "effective_1280", "effective_390"):
            col = "nominal_injected" if k == "nominal" else k
            lab[k][(r["page_id"], r["defect_type"])] = int(r[col])
    pages = sorted({p for p, _ in lab["nominal"]})
    L = ["# 확인 7: axe-core 추가 스캔 (WCAG 2.2 규칙 켬, 1280px 와 모바일 390px)", "",
         "작성: `experiments/revision/e6b_axe_scan.py`(스캔), `experiments/revision/e6b_axe_report.py`(이 보고서).",
         "사전 지정: `results/revision/analysis_plan_addendum_e6b.md` (스캔 전 커밋 65d2751). API 비용 없음(로컬 스캔).",
         f"axe-core 4.14.0, Chromium {log.get('chromium_version')}, 대기 {log['wait']}. 스캔 오류 {len(log['errors'])}건.",
         f"스캔 시각 {log['started_utc']} ~ {log['finished_utc']}. 페이지 수 {log['pages_scanned']}.", "",
         "## 1. 설정 C", "",
         "- E6 설정 B(duplicate-id, duplicate-id-active, duplicate-id-aria 켬) + `axe.getRules(['wcag22a','wcag22aa'])` 규칙 전부 켬.",
         f"- 이 설치본에서 WCAG 2.2 태그로 켠 규칙: {', '.join(f'`{x}`' for x in log.get('enabled_extra_rules') or [])}.",
         "- 유형별 대응 규칙은 E6 부록 (c) 그대로: 대비 color-contrast, 중복 ID duplicate-id 계열, 버튼 target-size,",
         "  모바일·용어 없음.", "",
         "## 2. 유형별 TP·FP 페이지 수", "",
         "칸 = 페이지 수. 양성 = 그 라벨의 양성 페이지 수. inc = 대응 규칙이 incomplete 로만 보고된 페이지(위반으로 세지 않음).",
         "effective 는 스캔 뷰포트와 같은 뷰포트 라벨이다. 'E6 B' 열은 같은 뷰포트의 기존 설정 B 결과(TP / FP).", ""]
    summary = []
    for vk in VP:
        d, viol, inc, ran = load(f"{D}/scan_C_{vk}.json")
        _, vB, _, _ = load(f"results/revision/e6/scan_B_{vk}.json")
        for labk in ("nominal", f"effective_{vk}"):
            N = lab[labk]
            rows = []
            for t in e6r.TYPES:
                rules = e6r.MAP[t]
                det = lambda p, v=viol: any(r in v.get(p, {}) for r in rules)            # noqa: E731
                detB = lambda p: any(r in vB.get(p, {}) for r in rules)                  # noqa: E731
                incp = sum(1 for p in pages if not det(p) and any(r in inc.get(p, set()) for r in rules))
                pos = sum(N[(p, t)] for p in pages)
                tp = sum(1 for p in pages if det(p) and N[(p, t)])
                fp = sum(1 for p in pages if det(p) and not N[(p, t)])
                tpB = sum(1 for p in pages if detB(p) and N[(p, t)])
                fpB = sum(1 for p in pages if detB(p) and not N[(p, t)])
                rows.append([e6r.SH[t], pos, tp, fp, incp, f"{tpB} / {fpB}", ", ".join(rules) or "없음"])
                if labk == "nominal":
                    summary.append((vk, e6r.SH[t], pos, tp, fp))
            L += [f"### 2.{VP.index(vk) + 1} 설정 C, {vk}, 라벨 {labk}", ""]
            L += tab(["유형", "양성", "TP", "FP", "inc", "E6 B (TP / FP)", "대응 규칙"], rows)
            L += ["", f"출처: `{D}/scan_C_{vk}.json`, `results/revision/e6/scan_B_{vk}.json`, `{GT}`", ""]
        ts_ran = sum(1 for p in pages if "target-size" in ran.get(p, set()))
        ts_v = sum(1 for p in pages if "target-size" in viol.get(p, {}))
        ts_i = sum(1 for p in pages if "target-size" in inc.get(p, set()))
        L += [f"- {vk}: target-size 가 실행된 페이지 {ts_ran}, 위반 {ts_v}, incomplete {ts_i}.", ""]
    L += ["## 3. target-size 와 버튼 결함 (규칙 × 페이지)", ""]
    rows = []
    for vk in VP:
        d, viol, inc, ran = load(f"{D}/scan_C_{vk}.json")
        btn = [p for p in pages if lab["nominal"][(p, "Button Area Clipping")]]
        nonb = [p for p in pages if not lab["nominal"][(p, "Button Area Clipping")]]
        f = lambda ps, s: sum(1 for p in ps if "target-size" in s.get(p, {}))    # noqa: E731
        rows.append([vk, len(btn), f(btn, viol), f(btn, inc), len(nonb), f(nonb, viol), f(nonb, inc)])
    L += tab(["뷰포트", "버튼 결함 페이지", "위반", "incomplete", "나머지 페이지", "위반", "incomplete"], rows)
    L += ["", f"출처: `{D}/scan_C_{{1280,390}}.json`, `{GT}` (nominal)", "",
          "## 4. 한계", "",
          "- 사전 계획(E6 부록) 밖의 사후 추가 스캔이다(연구자 지시 2026-11-19). E6 결과는 바꾸지 않았다.",
          "- 버튼 결함은 버튼 높이 2px·글자 크기 0으로 만든다. target-size 는 24×24 CSS px 기준의 크기·간격 검사라 대응 규칙으로",
          "  보지만, 버튼이 없는 템플릿에서는 결함이 화면에 나타나지 않는다(`injection_procedure.md`).",
          "- 모바일 레이아웃 깨짐과 표준 용어는 axe-core 에 대응 규칙이 없어 구조적으로 0이다.",
          "- 페이지 단위 기술 집계이며 검정은 하지 않았다.", ""]
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(OUT, [s for s in summary])


if __name__ == "__main__":
    main()
