"""
E6 axe-core 스캔 (API 호출 없음, 로컬). 사전 지정: results/revision/analysis_plan_addendum_e6.md.

- 대상: testbed_200 200페이지, 뷰포트 1280x800 / 390x844, Playwright Chromium, 프로덕션과 같은 UA(e0_ground_truth.UA),
  `networkidle` 후 3초 대기 → axe.min.js(4.14.0) 주입 → 설정 A(기본), 설정 B(기본 + duplicate-id 계열 켬)를 같은 렌더링에서 차례로 실행.
- axe.version 이 4.14.0 이 아니면 멈춘다.
- 출력 (덮어쓰지 않음): results/revision/e6/scan_{A,B}_{1280,390}.json, SHA256SUMS, run_log.json
  페이지별: version, url, timestamp, violations(전체), incomplete(전체), passes/inapplicable 규칙 ID 와 건수.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e0_ground_truth as e0     # noqa: E402  (UA, VIEWPORTS)

OUT = "results/revision/e6"
AXE = "axe.min.js"
BASE = "http://localhost:8080/testbed_200"
CONFIGS = {"A": {}, "B": {"rules": {"duplicate-id": {"enabled": True}, "duplicate-id-active": {"enabled": True},
                                    "duplicate-id-aria": {"enabled": True}}}}
RUN_JS = """async (opts) => { const r = await axe.run(document, opts);
  return {version: axe.version, url: r.url, timestamp: r.timestamp, testEngine: r.testEngine, toolOptions: r.toolOptions,
          violations: r.violations, incomplete: r.incomplete,
          passes: r.passes.map(x => ({id: x.id, n_nodes: x.nodes.length})),
          inapplicable: r.inapplicable.map(x => x.id)}; }"""


def up():
    try:
        urllib.request.urlopen(f"{BASE}/page_001.html", timeout=2)
        return True
    except Exception:
        return False


def main():
    from playwright.sync_api import sync_playwright
    if os.path.exists(OUT):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {OUT}")
    srv = None
    if not up():
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8080", "--bind", "127.0.0.1", "--directory", ROOT],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if up():
                break
            time.sleep(0.25)
    os.makedirs(OUT)
    meta = json.load(open("testbed_200/dataset_metadata.json", encoding="utf-8"))
    pages = sorted(g["page_id"][:-5] for g in meta)
    axe_src = open(AXE, encoding="utf-8").read()
    log = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "axe_file": AXE,
           "axe_sha256": hashlib.sha256(open(AXE, "rb").read()).hexdigest(), "configs": CONFIGS, "user_agent": e0.UA,
           "wait": "goto(wait_until='networkidle', timeout=30000) + 3000 ms", "base": BASE, "errors": []}
    res = {(c, v): {} for c in CONFIGS for v in e0.VIEWPORTS}
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(headless=True)
            log["chromium_version"] = br.version
            for vk, (w, h) in e0.VIEWPORTS.items():
                ctx = br.new_context(viewport={"width": w, "height": h}, user_agent=e0.UA)
                pg = ctx.new_page()
                for i, pid in enumerate(pages):
                    try:
                        pg.goto(f"{BASE}/{pid}.html", wait_until="networkidle", timeout=30000)
                        pg.wait_for_timeout(3000)
                        pg.add_script_tag(content=axe_src)
                        for c, opts in CONFIGS.items():
                            r = pg.evaluate(RUN_JS, opts)
                            if r["version"] != "4.14.0":
                                raise SystemExit(f"axe.version {r['version']} != 4.14.0 → 멈춤")
                            res[(c, vk)][pid] = r
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
    for (c, vk), d in res.items():
        fn = f"scan_{c}_{vk}.json"
        with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
            json.dump({"config": c, "viewport": vk, "options": CONFIGS[c], "pages": d}, f, ensure_ascii=False)
        sums.append(f"{hashlib.sha256(open(os.path.join(OUT, fn), 'rb').read()).hexdigest()}  {fn}")
    log["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log["pages_scanned"] = {f"{c}_{v}": len(d) for (c, v), d in res.items()}
    json.dump(log, open(os.path.join(OUT, "run_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sums.append(f"{hashlib.sha256(open(os.path.join(OUT, 'run_log.json'), 'rb').read()).hexdigest()}  run_log.json")
    open(os.path.join(OUT, "SHA256SUMS"), "w", encoding="utf-8", newline="\n").write("\n".join(sums) + "\n")
    print(json.dumps({"pages_scanned": log["pages_scanned"], "errors": len(log["errors"])}))


if __name__ == "__main__":
    main()
