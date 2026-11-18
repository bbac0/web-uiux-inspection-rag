"""
의미 채점 잘림(stop_reason max_tokens) 분석 (API 호출 없음, 통계 검정 없음).

읽기: results/revision/semantic_scores/*-sem-*/grades.jsonl (읽기만), results/revision/runs/{run}/reports.jsonl,
      results/revision/ground_truth.csv (nominal_injected), scoring/grader_config.json
쓰기: results/revision/reports/semantic_truncation_report.md
      results/revision/semantic_truncation_targets.csv (잘린 150건 목록: 재채점 계획의 대상, API 없음)

페이지 결함 유형 = ground_truth.csv 에서 nominal_injected=1 인 유형(한 페이지에 2개일 수 있음 → 두 유형 모두에 센다).
주입 유형이 없는 페이지 = 대조군.
"""
import csv
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import semantic_grader_anthropic as g     # noqa: E402
from scoring import issue_table as it                  # noqa: E402

SEM = "results/revision/semantic_scores"
OUT = "results/revision/reports/semantic_truncation_report.md"
TARGETS = "results/revision/semantic_truncation_targets.csv"
GT = "results/revision/ground_truth.csv"
OUT_IDS = ["E1-R1-sem-p1", "E1-R1-sem-p2", "E1-R1-sem-desc-p1", "E1-R2-sem-p1", "E1-R3b-sem-p1", "E2-A1-1-sem-p1",
           "E2-A1-2-sem-p1", "E2-A1-3-sem-p1", "E3-page-sem-p1", "E3-oracle-sem-p1", "E4-mobile-sem-p1"]
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
SHORT = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
         "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복 ID", "control": "대조군"}
TERM = "Standard Terminology Violation"


def src(*paths):
    return ["", "출처:"] + [f"- `{p}`" for p in paths] + [""]


def q(xs):
    xs = sorted(xs)
    if not xs:
        return "-"
    k = lambda p: xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]
    return f"{xs[0]} / {k(.25)} / {k(.5)} / {k(.75)} / {xs[-1]} (평균 {st.mean(xs):.1f})"


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "-"


