"""
키워드 대 의미 채점 pass1: 유형별 TP·FP 페이지 수 (재채점 전 잠정 집계, API 호출 없음, 통계 검정 없음).

라벨: nominal (ground_truth.csv nominal_injected). 페이지 집합 = 각 run 의 run_meta pages.
예측: 그 페이지의 대상 이슈 중 하나라도 해당 유형이면 양성 (키워드: description 다중 라벨, 의미: pass1 ok 라벨).
실패 페이지(응답 없음)는 음성 (E7 주 분석 규칙).
잘림 처리: (i) 잘린 이슈를 음성으로 둔다 (analysis_plan 10절 1항 규칙),
           (ii) 잘린 이슈가 1건이라도 있는 페이지를 그 run 의 모든 유형 셀에서 뺀다(키워드도 같은 페이지 집합으로 다시 셈).
출력: results/revision/reports/semantic_provisional_compare.md
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import issue_table as it          # noqa: E402

SEM = "results/revision/semantic_scores"
RUNS = "results/revision/runs"
GT = "results/revision/ground_truth.csv"
OUT = "results/revision/reports/semantic_provisional_compare.md"
RUN_IDS = ["E1-R1", "E1-R2", "E1-R3b", "E2-A1-1", "E2-A1-2", "E2-A1-3", "E3-page", "E3-oracle", "E4-mobile"]
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
SHORT = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
         "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복 ID"}
MOB = "Mobile Layout Breakage"
RAG_ON, RAG_OFF = ["E1-R1", "E1-R2", "E1-R3b"], ["E2-A1-1", "E2-A1-2", "E2-A1-3"]


def src(*paths):
    return ["", "출처:"] + [f"- `{p}`" for p in paths] + [""]


def load(run):
    pages = json.load(open(f"{RUNS}/{run}/run_meta.json", encoding="utf-8"))["pages"]
    trunc = {}
    for l in open(f"{SEM}/{run}-sem-p1/grades.jsonl", encoding="utf-8"):
        r = json.loads(l)
        trunc[r["issue_id"]] = bool(r.get("truncated"))
    rows = it.build_rows(run, f"{run}-sem-p1")
    kw, sem = defaultdict(set), defaultdict(set)
    tpages = set()
    for r in rows:
        p = r["page_id"]
        for t in filter(None, r["keyword_types"].split(";")):
            kw[p].add(t)
        if r["semantic_pass1_status"] == "ok" and r["semantic_pass1"] in TYPES:
            sem[p].add(r["semantic_pass1"])
        if trunc.get(r["issue_id"]):
            tpages.add(p)
    return pages, kw, sem, tpages, rows, trunc


def counts(pages, pred, lab, t):
    tp = sum(1 for p in pages if lab[(p, t)] and t in pred[p])
    fp = sum(1 for p in pages if not lab[(p, t)] and t in pred[p])
    return tp, fp


def main():
    lab = {}
    for r in csv.DictReader(open(GT, encoding="utf-8")):
        lab[(r["page_id"], r["defect_type"])] = int(r["nominal_injected"])
    D = {run: load(run) for run in RUN_IDS}

    L = ["# 키워드 대 의미 채점 pass1: 유형별 TP·FP 페이지 수 (잠정)", "",
         "**재채점 전의 잠정 집계다.** 의미 채점의 잘림 150건(주 결과 9 run 에서는 117건)은 아직 다시 채점하지 않았다",
         "(`docs/semantic_truncation_retry_plan.md`). 재채점 후 숫자가 바뀔 수 있다.", "",
         "작성: `experiments/revision/semantic_provisional_compare.py` (API 호출 없음, 기술 집계만, 통계 검정 없음).",
         "라벨 nominal. 예측 = 그 페이지 대상 이슈 중 하나라도 해당 유형이면 양성. 실패 페이지는 음성.",
         "키워드 = description 다중 라벨. 의미 = pass1 이 성공(ok)인 이슈의 단일 라벨.",
         "잘림 처리 (i) 잘린 이슈를 음성으로 둠 (사전 규칙), (ii) 잘린 이슈가 있는 페이지를 그 run 의 모든 셀에서 뺌",
         "(키워드도 같은 페이지 집합으로 다시 셈). E3 은 용어+대조군 84페이지, E4 는 모바일+대조군 95페이지만 실행했다.", ""]

    L += ["## 1. 잘림 페이지 (별도 열)", "",
          "| run | 페이지 | 잘림 이슈 | 잘림 페이지 | 그중 대조군 | 그중 주입 페이지 |", "|---|---|---|---|---|---|"]
    for run in RUN_IDS:
        pages, kw, sem, tp_, rows, trunc = D[run]
        ctrl = [p for p in tp_ if not any(lab[(p, t)] for t in TYPES)]
        L.append(f"| {run} | {len(pages)} | {sum(trunc.values())} | {len(tp_)} | {len(ctrl)} | {len(tp_) - len(ctrl)} |")
    L += src(f"{SEM}/{{run}}-sem-p1/grades.jsonl", f"{RUNS}/{{run}}/run_meta.json", GT)

    L += ["## 2. 유형별 TP·FP 페이지 수", "",
          "열: 양성 = nominal 양성 페이지 수. 키 = 키워드, 의(i) = 의미 채점 잘림 음성 처리.",
          "잘림 양/음 = 잘린 이슈가 있는 페이지 중 그 유형 양성/음성 페이지 수.",
          "(ii) 열 = 잘림 페이지를 뺀 집합 (양성 수도 그 집합 기준).", "",
          "| run | 유형 | 양성 | 키 TP | 키 FP | 의(i) TP | 의(i) FP | 잘림 양/음 | 양성(ii) | 키 TP | 키 FP | 의 TP | 의 FP |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    csvrows = []
    for run in RUN_IDS:
        pages, kw, sem, tpg, rows, trunc = D[run]
        keep = [p for p in pages if p not in tpg]
        for t in TYPES:
            pos = sum(lab[(p, t)] for p in pages)
            k1, s1 = counts(pages, kw, lab, t), counts(pages, sem, lab, t)
            k2, s2 = counts(keep, kw, lab, t), counts(keep, sem, lab, t)
            tpos = sum(lab[(p, t)] for p in tpg)
            pos2 = sum(lab[(p, t)] for p in keep)
            L.append(f"| {run} | {SHORT[t]} | {pos} | {k1[0]} | {k1[1]} | {s1[0]} | {s1[1]} | {tpos}/{len(tpg) - tpos} | "
                     f"{pos2} | {k2[0]} | {k2[1]} | {s2[0]} | {s2[1]} |")
            csvrows.append((run, t, k1, s1, k2, s2))
    L += src(f"{RUNS}/{{run}}/reports.jsonl", f"{SEM}/{{run}}-sem-p1/grades.jsonl", GT, "scoring/issue_table.py")

    # 3. 모바일 FP: RAG 켬 대 끔
    L += ["## 3. 모바일 FP: RAG 켬(E1) 대 RAG 끔(E2-A1), 키워드와 의미 채점", "",
          "E1-R1~R3b = RAG 켬(고정 질의), E2-A1-1~3 = RAG 끔. 200페이지, 모바일 nominal 양성 페이지 수는 같다.", "",
          "| run | RAG | 키 FP | 의(i) FP | 의(ii) FP | 키 TP | 의(i) TP |", "|---|---|---|---|---|---|---|"]
    agg = defaultdict(list)
    for run in RAG_ON + RAG_OFF:
        r = [x for x in csvrows if x[0] == run and x[1] == MOB][0]
        g = "켬" if run in RAG_ON else "끔"
        L.append(f"| {run} | {g} | {r[2][1]} | {r[3][1]} | {r[5][1]} | {r[2][0]} | {r[3][0]} |")
        for k, v in (("kfp", r[2][1]), ("sfp", r[3][1]), ("sfp2", r[5][1]), ("ktp", r[2][0]), ("stp", r[3][0])):
            agg[(g, k)].append(v)
    m = lambda g, k: sum(agg[(g, k)]) / 3
    L += ["", "| 3회 평균 | 키 FP | 의(i) FP | 의(ii) FP | 키 TP | 의(i) TP |", "|---|---|---|---|---|---|"]
    for g in ("켬", "끔"):
        L.append(f"| RAG {g} | {m(g, 'kfp'):.1f} | {m(g, 'sfp'):.1f} | {m(g, 'sfp2'):.1f} | {m(g, 'ktp'):.1f} | {m(g, 'stp'):.1f} |")
    L.append(f"| 차이 (끔 - 켬) | {m('끔', 'kfp') - m('켬', 'kfp'):+.1f} | {m('끔', 'sfp') - m('켬', 'sfp'):+.1f} | "
             f"{m('끔', 'sfp2') - m('켬', 'sfp2'):+.1f} | {m('끔', 'ktp') - m('켬', 'ktp'):+.1f} | "
             f"{m('끔', 'stp') - m('켬', 'stp'):+.1f} |")
    L += ["", "의(ii) 는 잘림 페이지를 뺀 집합이라 run 마다 페이지 수가 다르다(1절)."]
    L += src(f"{RUNS}/{{run}}/reports.jsonl", f"{SEM}/{{run}}-sem-p1/grades.jsonl", GT)

    # 3b. 키워드만 모바일 양성인 이슈: 의미 채점 라벨과 키워드 구문
    phrases = ["레이아웃이 깨", "레이아웃 깨짐", "가로 스크롤", "viewport", "모바일 화면", "반응형", "overflow"]
    L += ["### 3a. 키워드에만 모바일 양성인 이슈: 의미 채점 라벨과 걸린 구문", "",
          "| run | RAG | 키워드만 모바일 이슈 | 의미 None | 의미 다른 유형 | 의미 비성공 | 'viewport' 포함 |",
          "|---|---|---|---|---|---|---|"]
    tot = Counter()
    from scoring import semantic_grader_anthropic as g   # noqa: E402
    for run in RAG_ON + RAG_OFF:
        pages, kw, sem, tpg, rows, trunc = D[run]
        desc = {iid: (iss.get("description") or "") for iid, _, iss in g.iter_run_issues(run)}
        only = [r for r in rows if MOB in r["keyword_types"].split(";")
                and not (r["semantic_pass1_status"] == "ok" and r["semantic_pass1"] == MOB)]
        c = Counter()
        for r in only:
            if r["semantic_pass1_status"] != "ok":
                c["nonok"] += 1
            elif r["semantic_pass1"] == "None":
                c["none"] += 1
            else:
                c["other"] += 1
                tot["lab:" + r["semantic_pass1"]] += 1
            c["vp"] += "viewport" in desc[r["issue_id"]].lower()
        L.append(f"| {run} | {'켬' if run in RAG_ON else '끔'} | {len(only)} | {c['none']} | {c['other']} | {c['nonok']} | {c['vp']} |")
        for k in ("none", "other", "nonok", "vp"):
            tot[k] += c[k]
        tot["n"] += len(only)
        for ph in phrases:
            tot["ph:" + ph] += sum(ph.lower() in desc[r["issue_id"]].lower() for r in only)
    L.append(f"| 합계 | | {tot['n']} | {tot['none']} | {tot['other']} | {tot['nonok']} | {tot['vp']} |")
    L += ["", "의미 '다른 유형' 내역(합계): " + ", ".join(
              f"{SHORT[t]} {tot['lab:' + t]}" for t in TYPES if tot["lab:" + t]) + ".",
          "키워드 모바일 구문별 건수(합계, 한 이슈에 여러 구문 가능):",
          ", ".join(f"'{ph}' {tot['ph:' + ph]}" for ph in phrases) + ".",
          "JUDGE_PROMPT v1 은 'viewport meta 태그가 없다는 지적 자체는 모바일에 포함하지 않는다'고 정의한다.", ""]
    L += src(f"{RUNS}/{{run}}/reports.jsonl", f"{SEM}/{{run}}-sem-p1/grades.jsonl",
             "experiments/semantic_issue_classifier.py")
    L += ["### 3b. 요약 (기술 집계, 해석·검정 아님)", "",
          f"- 키워드 기준 모바일 FP 페이지는 RAG 끔이 켬보다 3회 평균 {m('끔', 'kfp') - m('켬', 'kfp'):+.1f} 많다.",
          f"- 의미 채점 pass1 기준으로는 그 차이가 (i) {m('끔', 'sfp') - m('켬', 'sfp'):+.1f}, "
          f"(ii) {m('끔', 'sfp2') - m('켬', 'sfp2'):+.1f} 페이지다.",
          f"  키워드에만 모바일 양성인 이슈(6 run 합계 {tot['n']}건, 이슈 단위)는 의미 채점에서 버튼 "
          f"{tot['lab:Button Area Clipping']}건, None {tot['none']}건을 받았다(3a).",
          "  RAG 끔에서 늘어난 키워드만 이슈는 주로 'viewport' 언급(None)이다(3a 의 run 별 열).",
          "- 모바일 TP 는 두 채점기, 두 조건 모두 56/56 이다.",
          "- 잘린 이슈 중 키워드 모바일 양성은 없으므로(잘림 보고서 d1) 모바일 비교는 잘림 처리 방식의 영향을",
          "  (ii) 의 페이지 집합 변화로만 받는다.", ""]

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    long = [i + 1 for i, l in enumerate(L) if len(l) > 100]
    print(f"{OUT}: {len(L)} lines; long {long[:10]}")


if __name__ == "__main__":
    main()
