"""
E3 준비 (API 호출 없음).

  python experiments/revision/e3_oracle_prep.py template
      results/revision/oracle_chunks_template.csv : E3 대상 84페이지(용어 위반 45 + 대조군 39) 목록, chunk_id 칸은 비움
      results/revision/terminology_string_pairs.md : 용어 위반 주입의 정확한 문자열 쌍 (템플릿별)

  python experiments/revision/e3_oracle_prep.py expand --chunks ID1,ID2,...
      연구자가 고른 청크 ID 들을 84페이지 모두에 똑같이 넣어 results/revision/oracle_chunks.csv 를 만든다
      (페이지 × 청크 행, 청크 순서 유지). oracle_chunks.csv 는 동결 파일이므로 사용자 승인 뒤 새 동결 태그와 함께만 실행한다.
"""
import argparse
import csv
import importlib.util
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "results/revision"
TERM = "Standard Terminology Violation"


def e3_pages():
    meta = json.load(open("testbed_200/dataset_metadata.json", encoding="utf-8"))
    rows = []
    for p in meta:
        types = {d["type"] for d in p["defects"]}
        if TERM in types or not p["has_defect"]:
            rows.append({"page_id": p["page_id"][:-5], "page_group": "terminology" if TERM in types else "control",
                         "template_id": p["base_template"]})
    return sorted(rows, key=lambda r: r["page_id"])


def template():
    rows = e3_pages()
    with open(os.path.join(OUT, "oracle_chunks_template.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page_id", "chunk_id", "page_group", "template_id"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "chunk_id": ""})
    print(f"oracle_chunks_template.csv: {len(rows)} pages "
          f"(terminology {sum(r['page_group'] == 'terminology' for r in rows)}, control {sum(r['page_group'] == 'control' for r in rows)})")

    spec = importlib.util.spec_from_file_location("gen", "experiments/generate_200_testbed.py")
    gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
    apply = next(d for d in gen.DEFECT_POOL if d["id"] == "DEF_OPS_01")["apply"]
    meta = json.load(open("testbed_200/dataset_metadata.json", encoding="utf-8"))
    n_pages = {}
    for p in meta:
        if any(d["type"] == TERM for d in p["defects"]):
            n_pages[p["base_template"]] = n_pages.get(p["base_template"], 0) + 1
    L = ["# 표준 용어 위반 주입: 정확한 문자열 쌍", "",
         "- 주입 규칙: `experiments/generate_200_testbed.py` 의 `DEF_OPS_01` = `html.replace(\"로그인\", \"접속하기\")` (모든 출현 치환).",
         "- 아래 표는 각 템플릿 원문에서 '로그인'이 들어 있는 요소를 찾아, 치환 전후 문자열을 그대로 적은 것이다 (요소 단위).",
         "- `href=\"/login\"` 의 영문 `login` 은 바뀌지 않는다.", "",
         "| 템플릿 | 용어 위반 페이지 수 | 위치 | 원래 문자열 | 주입 후 문자열 |", "|---|---:|---|---|---|"]
    for t, html in gen.BASE_TEMPLATES.items():
        after = apply(html)
        found = False
        for m in re.finditer(r"<(title|h1|h2|h3|a|button|li)\b[^>]*>[^<]*로그인[^<]*</\1>", html):
            s = m.group(0)
            L.append(f"| `{t}` | {n_pages.get(t, 0)} | `<{m.group(1)}>` | `{s}` | `{s.replace('로그인', '접속하기')}` |")
            found = True
            assert s.replace("로그인", "접속하기") in after
        if not found:
            L.append(f"| `{t}` | {n_pages.get(t, 0)} | - | ('로그인' 없음, 주입되지 않음) | - |")
    L += ["", "치환되는 단어 쌍은 모든 템플릿에서 하나다: **`로그인` → `접속하기`**. "
          "login_page 만 세 곳(`<title>`, `<h2>`, `<button>`)이 바뀌고, 나머지 템플릿은 `<a href=\"/login\">` 링크 텍스트 한 곳이 바뀐다. "
          "form_page 에는 '로그인'이 없어 용어 위반 3페이지(page_028, page_038, page_168)는 주입되지 않았다."]
    open(os.path.join(OUT, "terminology_string_pairs.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


def expand(chunks):
    ids = [c.strip() for c in chunks.split(",") if c.strip()]
    rows = e3_pages()
    with open(os.path.join(OUT, "oracle_chunks.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["page_id", "chunk_id"])
        for r in rows:
            for c in ids:
                w.writerow([r["page_id"], c])
    print(f"oracle_chunks.csv: {len(rows)} pages x {len(ids)} chunks = {len(rows) * len(ids)} rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["template", "expand"])
    ap.add_argument("--chunks", default="")
    a = ap.parse_args()
    template() if a.mode == "template" else expand(a.chunks)
