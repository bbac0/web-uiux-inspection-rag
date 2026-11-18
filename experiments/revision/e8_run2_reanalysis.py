"""
E8 레거시 run2 재분석 (API 호출 없음, 읽기 전용).
입력: paper_results/run2/report_page_*.json (200개, 분석 360건), results/revision/ground_truth.csv (E0)
채점: evaluate_performance_v5.py 의 키워드 사전과 대상 페이지 필터를 그대로 import 해 쓴다 (수정 없음).

출력 (results/revision/): e8_run2_reanalysis.md, e8_*.csv
"""

import csv
import importlib.util
import json
import os
import re
from collections import Counter, defaultdict

from PyPDF2 import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
RUN2 = "paper_results/run2"
OUT = "results/revision"
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
CORPUS = {"gov_guide.pdf": len(PdfReader("data/gov_guide.pdf").pages),
          "gov_check.pdf": len(PdfReader("data/gov_check.pdf").pages)}
PROMPT_EXAMPLE_FILE = "gov_guide.pdf"
PROMPT_EXAMPLE_PAGES = ([12], [12, 13])


def load_kw():
    spec = importlib.util.spec_from_file_location("kw", "experiments/evaluate_performance_v5.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def wcsv(name, rows, fields=None):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    kw = load_kw()
    gt = defaultdict(dict)
    tpl = {}
    for r in csv.DictReader(open(os.path.join(OUT, "ground_truth.csv"), encoding="utf-8")):
        gt[r["page_id"]][r["defect_type"]] = (int(r["nominal_injected"]), int(r["effective_1280"]))
        tpl[r["page_id"]] = r["template_id"]

    pages = {}
    for pid in sorted(gt):
        rep = json.load(open(f"{RUN2}/report_{pid}.json", encoding="utf-8"))
        marker = f"testbed_200/{pid}.html"
        on = [i for i in rep.get("issues", []) if isinstance(i, dict) and marker in (i.get("description") or "")]
        matched = defaultdict(list)
        for i in on:
            for t in kw.match_categories_in_issue(i.get("description") or ""):
                matched[t].append(i["description"])
        pages[pid] = {"report": rep, "on": on, "matched": matched}

    L = ["# E8 레거시 run2 재분석", "",
         f"- 입력: `{RUN2}` 리포트 200개 (SHA-256 은 `legacy_run2_manifest.csv`), 정답은 E0 `ground_truth.csv` (effective = 1280 뷰포트).",
         "- 채점: `evaluate_performance_v5.py` 키워드 사전과 대상 페이지 필터를 그대로 사용 (다중 라벨).",
         "- run2 는 빈 벡터 DB(0청크)로 실행되었다 → (iv).", ""]

    # (i) 효과 없는 버튼 잘림
    ineff_btn = [p for p in gt if gt[p]["Button Area Clipping"] == (1, 0)]
    rows_i = []
    for p in ineff_btn:
        hit = p in pages and "Button Area Clipping" in pages[p]["matched"]
        ev = pages[p]["matched"].get("Button Area Clipping", [])
        rows_i.append({"page_id": p, "template_id": tpl[p], "keyword_detected_button": int(hit),
                       "n_matching_issues": len(ev), "example_description": (ev[0] if ev else "")[:300]})
    wcsv("e8_i_ineffective_button.csv", rows_i)
    nhit = sum(r["keyword_detected_button"] for r in rows_i)
    eff_btn = [p for p in gt if gt[p]["Button Area Clipping"] == (1, 1)]
    nhit_eff = sum("Button Area Clipping" in pages[p]["matched"] for p in eff_btn)
    L += ["## (i) 효과 없는 버튼 잘림 26페이지", "",
          f"- 키워드 채점이 Button Area Clipping 을 '탐지'로 센 페이지: **{nhit}/{len(ineff_btn)} ({nhit / len(ineff_btn):.1%})**",
          f"- 참고: 효과가 있는 버튼 잘림 페이지에서는 {nhit_eff}/{len(eff_btn)} ({nhit_eff / len(eff_btn):.1%})",
          "- 상세: `e8_i_ineffective_button.csv`", ""]

    # (ii) 미주입 용어 위반
    nonterm = [p for p in gt if gt[p]["Standard Terminology Violation"] == (1, 0)]
    rows_ii = []
    L += ["## (ii) 미주입 용어 위반 3페이지 (form_page)", "",
          "| page_id | 다른 nominal 결함 | 키워드 매칭 유형 | 용어 탐지 | 대상 이슈 수 | '로그인'/'접속' 언급 이슈 |", "|---|---|---|---|---:|---:|"]
    for p in nonterm:
        others = [t for t in TYPES if gt[p][t][0] and t != "Standard Terminology Violation"]
        m = sorted(pages[p]["matched"])
        term_mentions = [i["description"] for i in pages[p]["on"] if re.search("로그인|접속", i.get("description") or "")]
        rows_ii.append({"page_id": p, "other_nominal_defects": ";".join(others), "keyword_matched_types": ";".join(m),
                        "terminology_detected": int("Standard Terminology Violation" in m),
                        "n_on_target_issues": len(pages[p]["on"]), "n_login_mentions": len(term_mentions),
                        "descriptions": " || ".join(i["description"][:200] for i in pages[p]["on"])})
        L.append(f"| {p} | {', '.join(others)} | {', '.join(m) or '-'} | {'예' if 'Standard Terminology Violation' in m else '아니오'} | "
                 f"{len(pages[p]['on'])} | {len(term_mentions)} |")
    wcsv("e8_ii_noninjected_terminology.csv", rows_ii)
    L += ["", "- 이슈 원문: `e8_ii_noninjected_terminology.csv`", ""]

    # (iii) 유형별 탐지율 nominal vs effective
    rows_iii = []
    L += ["## (iii) 키워드 채점 유형별 결과: nominal vs effective", "",
          "| 유형 | 라벨 | 양성 | TP | 재현율 | FP | 음성 | 특이도 |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for t in TYPES:
        for li, lab in ((0, "nominal"), (1, "effective")):
            tp = fn = fp = tn = 0
            for p in gt:
                y = gt[p][t][li]
                d = t in pages[p]["matched"]
                tp += y and d; fn += y and not d; fp += (not y) and d; tn += (not y) and not d
            rec = tp / (tp + fn) if tp + fn else None
            spe = tn / (tn + fp) if tn + fp else None
            rows_iii.append({"defect_type": t, "label_set": lab, "positives": tp + fn, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
                             "recall": rec, "specificity": spe})
            L.append(f"| {t} | {lab} | {tp + fn} | {tp} | {rec:.3f} | {fp} | {tn + fp} | {spe:.3f} |")
    wcsv("e8_iii_type_detection.csv", rows_iii)
    L += ["", "- 셀 단위(페이지×유형) 결과. effective 에서는 효과 없는 버튼 26셀·미주입 용어 3셀이 음성으로 바뀌므로 그 셀의 탐지는 FP 가 된다.", ""]

    # (iv) rag_status
    rag = Counter()
    for p, d in pages.items():
        for s in d["report"].get("rag_status", []):
            role = "target" if s.get("url", "").endswith(f"{p}.html") else "linked(/login 등)"
            rag[(role, s.get("enabled"), s.get("ok"), s.get("n_chunks"), s.get("error"))] += 1
    rows_iv = [{"role": k[0], "enabled": k[1], "ok": k[2], "n_chunks": k[3], "error": k[4], "count": v} for k, v in sorted(rag.items(), key=str)]
    wcsv("e8_iv_rag_status.csv", rows_iv)
    L += ["## (iv) rag_status 집계 (분석 360건)", "", "| 대상 | enabled | ok | n_chunks | error | 건수 |", "|---|---|---|---:|---|---:|"]
    L += [f"| {r['role']} | {r['enabled']} | {r['ok']} | {r['n_chunks']} | {r['error']} | {r['count']} |" for r in rows_iv]
    L += [""]

    # (v) source_file / page_number
    allissues = []
    for p, d in pages.items():
        for i in d["report"].get("issues", []):
            if isinstance(i, dict):
                allissues.append((p, "target" if i in d["on"] else "linked", i))
    n = len(allissues)
    sf = Counter(str(i.get("source_file")) for _, _, i in allissues)
    pn = Counter(json.dumps(i.get("page_number"), ensure_ascii=False) for _, _, i in allissues)
    is_ex_file = sum(i.get("source_file") == PROMPT_EXAMPLE_FILE for _, _, i in allissues)
    is_ex_pages = sum(i.get("page_number") in PROMPT_EXAMPLE_PAGES for _, _, i in allissues)
    has12 = sum(isinstance(i.get("page_number"), list) and 12 in i["page_number"] for _, _, i in allissues)
    both_ex = sum(i.get("source_file") == PROMPT_EXAMPLE_FILE and i.get("page_number") in PROMPT_EXAMPLE_PAGES for _, _, i in allissues)
    not_corpus = sum(i.get("source_file") not in CORPUS for _, _, i in allissues)
    out_of_range = 0
    for _, _, i in allissues:
        f, pg = i.get("source_file"), i.get("page_number")
        if f in CORPUS and isinstance(pg, list) and any((not isinstance(x, int)) or x < 1 or x > CORPUS[f] for x in pg):
            out_of_range += 1
    wcsv("e8_v_source_file.csv", [{"source_file": k, "count": v, "share": round(v / n, 4), "in_corpus": int(k in CORPUS)}
                                  for k, v in sf.most_common()])
    wcsv("e8_v_page_number.csv", [{"page_number": k, "count": v, "share": round(v / n, 4),
                                   "equals_prompt_example": int(json.loads(k) in PROMPT_EXAMPLE_PAGES)} for k, v in pn.most_common()])
    pct = lambda x: f"{x}/{n} ({x / n:.1%})"
    L += ["## (v) 근거 필드 (source_file, page_number) — 이슈 전체", "",
          f"- 이슈 수: {n} (대상 페이지 {sum(1 for a in allissues if a[1] == 'target')}, 링크된 페이지 {sum(1 for a in allissues if a[1] == 'linked')})",
          f"- 말뭉치 PDF 쪽수: gov_guide.pdf {CORPUS['gov_guide.pdf']}쪽, gov_check.pdf {CORPUS['gov_check.pdf']}쪽",
          f"- source_file 이 프롬프트 예시값 `gov_guide.pdf`: {pct(is_ex_file)}",
          f"- page_number 가 프롬프트 예시값 `[12]` 또는 `[12, 13]`: {pct(is_ex_pages)}; 12 를 포함: {pct(has12)}",
          f"- 파일과 쪽이 모두 프롬프트 예시값: {pct(both_ex)}",
          f"- 말뭉치에 없는 파일명: {pct(not_corpus)}",
          f"- 말뭉치 파일이지만 쪽 번호가 범위 밖이거나 정수가 아님: {pct(out_of_range)}",
          "- run2 는 검색 컨텍스트가 비어 있었으므로 모든 인용은 모델이 컨텍스트 없이 만든 값이다.", "",
          "| source_file | 건수 | 비율 |", "|---|---:|---:|"]
    L += [f"| `{k}` | {v} | {v / n:.1%} |" for k, v in sf.most_common(10)]
    L += ["", "| page_number | 건수 | 비율 |", "|---|---:|---:|"]
    L += [f"| `{k}` | {v} | {v / n:.1%} |" for k, v in pn.most_common(10)]
    L += [""]

    # (vi) total_checked_count
    tc = Counter()
    for p, d in pages.items():
        npg = len(d["report"].get("rag_status", []))
        tc[(npg, d["report"].get("total_count"))] += 1
    rows_vi = [{"pages_analyzed_in_report": k[0], "total_count": k[1], "reports": v} for k, v in sorted(tc.items())]
    wcsv("e8_vi_total_checked_count.csv", rows_vi)
    one = {k[1]: v for k, v in tc.items() if k[0] == 1}
    two = {k[1]: v for k, v in tc.items() if k[0] == 2}
    bucket = lambda d: {"30": d.get(30, 0), "60": d.get(60, 0), "기타": sum(v for k, v in d.items() if k not in (30, 60))}
    L += ["## (vi) total_checked_count 분포", "",
          "리포트의 `total_count` 는 분석한 페이지들의 `total_checked_count` 합이다. 1페이지 리포트(40개)만 값이 곧 모델 출력이다.", "",
          f"- 1페이지 리포트 {sum(one.values())}개: {bucket(one)} — 상세 {dict(sorted(one.items()))}",
          f"- 2페이지 리포트 {sum(two.values())}개 (두 값의 합): {bucket(two)} — 상세 {dict(sorted(two.items()))}",
          "- 상세: `e8_vi_total_checked_count.csv`"]
    open(os.path.join(OUT, "e8_run2_reanalysis.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
