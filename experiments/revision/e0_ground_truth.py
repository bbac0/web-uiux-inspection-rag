"""
E0 결함 주입 검증 (API 호출 없음, 결정적 검사).

각 페이지를 1280x800 과 390x844 로 렌더링해 계산된 스타일/레이아웃을 측정하고, 분석 계획 1절의 규칙으로
effective 라벨을 정한다. 대조군은 axe-core(v4.14.0, 기본 설정)로 자연 발생 이슈를 뽑는다.

출력 (results/revision/)
  ground_truth.csv        페이지 × 유형 1,000행: nominal_injected, effective_1280, effective_390, effective_injected, ...
  e0_measurements.json    페이지·뷰포트별 원 측정값
  control_issues.csv      대조군 39페이지 axe-core 위반 목록 (1280x800)
  e0_axe_controls_raw.json axe-core 원본 결과
  e0_summary.md           요약과 nominal/effective 불일치 목록

사용법:  python -m http.server 8080 --bind 127.0.0.1   (별도 터미널)
         python experiments/revision/e0_ground_truth.py
"""

import csv
import importlib.util
import json
import os
import sys
from collections import Counter

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = os.path.join("results", "revision")
BASE = os.environ.get("TESTBED_BASE_URL", "http://localhost:8080/testbed_200")
AXE = "axe.min.js"
VIEWPORTS = {"1280": (1280, 800), "390": (390, 844)}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")          # 프로덕션과 같은 UA
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
TERM = "접속하기"

MEASURE_JS = r"""() => {
  const rgb = s => { const m = (s || '').match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(',').map(x => parseFloat(x)); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const lin = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lum = c => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor);
      if (c && c.a > 0) return c; } return {r: 255, g: 255, b: 255, a: 1}; };
  const visible = (el, cs) => cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0;
  // 대비: 직접 텍스트 노드가 있는 보이는 요소
  const texts = [];
  for (const el of document.body.querySelectorAll('*')) {
    const own = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (!own) continue;
    const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    if (!visible(el, cs) || parseFloat(cs.fontSize) === 0 || r.width === 0 || r.height === 0) continue;
    const fg = rgb(cs.color), bg = bgOf(el);
    const L1 = lum(fg), L2 = lum(bg);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    texts.push({tag: el.tagName.toLowerCase(), text: own.slice(0, 40), color: cs.color, bg: `rgb(${bg.r}, ${bg.g}, ${bg.b})`,
                ratio: Math.round(ratio * 1000) / 1000});
  }
  texts.sort((a, b) => a.ratio - b.ratio);
  const btns = Array.from(document.querySelectorAll('button, input[type=submit], input[type=button], input[type=reset]')).map(b => {
    const r = b.getBoundingClientRect(), cs = getComputedStyle(b);
    return {tag: b.tagName.toLowerCase(), cls: b.className || '', text: (b.textContent || b.value || '').trim(),
            height: Math.round(r.height * 100) / 100, width: Math.round(r.width * 100) / 100, fontSize: parseFloat(cs.fontSize)}; });
  const ids = {}; for (const el of document.querySelectorAll('[id]')) { (ids[el.id] = ids[el.id] || []).push(el); }
  const dups = Object.entries(ids).filter(([k, v]) => v.length > 1).map(([k, v]) => ({id: k, count: v.length,
      visible_area: v.reduce((s, e) => { const r = e.getBoundingClientRect(); return s + r.width * r.height; }, 0)}));
  const termEls = Array.from(document.querySelectorAll('title, body *')).filter(e =>
      Array.from(e.childNodes).some(n => n.nodeType === 3 && n.textContent.includes('%TERM%'))).map(e => e.tagName.toLowerCase());
  return {
    viewport: [window.innerWidth, window.innerHeight],
    scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth,
    texts: texts.slice(0, 5), n_texts: texts.length, min_ratio: texts.length ? texts[0].ratio : null,
    buttons: btns, dup_ids: dups, term_in_text: (document.title + ' ' + document.body.textContent).includes('%TERM%'),
    term_elements: termEls, login_count: (document.title + ' ' + document.body.textContent).split('로그인').length - 1,
  };
}""".replace("%TERM%", TERM)


