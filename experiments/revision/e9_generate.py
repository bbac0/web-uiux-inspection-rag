"""
E9 테스트베드 생성기 (docs/e9_design.md v5, API 호출 없음).

  python experiments/revision/e9_generate.py [--seed 20261116] [--overwrite]

출력
  testbed_e9/e9_001.html ~ e9_091.html     (서버 루트 = testbed_e9/; python -m http.server 8090 --bind 127.0.0.1 --directory testbed_e9)
  testbed_e9/login/index.html, testbed_e9/signup/index.html   (/login, /signup 목적지 페이지)
  testbed_e9/dataset_metadata_e9.json      (페이지별 본문 템플릿, 결함 ID, 강도·변형, 주입 문자열, 실패해야 하는 검사 목록)

규칙
  - 페이지 91개: E9-1a 8, E9-1b 8, E9-2 15 (배너 7, 헤더 4, 푸터 4), E9-3 15, E9-4 15(보조), 대조군 30. 결함은 페이지당 1종.
  - 기준 페이지 골격(순서 고정): <head> 규격 <style> → 공식 배너 → 규격 헤더(유틸리티, 아이콘 링크 '검색'·'로그인', 메인 메뉴)
    → <main>(기존 10개 템플릿의 <main> 재사용) → 규격 푸터(연락처, 정책 링크, 저작권).
  - 본문 재사용 규칙: 템플릿의 <main ...>...</main> 을 그대로 쓰되, 그 안의 `<a href="/login">로그인</a>` 링크는 지운다
    (헤더 로그인 링크가 페이지의 유일한 로그인 링크가 되게; faq_page, terms_page, contact_page 에 해당). 그 밖의 내용은 바꾸지 않는다.
  - 본문 템플릿 배정: 결함 하위 유형마다 10개 템플릿을 시드로 섞은 순서대로 돌아가며 배정(고르게). 변형(문구·속성)도 목록을 시드로 섞어 돌아가며 배정.
  - 푸터 결함은 탐지 가능성 사전 검증(e9_verify.py)을 통과해야 한다. 통과하지 못하면 --reassign 파일에 따라 다른 본문 템플릿으로
    다시 생성한다(재배정 기록은 dataset_metadata_e9.json 의 reassignments).
"""
import argparse
import importlib.util
import json
import os
import random
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
OUT = "testbed_e9"
DEFAULT_SEED = 20261116
BANNER_TEXT = "이 누리집은 대한민국 공식 전자정부 누리집입니다."

# ---- 규격 스타일 (gov_check 68·71·77쪽 규정값). 규칙별로 선언을 dict 로 두고 문자열로 그린다 ----
BASE_RULES = [
    ("body", {"margin": "0", "font-family": "pretendardGOV,sans-serif", "color": "#1D1D1D"}),
    (".gov-banner", {"display": "flex", "align-items": "center", "gap": "8px", "height": "32px", "padding": "0 16px",
                     "background": "#EDF1F5", "font-family": "pretendardGOV", "font-size": "15px", "font-weight": "400",
                     "color": "#1D1D1D"}),
    (".gov-banner .flag", {"width": "24px", "height": "16px"}),   # v3 (c1): 회색 자리 표시 배경 제거, 실제 국기 그림 사용
    (".hd", {"background": "#FFFFFF", "border-bottom": "1px solid #D8D8D8", "color": "#1D1D1D", "padding": "8px 16px"}),
    (".hd a", {"color": "#1D1D1D", "text-decoration": "none", "margin-right": "12px"}),
    (".hd-util a", {"font-size": "15px", "font-weight": "400"}),
    (".hd-icon", {"font-size": "17px", "font-weight": "700"}),
    (".hd-menu a", {"font-size": "19px", "font-weight": "700"}),
    ("main", {"padding": "16px"}),
    (".ft", {"background": "#F8F8F8", "border-top": "1px solid #D8D8D8", "color": "#1D1D1D", "padding": "12px 16px"}),
    (".ft-contact", {"font-size": "17px", "font-weight": "400"}),
    (".ft-policy a", {"font-size": "17px", "font-weight": "700", "color": "#1D1D1D", "margin-right": "12px"}),
    (".ft-copy", {"font-size": "15px", "font-weight": "400"}),
]
E9_4_MEDIA = '@media (max-width: 768px) { header a[href="/login"] { display: none !important; } }'

