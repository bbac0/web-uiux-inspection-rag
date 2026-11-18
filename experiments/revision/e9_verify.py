"""
E9 결정적 검증과 탐지 가능성 사전 검증 (docs/e9_design.md §2·§3, API 호출 없음).

  python experiments/revision/e9_verify.py [--port 8090] [--concurrency 3] [--testbed main|pilot]
  (pilot: testbed_e9_pilot/ → results/revision/e9_pilot/)

- 시스템 입력과 같은 조건: Playwright Chromium, 1280x800, `networkidle` 후 3초 대기, 렌더링 HTML = page.content().
- 서버: testbed_e9/ 를 루트로 하는 http.server 를 이 스크립트가 띄우고 끝나면 내린다(/login, /signup 목적지 포함).
- 검사 (계산된 스타일·속성, 페이지마다 같은 목록):
    banner_text, banner_font_family, banner_font_size, banner_font_weight, banner_color, banner_background, banner_height,
    banner_padding, banner_flag_size, banner_gap,
    header_background, header_border, header_color, header_util_font, header_icon_font_size, header_icon_font_weight, header_menu_font,
    footer_background, footer_border, footer_color, footer_contact_font_size, footer_contact_font_weight, footer_policy_font,
    footer_copy_font_size, footer_copy_font_weight,
    login_href, login_destination(클릭 후 도착 페이지 제목 = '로그인'), login_visible_1280, login_visible_768, login_visible_390
- 통과 기준: 대조군은 모든 검사 통과(조항 부합). 결함 페이지는 실패한 검사 집합 = 주입 결함의 expected_failing_checks.
- 탐지 가능성(§3): inj_offset_start/end(렌더링 HTML 에서 주입 문자열 위치), in_first_5000(= end ≤ 5000),
  in_viewport_1280x800(결함 요소의 사각형이 뷰포트와 겹치고 보임), structurally_undetectable(둘 중 하나라도 거짓).
  E9-3·E9-4 는 로그인 링크 요소의 위치를 기록한다(정의상 화면만으로는 탐지 불가, 해석은 표에 따로).
- 출력: results/revision/e9/ground_truth_e9.csv, e9_verify_summary.json
         (푸터 결함이 탐지 가능성 검사를 통과하지 못하면 footer_reassign_needed.json 을 쓰고 종료 코드 3)
"""
import argparse
import asyncio
import csv
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
TB = "testbed_e9"
OUT = "results/revision/e9"
BANNER_TEXT = "이 누리집은 대한민국 공식 전자정부 누리집입니다."
DEFECT_ELEMENT = {"E9-1": ".banner-text", "banner": ".gov-banner", "header": ".hd-icon", "E9-3": ".login-link", "E9-4": ".login-link"}

CHECK_JS = r"""(req) => {
  const cs = (sel) => { const e = document.querySelector(sel); return e ? getComputedStyle(e) : null; };
  const all = (sel) => Array.from(document.querySelectorAll(sel)).map(e => getComputedStyle(e));
  const rgb = {d: 'rgb(29, 29, 29)', w: 'rgb(255, 255, 255)', g: 'rgb(216, 216, 216)', b: 'rgb(237, 241, 245)', f: 'rgb(248, 248, 248)'};
  const r = {};
  const bt = document.querySelector('.banner-text');
  r.banner_text = !!bt && bt.textContent === req;
  const b = cs('.gov-banner');
  r.banner_font_family = !!b && b.fontFamily.includes('pretendardGOV');
  r.banner_font_size = !!b && b.fontSize === '15px';
  r.banner_font_weight = !!b && b.fontWeight === '400';
  r.banner_color = !!b && b.color === rgb.d;
  r.banner_background = !!b && b.backgroundColor === rgb.b;
  r.banner_height = !!b && b.height === '32px';
  r.banner_padding = !!b && b.paddingTop === '0px' && b.paddingBottom === '0px';
  const fl = document.querySelector('.gov-banner .flag'); const flr = fl && fl.getBoundingClientRect();
  r.banner_flag_size = !!fl && Math.round(flr.width) === 24 && Math.round(flr.height) === 16;
  r.banner_gap = !!b && (b.columnGap === '8px' || b.gap === '8px');
  const h = cs('.hd');
  r.header_background = !!h && h.backgroundColor === rgb.w;
  r.header_border = !!h && h.borderBottomColor === rgb.g;
  r.header_color = !!h && h.color === rgb.d;
  const hu = all('.hd-util a'); r.header_util_font = hu.length > 0 && hu.every(s => s.fontSize === '15px' && s.fontWeight === '400');
  const hi = all('.hd-icon');
  r.header_icon_font_size = hi.length > 0 && hi.every(s => s.fontSize === '17px');
  r.header_icon_font_weight = hi.length > 0 && hi.every(s => s.fontWeight === '700');
  const hm = all('.hd-menu a'); r.header_menu_font = hm.length > 0 && hm.every(s => s.fontSize === '19px' && s.fontWeight === '700');
  const f = cs('.ft');
  r.footer_background = !!f && f.backgroundColor === rgb.f;
  r.footer_border = !!f && f.borderTopColor === rgb.g;
  r.footer_color = !!f && f.color === rgb.d;
  const fc = cs('.ft-contact'); r.footer_contact_font_size = !!fc && fc.fontSize === '17px'; r.footer_contact_font_weight = !!fc && fc.fontWeight === '400';
  const fp = all('.ft-policy a'); r.footer_policy_font = fp.length > 0 && fp.every(s => s.fontSize === '17px' && s.fontWeight === '700' && s.color === rgb.d);
  const fy = cs('.ft-copy'); r.footer_copy_font_size = !!fy && fy.fontSize === '15px'; r.footer_copy_font_weight = !!fy && fy.fontWeight === '400';
  const ll = Array.from(document.querySelectorAll('a')).filter(a => a.textContent.trim() === '로그인');
  r._login_links = ll.length;
  r.login_href = ll.length === 1 && ll[0].getAttribute('href') === '/login';
  return r;
}"""

