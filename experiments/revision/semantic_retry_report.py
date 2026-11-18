"""
의미 채점 잘림 150건 재채점 결과 보고 (API 호출 없음, 통계 검정 없음). 사전 지정: analysis_plan_addendum_semantic_retry.md.
입력: results/revision/semantic_scores/{out_id}-retry/ (읽기만), 원 out_id 폴더, results/revision/runs/{run}/, ground_truth.csv
출력: results/revision/reports/semantic_retry_report.md, results/revision/issue_tables_merged/{run}.csv
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
from scoring import issue_table_merged as itm          # noqa: E402
from services import llm_wrapper as lw                 # noqa: E402

SEM = "results/revision/semantic_scores"
GT = "results/revision/ground_truth.csv"
OUT = "results/revision/reports/semantic_retry_report.md"
MERGED = "results/revision/issue_tables_merged"
OUT_IDS = ["E1-R1-sem-p1", "E1-R1-sem-p2", "E1-R1-sem-desc-p1", "E1-R2-sem-p1", "E1-R3b-sem-p1", "E2-A1-1-sem-p1",
           "E2-A1-2-sem-p1", "E2-A1-3-sem-p1", "E3-page-sem-p1", "E3-oracle-sem-p1", "E4-mobile-sem-p1"]
RUNS = ["E1-R1", "E1-R2", "E1-R3b", "E2-A1-1", "E2-A1-2", "E2-A1-3", "E3-page", "E3-oracle", "E4-mobile"]
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
SH = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
      "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복ID", "None": "None"}


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def src(*p):
    return ["", "출처:"] + [f"- `{x}`" for x in p] + [""]


def tab(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return po, ((po - pe) / (1 - pe) if pe < 1 else float("nan"))


def status_of(r):
    if r["status"] == "ok":
        return "ok"
    return "truncated" if r.get("truncated") else r["status"]


def main():
    R = {o: jl(f"{SEM}/{o}-retry/grades.jsonl") for o in OUT_IDS}
    O = {o: {r["issue_id"]: r for r in jl(f"{SEM}/{o}/grades.jsonl")} for o in OUT_IDS}
    lab = {(r["page_id"], r["defect_type"]): int(r["nominal_injected"]) for r in csv.DictReader(open(GT, encoding="utf-8"))}
    allr = [r for o in OUT_IDS for r in R[o]]
    L = ["# 의미 채점 잘림 150건 재채점 결과", "",
         "작성: `experiments/revision/semantic_retry_report.py` (API 호출 없음, 기술 집계만, 통계 검정 없음).",
         "사전 지정: `results/revision/analysis_plan_addendum_semantic_retry.md`",
         "(주 분석 = 재채점 포함, max_tokens 800, 1회). 재채점 폴더는 읽기만 했다.",
         "연구자 메시지의 '오류나 경고 [있음/없음]' 칸은 채워지지 않아 기록(batches.jsonl, grades.jsonl)으로만 확인했다.", ""]

    # (1)
    rows = []
    for o in OUT_IDS:
        m = json.load(open(f"{SEM}/{o}-retry/run_meta.json", encoding="utf-8"))
        c = Counter(status_of(r) for r in R[o])
        ev = [e["event"] for e in jl(f"{SEM}/{o}-retry/batches.jsonl")]
        locked = os.path.exists(f"{SEM}/{o}-retry/SHA256SUMS")
        ver = "OK" if locked and not lw.verify_run(f"{SEM}/{o}-retry") else "불일치"
        rows.append([o + "-retry", len(m["targets"]), len(R[o]), c["ok"], c["parse_error"], c["refusal"], c["api_error"],
                     c["truncated"], len(m["targets"]) - c["ok"], f"{'잠김' if locked else '안 잠김'} ({ver})", ", ".join(ev)])
    L += ["## 1. out_id 별 재채점 건수와 상태", ""]
    rows = [[r[0].replace("-sem-", "-").replace("-retry", "-rt")] + r[1:-1] + [r[-1].replace("submit_failed", "실패").replace("submitted", "제출").replace("collected", "회수")] for r in rows]
    L += tab(["재채점", "대상", "기록", "ok", "parse_err", "refusal", "api_err", "재잘림", "미해결", "잠금(검증)",
              "이벤트"], rows)
    L += ["", "재채점 이름: `E1-R1-p1-rt` = `E1-R1-sem-p1-retry` (표 폭 때문에 줄임)."]
    tot = Counter(status_of(r) for r in allr)
    L += ["", f"합계: 대상 150, 기록 {len(allr)}, ok {tot['ok']}, 미해결 {150 - tot['ok']}. "
          f"stop_reason: {dict(Counter(r.get('stop_reason') for r in allr))}.",
          "E1-R1-sem-p1-retry 의 submit_failed(실패)는 첫 제출의 크레딧 거부 기록이다(`retry_submit_state.md`).",
          "그 뒤 --resume 으로 제출됨."]
    L += src(f"{SEM}/{{out_id}}-retry/grades.jsonl", f"{SEM}/{{out_id}}-retry/run_meta.json", f"{SEM}/{{out_id}}-retry/batches.jsonl")

    # (2)
    L += ["## 2. 재채점 라벨", "", "### 2.1 out_id 별 라벨 분포", ""]
    labs = TYPES + ["None"]
    L += tab(["재채점 out_id"] + [SH[t] for t in labs] + ["비성공"],
             [[o + "-retry"] + [sum(r["label"] == t for r in R[o] if r["status"] == "ok") for t in labs]
              + [sum(r["status"] != "ok" for r in R[o])] for o in OUT_IDS] +
             [["합계"] + [sum(r["label"] == t for r in allr if r["status"] == "ok") for t in labs]
              + [sum(r["status"] != "ok" for r in allr)]])
    L += src(f"{SEM}/{{out_id}}-retry/grades.jsonl")
    # 원 응답의 label_if_parsed, 키워드·string_match, 페이지 주입 유형 대비
    tabs = {}
    for o in OUT_IDS:
        run = json.load(open(f"{SEM}/{o}/summary.json", encoding="utf-8"))["source_run"]
        if run not in tabs:
            tabs[run] = {r["issue_id"]: r for r in itm.it.build_rows(run)}
    cross_lip, cross_kw, cross_pg = Counter(), Counter(), Counter()
    for o in OUT_IDS:
        run = json.load(open(f"{SEM}/{o}/summary.json", encoding="utf-8"))["source_run"]
        for r in R[o]:
            new = r["label"] if r["status"] == "ok" else "비성공"
            orig = O[o][r["issue_id"]]
            cross_lip[(orig.get("label_if_parsed") or "(없음)", new)] += 1
            t = tabs[run][r["issue_id"]]
            k = "sm=1(접속하기)" if t["string_match_term"] else (t["keyword_types"] or "(키워드 없음)")
            cross_kw[(k, new)] += 1
            pg = r["source"]["page_id"]
            for g in ([x for x in TYPES if lab[(pg, x)]] or ["대조군"]):
                cross_pg[(g, new)] += 1
    L += ["### 2.2 원래 잘린 응답의 참고값(label_if_parsed) → 재채점 라벨", "",
          "label_if_parsed = 잘린 문장에서 유형 이름이 언급되어 원 채점기가 남긴 참고값(라벨로 쓰지 않았음).", ""]
    L += tab(["원 참고값", "재채점 라벨", "건수"], [[SH.get(a, a), SH.get(b, b), n] for (a, b), n in sorted(cross_lip.items(), key=lambda x: -x[1])])
    L += src(f"{SEM}/{{out_id}}/grades.jsonl", f"{SEM}/{{out_id}}-retry/grades.jsonl")
    L += ["### 2.3 키워드·string_match 판정 → 재채점 라벨", ""]
    L += tab(["키워드 / string_match", "재채점 라벨", "건수"],
             [[";".join(SH.get(x, x) for x in a.split(";")), SH.get(b, b), n] for (a, b), n in sorted(cross_kw.items(), key=lambda x: -x[1])])
    L += src("scoring/issue_table.py", f"{SEM}/{{out_id}}-retry/grades.jsonl")
    L += ["### 2.4 이슈가 속한 페이지의 주입 유형 → 재채점 라벨 (주입 유형 2개면 둘 다 셈)", ""]
    L += tab(["페이지 주입 유형", "재채점 라벨", "건수"],
             [[SH.get(a, a), SH.get(b, b), n] for (a, b), n in sorted(cross_pg.items(), key=lambda x: (x[0][0], -x[1]))])
    L += src(GT, f"{SEM}/{{out_id}}-retry/grades.jsonl")

    # (3)
    rows = []
    ti = to = 0
    for o in OUT_IDS:
        i_ = sum(r["input_tokens"] or 0 for r in R[o]); o_ = sum(r["output_tokens"] or 0 for r in R[o])
        ti += i_; to += o_
        rows.append([o + "-retry", len(R[o]), i_, o_, max(r["output_tokens"] or 0 for r in R[o]), f"{(i_ + 5 * o_) / 1e6:.4f}"])
    rows.append(["합계", len(allr), ti, to, max(r["output_tokens"] or 0 for r in allr), f"{(ti + 5 * to) / 1e6:.4f}"])
    outs = sorted(r["output_tokens"] for r in allr)
    L += ["## 3. 비용 (배치 단가 입력 $1/1M, 출력 $5/1M)", ""]
    L += tab(["재채점 out_id", "건", "입력 토큰", "출력 토큰", "최대 출력", "USD"], rows)
    L += ["", f"출력 토큰 최소/중앙/최대: {outs[0]} / {st.median(outs)} / {outs[-1]} (max_tokens 800)."]
    L += src(f"{SEM}/{{out_id}}-retry/grades.jsonl")

    # (4)
    rows = []
    for o in OUT_IDS:
        for e in jl(f"{SEM}/{o}-retry/batches.jsonl"):
            if e["event"] in ("submitted", "collected"):
                rows.append([o + "-retry", e["event"], e["batch_id"][-8:], e["ts_utc"][:19]])
    L += ["## 4. 모델 버전과 호출 날짜", "",
          f"응답 model 문자열: {', '.join(sorted({r.get('model_version') or '?' for r in allr}))} (모든 레코드), "
          f"요청 max_tokens: {sorted({r.get('max_tokens') for r in allr})}.", ""]
    L += tab(["재채점 out_id", "이벤트", "batch_id 끝 8자", "시각 (UTC)"], rows)
    L += src(f"{SEM}/{{out_id}}-retry/batches.jsonl", f"{SEM}/{{out_id}}-retry/grades.jsonl")

    # (5) 병합 표
    os.makedirs(MERGED, exist_ok=True)
    merged = {}
    rows = []
    for run in RUNS:
        mr = itm.build_rows(run, f"{run}-sem-p1")
        merged[run] = mr
        with open(f"{MERGED}/{run}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=itm.COLUMNS); w.writeheader(); w.writerows(mr)
        filled = [r for r in mr if r["semantic_pass1_filled_by_retry"]]
        c = Counter(r["semantic_pass1_merged"] for r in filled)
        rows.append([run, len(mr), len(filled)] + [c[t] for t in TYPES] + [c["None"],
                    sum(r["semantic_pass1_source"] == "unresolved" for r in mr)])
    L += ["## 5. 병합 통합 표: 재채점으로 채운 건수 (pass1, 유형별)", "",
          f"`scoring/issue_table_merged.py` 로 run 별 CSV 를 `{MERGED}/{{run}}.csv` 에 썼다.", ""]
    L += tab(["run", "이슈", "재채점으로 채움"] + [SH[t] for t in TYPES] + ["None", "미해결"], rows)
    L += src(f"{MERGED}/{{run}}.csv", "scoring/issue_table_merged.py")

    # (6) 세 기준
    L += ["## 6. 유형별 TP / FP 페이지 수: 재채점 포함(주), 원 규칙(잘림 = 음성), 잘림 페이지 제외", "",
          "라벨 nominal, 페이지 = run_meta pages, 실패 페이지 음성. 잘림 페이지 제외 = 원 채점에서 잘린 이슈가 있는 페이지를",
          "그 run 의 모든 셀에서 뺌(양성 수도 그 집합 기준).", ""]
    rows = []
    for run in RUNS:
        pages = json.load(open(f"results/revision/runs/{run}/run_meta.json", encoding="utf-8"))["pages"]
        P = {k: defaultdict(set) for k in ("m", "o")}
        tp_pages = set()
        for r in merged[run]:
            p = r["page_id"]
            if r["semantic_pass1_merged"] in TYPES:
                P["m"][p].add(r["semantic_pass1_merged"])
            if r["semantic_pass1_status"] == "ok" and r["semantic_pass1"] in TYPES:
                P["o"][p].add(r["semantic_pass1"])
            if r["semantic_pass1_status"] != "ok":
                tp_pages.add(p)
        keep = [p for p in pages if p not in tp_pages]
        for t in TYPES:
            f = lambda pp, k: (sum(1 for p in pp if lab[(p, t)] and t in P[k][p]), sum(1 for p in pp if not lab[(p, t)] and t in P[k][p]))
            a, b, c = f(pages, "m"), f(pages, "o"), f(keep, "o")
            rows.append([run, SH[t], sum(lab[(p, t)] for p in pages), f"{a[0]} / {a[1]}", f"{b[0]} / {b[1]}",
                         sum(lab[(p, t)] for p in keep), f"{c[0]} / {c[1]}"])
    L += tab(["run", "유형", "양성", "재채점 포함 TP/FP (주)", "원 규칙 TP/FP", "양성(제외 후)", "잘림 제외 TP/FP"], rows)
    L += src("results/revision/runs/{run}/run_meta.json", GT, f"{MERGED}/{{run}}.csv")

    # (7)
    def merged_labels(o):
        rmap = {r["issue_id"]: r for r in R[o]}
        out = {}
        for iid, r in O[o].items():
            if r["status"] == "ok":
                out[iid] = r["label"]
            elif iid in rmap and rmap[iid]["status"] == "ok":
                out[iid] = rmap[iid]["label"]
            else:
                out[iid] = status_of(r if iid not in rmap else rmap[iid])
        return out
    orig = {o: {i: (r["label"] if r["status"] == "ok" else status_of(r)) for i, r in O[o].items()} for o in OUT_IDS}
    mer = {o: merged_labels(o) for o in ("E1-R1-sem-p1", "E1-R1-sem-p2", "E1-R1-sem-desc-p1")}
    rows = []
    for name, x, y in (("pass1 대 pass2", "E1-R1-sem-p1", "E1-R1-sem-p2"), ("pass1 대 description-only", "E1-R1-sem-p1", "E1-R1-sem-desc-p1")):
        for basis, D in (("원 기준", orig), ("재채점 포함", mer)):
            ids = sorted(set(D[x]) & set(D[y]))
            a, b = [D[x][i] for i in ids], [D[y][i] for i in ids]
            po, k = kappa(a, b)
            ok_ids = [i for i in ids if D[x][i] in TYPES + ["None"] and D[y][i] in TYPES + ["None"]]
            po2, k2 = kappa([D[x][i] for i in ok_ids], [D[y][i] for i in ok_ids])
            rows.append([name, basis, len(ids), f"{po:.3f}", f"{k:.3f}", len(ok_ids), f"{po2:.3f}", f"{k2:.3f}"])
    L += ["## 7. E1-R1 pass1 대 pass2, pass1 대 description-only", "",
          "포함 = 비성공(잘림 등)을 별도 범주로 둠, 제외 = 두 쪽 모두 6분류 라벨이 있는 이슈만. Cohen's kappa 는 기술 지표(검정 아님).", ""]
    L += tab(["비교", "기준", "이슈(포함)", "일치율", "kappa", "이슈(제외)", "일치율", "kappa"], rows)
    dis = Counter((mer["E1-R1-sem-p1"][i], mer["E1-R1-sem-p2"][i]) for i in mer["E1-R1-sem-p1"]
                  if mer["E1-R1-sem-p1"][i] != mer["E1-R1-sem-p2"][i])
    dis2 = Counter((mer["E1-R1-sem-p1"][i], mer["E1-R1-sem-desc-p1"][i]) for i in mer["E1-R1-sem-p1"]
                   if mer["E1-R1-sem-p1"][i] != mer["E1-R1-sem-desc-p1"][i])
    L += ["", "재채점 포함 기준 불일치 쌍:", ""]
    L += tab(["비교", "pass1", "상대", "건수"], [["pass2", SH.get(a, a), SH.get(b, b), n] for (a, b), n in dis.most_common()]
             + [["desc-only", SH.get(a, a), SH.get(b, b), n] for (a, b), n in dis2.most_common()])
    L += src(f"{SEM}/E1-R1-sem-p1/grades.jsonl", f"{SEM}/E1-R1-sem-p2/grades.jsonl", f"{SEM}/E1-R1-sem-desc-p1/grades.jsonl",
             f"{SEM}/{{위 3개}}-retry/grades.jsonl")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print(OUT, "long:", [i + 1 for i, l in enumerate(L) if len(l) > 100])


if __name__ == "__main__":
    main()
