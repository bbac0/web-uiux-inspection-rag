"""
사람 평가 시트 생성 (5단계 E5, API 호출 없음). R1 로그가 완성되고 사용자 승인을 받은 뒤에만 실행한다.

페이지 표본 (주입 라벨과 대조군 여부만 사용. 키워드·의미 채점 결과나 채점기 간 불일치는 표본 추출에 쓰지 않는다)
  평가자 A 전체 시트: 대조군 39 + 용어 위반 45 + 나머지 4개 유형마다 아직 뽑히지 않은 해당 유형 페이지 12개 (총 132)
                      → 4개 유형은 각각 12페이지 이상 포함된다 (용어 위반 페이지에 섞인 다른 결함은 추가로 더해짐)
  평가자 B 부분 시트: A 의 부분집합. A 를 뽑은 층(대조군, 용어, 대비, 모바일, 버튼, 중복 ID)별로 비례 배분(최대 나머지 방식)한
                      약 60페이지. 모든 층에서 최소 1페이지 이상.
  각 페이지의 R1 대상 페이지 이슈를 전부 넣는다.

가림 처리
  - issue_id 는 무작위 토큰(시트마다 같은 이슈는 같은 id). 페이지 ID, run_id, 조건명, 주입 라벨은 시트에 넣지 않는다.
  - 이슈 설명 앞의 "[URL]" 접두어(페이지 ID 포함)는 지운다. 설명/제안 본문에 페이지 ID 가 남아 있으면 오류로 멈춘다.
  - 스크린샷은 페이지마다 무작위 토큰 이름으로 복사한다 (eval/shots/{token}.png).
  - A 와 B 는 서로 다른 시드로 행 순서를 섞는다 (페이지와 이슈 순서 모두 섞임).
  - 정답 키(eval_key.csv)는 별도 파일: issue_id → run_id, page_id, template_id, 이슈 순번, 표본 층, nominal/effective 라벨.

열 (eval_sheet_A.csv, eval_sheet_B.csv)
  issue_id, screenshot_path, description, suggestion, rater_category, exists_in_code, visible_on_screen,
  login_link_label_concern (이슈가 로그인 링크 레이블의 문구 또는 의미 명확성을 지적하는가: 예/아니오), rater_notes

사용법
  python experiments/revision/make_eval_sheets.py --run-id E1-R1 --seed-a <A 시드> --seed-b <B 시드> [--out results/revision/eval]
  (불일치 중심 표본이 필요하면 별도 스크립트로 만들고 파일 이름에 disagreement_focus 를 붙인다. 이 스크립트는 만들지 않는다.)
"""
import argparse
import csv
import json
import os
import random
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
TERM = "Standard Terminology Violation"
OTHER = [t for t in TYPES if t != TERM]
STRATA = ["control", "terminology"] + OTHER
PER_OTHER_TYPE = 12
B_TARGET = 60
URL_PREFIX_RE = re.compile(r"^\s*\[(?:https?|file)://[^\]]*\]\s*")
LEAK_RE = re.compile(r"page_\d{3}|testbed_200|localhost:\d+")
SHEET_COLS = ["issue_id", "screenshot_path", "description", "suggestion",
              "rater_category", "exists_in_code", "visible_on_screen", "login_link_label_concern", "rater_notes"]
CATEGORY_CHOICES = ["명도 대비 부족", "모바일 레이아웃 깨짐", "버튼 영역 잘림", "표준 용어 위반", "중복 ID", "해당 없음"]


class LeakError(ValueError):
    pass


def load_labels(metadata_path, ground_truth_path):
    meta = json.load(open(metadata_path, encoding="utf-8"))
    nominal = {p["page_id"][:-5]: sorted({d["type"] for d in p["defects"]}) for p in meta}
    template = {p["page_id"][:-5]: p["base_template"] for p in meta}
    eff = {}
    for r in csv.DictReader(open(ground_truth_path, encoding="utf-8")):
        if r["effective_1280"] == "1":
            eff.setdefault(r["page_id"], []).append(r["defect_type"])
    return nominal, template, eff


def select_pages_a(nominal, seed_a):
    """A 표본: (page_id → 층). 무작위성은 seed_a 의 독립 난수열 하나만 쓴다."""
    rng = random.Random(f"A-select-{seed_a}")
    chosen = {}
    for p in sorted(nominal):
        if not nominal[p]:
            chosen[p] = "control"
        elif TERM in nominal[p]:
            chosen[p] = "terminology"
    for t in OTHER:
        pool = sorted(p for p in nominal if t in nominal[p] and p not in chosen)
        for p in rng.sample(pool, min(PER_OTHER_TYPE, len(pool))):
            chosen[p] = t
    return chosen


def select_pages_b(a_strata, seed_b, target=B_TARGET):
    """B 표본: A 의 층별 비례 배분 (최대 나머지), 층마다 최소 1."""
    rng = random.Random(f"B-select-{seed_b}")
    by = {s: sorted(p for p, st in a_strata.items() if st == s) for s in STRATA}
    total = sum(len(v) for v in by.values())
    exact = {s: target * len(by[s]) / total for s in STRATA if by[s]}
    quota = {s: max(1, int(x)) for s, x in exact.items()}
    for s in sorted(exact, key=lambda s: (-(exact[s] - int(exact[s])), STRATA.index(s))):
        if sum(quota.values()) >= target:
            break
        if quota[s] < len(by[s]):
            quota[s] += 1
    out = {}
    for s in STRATA:
        for p in rng.sample(by[s], min(quota.get(s, 0), len(by[s]))):
            out[p] = s
    return out