VIS_JS = r"""(sel) => {
  const e = document.querySelector(sel); if (!e) return {exists: false};
  const s = getComputedStyle(e); const r = e.getBoundingClientRect();
  return {exists: true, display: s.display, visibility: s.visibility, x: r.x, y: r.y, w: r.width, h: r.height,
          visible: s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0};
}"""


def free_port(p):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", p)) != 0


async def wait_like_system(page, url):
    await page.goto(url, wait_until="networkidle")
    await asyncio.sleep(3)


async def check_page(browser, base, meta, sem):
    async with sem:
        pid = meta["page_id"]
        url = f"{base}/{pid}.html"
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()
        await wait_like_system(page, url)
        html = await page.content()
        res = await page.evaluate(CHECK_JS, BANNER_TEXT)
        vis = {}
        vis[1280] = await page.evaluate(VIS_JS, ".login-link")
        key = meta["defect_id"] if meta["defect_id"] in ("E9-1", "E9-3", "E9-4") else meta["intensity"]
        el = None
        if meta["defect_id"] == "E9-2" and meta["intensity"] == "footer":
            el = meta["variant"].split(" ")[0]
        elif meta["defect_id"]:
            el = DEFECT_ELEMENT[key]
        elv = await page.evaluate(VIS_JS, el) if el else None
        for w, hgt in ((768, 1024), (390, 844)):
            await page.set_viewport_size({"width": w, "height": hgt})
            await asyncio.sleep(0.3)
            vis[w] = await page.evaluate(VIS_JS, ".login-link")
        await page.set_viewport_size({"width": 1280, "height": 800})
        # 목적지: 로그인 링크 클릭 → 도착 페이지 제목
        dest = None
        try:
            async with page.expect_navigation(wait_until="load", timeout=10000):
                await page.click(".login-link")
            dest = await page.title()
        except Exception as e:
            dest = f"ERROR {type(e).__name__}"
        await ctx.close()
    checks = {k: v for k, v in res.items() if not k.startswith("_")}
    checks["login_destination"] = dest == "로그인"
    checks["login_visible_1280"] = bool(vis[1280].get("visible"))
    checks["login_visible_768"] = bool(vis[768].get("visible"))
    checks["login_visible_390"] = bool(vis[390].get("visible"))
    failing = sorted(k for k, v in checks.items() if not v)
    expected = sorted(meta["expected_failing_checks"])
    row = {"page_id": pid, "subtype": meta["subtype"], "defect_id": meta["defect_id"] or "control",
           "intensity": meta["intensity"] or "", "variant": meta["variant"] or "", "body_template": meta["body_template"],
           "injected_string": meta["injected_string"] or "", "expected_failing_checks": ";".join(expected),
           "observed_failing_checks": ";".join(failing), "verification_pass": int(failing == expected),
           "login_links_in_page": res["_login_links"], "login_destination_title": dest,
           "rendered_html_chars": len(html)}
    if meta["injected_string"]:
        s = html.find(meta["injected_string"])
        row["inj_offset_start"] = s
        row["inj_offset_end"] = s + len(meta["injected_string"]) if s >= 0 else -1
        row["in_first_5000"] = int(s >= 0 and row["inj_offset_end"] <= 5000)
        inv = bool(elv and elv.get("visible") and elv["x"] < 1280 and elv["x"] + elv["w"] > 0 and elv["y"] < 800 and elv["y"] + elv["h"] > 0)
        row["defect_element"] = el
        row["defect_element_rect_1280"] = json.dumps({k: round(elv[k], 1) for k in ("x", "y", "w", "h")}) if elv and elv.get("exists") else ""
        row["in_viewport_1280x800"] = int(inv)
        row["structurally_undetectable"] = int(not (row["in_first_5000"] and inv))
        row["screen_only_note"] = {"E9-3": "destination-only defect: not visible on screen by definition (link element position recorded)",
                                   "E9-4": "hidden only at <=768px: not visible at 1280 by definition (link element position recorded)"}.get(meta["defect_id"], "")
    return row


