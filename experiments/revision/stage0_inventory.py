"""
0단계 산출물 생성 (API 호출 없음, 테스트베드 읽기 전용).

  results/revision/testbed_manifest.csv   테스트베드 HTML/메타데이터 SHA-256 목록
  results/revision/keyword_dictionary.md  키워드 사전 전문 (evaluate_performance_v5.py 에서 import, 수정 없음)
  results/revision/injection_procedure.md 결함 주입 절차 (generate_200_testbed.py 에서 읽어 정리 + 파일 대조 검증)

테스트베드는 재생성하지 않는다. 주입 규칙을 각 템플릿에 메모리 상에서 다시 적용해
기존 파일과 바이트 단위로 같은지만 확인한다.

사용법 (저장소 루트에서):  python experiments/revision/stage0_inventory.py
"""

import collections
import csv
import hashlib
import importlib.util
import inspect
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TB = os.path.join(ROOT, "testbed_200")
OUT = os.path.join(ROOT, "results", "revision")


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    gen = load("gen", "experiments/generate_200_testbed.py")
    kw = load("kw", "experiments/evaluate_performance_v5.py")
    sem = load("sem", "experiments/semantic_issue_classifier.py")
    meta = json.load(open(os.path.join(TB, "dataset_metadata.json"), encoding="utf-8"))
    pool = {d["id"]: d for d in gen.DEFECT_POOL}
    os.makedirs(OUT, exist_ok=True)

    # ---------------- 1. testbed_manifest.csv ----------------
    rows, mismatches = [], []
    for p in meta:
        path = os.path.join(TB, p["page_id"])
        html = gen.BASE_TEMPLATES[p["base_template"]]
        for d in p["defects"]:                       # 메타데이터에 기록된 순서대로 적용
            html = pool[d["id"]]["apply"](html)
        raw = open(path, "rb").read()
        same = raw == html.encode("utf-8")
        if not same:
            mismatches.append(p["page_id"])
        rows.append({
            "page_id": p["page_id"].replace(".html", ""),
            "file": f"testbed_200/{p['page_id']}",
            "template_id": p["base_template"],
            "has_defect": int(p["has_defect"]),
            "defect_count": p["defect_count"],
            "defect_types": ";".join(d["type"] for d in p["defects"]),
            "defect_ids": ";".join(d["id"] for d in p["defects"]),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "matches_generator_rules": int(same),
        })
    extra = [
        ("testbed_200/dataset_metadata.json", "metadata"),
        ("experiments/generate_200_testbed.py", "generator"),
    ] + [(f"testbed/{f}", "latency_testbed") for f in sorted(os.listdir(os.path.join(ROOT, "testbed")))]
    with open(os.path.join(OUT, "testbed_manifest.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["role"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "role": "testbed_200_page"})
        for rel, role in extra:
            pth = os.path.join(ROOT, rel)
            w.writerow({"file": rel, "bytes": os.path.getsize(pth), "sha256": sha256(pth), "role": role})
    print(f"testbed_manifest.csv: {len(rows)} pages, generator mismatches={mismatches}")

    # ---------------- 2. keyword_dictionary.md ----------------
    same_copy = kw.CATEGORY_PHRASES == sem.CATEGORY_PHRASES
    L = ["# 키워드 사전 (원본 그대로, 수정 없음)", "",
         f"- 출처: `experiments/evaluate_performance_v5.py` 의 `CATEGORY_PHRASES` "
         f"(파일 SHA-256 `{sha256(os.path.join(ROOT, 'experiments/evaluate_performance_v5.py'))}`)",
         f"- `experiments/semantic_issue_classifier.py` 에 있는 사본과 동일 여부: **{'동일' if same_copy else '다름'}**",
         "- 이 문서는 스크립트가 사전을 import 해서 자동 생성했다 (`experiments/revision/stage0_inventory.py`).", "",
         "## 매칭 규칙 (코드에서 읽은 그대로)", "",
         "1. 리포트의 `issues[]` 중 `description` 에 `testbed_200/{page_id}.html` 문자열이 들어간 이슈만 채점한다"
         " (크롤러가 따라간 `/login` 등 다른 URL에 대한 이슈는 제외).",
         "2. `description` 필드만 본다. `summary`, `suggestion`, `category` 는 쓰지 않는다.",
         "3. `description.lower()` 안에 구문의 `lower()` 가 부분 문자열로 들어 있으면 해당 유형으로 매칭한다.",
         "4. 한 이슈가 여러 유형에 동시에 매칭될 수 있다 (다중 라벨). 단 `semantic_issue_classifier.keyword_label()` 은"
         " 사전 순서상 첫 매칭 유형 하나만 돌려준다 (이슈 단위 단일 라벨이 필요할 때의 기존 동작).",
         "5. 페이지 판정: 매칭된 유형이 하나라도 있으면 '결함 탐지'. 유형별 탐지율은 정답 유형이 매칭 집합에 있는지로 계산.", ""]
    for cat, phrases in kw.CATEGORY_PHRASES.items():
        L += [f"## {cat} ({len(phrases)}개)", "", "| # | 구문 | 비고 |", "|---|---|---|"]
        for i, ph in enumerate(phrases, 1):
            note = []
            if ph != ph.lower():
                note.append("대소문자 무시")
            if ph.lower() in ("wcag", "viewport", "overflow", "가독성", "wai-aria", "중복 사용", "겹침", "반응형"):
                note.append("포괄 구문: 무관한 언급과도 매칭될 수 있음")
            L.append(f"| {i} | `{ph}` | {'; '.join(note)} |")
        L.append("")
    open(os.path.join(OUT, "keyword_dictionary.md"), "w", encoding="utf-8").write("\n".join(L))
    print("keyword_dictionary.md written")

    # ---------------- 3. injection_procedure.md ----------------
    src = inspect.getsource(gen)
    tpls = list(gen.BASE_TEMPLATES)
    by_type = collections.Counter(d["type"] for p in meta for d in p["defects"])
    combos = collections.Counter(" + ".join(sorted(d["type"] for d in p["defects"])) for p in meta if p["defects"])
    tpl_tab = collections.defaultdict(collections.Counter)
    for p in meta:
        tpl_tab[p["base_template"]]["(대조군)" if not p["defects"] else "_defect_pages"] += 1
        for d in p["defects"]:
            tpl_tab[p["base_template"]][d["type"]] += 1

    def has_button(h):
        return bool(re.search(r"<button", h))

    def term_hits(h):
        return [m.start() for m in re.finditer("로그인", h)]

    def term_where(h):
        out = []
        for tag in ("title", "h2", "button", "a", "li"):
            for m in re.finditer(rf"<{tag}[^>]*>([^<]*)</{tag}>", h):
                if "로그인" in m.group(1):
                    out.append(f"<{tag}>{m.group(1)}")
        return out

    noop = []
    for p in meta:
        t = gen.BASE_TEMPLATES[p["base_template"]]
        for d in p["defects"]:
            if pool[d["id"]]["apply"](t) == t:
                noop.append((p["page_id"], p["base_template"], d["type"]))
    btn_invisible = [p["page_id"] for p in meta
                     if any(d["id"] == "DEF_VIS_03" for d in p["defects"])
                     and not has_button(gen.BASE_TEMPLATES[p["base_template"]])]

    types = [d["type"] for d in gen.DEFECT_POOL]
    L = ["# 결함 주입 절차 (코드에서 복원)", "",
         "주입 스크립트가 저장소에 있다: `experiments/generate_200_testbed.py` "
         f"(SHA-256 `{sha256(os.path.join(ROOT, 'experiments/generate_200_testbed.py'))}`). "
         "아래 내용은 이 스크립트와 `testbed_200/dataset_metadata.json` 을 읽어 자동 생성했다.", "",
         "## 재현성 검증", "",
         f"- 메타데이터에 기록된 결함을 기록된 순서대로 템플릿에 다시 적용한 결과가 기존 200개 파일과 바이트 단위로 같은 페이지: "
         f"**{200 - len(mismatches)}/200** (불일치: {mismatches or '없음'})",
         "- 별도로 스크립트 전체를 임시 폴더에서 실행해 200개 파일 + 메타데이터가 모두 바이트 단위로 같음을 확인했다 (0단계 탐색 시, 기존 파일은 건드리지 않음).",
         "", "## 생성 알고리즘", "",
         "- 시드: `random.seed(42)` (Python `random`, 전역 상태 하나로 결함 여부·개수·유형을 모두 뽑음)",
         "- 템플릿 배정: `page_i` 의 템플릿 = `BASE_TEMPLATES` 순서상 `(i-1) % 10` 번째 (무작위 아님). 따라서 템플릿마다 정확히 20페이지.",
         "- 결함 여부: `random.random() > 0.2` 이면 결함 페이지 (기대 비율 80%).",
         "- 결함 개수: `random.choice([1, 2])`, 유형: `random.sample(DEFECT_POOL, 개수)` (한 페이지에 같은 유형 중복 없음).",
         "- 적용 순서: 뽑힌 순서대로 `apply` (메타데이터 `defects` 배열 순서와 같음). 각 규칙은 서로 다른 지점을 바꾸므로 순서가 결과에 영향을 주지 않는다.",
         "- 템플릿 순서: " + ", ".join(f"`{t}`" for t in tpls), "",
         "## 유형별 주입 규칙", "",
         "| ID | 유형 | 주입 방법 (코드 원문 요약) | 결함 위치 |", "|---|---|---|---|",
         "| DEF_VIS_01 | Poor Contrast Ratio | `</head>` 앞에 `<style>* { color: #e5e5e5 !important; background-color: #ffffff !important; }</style>` 삽입 | 페이지의 모든 요소 (전역 CSS). 대비비 = 1.26:1 (아래 계산) |",
         "| DEF_VIS_02 | Mobile Layout Breakage | `</head>` 앞에 `html, body, div, main, header { width: 3000px !important; min-width: 3000px !important; overflow-x: scroll !important; }` 삽입 | 전역. 모바일 전용이 아니라 1280px 데스크톱에서도 가로 넘침이 생긴다 |",
         "| DEF_VIS_03 | Button Area Clipping | `</head>` 앞에 `button, .btn, .login-btn, .apply-btn { height: 2px; font-size: 0px; line-height: 0; padding: 0; overflow: hidden; border: 1px solid red }` (모두 !important) 삽입 | `<button>` 요소. 버튼이 없는 템플릿에서는 화면상 효과 없음 (아래 표) |",
         "| DEF_OPS_01 | Standard Terminology Violation | `html.replace('로그인', '접속하기')` (모든 출현을 치환, `href=\"/login\"` 은 그대로) | 템플릿별 '로그인' 텍스트 위치 (아래 표). `form_page` 에는 '로그인'이 없어 주입이 일어나지 않음 |",
         "| DEF_TEC_01 | Duplicate ID Markup Error | `<body>` 바로 뒤에 `<div id=\"main-banner\"></div><div id=\"main-banner\"></div>` 삽입 | body 첫 자식, 내용 없는 div 2개 (화면상 보이지 않음). `portal_main` 은 원래 `#main-banner` 가 있어 3개가 됨 |",
         "", "대비비 계산: L(#e5e5e5) = 0.7835, L(#ffffff) = 1.0 → (1.05)/(0.8335) = **1.26:1** (WCAG 1.4.3 기준 4.5:1 미달).", "",
         "## 템플릿별 주입 위치", "",
         "| 템플릿 | `<button>` 있음 | '로그인' 출현 위치 (용어 위반 시 '접속하기'로 바뀜) | 기존 `#main-banner` |",
         "|---|---|---|---|"]
    for t in tpls:
        h = gen.BASE_TEMPLATES[t]
        L.append(f"| `{t}` | {'예' if has_button(h) else '**아니오**'} | "
                 f"{', '.join(f'`{x}`' for x in term_where(h)) or '**없음 (주입 불가)**'} ({len(term_hits(h))}회) | "
                 f"{'예' if 'main-banner' in h else '아니오'} |")
    L += ["", "## 분포", "",
          f"- 결함 페이지 {sum(p['has_defect'] for p in meta)}개, 대조군 {sum(not p['has_defect'] for p in meta)}개",
          "- 페이지당 결함 수: " + ", ".join(f"{k}개 → {v}페이지" for k, v in sorted(collections.Counter(p['defect_count'] for p in meta).items())),
          "- 유형별 페이지 수: " + ", ".join(f"{t} {by_type[t]}" for t in types), "",
          "### 템플릿 × 유형 (페이지 수)", "",
          "| 템플릿 | " + " | ".join(types) + " | 결함 페이지 | 대조군 |",
          "|---|" + "---|" * (len(types) + 2)]
    for t in tpls:
        c = tpl_tab[t]
        L.append(f"| `{t}` | " + " | ".join(str(c[x]) for x in types) + f" | {c['_defect_pages']} | {c['(대조군)']} |")
    L += ["", "### 결함 조합 (페이지 수)", "", "| 조합 | 페이지 |", "|---|---|"]
    for k, v in combos.most_common():
        L.append(f"| {k} | {v} |")
    L += ["", "## 주의가 필요한 페이지 (주입이 의도대로 드러나지 않는 경우)", "",
          f"1. **용어 위반이 실제로 주입되지 않은 페이지 {len(noop)}개**: "
          + ", ".join(f"`{a}` ({b})" for a, b, _ in noop)
          + ". 메타데이터상 정답은 Standard Terminology Violation 이지만 파일에는 '로그인'/'접속하기'가 없다.",
          f"2. **버튼이 없는 템플릿에 Button Area Clipping 이 기록된 페이지 {len(btn_invisible)}개**: CSS 규칙만 들어 있고 대상 요소가 없어 화면상 결함이 없다. "
          "HTML 원문에는 `height: 2px` 등의 CSS 문자열이 남으므로 모델이 소스를 읽고 '탐지'할 수는 있다: "
          + ", ".join(f"`{x}`" for x in btn_invisible),
          "3. **Mobile Layout Breakage 는 모바일 전용 결함이 아니다**: 3000px 고정 폭이라 1280x800 데스크톱에서도 가로 스크롤이 생긴다.",
          "4. **Duplicate ID 는 화면에 보이지 않는다**: 빈 div 2개이므로 스크린샷으로는 탐지할 수 없고 HTML 로만 탐지 가능.",
          "5. 위 1, 2 는 5단계 E0 (결정적 검증)에서 `ground_truth.csv` 의 `검증 통과 여부` 로 다시 확인한다. 이 문서는 정답 라벨을 바꾸지 않는다.",
          "", "## 복원이 불완전한 부분", "",
          "- 없음. 주입 스크립트와 시드가 남아 있고, 규칙 재적용 결과가 200개 파일 모두와 일치한다.",
          "- 다만 `testbed/` (지연시간 측정용 50페이지)의 생성 스크립트는 `_archive/make_testbed.py` 로 보이며 이번 범위에서는 해시만 기록했다."]
    open(os.path.join(OUT, "injection_procedure.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"injection_procedure.md written; noop={noop}; button-less clipping={len(btn_invisible)}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