def main():
    page_types = defaultdict(set)
    for r in csv.DictReader(open(GT, encoding="utf-8")):
        if r["nominal_injected"] == "1":
            page_types[r["page_id"]].add(r["defect_type"])
    cfg = g.load_config(g.CONFIG_PATH)

    recs, info = [], {}
    for o in OUT_IDS:
        meta = json.load(open(f"{SEM}/{o}/summary.json", encoding="utf-8"))
        run, fields = meta["source_run"], meta["input_fields"]
        c = dict(cfg, input_fields=fields)
        texts = {iid: g.build_input(iss, c) for iid, _, iss in g.iter_run_issues(run)}
        tab = {r["issue_id"]: r for r in it.build_rows(run)}
        for l in open(f"{SEM}/{o}/grades.jsonl", encoding="utf-8"):
            r = json.loads(l)
            pid = r["source"]["page_id"]
            groups = sorted(page_types[pid]) or ["control"]
            recs.append({"out_id": o, "run": run, "pass": r["pass"], "issue_id": r["issue_id"], "page_id": pid,
                         "groups": groups, "trunc": bool(r.get("truncated")), "status": r["status"],
                         "in_tok": r.get("input_tokens") or 0, "out_tok": r.get("output_tokens") or 0,
                         "chars": len(texts[r["issue_id"]]), "raw": r.get("raw_response") or "",
                         "lip": r.get("label_if_parsed"), "kw": tab[r["issue_id"]]["keyword_types"],
                         "sm": tab[r["issue_id"]]["string_match_term"], "fields": "+".join(fields)})
        info[o] = run
    T = [r for r in recs if r["trunc"]]
    N = [r for r in recs if not r["trunc"]]

    # 대상 목록 (재채점 계획용)
    with open(TARGETS, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["out_id", "retry_out_id", "source_run", "pass", "input_fields", "issue_id", "orig_input_tokens"])
        for r in T:
            w.writerow([r["out_id"], r["out_id"] + "-retry", r["run"], r["pass"], r["fields"], r["issue_id"], r["in_tok"]])

    L = ["# 의미 채점 잘림 150건 분석", "",
         "작성: `experiments/revision/semantic_truncation_report.py` (API 호출 없음, 기술 집계만, 통계 검정 없음).",
         "대상: 의미 채점 11개 out_id (확인용 batch-check-E1-R1 1건 제외). 잘림 = stop_reason max_tokens.",
         "페이지 결함 유형 = ground_truth.csv 의 nominal_injected=1 유형. 한 페이지에 주입 유형이 2개면",
         "두 유형 모두에 센다(행 합계가 이슈 수보다 클 수 있음). 주입 유형이 없는 페이지 = 대조군.", "",
         f"잘림 {len(T)}건 / 전체 {len(recs)}건 ({pct(len(T), len(recs))}).", ""]

    # (a)
    L += ["## (a) 잘림 건수와 비율", "", "### (a1) out_id 별", "",
          "| out_id | 원 run | pass | 입력 | 이슈 | 잘림 | 비율 |", "|---|---|---|---|---|---|---|"]
    for o in OUT_IDS:
        rr = [r for r in recs if r["out_id"] == o]
        t = sum(r["trunc"] for r in rr)
        L.append(f"| {o} | {info[o]} | {rr[0]['pass']} | {rr[0]['fields']} | {len(rr)} | {t} | {pct(t, len(rr))} |")
    L += src(f"{SEM}/{{out_id}}/grades.jsonl")
    L += ["### (a2) 원 run 별 (주 결과 pass1, description+suggestion 만)", "",
          "| 원 run | 이슈 | 잘림 | 비율 |", "|---|---|---|---|"]
    main_recs = [r for r in recs if r["pass"] == 1 and r["fields"] == "description+suggestion"]
    for run in dict.fromkeys(r["run"] for r in main_recs):
        rr = [r for r in main_recs if r["run"] == run]
        t = sum(r["trunc"] for r in rr)
        L.append(f"| {run} | {len(rr)} | {t} | {pct(t, len(rr))} |")
    t = sum(r["trunc"] for r in main_recs)
    L.append(f"| 합계 (9 run) | {len(main_recs)} | {t} | {pct(t, len(main_recs))} |")
    L += ["", "E1-R1 pass2 와 description-only 는 (a1) 에만 있다."]
    L += src(f"{SEM}/{{run}}-sem-p1/grades.jsonl")
    L += ["### (a3) 페이지 결함 유형 별 (11개 out_id 전체)", "",
          "| 페이지 결함 유형 | 이슈 | 잘림 | 비율 | 주 결과 9 run 이슈 | 잘림 | 비율 |", "|---|---|---|---|---|---|---|"]
    for gname in TYPES + ["control"]:
        rr = [r for r in recs if gname in r["groups"]]
        mm = [r for r in main_recs if gname in r["groups"]]
        a, b = sum(r["trunc"] for r in rr), sum(r["trunc"] for r in mm)
        L.append(f"| {SHORT[gname]} | {len(rr)} | {a} | {pct(a, len(rr))} | {len(mm)} | {b} | {pct(b, len(mm))} |")
    L += src(f"{SEM}/{{out_id}}/grades.jsonl", GT)
    L += ["### (a4) 원 run × 페이지 결함 유형 (주 결과 9 run, 잘림/이슈)", "",
          "| 원 run | 대비 | 모바일 | 버튼 | 용어 | 중복 ID | 대조군 |", "|---|---|---|---|---|---|---|"]
    for run in dict.fromkeys(r["run"] for r in main_recs):
        cells = []
        for gname in TYPES + ["control"]:
            rr = [r for r in main_recs if r["run"] == run and gname in r["groups"]]
            cells.append(f"{sum(r['trunc'] for r in rr)}/{len(rr)}")
        L.append(f"| {run} | " + " | ".join(cells) + " |")
    L += src(f"{SEM}/{{run}}-sem-p1/grades.jsonl", GT)

    # (b)
    L += ["## (b) 잘린 응답의 내용과 출력 토큰", "",
          f"출력 토큰: 잘림 {len(T)}건 모두 {sorted(Counter(r['out_tok'] for r in T).items())} (max_tokens 100).",
          f"성공 {sum(r['status'] == 'ok' for r in N)}건의 출력 토큰 최소/사분위/최대: "
          f"{q([r['out_tok'] for r in N if r['status'] == 'ok'])}.", ""]
    starts = Counter()
    for r in T:
        s = r["raw"].lstrip()
        starts["JSON 으로 시작 ({)" if s.startswith("{") else "``` 로 시작" if s.startswith("```") else "설명 문장으로 시작"] += 1
    with_json = sum('{"label"' in r["raw"].replace(" ", "") or "{\"label\"" in r["raw"] for r in T)
    L += ["| 잘린 응답의 시작 형태 | 건수 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in starts.most_common()]
    L += ["", f"잘린 응답 중 '{{\"label\"' 문자열이 들어 있는 건: {with_json}.",
          f"잘린 응답 길이(문자) 최소/사분위/최대: {q([len(r['raw']) for r in T])}.",
          "label_if_parsed (잘린 문장에서 유형 이름이 언급된 경우 채점기가 남긴 참고값, 라벨로 쓰지 않음):",
          ", ".join(f"{k or '없음'} {v}" for k, v in Counter(r["lip"] for r in T).most_common()) + "."]
    L += src(f"{SEM}/{{out_id}}/grades.jsonl")
    L += ["### (b2) 잘린 응답 앞 200자 (전체 150건)", "",
          "줄바꿈·파이프는 공백·'/'로 바꾸고, 표 대신 목록으로 적었다(줄 길이 제한).", ""]
    for r in T:
        txt = r["raw"][:200].replace("\n", " ").replace("|", "/")
        L.append(f"- `{r['out_id']}` `{r['issue_id']}` (out {r['out_tok']}):")
        while txt:
            L.append("  " + txt[:45]); txt = txt[45:]
    L += src(f"{SEM}/{{out_id}}/grades.jsonl")

    # (c)
    L += ["## (c) 입력 토큰과 입력 길이", "",
          "입력 토큰 = grades.jsonl input_tokens (프롬프트 포함).",
          "입력 문자 = 채점기 입력 문구(description[+suggestion]) 길이.", "",
          "| 집합 | 건수 | 입력 토큰 최소/25/50/75/최대 (평균) |", "|---|---|---|",
          f"| 잘림 | {len(T)} | {q([r['in_tok'] for r in T])} |",
          f"| 잘리지 않음 | {len(N)} | {q([r['in_tok'] for r in N])} |", "",
          "| 집합 | 입력 문자 최소/25/50/75/최대 (평균) |", "|---|---|",
          f"| 잘림 | {q([r['chars'] for r in T])} |", f"| 잘리지 않음 | {q([r['chars'] for r in N])} |"]
    L += src(f"{SEM}/{{out_id}}/grades.jsonl", "results/revision/runs/{run}/reports.jsonl")
    allin = sorted(r["in_tok"] for r in recs)
    cuts = [allin[int(len(allin) * k / 4)] for k in (1, 2, 3)]
    bins = Counter(); tb = Counter()
    for r in recs:
        b = sum(r["in_tok"] >= c for c in cuts)
        bins[b] += 1; tb[b] += r["trunc"]
    L += ["### (c2) 입력 토큰 사분위 구간별 잘림 (전체 11 out_id 기준 구간)", "",
          "| 구간 | 경계 | 이슈 | 잘림 | 비율 |", "|---|---|---|---|---|"]
    edges = [allin[0]] + cuts + [allin[-1]]
    for b in range(4):
        L.append(f"| Q{b + 1} | {edges[b]}~{edges[b + 1]} | {bins[b]} | {tb[b]} | {pct(tb[b], bins[b])} |")
    L += src(f"{SEM}/{{out_id}}/grades.jsonl")

    # (d)
    L += ["## (d) 잘림이 몰린 곳", "",
          "### (d1) 채점기 입력 문구의 키워드·string_match 판정별 잘림 (11 out_id)", "",
          "| 이슈 묶음 | 이슈 | 잘림 | 비율 |", "|---|---|---|---|"]
    def grp(r):
        if r["sm"]:
            return "string_match 1 ('접속하기' 포함)"
        if TERM in r["kw"].split(";"):
            return "키워드 용어 (string_match 0)"
        return "키워드 " + (SHORT.get(r["kw"].split(";")[0], "-") if r["kw"] else "없음") + \
               (" 외" if ";" in r["kw"] else "")
    gc, gt = Counter(), Counter()
    for r in recs:
        k = grp(r); gc[k] += 1; gt[k] += r["trunc"]
    for k in sorted(gc, key=lambda k: -gt[k]):
        L.append(f"| {k} | {gc[k]} | {gt[k]} | {pct(gt[k], gc[k])} |")
    L += ["", "키워드 열의 '외' 는 키워드 다중 라벨 중 첫 유형만 이름으로 쓴 것."]
    L += src(f"{SEM}/{{out_id}}/grades.jsonl", "scoring/issue_table.py")
    pages = Counter(r["page_id"] for r in T)
    L += ["### (d2) 같은 이슈가 여러 채점에서 잘렸는가 (E1-R1 의 3개 out_id)", ""]
    r1 = defaultdict(set)
    for r in T:
        if r["run"] == "E1-R1":
            r1[r["issue_id"]].add(r["out_id"])
    cnt = Counter(len(v) for v in r1.values())
    L += [f"E1-R1 잘림 이슈(중복 제거) {len(r1)}건: " + ", ".join(f"{k}개 out_id 에서 잘림 {v}건" for k, v in sorted(cnt.items())),
          f"잘림이 나온 페이지 {len(pages)}개 (전체 out_id 합). 한 페이지에서 가장 많이 잘린 건수:",
          ", ".join(f"{p} {n}" for p, n in pages.most_common(5)) + "."]
    L += src(f"{SEM}/E1-R1-sem-p1/grades.jsonl", f"{SEM}/E1-R1-sem-p2/grades.jsonl", f"{SEM}/E1-R1-sem-desc-p1/grades.jsonl")

    # (e)
    L += ["## (e) 통합 표에서 비성공 건의 처리", "",
          "- `scoring/issue_table.py`(동결): 비성공 건은 `semantic_pass1` 이 빈 칸,",
          "  `semantic_pass1_status` 가 `parse_error` (잘림도 parse_error 로 기록됨; 잘림 여부는",
          "  grades.jsonl 의 truncated 로만 구분). 키워드·string_match 열은 의미 채점 상태와 무관하게 채워진다.",
          "- `semantic_scoring_report.md` 6절: 비성공 건은 어느 유형으로도 세지 않았다(analysis_plan 10절 1항",
          "  \"셀 예측에서는 해당 유형으로 세지 않는다\"). 따라서 키워드 양성인 잘림 이슈(모두 용어 유형)는",
          "  6절 용어 행의 '키워드만' 칸, 6a 의 101 칸에 들어갔다.",
          "- 4·5절(일치율, kappa)은 비성공을 별도 범주로 둔 경우와 제외한 경우를 함께 적었다.",
          f"- 주 결과 9 run 의 잘림 {sum(r['trunc'] for r in main_recs)}건 중 키워드 양성(어느 유형이든) "
          f"{sum(bool(r['kw']) for r in main_recs if r['trunc'])}건, string_match 1 "
          f"{sum(r['sm'] for r in main_recs if r['trunc'])}건."]
    L += src("scoring/issue_table.py", "results/revision/reports/semantic_scoring_report.md", "results/revision/analysis_plan.md")

    # 근거
    sm_t, sm_n = sum(r["sm"] for r in T), sum(r["sm"] for r in recs)
    L += ["## 원인에 대한 근거 (max_tokens=100 부족인가)", "",
          f"1. 잘린 {len(T)}건 모두 출력 토큰이 정확히 100 이고 stop_reason 이 max_tokens 다. 성공 건의 출력은 최대 "
          f"{max(r['out_tok'] for r in N if r['status'] == 'ok')} 토큰이다.",
          f"2. 잘린 응답은 {starts.get('설명 문장으로 시작', 0)}건이 JSON 이 아니라 설명 문장으로 시작한다. 성공 건은 JSON 만 낸다.",
          "   즉 모델이 JSON 앞에 판단 근거를 글로 쓰기 시작한 경우에 100 토큰 안에 JSON 에 닿지 못했다.",
          "   (출력 토큰에 thinking 블록이 포함되는지는 기록으로 구분할 수 없다. raw_response 는 text 블록만이다.)",
          f"3. 내용에 몰려 있다: 잘림 {len(T)}건 중 키워드 사전에 걸린 것은 '접속하기'(용어) 이슈뿐이고 다른 4유형",
          "   키워드에 걸린 이슈는 0건이다.",
          f"   string_match 1 이슈는 {sm_n}건 중 {sm_t}건({pct(sm_t, sm_n)})이 잘렸다((d1)). 페이지 유형으로는 대비 페이지가",
          "   가장 높다((a3)). (b2) 문장을 보면 '!important 남용' 처럼 대비 색상과 다른 지적이 겹친 설명,",
          "   '접속하기' 처럼 용어 지적인지 일반 준수 미흡인지 모호한 설명에서 모델이 근거를 먼저 쓴다.",
          "4. 길이와의 관계는 약하다: 잘림 건의 입력 토큰 중앙값은 잘리지 않은 건보다 약 40 토큰 길고,",
          "   입력 토큰 상위 사분위의 잘림 비율이 하위보다 높다((c), (c2)). 그러나 같은 길이대에서도 키워드에 걸린",
          "   이슈는 잘리지 않았으므로 길이보다 '유형 경계가 모호한 내용'과의 관계가 더 뚜렷하다.",
          "   E1-R1 에서 같은 이슈가 3개 채점 모두에서 잘린 경우가 10건 있어 우연한 잘림만은 아니다((d2)).",
          "5. 잘림은 무작위가 아니므로, 비성공을 음성으로 두는 현재 규칙은 대비·용어 유형의 의미 채점 양성을",
          "   줄이는 쪽으로 치우칠 수 있다.",
          "6. 직접 원인은 max_tokens=100 이 '설명 후 JSON' 형식의 응답을 담기에 모자란 것으로 보인다.",
          "   잘린 문장이 92~150자(약 100 토큰)에서 끊겼고 JSON 에 닿지 않았다.",
          "   300 으로 올리면 대부분 JSON 까지 닿을 것으로 예상되나(성공 건 출력 최대 21 토큰),",
          "   이는 재채점 전의 추정이다."]
    L += src(f"{SEM}/{{out_id}}/grades.jsonl", TARGETS)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    long = [i + 1 for i, l in enumerate(L) if len(l) > 100]
    print(f"{OUT}: {len(L)} lines; targets {len(T)}; long lines {long[:10]}")


if __name__ == "__main__":
    main()