# ---- 결함 변형 (미준수 사례 값; e9_design §1) ----
E9_1A = [("replace_whole", "대한민국 공식 전자정부 웹사이트입니다."),
         ("nurijip_to_homepage", "이 누리집은 대한민국 공식 전자정부 홈페이지입니다."),
         ("delete_gongsik", "이 누리집은 대한민국 전자정부 누리집입니다.")]
E9_1B = [("space_gongsik_jeonja", "이 누리집은 대한민국 공식전자정부 누리집입니다."),
         ("space_i_nurijip", "이누리집은 대한민국 공식 전자정부 누리집입니다."),
         ("space_jeonja_nurijip", "이 누리집은 대한민국 공식 전자정부누리집입니다.")]
# (영역, 셀렉터, 속성, 미준수 값, 실패해야 하는 검사)
E9_2_BANNER = [("banner", ".gov-banner", "font-size", "14px", ["banner_font_size"]),
               ("banner", ".gov-banner", "color", "#000000", ["banner_color"]),
               ("banner", ".gov-banner", "font-weight", "700", ["banner_font_weight"]),
               ("banner", ".gov-banner", "background", "#FFFFFF", ["banner_background"]),
               ("banner", ".gov-banner", "padding", "10px", ["banner_padding"])]
E9_2_HEADER = [("header", ".hd-icon", "font-size", "15px", ["header_icon_font_size"])]
E9_2_FOOTER = [("footer", ".ft-contact", "font-size", "15px", ["footer_contact_font_size"]),
               ("footer", ".ft-copy", "font-weight", "700", ["footer_copy_font_weight"]),
               ("footer", ".ft", "color", "#000000", ["footer_color"]),
               ("footer", ".ft", "background", "#FFFFFF", ["footer_background"])]
PLAN = [("E9-1a", 8), ("E9-1b", 8), ("E9-2-banner", 7), ("E9-2-header", 4), ("E9-2-footer", 4),
        ("E9-3", 15), ("E9-4", 15), ("control", 30)]


def flag_svg():
    """v3 (c1): 공식 배너 국기 그림. 태극기(3:2) — 흰 바탕, 태극(빨강·파랑), 네 괘. 결정적으로 같은 문자열을 만든다."""
    import math
    th = math.degrees(math.atan2(2, 3))           # 대각선 각도 33.69°
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-36 -24 72 48" width="24" height="16">',
             '<rect x="-36" y="-24" width="72" height="48" fill="#FFFFFF"/>',
             f'<g transform="rotate({-th:.2f})">',     # 태극 S 곡선을 대각선에 맞춘다
             '<path d="M-12,0A12,12 0 0,1 12,0A6,6 0 0,1 0,0A6,6 0 0,0 -12,0Z" fill="#CD2E3A"/>',
             '<path d="M12,0A12,12 0 0,1 -12,0A6,6 0 0,1 0,0A6,6 0 0,0 12,0Z" fill="#0047A0"/>', '</g>']
    # (중심 방향 각도, 세 줄이 끊긴 줄인지) — 건(☰) 좌상, 감(☵) 우상, 리(☲) 좌하, 곤(☷) 우하
    trigrams = [(180 + th, (False, False, False)), (-th, (True, False, True)),
                (180 - th, (False, True, False)), (th, (True, True, True))]
    for ang, lines in trigrams:
        cx, cy = 21 * math.cos(math.radians(ang)), 21 * math.sin(math.radians(ang))
        parts.append(f'<g transform="translate({cx:.2f},{cy:.2f}) rotate({ang + 90:.2f})">')
        for k, broken in enumerate(lines):
            y = -4 + 3 * k
            if broken:
                parts.append(f'<rect x="-6" y="{y}" width="5.5" height="2" fill="#000000"/>')
                parts.append(f'<rect x="0.5" y="{y}" width="5.5" height="2" fill="#000000"/>')
            else:
                parts.append(f'<rect x="-6" y="{y}" width="12" height="2" fill="#000000"/>')
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts) + "\n"


