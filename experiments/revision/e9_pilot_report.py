"""
E9 파일럿 보고서 1~7절 (API 호출 없음). 8절(수정이 필요해 보이는 점)은 결과를 읽고 사람이/Claude 가 따로 적는다.

  python experiments/revision/e9_pilot_report.py
출력: results/revision/reports/e9_pilot_report.md (8절 자리표시 포함), results/revision/e9_pilot/tables/*.csv
"""
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import e9_rules as primary        # noqa: E402
from scoring import e9_rules_aux as aux        # noqa: E402
from experiments.revision import e9_regex_table as tbl   # noqa: E402

RUNS = "results/revision/runs_e9_pilot"
META = "testbed_e9_pilot/dataset_metadata_e9_pilot.json"
OUT = "results/revision/reports/e9_pilot_report.md"
CONDS = ["norag", "fixed", "page", "related", "fixedlong"]
CNAME = {"norag": "RAG 끔", "fixed": "고정 질의", "page": "페이지별 질의", "related": "관련 조항 제공", "fixedlong": "fixed-long"}
RELATED = ["906848de-bb99-4446-adb1-16a2dc61d34e", "574b8c73-13b0-43e7-bbe8-abc31f41bb2c", "265eeb6d-3e1a-43bc-99b7-d299c8ff4233",
           "1fff974d-ca33-444d-a3ac-8b93b5a8aadf", "87f08a4d-b8b6-427c-8fd5-2925b07b4d8a", "905711bf-2989-473d-9cf8-47a3ed1dd8f9"]
NONCOMPLIANCE_EXAMPLE = "대한민국 공식 전자정부 웹사이트입니다"
CODE_EVIDENCE = re.compile(r"(href|/signup|signup|@media|display\s*:\s*none|max-width|768\s*px|<a\b|a\[href)", re.I)
USED = []


def use(p):
    if p not in USED:
        USED.append(p)
    return p


def src(*paths):
    for p in paths:
        use(p)
    return f"출처: `{paths[0]}`" if len(paths) == 1 else "출처:\n" + "\n".join(f"- `{p}`" for p in paths)


def table(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "|".join("---" for _ in h) + "|"] + \
           ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def jl(p):
    return [json.loads(l) for l in open(use(p), encoding="utf-8") if l.strip()]


def chunk_texts(ids):
    con = sqlite3.connect("file:services/chroma_db/chroma.sqlite3?mode=ro", uri=True)
    q = ("SELECT e.embedding_id, m.string_value FROM embeddings e JOIN embedding_metadata m ON e.id = m.id "
         "WHERE m.key = 'chroma:document' AND e.embedding_id IN (%s)" % ",".join("?" * len(ids)))
    out = dict(con.execute(q, ids).fetchall())
    con.close()
    use("services/chroma_db/chroma.sqlite3")
    return out


def norm(s):
    return re.sub(r"\s+", "", s or "")


def context_of(prompt):
    a = prompt.find("[1. 정부 표준 가이드라인 (기본 지침)]")
    b = prompt.find("[2. 사용자 지정 추가 가이드라인")
    if a < 0 or b < 0:
        return None
    return prompt[a + len("[1. 정부 표준 가이드라인 (기본 지침)]"):b].strip()


