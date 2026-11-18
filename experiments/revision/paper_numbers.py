"""
논문 작성용 숫자표 최종판 (API 호출 없음, 통계 검정 새로 하지 않음). 모든 숫자는 원본 csv / jsonl 에서 읽거나 원본 jsonl 에서 셈한다.
각 표 아래와 셀 옆에 출처 파일 경로를 적는다. E7 최종, E5b, E6(원·재채점), E9 주 결과·사람 평가·보조 분석은
experiments/revision/paper_numbers_final.py 의 절을 쓰고, 보고서 값과 자동 대조한 결과를 13절에 적는다.

출력: results/revision/reports/paper_numbers.md
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import issue_table_merged as itm             # noqa: E402
from scoring import semantic_grader_anthropic as sga      # noqa: E402
from experiments.revision import e9_regex_table as tbl    # noqa: E402
from experiments.revision import paper_numbers_final as pf  # noqa: E402

R = "results/revision"
RUNS = f"{R}/runs"
SEM = f"{R}/semantic_scores"
GT = f"{R}/ground_truth.csv"
OUT = f"{R}/reports/paper_numbers.md"
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
SH = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
      "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복ID"}
TERM = "Standard Terminology Violation"
MAIN_RUNS = ["E1-R1", "E1-R2", "E1-R3b", "E2-A1-1", "E2-A1-2", "E2-A1-3", "E2-A2", "E2-A3", "E3-page", "E3-oracle", "E4-mobile"]
SEM_RUNS = ["E1-R1", "E1-R2", "E1-R3b", "E2-A1-1", "E2-A1-2", "E2-A1-3", "E3-page", "E3-oracle", "E4-mobile"]
FAIL = ("api_error", "rag_empty", "rag_error", "acquisition_error")
E9RUNS = f"{R}/runs_e9"
E9CONDS = ["norag", "fixed", "page", "related", "fixedlong"]
E9NAME = {"norag": "RAG 끔", "fixed": "고정 질의", "page": "페이지별 질의", "related": "관련 조항 제공", "fixedlong": "fixed-long"}


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def rcsv(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def src(*p):
    return ["", "출처:"] + [f"- `{x}`" for x in p] + [""]


def tab(h, rows):
    out = ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)]
    for r in rows:
        line = "| " + " | ".join(str(c) for c in r) + " |"
        out.append(line if len(line) <= 100 else "|" + "|".join(str(c) for c in r) + "|")
    return out


def f3(x):
    return "-" if x is None or x != x else f"{x:.3f}"


AB = {"keyword": "kw", "string_match": "sm", "nominal": "nom", "effective": "eff", "guideline_grounded": "gg",
      "guideline_grounded_btn_true": "gg_bt", "micro (5 types)": "micro", "Terminology": "Term"}
LEGEND = ("약어: kw = 키워드, sm = string_match, nom = nominal, eff = effective(1280),\n"
          "gg = guideline_grounded(버튼 false), gg_bt = guideline_grounded(버튼 true, 민감도),\n"
          "micro = 5유형 합산, Term = 용어.\n"
          "run: R1 = E1-R1, A1-1 = E2-A1-1, E1-maj = E1 3회 다수결, A1-maj = A1 3회 다수결.")


def ab(x):
    return AB.get(x, x)


def cmp_ab(x):
    return x.replace("-majority", "-maj").replace("E1-R", "R").replace("E2-A", "A").replace(" - ", "−")


def metrics(tp, fp, fn, tn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    s = tn / (tn + fp) if tn + fp else None
    d = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    m = (tp * tn - fp * fn) / d if d else None
    return p, r, s, m


def main():
    lab = {(r["page_id"], r["defect_type"]): int(r["nominal_injected"]) for r in rcsv(GT)}
    meta = {rid: json.load(open(f"{RUNS}/{rid}/run_meta.json", encoding="utf-8")) for rid in os.listdir(RUNS)
            if os.path.exists(f"{RUNS}/{rid}/run_meta.json")}
    B = pf.Book()
    L = ["# 논문 작성용 숫자표 (최종)", "",
         "작성: `experiments/revision/paper_numbers.py`, `paper_numbers_final.py` (API 호출 없음). 2026-11-18.",
         "숫자는 원본 csv/jsonl 에서 읽거나 원본 jsonl 에서 셌다. 새 통계 검정은 하지 않았다(구간은 산출 csv 값).",
         "주 채점기는 의미 채점(재채점 retry800 병합), 키워드는 보조다. 라벨은 따로 적지 않으면 nominal.",
         "정규식·지표·동결 규칙·기존 보고서는 고치지 않았다. 보고서와의 자동 대조 결과는 13절.",
         "사람 평가 결과를 본 뒤 채점 모델, 프롬프트, 키워드 사전, 정규식을 바꾸지 않았다(사전 등록 10절 5항).", ""]

    # (1) 시스템 설정
    m1 = meta["E1-R1"]
    c1 = jl(f"{RUNS}/E1-R1/calls.jsonl")[0]
    gcfg = json.load(open("scoring/grader_config.json", encoding="utf-8"))
    nchunk = len(rcsv(f"{R}/fixed_query_embedding/ranking.csv"))
    rows = [[f"생성 모델 ({k})", v, f"{RUNS}/E1-R1/run_meta.json frozen_settings"] for k, v in m1["frozen_settings"].items()]
    rows += [["응답 model_version", c1["model_version"], f"{RUNS}/E1-R1/calls.jsonl"],
             ["뷰포트", "x".join(map(str, c1["viewport"])), f"{RUNS}/E1-R1/calls.jsonl"],
             ["모달리티 (E1)", c1["modality"], f"{RUNS}/E1-R1/calls.jsonl"],
             ["프롬프트 날짜", m1["args"]["prompt_date"], f"{RUNS}/E1-R1/run_meta.json"],
             ["벡터 DB 청크 수", nchunk, f"{R}/fixed_query_embedding/ranking.csv"]]
    rows += [[f"패키지 {k}", v, f"{RUNS}/E1-R1/run_meta.json env"] for k, v in m1["env"]["packages"].items()]
    rows += [["Python", m1["env"]["python"], f"{RUNS}/E1-R1/run_meta.json env"]]
    rows += [[f"의미 채점 {k}", json.dumps(gcfg[k], ensure_ascii=False) if isinstance(gcfg[k], (dict, list)) else gcfg[k],
              "scoring/grader_config.json"]
             for k in ("provider", "model", "temperature", "max_tokens", "thinking", "effort", "input_fields", "judge_prompt_version")]
    rcfg = json.load(open("scoring/grader_config_retry800.json", encoding="utf-8"))
    rows += [["재채점 max_tokens", rcfg["max_tokens"], "scoring/grader_config_retry800.json"]]
    keys = {}
    for r in rows:
        r[2] = keys.setdefault(r[2], f"[{len(keys) + 1}]")
    L += ["## 1. 시스템 설정", ""] + tab(["항목", "값", "출처"], rows)
    L += ["", "출처:"] + [f"- {k} `{v}`" for v, k in keys.items()] + [""]

    # (2) run 표
    rows = []
    for rid in sorted(meta, key=lambda r: meta[r]["started_utc"]):
        m, calls = meta[rid], jl(f"{RUNS}/{rid}/calls.jsonl")
        if m.get("mock") or rid.startswith("pilot"):
            continue
        reps = jl(f"{RUNS}/{rid}/reports.jsonl")
        st = Counter(c["status"] for c in calls)
        n_all = sum(len((r.get("report") or {}).get("issues") or []) for r in reps)
        n_t = sum(1 for _ in sga.iter_run_issues(rid)) if os.path.exists(f"{RUNS}/{rid}/reports.jsonl") else 0
        a = m["args"]
        rows.append([rid, a["modality"], "끔" if a["no_rag"] else a["query_mode"], len(m["pages"]),
                     "aborted" if os.path.exists(f"{RUNS}/{rid}/ABORTED.json") else "complete",
                     ", ".join(f"{k} {v}" for k, v in sorted(st.items())), n_all, n_t,
                     f"{sum(c['cost_usd']['total'] for c in calls):.4f}"])
    L += ["## 2. run 표와 이슈 수", "", "### 2.1 testbed_200 run", ""]
    L += tab(["run", "모달", "RAG", "페이지", "상태", "호출 상태", "이슈 전체", "대상 이슈", "비용"], rows)
    L += src(f"{RUNS}/{{run}}/run_meta.json", f"{RUNS}/{{run}}/calls.jsonl", f"{RUNS}/{{run}}/reports.jsonl",
             "대상 이슈 = scoring/semantic_grader_anthropic.iter_run_issues (description 에 그 페이지 URL)")
    rows = []
    for d in sorted(os.listdir(E9RUNS)):
        calls, reps = jl(f"{E9RUNS}/{d}/calls.jsonl"), jl(f"{E9RUNS}/{d}/reports.jsonl")
        rows.append([d, len(calls), ", ".join(f"{k} {v}" for k, v in sorted(Counter(c["status"] for c in calls).items())),
                     sum(len((r.get("report") or {}).get("issues") or []) for r in reps),
                     f"{sum(c['cost_usd']['total'] for c in calls):.4f}"])
    L += ["### 2.2 E9 run", ""] + tab(["run", "호출", "상태", "이슈 전체", "비용"], rows)
    L += src(f"{E9RUNS}/{{run}}/calls.jsonl", f"{E9RUNS}/{{run}}/reports.jsonl")
    rows = []
    for d in sorted(os.listdir(SEM)):
        g = jl(f"{SEM}/{d}/grades.jsonl")
        if not g:
            continue
        st = Counter("truncated" if x.get("truncated") else x["status"] for x in g)
        rows.append([d, len(g), ", ".join(f"{k} {v}" for k, v in sorted(st.items()))])
    L += ["### 2.3 의미 채점 out_id", ""] + tab(["out_id", "레코드", "상태 (잘림 = truncated)"], rows)
    L += src(f"{SEM}/{{out_id}}/grades.jsonl")

    # (3) 유형별 TP, FP
    preds = {}
    for rid in MAIN_RUNS:
        pages = meta[rid]["pages"]
        oid = f"{rid}-sem-p1" if rid in SEM_RUNS else None
        rows_ = itm.build_rows(rid, oid) if oid else [dict(r, semantic_pass1="", semantic_pass1_status="",
                                                           semantic_pass1_merged="", semantic_pass1_source="")
                                                      for r in itm.it.build_rows(rid)]
        P = {k: defaultdict(set) for k in ("kw", "sem", "merged", "sm")}
        unres = 0
        for r in rows_:
            p = r["page_id"]
            for t in filter(None, r["keyword_types"].split(";")):
                P["kw"][p].add(t)
            if r["semantic_pass1_status"] == "ok" and r["semantic_pass1"] in TYPES:
                P["sem"][p].add(r["semantic_pass1"])
            if r["semantic_pass1_merged"] in TYPES:
                P["merged"][p].add(r["semantic_pass1_merged"])
            if r["string_match_term"]:
                P["sm"][p].add(TERM)
            unres += oid is not None and r["semantic_pass1_source"] == "unresolved"
        preds[rid] = (pages, P, unres, oid is not None)
    L += ["## 3. 유형별 TP·FP 페이지 수 (nominal)", "",
          "키 = 키워드(description 다중 라벨), 의(원) = 의미 pass1 원 규칙(잘림 = 음성), 의(재) = 재채점(retry800) 병합",
          "(주 분석; 재채점 뒤에도 미해결인 건은 음성), sm = string_match(용어만). 실패 페이지는 음성. '-' = 해당 채점 없음.", ""]
    rows = []
    for rid in MAIN_RUNS:
        pages, P, unres, has = preds[rid]
        for t in TYPES:
            pos = sum(lab[(p, t)] for p in pages)
            c = {k: (sum(1 for p in pages if lab[(p, t)] and t in P[k][p]), sum(1 for p in pages if not lab[(p, t)] and t in P[k][p]))
                 for k in P}
            sm = f"{c['sm'][0]} / {c['sm'][1]}" if t == TERM else "-"
            rows.append([rid, SH[t], len(pages), pos, f"{c['kw'][0]} / {c['kw'][1]}",
                         f"{c['sem'][0]} / {c['sem'][1]}" if has else "-",
                         f"{c['merged'][0]} / {c['merged'][1]}" if has else "-", sm, unres if has else "-"])
    L += tab(["run", "유형", "페이지", "양성", "키 TP/FP", "의(원) TP/FP", "의(재) TP/FP", "sm TP/FP", "run 미해결 이슈"], rows)
    L += src(f"{RUNS}/{{run}}/reports.jsonl", f"{RUNS}/{{run}}/run_meta.json", GT,
             f"{SEM}/{{run}}-sem-p1/grades.jsonl", f"{SEM}/{{run}}-sem-p1-retry/grades.jsonl",
             "scoring/issue_table_merged.py")

    # (4) E7 최종, (5) E6
    pf.sec_e7(L, B, tab)
    pf.sec_e6(L, B, tab, preds, lab, TYPES, SH)

    # (6) E9 주 결과
    pf.sec_e9(L, B, tab)

    # (7) 지연시간
    lat = rcsv(f"{R}/tables/latency_E1-R1.csv")
    L += ["## 7. 지연시간 (E1-R1, 순차 실행, 초)", ""]
    L += tab(["단계", "n", "평균", "SD", "중앙값", "p95", "최소", "최대", "평균 비중"],
             [[r["label_en"].replace("$^{a}$", "(a)").replace("|", "/"), r["n"], r["mean"], r["sd"], r["median"], r["p95"],
               r["min"], r["max"], r["share_of_total_mean"]] for r in lat])
    L += src(f"{R}/tables/latency_E1-R1.csv")

    # (8) 비용
    rows = []
    for name, base in (("testbed_200", RUNS), ("testbed_200 파일럿", RUNS), ("E9 파일럿", f"{R}/runs_e9_pilot"), ("E9 본 실험", E9RUNS)):
        tot, n = 0.0, 0
        for d in sorted(os.listdir(base)):
            if base == RUNS and (d.startswith("pilot") != (name == "testbed_200 파일럿")):
                continue
            cs = jl(f"{base}/{d}/calls.jsonl")
            tot += sum(c["cost_usd"]["total"] for c in cs); n += len(cs)
        rows.append([f"Gemini 생성: {name}", n, f"{tot:.4f}", f"{base}/{{run}}/calls.jsonl"])
    sp = json.load(open(f"{R}/tables/spend_summary.json", encoding="utf-8"))
    e = sp["unlogged_estimates"][0]["cost_usd"]
    rows.append(["E1-R3 미기록 과금 추정 (합계 밖)", "-", f"{e['likely']:.4f}~{e['high_max_based']:.4f}",
                 f"{R}/tables/spend_summary.json"])
    probe = jl(f"{SEM}/probe-E1-R1/probe.jsonl")
    rows.append(["Anthropic 시험 호출 (표준가 $2/$10 per 1M)", len(probe),
                 f"{(sum(x['input_tokens'] for x in probe) * 2 + sum(x['output_tokens'] for x in probe) * 10) / 1e6:.4f}",
                 f"{SEM}/probe-E1-R1/probe.jsonl"])
    for d in sorted(os.listdir(SEM)):
        g = [x for x in jl(f"{SEM}/{d}/grades.jsonl") if x.get("mode") == "batch"]
        if g:
            rows.append([f"Anthropic 배치 {d} ($1/$5 per 1M)", len(g),
                         f"{sum((x['input_tokens'] or 0) + 5 * (x['output_tokens'] or 0) for x in g) / 1e6:.4f}",
                         f"{SEM}/{d}/grades.jsonl"])
    emb = jl(f"{R}/e9/page_query_embedding/call_log.jsonl") + jl(f"{R}/e9/page_query_embedding_attempt1_failed/call_log.jsonl")
    rows.append(["임베딩 (페이지별 질의, 추정 상한)", len(emb), f"{sum(x['cost_estimate_usd_upper'] for x in emb):.6f}",
                 f"{R}/e9/page_query_embedding*/call_log.jsonl"])
    keys = {}
    for r in rows:
        r[0] = r[0].replace(" ($1/$5 per 1M)", "").replace("Anthropic 배치 ", "Anthropic 배치: ")
        r[3] = keys.setdefault(r[3], f"[{len(keys) + 1}]")
    L += ["## 8. 비용", "", "Anthropic 배치 단가 $1/$5 per 1M (입력/출력).", ""] + tab(["항목", "호출", "USD", "출처"], rows)
    L += ["", "출처:"] + [f"- {k} `{v}`" for v, k in keys.items()]
    L += ["", "Gemini 단가는 러너가 호출마다 기록한 값(입력 $0.30, 캐시 $0.03, 출력+사고 $2.50 per 1M)의 합이다.",
          "Anthropic 금액은 토큰 기록 × 단가이며 실제 청구는 콘솔 기준이다. 고정 질의 임베딩 1회, File API 는 비용 기록 대상 아님.", ""]

    # (9) 사람 평가 E5b
    pf.sec_e5b(L, B, tab)

    # (10) 근거 필드
    L += ["## 10. 근거 필드 지표 (대상 이슈의 source_file, page_number)", "",
          "말뭉치 = gov_guide.pdf, gov_check.pdf. 결측 = null, '', 'N/A'. [12] = 프롬프트 예시값과 같은 쪽 번호 목록.",
          "제공 청크 일치 = 이슈의 (source_file, page_number 중 하나)가 그 페이지 호출에 실제로 넣은 RAG 청크 (문서, 쪽)와 같음.", ""]
    rows = []
    for rid in MAIN_RUNS:
        calls = {c["page_id"]: c for c in jl(f"{RUNS}/{rid}/calls.jsonl")}
        cnt = Counter()
        for iid, s, iss in sga.iter_run_issues(rid):
            sf, pn = iss.get("source_file"), iss.get("page_number")
            cnt["n"] += 1
            if sf in (None, "", "N/A"):
                cnt["miss"] += 1
            elif sf in ("gov_guide.pdf", "gov_check.pdf"):
                cnt[sf] += 1
            else:
                cnt["out"] += 1
            pl = pn if isinstance(pn, list) else ([pn] if pn not in (None, "") else [])
            cnt["empty_pn"] += not pl
            cnt["pn12"] += pl == [12]
            ch = ((calls.get(s["page_id"]) or {}).get("rag") or {}).get("chunks") or []
            prov = {(c.get("source"), c.get("page")) for c in ch}
            cnt["prov"] += any((sf, p) in prov for p in pl if isinstance(p, int))
        n = cnt["n"]
        rows.append([rid, n, cnt["gov_guide.pdf"], cnt["gov_check.pdf"], cnt["out"], cnt["miss"], cnt["empty_pn"],
                     cnt["pn12"], cnt["prov"], f"{cnt['prov'] / n:.3f}" if n else "-"])
    L += tab(["run", "이슈", "guide", "check", "말뭉치 밖", "결측", "쪽 빈칸", "쪽 [12]", "제공 청크 일치", "비율"], rows)
    L += src(f"{RUNS}/{{run}}/reports.jsonl", f"{RUNS}/{{run}}/calls.jsonl (rag.chunks)")
    d = rcsv(f"{R}/e8_v_definitions.csv")
    L += ["### 10.1 레거시 run2 (E8) 말뭉치 밖 인용 정의별", ""]
    L += tab(["정의", "분모", "분자", "비율"], [[r["definition"], r["denominator"], r["numerator"], r["rate"]] for r in d])
    L += src(f"{R}/e8_v_definitions.csv")

    # (11) E9 사람 평가, (12) 보조 하한, (13) 출처·대조
    pf.sec_e9_human(L, B, tab)
    res = pf.run_checks(B.checks)
    pf.sec_audit(L, B, res)
    json.dump({"unsourced": B.unsourced, "checks": res}, open(f"{R}/reports/paper_numbers_audit.json", "w",
                                                               encoding="utf-8"), ensure_ascii=False, indent=1)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    long = [i + 1 for i, l in enumerate(L) if len(l) > 100]
    from collections import Counter as C_
    print(f"{OUT}: {len(L)} lines; long {len(long)} e.g. {long[:8]}; unsourced {len(B.unsourced)}; "
          f"checks {dict(C_(r['status'] for r in res))}")


if __name__ == "__main__":
    main()
