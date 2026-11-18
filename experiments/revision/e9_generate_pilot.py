"""
E9 파일럿 세트 생성 (2026-11-13 연구자 지시; 시드 20261117; 결과는 분석에서 제외). API 호출 없음.

  python experiments/revision/e9_generate_pilot.py [--overwrite]

- 8페이지: E9-1a 1, E9-1b 1, E9-2 배너 1, E9-2 푸터 1, E9-3 1, E9-4 1, 대조군 2. (E9-2 헤더는 변형이 하나뿐이라 넣지 않았다.)
- 페이지 ID `e9p_001`~`e9p_008`, 폴더 `testbed_e9_pilot/` (서버 루트, /login/·/signup/ 포함). 본 실험 `testbed_e9/` 와 파일·ID 가 겹치지 않는다.
- 페이지 구성은 본 실험 생성기(e9_generate.py)의 render() 를 그대로 쓴다(같은 골격·규격값·주입 규칙·본문 재사용 규칙).
- 결함 페이지는 본 실험 91페이지에 쓰인 (본문 템플릿, 변형) 조합을 가능하면 피해서 고른다.
  **피할 수 없는 경우:** E9-3·E9-4 는 변형이 하나뿐이고 본 실험이 10개 템플릿을 모두 썼으며, 대조군은 (본문 템플릿 + 규격 골격) 뿐이라
  이 페이지들은 같은 템플릿의 본 실험 페이지와 HTML 이 같다(파일·ID 는 다름). 메타데이터의 identical_to_main_page 에 표시한다.
"""
import argparse
import hashlib
import json
import os
import random
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from experiments.revision import e9_generate as g   # noqa: E402

OUT = "testbed_e9_pilot"
SEED = 20261117
PLAN = ["E9-1a", "E9-1b", "E9-2-banner", "E9-2-footer", "E9-3", "E9-4", "control", "control"]
VARIANTS = {"E9-1a": g.E9_1A, "E9-1b": g.E9_1B, "E9-2-banner": g.E9_2_BANNER, "E9-2-footer": g.E9_2_FOOTER}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    main_meta = json.load(open(os.path.join(g.OUT, "dataset_metadata_e9.json"), encoding="utf-8"))
    used = {(p["subtype"], p["body_template"], p["variant"]) for p in main_meta["pages"]}
    main_hashes = {hashlib.sha256(open(os.path.join(g.OUT, p["page_id"] + ".html"), "rb").read()).hexdigest(): p["page_id"]
                   for p in main_meta["pages"]}
    if os.path.exists(OUT):
        if not a.overwrite:
            raise SystemExit(f"{OUT} 이미 있음 (--overwrite)")
        shutil.rmtree(OUT)
    templates = g.load_templates()
    tnames = sorted(templates)
    rng = random.Random(SEED)
    items = []
    for k, sub in enumerate(PLAN):
        combos = []
        for t in tnames:
            for v in VARIANTS.get(sub, [None]):
                vid = (v[0] if sub in ("E9-1a", "E9-1b") else f"{v[1]} {v[2]}:{v[3]}") if v else None
                combos.append((t, v, vid))
        rng.shuffle(combos)
        if sub != "control":
            meta_variant = lambda vid: vid if sub not in ("E9-3", "E9-4") else (
                "href /login -> /signup" if sub == "E9-3" else "hide login link at max-width 768px")
            free = [c for c in combos if (sub, c[0], meta_variant(c[2])) not in used]
            choice = free[0] if free else combos[0]
        else:
            already = [it["body_template"] for it in items if it["subtype"] == "control"]
            choice = next(c for c in combos if c[0] not in already)
        items.append({"page_id": f"e9p_{k + 1:03d}", "subtype": sub, "body_template": choice[0], "variant": choice[1]})
    order = list(range(len(items)))
    rng.shuffle(order)
    items = [dict(items[i], page_id=f"e9p_{n + 1:03d}") for n, i in enumerate(order)]
    os.makedirs(OUT)
    metas = []
    for it in items:
        html, meta = g.render(it, templates)
        h = hashlib.sha256(html.encode("utf-8")).hexdigest()
        meta["identical_to_main_page"] = main_hashes.get(h)
        meta["bytes"] = len(html.encode("utf-8"))
        with open(os.path.join(OUT, f"{it['page_id']}.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        metas.append(meta)
    for name, title in (("login", "로그인"), ("signup", "회원가입")):
        os.makedirs(os.path.join(OUT, name))
        with open(os.path.join(OUT, name, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"<!DOCTYPE html><html lang=\"ko\"><head><meta charset=\"UTF-8\"><title>{title}</title></head>"
                    f"<body><main><h1>{title}</h1></main></body></html>")
    g.write_flag(OUT)      # v3 (c1): 국기 그림
    doc = {"seed": SEED, "generator": "experiments/revision/e9_generate_pilot.py (render from e9_generate.py)",
           "purpose": "E9 pilot only; excluded from all analyses", "pages": metas}
    json.dump(doc, open(os.path.join(OUT, "dataset_metadata_e9_pilot.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for m in metas:
        print(m["page_id"], m["subtype"], m["body_template"], m["variant"], "identical_to_main:", m["identical_to_main_page"])


if __name__ == "__main__":
    sys.exit(main())