def main():
    meta = {p["page_id"]: p for p in json.load(open(use(META), encoding="utf-8"))["pages"]}
    controls = sorted(p for p, m in meta.items() if m["defect_id"] is None)
    PREFIX = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else "e9-pilot"
    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else OUT
    freeze = sys.argv[sys.argv.index("--freeze") + 1] if "--freeze" in sys.argv else "exp-freeze-e9-v2"
    runs = {c: f"{RUNS}/{PREFIX}-{c}" for c in CONDS}
    calls = {c: jl(f"{runs[c]}/calls.jsonl") for c in CONDS}
    reps = {c: {r["page_id"]: r for r in jl(f"{runs[c]}/reports.jsonl")} for c in CONDS}
    L = [f"# E9 파일럿 보고서 ({PREFIX}, 2026-11-13)", "",
         "- 대상: `testbed_e9_pilot/` 8페이지 × 5조건 × 1회. **파이프라인 점검용이며 모든 분석에서 제외한다.**",
         f"- 동결: `{freeze}` (실행 전 동결 목록 대조 통과). Anthropic 의미 채점과 E9 LLM 판정은 쓰지 않았다.",
         "- 러너 `experiments/revision/run_experiment_e9.py`, 순서 실행 `experiments/revision/run_e9_pilot.py`.",
         "- oracle 입력: 본 실험 입력과 같은 청크·같은 순서를 파일럿 페이지 ID 로 옮긴 파일",
         "  (`results/revision/e9_pilot/e9p_related_clause_chunks.csv`, `e9p_fixed_long_chunks.csv`).", ""]

    # 1. 비용과 토큰
    L += ["## 1. 호출당 비용과 토큰, 총 비용", ""]
    rows, tot = [], 0.0
    for c in CONDS:
        cs = calls[c]
        n = len(cs)
        cost = sum(x["cost_usd"]["total"] for x in cs)
        tot += cost
        tk = lambda k: sum(x["cost_usd"]["tokens"][k] for x in cs) / n
        conc = json.load(open(use(f"{runs[c]}/run_meta.json"), encoding="utf-8"))["args"]["concurrency"]
        rows.append([CNAME[c], n, conc, f"{tk('input_uncached'):.0f}", f"{tk('input_cached'):.0f}",
                     f"{tk('output_incl_thinking'):.0f}", f"{cost / n:.5f}", f"{cost:.4f}"])
    L += table(["조건", "호출", "동시", "입력/호출", "캐시 입력/호출", "출력+사고/호출", "비용/호출", "비용"], rows)
    L += ["", f"총 비용: ${tot:.4f} (40호출). 단가: 입력 $0.30/1M, 캐시 $0.03/1M, 출력+사고 $2.50/1M.", "",
          "출처: `" + RUNS + "/" + PREFIX + "-{조건}/calls.jsonl`, `run_meta.json`", ""]

    # 2. 파싱 실패와 오류
    L += ["## 2. 파싱 실패와 오류", ""]
    rows = []
    for c in CONDS:
        st = Counter(x["status"] for x in calls[c])
        retries = sum(x.get("retries", 0) for x in calls[c])
        errs = sum(len(x.get("errors") or []) for x in calls[c])
        rows.append([CNAME[c], st.get("ok", 0), st.get("parse_error", 0),
                     sum(v for k, v in st.items() if k not in ("ok", "parse_error")), retries, errs,
                     ";".join(sorted({x.get("model_version") or "-" for x in calls[c]}))])
    L += table(["조건", "ok", "파싱 실패", "그 밖의 오류", "재시도", "오류 기록", "모델 버전"], rows)
    L += ["", "출처: `" + RUNS + "/" + PREFIX + "-{조건}/calls.jsonl`", ""]

    # 3. 컨텍스트
    L += ["## 3. 가이드라인 컨텍스트가 프롬프트에 들어갔는가", "",
          "프롬프트 파일(`prompts/{prompt_sha256}.txt`)의 '[1. 정부 표준 가이드라인]' 절 길이(글자). 페이지별 값의 최소~최대.", ""]
    rows = []
    for c in CONDS:
        nch = Counter(x["rag"]["n_chunks"] for x in calls[c])
        lens, ids = [], set()
        for x in calls[c]:
            p = f"{runs[c]}/prompts/{x['prompt_sha256']}.txt"
            ctx = context_of(open(use(p), encoding="utf-8").read()) if os.path.exists(p) else None
            if ctx is not None:
                lens.append(len(ctx))
            ids.add(tuple(ch["id"][:8] for ch in x["rag"]["chunks"]))
        rows.append([CNAME[c], ";".join(f"{k}청크×{v}" for k, v in sorted(nch.items())),
                     f"{min(lens)}~{max(lens)}" if lens else "-", len(ids)])
    L += table(["조건", "청크 수", "컨텍스트 글자 수", "페이지 간 서로 다른 청크 목록 수"], rows)
    L += ["", "RAG 끔은 컨텍스트 절이 비어 있어야 한다(0자). 관련 조항 제공·fixed-long 은 모든 페이지에 같은 청크 목록(1개)이어야 한다.", "",
          "출처: `" + RUNS + "/" + PREFIX + "-{조건}/calls.jsonl`, `prompts/`", ""]

    # 4. 페이지별 이슈 요약
    L += ["## 4. 페이지별 모델 보고 이슈 요약", "",
          "주 지표 정규식으로 걸린 유형과, 그 유형에 걸린 첫 이슈(없으면 첫 이슈)의 설명 앞부분(URL 접두어 제거, 40자).", ""]
    for c in CONDS:
        L += [f"### 4.{CONDS.index(c) + 1} {CNAME[c]}", ""]
        rows = []
        for pid in sorted(meta):
            m = meta[pid]
            r = reps[c].get(pid)
            iss = tbl.target_issues(r.get("report") if r and r["status"] == "ok" else None, pid)
            inj = m["injected_string"] if m["defect_id"] == "E9-1" else None
            hits = [k for k in primary.TYPES if any(primary.match_issue(i, inj)[k] for i in iss)]
            pick = next((i for i in iss if hits and primary.match_issue(i, inj)[hits[0]]), iss[0] if iss else None)
            line = primary.issue_text(pick)[:40].replace("|", "/") if pick else "-"
            rows.append([pid, m["subtype"], len(iss), ",".join(hits) or "-", line])
        L += table(["페이지", "주입", "이슈", "정규식 탐지", "핵심 한 줄"], rows)
        L += ["", f"출처: `{runs[c]}/reports.jsonl`", ""]

    # 5. 정규식 주 지표 vs 보조
    out_dir = "results/revision/e9_pilot/tables" if PREFIX == "e9-pilot" else f"results/revision/e9_pilot/tables_{PREFIX}"
    tbl.main(["--runs-base", RUNS, "--testbed", "pilot", "--out", out_dir])
    rr = list(csv.DictReader(open(use(f"{out_dir}/e9_regex_primary_vs_aux.csv"), encoding="utf-8")))
    L += ["## 5. 정규식 주 지표와 보조 분석 (조건별, 유형별, 대조군 위양성)", "",
          "주 지표 = 그 페이지에 주입된 변형 문구만 인정. 보조 = 6개 변형 문구를 모든 페이지에 적용. 파일럿은 유형별 결함 1페이지, 대조군 2페이지.", ""]
    for c in CONDS:
        L += [f"### 5.{CONDS.index(c) + 1} {CNAME[c]}", ""]
        L += table(["유형", "규칙", "탐지/결함", "대조군 탐지/대조군"],
                   [[r["type"], "주 지표" if r["rule"] == "primary" else "보조", f"{r['detected']}/{r['defect_pages']}",
                     f"{r['control_detected']}/{r['controls']}"] for r in rr if r["run"] == f"{PREFIX}-{c}"])
        L += ["", src(f"{out_dir}/e9_regex_primary_vs_aux.csv"), ""]

    # 6. 관련 조항 제공: 대조군 이슈의 조항 문구 인용
    texts = chunk_texts(RELATED)
    grams = set()
    for t in texts.values():
        n = norm(t)
        grams.update(n[i:i + 15] for i in range(0, max(0, len(n) - 14)))
    L += ["## 6. 관련 조항 제공 조건: 대조군 이슈가 조항 청크 문구를 그대로 인용했는가", "",
          "검사: (a) 미준수 사례 문구 \"대한민국 공식 전자정부 웹사이트입니다\", (b) 규정 배너 문구, (c) 6청크 본문과 공백 제거 후",
          "15자 이상 연속 일치. 비교를 위해 같은 검사를 다른 조건의 대조군 이슈에도 적용했다.", ""]
    rows = []
    for c in CONDS:
        for pid in controls:
            r = reps[c].get(pid)
            iss = tbl.target_issues(r.get("report") if r and r["status"] == "ok" else None, pid)
            a = sum(NONCOMPLIANCE_EXAMPLE in primary.issue_text(i) for i in iss)
            b = sum(primary.REQUIRED_BANNER in primary.issue_text(i) for i in iss)
            g = 0
            for i in iss:
                n = norm(primary.issue_text(i))
                g += any(n[k:k + 15] in grams for k in range(0, max(0, len(n) - 14)))
            rows.append([CNAME[c], pid, len(iss), a, b, g])
    L += table(["조건", "대조군", "이슈", "(a) 미준수 사례 인용", "(b) 규정 문구 인용", "(c) 15자+ 일치 이슈"], rows)
    L += ["", src("services/chroma_db/chroma.sqlite3") + " (읽기 전용, 6청크 본문)",
          "및 `" + RUNS + "/" + PREFIX + "-{조건}/reports.jsonl`", ""]

    # 7. E9-3 / E9-4
    L += ["## 7. E9-3, E9-4 페이지: HTML 근거로 탐지되는가 (보고 내용 기준 관찰)", "",
          "시스템은 스크린샷과 HTML 을 함께 받는다(modality both). 아래는 이슈 문구에 코드 근거",
          "(href, signup, @media, display:none, max-width, 768px, a 태그)가 들어 있는지 본 관찰이며 판정이 아니다.", ""]
    rows = []
    for c in CONDS:
        for pid in sorted(meta):
            m = meta[pid]
            if m["defect_id"] not in ("E9-3", "E9-4"):
                continue
            r = reps[c].get(pid)
            iss = tbl.target_issues(r.get("report") if r and r["status"] == "ok" else None, pid)
            typ = m["defect_id"]
            hit = [i for i in iss if primary.match_issue(i)[typ]]
            code = [i for i in hit if CODE_EVIDENCE.search(primary.issue_text(i))]
            kw = [i for i in iss if re.search(r"(signup|회원\s*가입|768|@media|display\s*:\s*none)", primary.issue_text(i), re.I)]
            rows.append([CNAME[c], pid, typ, len(iss), len(hit), len(code), len(kw)])
    L += table(["조건", "페이지", "유형", "이슈", "정규식 탐지 이슈", "그중 코드 근거", "결함 관련어 언급 이슈"], rows)
    L += ["", "출처: `" + RUNS + "/" + PREFIX + "-{조건}/reports.jsonl`", ""]

    if "--compare" in sys.argv:
        from experiments.revision import e9_pilot_compare as cmpm
        old = sys.argv[sys.argv.index("--compare") + 1]
        old_tab = use("results/revision/e9_pilot/tables/e9_regex_primary_vs_aux.csv") if old == "e9-pilot" else \
            use(f"results/revision/e9_pilot/tables_{old}/e9_regex_primary_vs_aux.csv")
        tables = {old: cmpm.load_table(old_tab), PREFIX: rr}
        for c in CONDS:
            use(f"{RUNS}/{old}-{c}/reports.jsonl")
        L += cmpm.section(old, PREFIX, CONDS, CNAME, meta, tables)
    L += ["## 8. 수정이 필요해 보이는 점", "", "<<SECTION8>>", ""]
    L += ["## 9. 이 보고서에 사용한 파일", ""]
    files = [p for p in USED if os.path.isfile(p)]
    for c in CONDS:
        for f in ("calls.jsonl", "reports.jsonl", "run_meta.json", "SHA256SUMS"):
            p = f"{runs[c]}/{f}"
            if p not in files:
                files.append(p)
    L += table(["경로", "SHA-256 앞 16자리"], [[f"`{p}`", hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]]
                                          for p in files if "prompts/" not in p])
    L += ["", "프롬프트 파일은 각 run 의 `SHA256SUMS` 에 해시가 있다. 생성 스크립트: `experiments/revision/e9_pilot_report.py`", ""]
    L = [x for l in L for x in str(l).split("\n")]
    bad = [l for l in L if len(l) > 100]
    if bad:
        raise SystemExit("lines over 100 chars:\n" + "\n".join(f"{len(l)}: {l}" for l in bad))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(out_path)


if __name__ == "__main__":
    sys.exit(main())