def clean_text(s):
    return URL_PREFIX_RE.sub("", s or "", count=1).strip()


def collect_issues(run_dir, pages):
    """run 의 reports.jsonl 에서 표본 페이지의 대상 페이지 이슈 → [(page_id, issue_index, issue)]."""
    out = []
    with open(os.path.join(run_dir, "reports.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["page_id"] not in pages:
                continue
            marker = f"testbed_200/{r['page_id']}.html"
            for idx, issue in enumerate((r.get("report") or {}).get("issues", []) or []):
                if isinstance(issue, dict) and marker in (issue.get("description") or ""):
                    out.append((r["page_id"], idx, issue))
    return out


def build(run_id, seed_a, seed_b, out_dir, runs_base, metadata_path, ground_truth_path):
    if seed_a == seed_b:
        raise ValueError("seed-a 와 seed-b 는 서로 달라야 한다")
    run_dir = os.path.join(runs_base, run_id)
    nominal, template, eff = load_labels(metadata_path, ground_truth_path)
    a_strata = select_pages_a(nominal, seed_a)
    b_strata = select_pages_b(a_strata, seed_b)
    issues = collect_issues(run_dir, set(a_strata))

    tok_rng = random.Random(f"tokens-{seed_a}")
    page_token = {p: f"P{tok_rng.getrandbits(40):010x}" for p in sorted(a_strata)}
    issue_token, used = {}, set()
    for p, idx, _ in sorted(issues, key=lambda x: (x[0], x[1])):
        t = f"I{tok_rng.getrandbits(40):010x}"
        while t in used:
            t = f"I{tok_rng.getrandbits(40):010x}"
        used.add(t)
        issue_token[(p, idx)] = t

    os.makedirs(os.path.join(out_dir, "shots"), exist_ok=True)
    rows = []
    for p, idx, issue in issues:
        desc, sug = clean_text(issue.get("description")), (issue.get("suggestion") or "").strip()
        if LEAK_RE.search(desc) or LEAK_RE.search(sug):
            raise LeakError(f"page identifier left in issue text ({p}, #{idx})")
        src = os.path.join(run_dir, "shots", f"{p}.png")
        rel = f"shots/{page_token[p]}.png"
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(out_dir, rel))
        rows.append({"issue_id": issue_token[(p, idx)], "screenshot_path": rel, "description": desc, "suggestion": sug,
                     "rater_category": "", "exists_in_code": "", "visible_on_screen": "", "login_link_label_concern": "",
                     "rater_notes": "",
                     "_page": p, "_idx": idx})

    def write_sheet(name, sel, seed_tag):
        rs = [r for r in rows if r["_page"] in sel]
        random.Random(seed_tag).shuffle(rs)
        with open(os.path.join(out_dir, name), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=SHEET_COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rs)
        return [r["issue_id"] for r in rs]

    order_a = write_sheet("eval_sheet_A.csv", a_strata, f"A-shuffle-{seed_a}")
    order_b = write_sheet("eval_sheet_B.csv", b_strata, f"B-shuffle-{seed_b}")
    with open(os.path.join(out_dir, "eval_key.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue_id", "run_id", "page_id", "template_id", "issue_index", "page_token", "stratum",
                    "in_sheet_B", "nominal_types", "effective_types_1280"])
        for r in sorted(rows, key=lambda r: r["issue_id"]):
            p = r["_page"]
            w.writerow([r["issue_id"], run_id, p, template[p], r["_idx"], page_token[p], a_strata[p],
                        int(p in b_strata), ";".join(nominal[p]), ";".join(sorted(eff.get(p, [])))])
    manifest = {"run_id": run_id, "seed_a": seed_a, "seed_b": seed_b,
                "pages_A": len(a_strata), "pages_B": len(b_strata), "issues_A": len(order_a), "issues_B": len(order_b),
                "strata_A": {s: sum(1 for v in a_strata.values() if v == s) for s in STRATA},
                "strata_B": {s: sum(1 for v in b_strata.values() if v == s) for s in STRATA},
                "type_coverage_A": {t: sum(1 for p in a_strata if t in nominal[p]) for t in TYPES},
                "pages_without_issues_A": sorted(p for p in a_strata if not any(r["_page"] == p for r in rows)),
                "category_choices": CATEGORY_CHOICES, "answer_choices": ["예", "아니오", "판단 불가"],
                "login_link_label_concern_choices": ["예", "아니오"]}
    with open(os.path.join(out_dir, "sampling_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--seed-a", type=int, required=True)
    ap.add_argument("--seed-b", type=int, required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "revision", "eval"))
    ap.add_argument("--runs-base", default=os.path.join(ROOT, "results", "revision", "runs"))
    ap.add_argument("--metadata", default=os.path.join(ROOT, "testbed_200", "dataset_metadata.json"))
    ap.add_argument("--ground-truth", default=os.path.join(ROOT, "results", "revision", "ground_truth.csv"))
    a = ap.parse_args(argv)
    if os.path.exists(a.out) and os.listdir(a.out):
        raise SystemExit(f"output folder not empty: {a.out}")
    m = build(a.run_id, a.seed_a, a.seed_b, a.out, a.runs_base, a.metadata, a.ground_truth)
    print(json.dumps(m, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