def write_flag(out_dir):
    with open(os.path.join(out_dir, "flag.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(flag_svg())


def css(rules):
    return "".join(f"{sel}{{{';'.join(f'{k}:{v}' for k, v in decl.items())}}}" for sel, decl in rules)


def rule_text(sel, decl):
    return f"{sel}{{{';'.join(f'{k}:{v}' for k, v in decl.items())}}}"


def load_templates():
    spec = importlib.util.spec_from_file_location("gen", "experiments/generate_200_testbed.py")
    gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
    out = {}
    for name, html in gen.BASE_TEMPLATES.items():
        title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
        main = re.search(r"<main\b.*?</main>", html, re.S).group(0)
        removed = main.count('<a href="/login">로그인</a>')
        main = main.replace('<a href="/login">로그인</a>', "")
        # v3 (c2, 2026-11-13 연구자 승인): portal_main 본문의 자리 표시 '배너' 를 바꾼다(파일럿 대조군 위양성 원인)
        placeholder = main.count('<div id="main-banner">배너</div>')
        main = main.replace('<div id="main-banner">배너</div>', '<div id="main-notice">주요 소식</div>')
        out[name] = {"title": title, "main": main, "login_links_removed_from_main": removed,
                     "banner_placeholder_replaced_in_main": placeholder}
    return out


def build_page(title, main, rules, banner_text, extra_style=""):
    style = css(rules)
    head_extra = f"<style>{extra_style}</style>" if extra_style else ""
    return ("<!DOCTYPE html><html lang=\"ko\"><head><meta charset=\"UTF-8\">"
            f"<title>{title}</title><style>{style}</style>{head_extra}</head><body>"
            f"<div class=\"gov-banner\" id=\"gov-banner\"><img class=\"flag\" src=\"/flag.svg\" alt=\"대한민국 국기\" width=\"24\" height=\"16\">"
            f"<span class=\"banner-text\">{banner_text}</span></div>"
            "<header class=\"hd\"><div class=\"hd-util\"><a href=\"/sitemap\">사이트맵</a><a href=\"/en\">English</a></div>"
            "<div class=\"hd-top\"><a class=\"hd-logo\" href=\"/\">정부 서비스</a><a class=\"hd-icon\" href=\"/search\">검색</a>"
            "<a class=\"hd-icon login-link\" href=\"/login\">로그인</a></div>"
            "<nav class=\"hd-menu\"><a href=\"/svc\">민원 서비스</a><a href=\"/info\">정보 공개</a><a href=\"/news\">알림 소식</a></nav></header>"
            f"{main}"
            "<footer class=\"ft\"><p class=\"ft-contact\">대표전화 110 (평일 09:00~18:00)</p>"
            "<nav class=\"ft-policy\"><a href=\"/privacy\">개인정보처리방침</a><a href=\"/terms\">이용약관</a></nav>"
            "<p class=\"ft-copy\">© 정부 서비스. All rights reserved.</p></footer></body></html>")


def make_assignments(seed, templates, reassign=None):
    rng = random.Random(seed)
    tnames = sorted(templates)
    reassign = reassign or {}
    items = []
    variants = {"E9-1a": E9_1A, "E9-1b": E9_1B, "E9-2-banner": E9_2_BANNER, "E9-2-header": E9_2_HEADER, "E9-2-footer": E9_2_FOOTER}
    for sub, n in PLAN:
        order = tnames[:]
        rng.shuffle(order)
        vlist = list(variants.get(sub, [None]))
        rng.shuffle(vlist)
        for i in range(n):
            items.append({"subtype": sub, "slot": i, "body_template": order[i % len(order)], "variant": vlist[i % len(vlist)]})
    rng.shuffle(items)
    for k, it in enumerate(items):
        it["page_id"] = f"e9_{k + 1:03d}"
        if it["page_id"] in reassign:
            it["reassigned_from"] = it["body_template"]
            it["body_template"] = reassign[it["page_id"]]
    return items


def render(it, templates):
    t = templates[it["body_template"]]
    rules = [(s, dict(d)) for s, d in BASE_RULES]
    banner, extra = BANNER_TEXT, ""
    meta = {"page_id": it["page_id"], "subtype": it["subtype"], "body_template": it["body_template"],
            "defect_id": None, "intensity": None, "variant": None, "injected_string": None, "expected_failing_checks": []}
    sub = it["subtype"]
    if sub in ("E9-1a", "E9-1b"):
        vid, txt = it["variant"]
        banner = txt
        meta.update(defect_id="E9-1", intensity="a" if sub == "E9-1a" else "b", variant=vid, injected_string=txt,
                    expected_failing_checks=["banner_text"])
    elif sub.startswith("E9-2"):
        region, sel, prop, val, fails = it["variant"]
        for s, d in rules:
            if s == sel:
                d[prop] = val
                inj = rule_text(s, d)
        meta.update(defect_id="E9-2", intensity=region, variant=f"{sel} {prop}:{val}", injected_string=inj,
                    expected_failing_checks=fails)
    elif sub == "E9-3":
        meta.update(defect_id="E9-3", variant="href /login -> /signup", injected_string='href="/signup"',
                    expected_failing_checks=["login_href", "login_destination"])
    elif sub == "E9-4":
        extra = E9_4_MEDIA
        meta.update(defect_id="E9-4", variant="hide login link at max-width 768px", injected_string=E9_4_MEDIA,
                    expected_failing_checks=["login_visible_768", "login_visible_390"])
    html = build_page(t["title"], t["main"], rules, banner, extra)
    if sub == "E9-3":
        html = html.replace('<a class="hd-icon login-link" href="/login">', '<a class="hd-icon login-link" href="/signup">', 1)
    assert meta["injected_string"] is None or html.count(meta["injected_string"]) == 1, (it["page_id"], meta["injected_string"])
    return html, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--reassign", default=None, help="JSON {page_id: body_template} (푸터 결함 재배정)")
    a = ap.parse_args()
    if os.path.exists(OUT):
        if not a.overwrite:
            raise SystemExit(f"{OUT} 이미 있음 (--overwrite 로 다시 생성; 동결 전에만)")
        shutil.rmtree(OUT)
    reassign = json.load(open(a.reassign, encoding="utf-8")) if a.reassign else {}
    templates = load_templates()
    items = make_assignments(a.seed, templates, reassign)
    os.makedirs(OUT)
    metas = []
    for it in items:
        html, meta = render(it, templates)
        if "reassigned_from" in it:
            meta["reassigned_from"] = it["reassigned_from"]
        with open(os.path.join(OUT, f"{it['page_id']}.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        meta["bytes"] = len(html.encode("utf-8"))
        metas.append(meta)
    for name, title in (("login", "로그인"), ("signup", "회원가입")):
        os.makedirs(os.path.join(OUT, name))
        with open(os.path.join(OUT, name, "index.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"<!DOCTYPE html><html lang=\"ko\"><head><meta charset=\"UTF-8\"><title>{title}</title></head>"
                    f"<body><main><h1>{title}</h1></main></body></html>")
    write_flag(OUT)
    doc = {"seed": a.seed, "generator": "experiments/revision/e9_generate.py", "design": "docs/e9_design.md (v5)",
           "banner_text_required": BANNER_TEXT, "base_css": css(BASE_RULES), "base_css_chars": len(css(BASE_RULES)),
           "e9_4_media_query": E9_4_MEDIA,
           "body_templates": {k: {"title": v["title"], "login_links_removed_from_main": v["login_links_removed_from_main"]}
                              for k, v in templates.items()},
           "reassignments": reassign, "pages": metas}
    json.dump(doc, open(os.path.join(OUT, "dataset_metadata_e9.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(json.dumps({"pages": len(metas), "by_subtype": Counter(m["subtype"] for m in metas),
                      "base_css_chars": len(css(BASE_RULES)), "max_bytes": max(m["bytes"] for m in metas)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