def load_gen():
    spec = importlib.util.spec_from_file_location("gen", "experiments/generate_200_testbed.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def effective(t, m):
    if t == "Poor Contrast Ratio":
        return int(m["min_ratio"] is not None and m["min_ratio"] < 4.5)
    if t == "Mobile Layout Breakage":
        return int(m["scrollWidth"] > m["innerWidth"])
    if t == "Button Area Clipping":
        return int(any(b["height"] <= 4 or b["fontSize"] == 0 for b in m["buttons"]))
    if t == "Standard Terminology Violation":
        return int(m["term_in_text"])
    if t == "Duplicate ID Markup Error":
        return int(len(m["dup_ids"]) > 0)


def measurement_str(t, m):
    if t == "Poor Contrast Ratio":
        x = m["texts"][0] if m["texts"] else None
        return f"min_ratio={m['min_ratio']}" + (f" ({x['tag']} '{x['text']}' {x['color']} on {x['bg']})" if x else "")
    if t == "Mobile Layout Breakage":
        return f"scrollWidth={m['scrollWidth']} innerWidth={m['innerWidth']}"
    if t == "Button Area Clipping":
        return "; ".join(f"{b['tag']}.{b['cls']} h={b['height']} fs={b['fontSize']}" for b in m["buttons"]) or "no buttons"
    if t == "Standard Terminology Violation":
        return f"'{TERM}' in {m['term_elements'] or '-'}; '로그인' x{m['login_count']}"
    if t == "Duplicate ID Markup Error":
        return "; ".join(f"#{d['id']} x{d['count']} area={d['visible_area']:.0f}" for d in m["dup_ids"]) or "no duplicate ids"


def location(t, tpl, m):
    if t == "Poor Contrast Ratio":
        return "전역 CSS (* 선택자) → 모든 텍스트 요소"
    if t == "Mobile Layout Breakage":
        return "전역 CSS (html, body, div, main, header) width/min-width 3000px"
    if t == "Button Area Clipping":
        return ("CSS (button, .btn, .login-btn, .apply-btn) → " +
                (", ".join(f"{b['tag']}.{b['cls']}" for b in m["buttons"]) or "대상 요소 없음"))
    if t == "Standard Terminology Violation":
        return "텍스트 치환 '로그인'→'접속하기' → " + (", ".join(m["term_elements"]) or "치환 대상 없음")
    if t == "Duplicate ID Markup Error":
        return "<body> 첫 자식 div#main-banner ×2 (빈 요소)"


def main():
    gen = load_gen()
    pool = {d["type"]: d for d in gen.DEFECT_POOL}
    snippets = {"Poor Contrast Ratio": "* { color: #e5e5e5 !important; background-color: #ffffff !important; }",
                "Mobile Layout Breakage": "width: 3000px !important; min-width: 3000px !important;",
                "Button Area Clipping": "height: 2px !important; font-size: 0px !important;",
                "Standard Terminology Violation": TERM,
                "Duplicate ID Markup Error": '<div id="main-banner"></div><div id="main-banner"></div>'}
    meta = json.load(open("testbed_200/dataset_metadata.json", encoding="utf-8"))
    meas, rows, axe_raw, ctrl_rows = {}, [], {}, []
    axe_src = open(AXE, encoding="utf-8").read()
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        for vk, (w, h) in VIEWPORTS.items():
            ctx = br.new_context(viewport={"width": w, "height": h}, user_agent=UA)
            pg = ctx.new_page()
            for g in meta:
                pid = g["page_id"][:-5]
                pg.goto(f"{BASE}/{g['page_id']}", wait_until="networkidle", timeout=30000)
                meas.setdefault(pid, {})[vk] = pg.evaluate(MEASURE_JS)
                if vk == "1280" and not g["has_defect"]:
                    pg.add_script_tag(content=axe_src)
                    res = pg.evaluate("async () => { const r = await axe.run(); return {version: axe.version, violations: r.violations, incomplete: r.incomplete}; }")
                    axe_raw[pid] = res
                    for v in res["violations"]:
                        ctrl_rows.append({"page_id": pid, "template_id": g["base_template"], "axe_version": res["version"],
                                          "rule_id": v["id"], "impact": v["impact"], "tags": ";".join(v["tags"]),
                                          "n_nodes": len(v["nodes"]),
                                          "targets": " | ".join(",".join(n["target"]) for n in v["nodes"]),
                                          "help": v["help"]})
            ctx.close()
        br.close()

    for g in meta:
        pid = g["page_id"][:-5]
        html = open(f"testbed_200/{g['page_id']}", encoding="utf-8").read()
        nominal = {d["type"]: d["id"] for d in g["defects"]}
        for t in TYPES:
            m1, m3 = meas[pid]["1280"], meas[pid]["390"]
            e1, e3 = effective(t, m1), effective(t, m3)
            nom = int(t in nominal)
            rows.append({
                "page_id": pid, "template_id": g["base_template"], "defect_type": t,
                "defect_id": nominal.get(t, ""), "nominal_injected": nom,
                "static_string_present": int(snippets[t] in html),
                "effective_1280": e1, "effective_390": e3,
                "effective_injected": e1,              # E1~E3 기준 (E4 는 effective_390 사용)
                "injection_location": location(t, g["base_template"], m1) if nom else "",
                "exact_string": snippets[t] if nom else "",
                "measurement_1280": measurement_str(t, m1), "measurement_390": measurement_str(t, m3),
                "verification_pass_1280": int(nom == e1), "verification_pass_390": int(nom == e3),
                "screen_visible": "" if not nom else ("no" if t == "Duplicate ID Markup Error" else
                                                      ("no" if t == "Button Area Clipping" and not m1["buttons"] else "yes")),
            })

    with open(os.path.join(OUT, "ground_truth.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(os.path.join(OUT, "e0_measurements.json"), "w", encoding="utf-8") as f:
        json.dump(meas, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "e0_axe_controls_raw.json"), "w", encoding="utf-8") as f:
        json.dump(axe_raw, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "control_issues.csv"), "w", encoding="utf-8", newline="") as f:
        fields = ["page_id", "template_id", "axe_version", "rule_id", "impact", "tags", "n_nodes", "targets", "help"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(ctrl_rows)

    # ---- 요약과 불일치 분류
    no_button_tpl = {k for k, v in gen.BASE_TEMPLATES.items() if "<button" not in v}
    def known(r, vk):
        e = r[f"effective_{vk}"]
        if r["nominal_injected"] == 1 and e == 0:
            if r["defect_type"] == "Standard Terminology Violation" and r["template_id"] == "form_page":
                return "known: form_page 에 '로그인' 없음 (미주입)"
            if r["defect_type"] == "Button Area Clipping" and r["template_id"] in no_button_tpl:
                return "known: 버튼 없는 템플릿 (효과 없음)"
        return None
    mism = []
    for r in rows:
        for vk in ("1280", "390"):
            if r["nominal_injected"] != r[f"effective_{vk}"]:
                mism.append((r, vk, known(r, vk)))
    static_mism = [r for r in rows if r["static_string_present"] != r["nominal_injected"]
                   and not (r["defect_type"] == "Standard Terminology Violation" and r["template_id"] == "form_page")]
    new = [(r, vk) for r, vk, k in mism if k is None]
    L = ["# E0 결함 주입 검증 요약", "",
         f"- 렌더링: Chromium(Playwright), 뷰포트 1280x800 / 390x844, UA 프로덕션과 같음, `networkidle` 후 측정. axe-core {next(iter(axe_raw.values()))['version'] if axe_raw else '-'}.",
         "- 규칙: `analysis_plan.md` 1절 (대비 < 4.5:1, scrollWidth > innerWidth, 버튼 높이 ≤ 4px 또는 font-size 0, '접속하기' 존재, 같은 id ≥ 2).", "",
         "## 유형별 nominal vs effective (페이지 수)", "",
         "| 유형 | nominal | effective 1280 | effective 390 | nominal=1·eff1280=0 | nominal=0·eff1280=1 | nominal=1·eff390=0 | nominal=0·eff390=1 |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for t in TYPES:
        R = [r for r in rows if r["defect_type"] == t]
        c = lambda f: sum(1 for r in R if f(r))
        L.append(f"| {t} | {c(lambda r: r['nominal_injected'])} | {c(lambda r: r['effective_1280'])} | {c(lambda r: r['effective_390'])} | "
                 f"{c(lambda r: r['nominal_injected'] and not r['effective_1280'])} | {c(lambda r: not r['nominal_injected'] and r['effective_1280'])} | "
                 f"{c(lambda r: r['nominal_injected'] and not r['effective_390'])} | {c(lambda r: not r['nominal_injected'] and r['effective_390'])} |")
    ratios = sorted({meas[r['page_id']]['1280']['min_ratio'] for r in rows if r['defect_type'] == 'Poor Contrast Ratio' and r['nominal_injected']})
    cratio = sorted({meas[r['page_id']]['1280']['min_ratio'] for r in rows if r['defect_type'] == 'Poor Contrast Ratio' and not r['nominal_injected']})
    L += ["", f"- 대비 결함 페이지 최소 대비비 값: {ratios}; 비결함 페이지 최소 대비비 범위: {cratio[0] if cratio else '-'} ~ {cratio[-1] if cratio else '-'}",
          f"- 모바일 결함 scrollWidth: 1280 → {sorted({meas[r['page_id']]['1280']['scrollWidth'] for r in rows if r['defect_type']=='Mobile Layout Breakage' and r['nominal_injected']})}, "
          f"390 → {sorted({meas[r['page_id']]['390']['scrollWidth'] for r in rows if r['defect_type']=='Mobile Layout Breakage' and r['nominal_injected']})}",
          f"- 정적 문자열 검사(HTML 원문에 주입 문자열이 있는가)와 nominal 의 불일치(알려진 form_page 용어 3건 제외): {len(static_mism)}건",
          "", "## nominal ≠ effective 목록", "",
          f"- 전체 {len(mism)}건 (페이지×유형×뷰포트), 이 중 0단계에서 보고한 알려진 원인: {len(mism) - len(new)}건, **새로운 불일치: {len(new)}건**", ""]
    by_kind = Counter((r["defect_type"], vk, k) for r, vk, k in mism if k)
    for (t, vk, k), n in sorted(by_kind.items()):
        L.append(f"- {t} @ {vk}: {n}건 — {k}")
    if new:
        L += ["", "### 새로운 불일치 (상세)", "", "| page_id | template | 유형 | 뷰포트 | nominal | effective | 측정값 |", "|---|---|---|---|---:|---:|---|"]
        for r, vk in new:
            L.append(f"| {r['page_id']} | {r['template_id']} | {r['defect_type']} | {vk} | {r['nominal_injected']} | {r[f'effective_{vk}']} | {r[f'measurement_{vk}']} |")
    dv = [r for r in rows if r["defect_type"] == "Duplicate ID Markup Error" and r["nominal_injected"]]
    L += ["", f"- 중복 ID 결함 {len(dv)}페이지의 중복 요소 화면 면적 합: "
          f"{sorted({meas[r['page_id']]['1280']['dup_ids'][0]['visible_area'] for r in dv if meas[r['page_id']]['1280']['dup_ids']})} (0 이면 비가시)",
          "", "## 대조군 axe-core 자연 발생 이슈 (1280x800, 기본 설정)", "",
          "| rule_id | impact | 페이지 수 | 노드 합 |", "|---|---|---:|---:|"]
    agg = {}
    for r in ctrl_rows:
        a = agg.setdefault((r["rule_id"], r["impact"]), [set(), 0]); a[0].add(r["page_id"]); a[1] += r["n_nodes"]
    for (rid, imp), (ps, nn) in sorted(agg.items(), key=lambda kv: -len(kv[1][0])):
        L.append(f"| {rid} | {imp} | {len(ps)} | {nn} |")
    L.append(f"\n대조군 {sum(1 for g in meta if not g['has_defect'])}페이지 중 위반 0건인 페이지: "
             f"{sum(1 for g in meta if not g['has_defect'] and not axe_raw[g['page_id'][:-5]]['violations'])}")
    open(os.path.join(OUT, "e0_summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    return 3 if new else 0


if __name__ == "__main__":
    sys.exit(main())
