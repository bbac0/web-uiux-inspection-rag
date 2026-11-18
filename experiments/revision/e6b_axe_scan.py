"""
E6b axe-core 추가 스캔 (API 호출 없음, 로컬). 사전 지정: results/revision/analysis_plan_addendum_e6b.md.
설정 C = E6 설정 B + WCAG 2.2 태그(wcag22a, wcag22aa) 규칙 전부 켬(target-size 포함). 뷰포트 1280x800, 390x844.
렌더링·대기·UA·주입 방식은 experiments/revision/e6_axe_scan.py 와 같다. 출력은 results/revision/e6b/ (덮어쓰지 않음).
"""
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e0_ground_truth as e0     # noqa: E402
from experiments.revision import e6_axe_scan as e6         # noqa: E402

OUT = "results/revision/e6b"
BASE_RULES = e6.CONFIGS["B"]["rules"]
RUN_JS = """async (base) => {
  const extra = axe.getRules(['wcag22a', 'wcag22aa']).map(r => r.ruleId);
  const rules = Object.assign({}, base); for (const id of extra) rules[id] = {enabled: true};
  const r = await axe.run(document, {rules});
  return {version: axe.version, enabled_extra: extra, url: r.url, timestamp: r.timestamp, testEngine: r.testEngine,
          toolOptions: r.toolOptions, violations: r.violations, incomplete: r.incomplete,
          passes: r.passes.map(x => ({id: x.id, n_nodes: x.nodes.length})),
          inapplicable: r.inapplicable.map(x => x.id)}; }"""


def main():
    from playwright.sync_api import sync_playwright
    if os.path.exists(OUT):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUT}")
    srv = None
    if not e6.up():
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8080", "--bind", "127.0.0.1", "--directory", ROOT],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if e6.up():
                break
            time.sleep(0.25)
    os.makedirs(OUT)
    meta = json.load(open("testbed_200/dataset_metadata.json", encoding="utf-8"))
    pages = sorted(g["page_id"][:-5] for g in meta)
    axe_src = open(e6.AXE, encoding="utf-8").read()
    log = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "axe_file": e6.AXE,
           "axe_sha256": hashlib.sha256(open(e6.AXE, "rb").read()).hexdigest(), "config_C_base_rules": BASE_RULES,
           "config_C_extra_tags": ["wcag22a", "wcag22aa"], "user_agent": e0.UA,
           "wait": "goto(wait_until='networkidle', timeout=30000) + 3000 ms", "base": e6.BASE, "errors": []}
    res = {vk: {} for vk in e0.VIEWPORTS}
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(headless=True)
            log["chromium_version"] = br.version
            for vk, (w, h) in e0.VIEWPORTS.items():
                ctx = br.new_context(viewport={"width": w, "height": h}, user_agent=e0.UA)
                pg = ctx.new_page()
                for i, pid in enumerate(pages):
                    try:
                        pg.goto(f"{e6.BASE}/{pid}.html", wait_until="networkidle", timeout=30000)
                        pg.wait_for_timeout(3000)
                        pg.add_script_tag(content=axe_src)
                        r = pg.evaluate(RUN_JS, BASE_RULES)
                        if r["version"] != "4.14.0":
                            raise SystemExit(f"axe.version {r['version']} != 4.14.0 → 멈춤")
                        log.setdefault("enabled_extra_rules", r["enabled_extra"])
                        res[vk][pid] = r
                    except SystemExit:
                        raise
                    except Exception as e:
                        log["errors"].append({"viewport": vk, "page_id": pid, "error": f"{type(e).__name__}: {str(e)[:200]}"})
                    if (i + 1) % 50 == 0:
                        print(f"[{vk}] {i + 1}/200", flush=True)
                ctx.close()
            br.close()
    finally:
        if srv is not None:
            srv.terminate(); srv.wait(timeout=10)
    sums = []
    for vk, d in res.items():
        fn = f"scan_C_{vk}.json"
        with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
            json.dump({"config": "C", "viewport": vk, "base_rules": BASE_RULES, "extra_tags": ["wcag22a", "wcag22aa"],
                       "pages": d}, f, ensure_ascii=False)
        sums.append(f"{hashlib.sha256(open(os.path.join(OUT, fn), 'rb').read()).hexdigest()}  {fn}")
    log["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log["pages_scanned"] = {vk: len(d) for vk, d in res.items()}
    json.dump(log, open(os.path.join(OUT, "run_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sums.append(f"{hashlib.sha256(open(os.path.join(OUT, 'run_log.json'), 'rb').read()).hexdigest()}  run_log.json")
    open(os.path.join(OUT, "SHA256SUMS"), "w", encoding="utf-8", newline="\n").write("\n".join(sums) + "\n")
    print(json.dumps({"pages_scanned": log["pages_scanned"], "errors": len(log["errors"]),
                      "extra_rules": log.get("enabled_extra_rules")}))


if __name__ == "__main__":
    main()