async def run(base, metas, conc):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        sem = asyncio.Semaphore(conc)
        rows = await asyncio.gather(*[check_page(browser, base, m, sem) for m in metas])
        await browser.close()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--testbed", choices=["main", "pilot"], default="main")
    a = ap.parse_args()
    global TB, OUT
    if a.testbed == "pilot":
        TB, OUT = "testbed_e9_pilot", "results/revision/e9_pilot"
    doc = json.load(open(os.path.join(TB, "dataset_metadata_e9.json" if a.testbed == "main" else "dataset_metadata_e9_pilot.json"),
                         encoding="utf-8"))
    if not free_port(a.port):
        raise SystemExit(f"port {a.port} in use")
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(a.port), "--bind", "127.0.0.1", "--directory", TB],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{a.port}"
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(base + "/login/", timeout=2); break
            except Exception:
                time.sleep(0.25)
        t0 = time.time()
        rows = asyncio.run(run(base, doc["pages"], a.concurrency))
    finally:
        srv.terminate(); srv.wait(timeout=10)
    rows.sort(key=lambda r: r["page_id"])
    os.makedirs(OUT, exist_ok=True)
    fields = ["page_id", "subtype", "defect_id", "intensity", "variant", "body_template", "injected_string",
              "expected_failing_checks", "observed_failing_checks", "verification_pass", "inj_offset_start", "inj_offset_end",
              "in_first_5000", "defect_element", "defect_element_rect_1280", "in_viewport_1280x800", "structurally_undetectable",
              "screen_only_note", "login_links_in_page", "login_destination_title", "rendered_html_chars"]
    with open(os.path.join(OUT, "ground_truth_e9.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    from collections import Counter, defaultdict
    by = defaultdict(lambda: Counter())
    for r in rows:
        by[r["subtype"]]["pages"] += 1
        by[r["subtype"]]["verification_pass"] += r["verification_pass"]
        if r.get("injected_string"):
            by[r["subtype"]]["structurally_undetectable"] += r["structurally_undetectable"]
            by[r["subtype"]]["not_in_first_5000"] += 1 - r["in_first_5000"]
            by[r["subtype"]]["not_in_viewport"] += 1 - r["in_viewport_1280x800"]
    summ = {"pages": len(rows), "verification_pass": sum(r["verification_pass"] for r in rows),
            "controls_all_checks_pass": sum(r["verification_pass"] for r in rows if r["defect_id"] == "control"),
            "structurally_undetectable": sum(r.get("structurally_undetectable", 0) for r in rows),
            "by_subtype": {k: dict(v) for k, v in sorted(by.items())},
            "max_rendered_html_chars": max(r["rendered_html_chars"] for r in rows),
            "elapsed_sec": round(time.time() - t0, 1), "conditions": "Chromium, 1280x800, networkidle + 3s, page.content()",
            "failures": [{k: r[k] for k in ("page_id", "subtype", "expected_failing_checks", "observed_failing_checks")}
                         for r in rows if not r["verification_pass"]]}
    json.dump(summ, open(os.path.join(OUT, "e9_verify_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    bad_footer = [r["page_id"] for r in rows if r["subtype"] == "E9-2-footer" and r["structurally_undetectable"]]
    if bad_footer:
        json.dump(bad_footer, open(os.path.join(OUT, "footer_reassign_needed.json"), "w"), indent=1)
        return 3
    return 0 if summ["verification_pass"] == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
