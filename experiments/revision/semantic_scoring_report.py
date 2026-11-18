"""
의미 채점(Anthropic batch) 회수 결과 기술 집계 보고서 (API 호출 없음, 통계 검정 없음).

읽는 것: results/revision/semantic_scores/{out_id}/grades.jsonl, batches.jsonl, summary.json (읽기만 한다)
         results/revision/runs/{run_id}/reports.jsonl (이슈 단위 통합 표, scoring/issue_table.py 재사용)
쓰는 것: results/revision/reports/semantic_scoring_report.md

상태 분류: 성공 = status ok; 잘림 = truncated(stop_reason max_tokens, status parse_error);
           파싱 실패 = status parse_error 이면서 잘림이 아닌 것; refusal; api_error.
비용: 배치 단가 입력 $1/1M, 출력 $5/1M (연구자 지정) × grades.jsonl 의 토큰.
유형별 일치(6항): 의미 채점 pass1 이 ok 가 아니면(잘림 등) 그 이슈는 어느 유형으로도 세지 않는다(analysis_plan 1항).
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from scoring import issue_table as it          # noqa: E402

SEM = "results/revision/semantic_scores"
OUT = "results/revision/reports/semantic_scoring_report.md"
PIN, POUT = 1.0, 5.0
TYPES = ["Poor Contrast Ratio", "Mobile Layout Breakage", "Button Area Clipping",
         "Standard Terminology Violation", "Duplicate ID Markup Error"]
SHORT = {"Poor Contrast Ratio": "대비", "Mobile Layout Breakage": "모바일", "Button Area Clipping": "버튼",
         "Standard Terminology Violation": "용어", "Duplicate ID Markup Error": "중복 ID"}
PASS1 = ["E1-R1-sem-p1", "E1-R2-sem-p1", "E1-R3b-sem-p1", "E2-A1-1-sem-p1", "E2-A1-2-sem-p1",
         "E2-A1-3-sem-p1", "E3-page-sem-p1", "E3-oracle-sem-p1", "E4-mobile-sem-p1"]


def grades(out_id):
    return [json.loads(l) for l in open(f"{SEM}/{out_id}/grades.jsonl", encoding="utf-8")]


def cat(r):
    if r["status"] == "ok":
        return "ok"
    if r.get("truncated") or r.get("stop_reason") == "max_tokens":
        return "truncated"
    return r["status"]          # parse_error / refusal / api_error


def label7(r):
    """6분류 + 비성공 상태 이름 (포함 분석용)."""
    return r["label"] if r["status"] == "ok" else cat(r)


def kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan"), 0.0
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return ((po - pe) / (1 - pe) if pe < 1 else float("nan")), po


def fmt(x, d=3):
    return "-" if x != x else f"{x:.{d}f}"


def src(*paths):
    return ["", "출처:"] + [f"- `{p}`" for p in paths] + [""]


def main():
    dirs = sorted(d for d in os.listdir(SEM) if os.path.exists(f"{SEM}/{d}/grades.jsonl"))
    G = {d: grades(d) for d in dirs}
    L = ["# 의미 채점 회수 결과 기술 집계", "",
         "작성: `experiments/revision/semantic_scoring_report.py` (API 호출 없음). 기술 집계만 하며 통계 검정은 하지 않는다.",
         "채점 모델 요청값 `claude-sonnet-5-5`, JUDGE_PROMPT v1, 입력 description + suggestion",
         "(민감도 폴더만 description). 연구자가 별도 창에서 배치를 제출하고 회수했다.",
         "사람 평가 시트는 만들지 않았다.", "",
         "상태 정의: 성공 = status ok. 잘림 = stop_reason max_tokens(status parse_error, truncated true).",
         "파싱 실패 = parse_error 중 잘림이 아닌 것. refusal, api_error 는 status 그대로.", ""]

    # (1)
    L += ["## 1. out_id 별 채점 이슈 수와 상태", "",
          "| out_id | 원 run | pass | 입력 | 이슈 | run 이슈 | 성공 | 파싱 실패 | refusal | 잘림 | api_error |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    tot = Counter()
    for d in dirs:
        s = json.load(open(f"{SEM}/{d}/summary.json", encoding="utf-8"))
        c = Counter(cat(r) for r in G[d])
        n_run = len(it.build_rows(s["source_run"], None))
        inp = "desc" if s["input_fields"] == ["description"] else "desc+sugg"
        L.append(f"| {d} | {s['source_run']} | {s['pass']} | {inp} | {len(G[d])} | {n_run} | {c['ok']} | "
                 f"{c['parse_error']} | {c['refusal']} | {c['truncated']} | {c['api_error']} |")
        for k in ("ok", "parse_error", "refusal", "truncated", "api_error"):
            tot[k] += c[k]
        tot["n"] += len(G[d])
    L.append(f"| 합계 | | | | {tot['n']} | | {tot['ok']} | {tot['parse_error']} | {tot['refusal']} | "
             f"{tot['truncated']} | {tot['api_error']} |")
    L += ["", "run 이슈 = `scoring/issue_table.py` 가 원 run reports.jsonl 에서 뽑은 대상 페이지 이슈 수(대조용).",
          "batch-check-E1-R1 은 배치 경로 확인용 1건(잠금 없음)이며 결과 분석에는 쓰지 않는다.",
          "모든 레코드의 batch result_type 은 succeeded 였다."]
    L += src(f"{SEM}/{{out_id}}/grades.jsonl", f"{SEM}/{{out_id}}/summary.json")

    # (2)
    L += ["## 2. 모델 버전 문자열과 호출 날짜", "",
          "| out_id | batch_id | 제출 (UTC) | 회수 (UTC) | 요청 수 | 응답 model |",
          "|---|---|---|---|---|---|"]
    models = set()
    for d in dirs:
        ev = [json.loads(l) for l in open(f"{SEM}/{d}/batches.jsonl", encoding="utf-8")]
        sub = [e for e in ev if e["event"] == "submitted"]
        col = [e for e in ev if e["event"] == "collected"]
        mv = ", ".join(sorted({r.get("model_version") or "?" for r in G[d]}))
        models.add(mv)
        for e in sub:
            cc = [c for c in col if c["batch_id"] == e["batch_id"]]
            L.append(f"| {d} | {e['batch_id'][-8:]} | {e['ts_utc'][11:19]} | "
                     f"{cc[-1]['ts_utc'][11:19] if cc else '-'} | {e['n_requests']} | {mv} |")
    L += ["", "batch_id 는 끝 8자만 적었다. 제출·회수 시각은 batches.jsonl, 응답 model 은 grades.jsonl 의",
          "model_version(batches.jsonl 에는 모델 문자열이 없음). 제출·회수 열은 시각만 적었다.",
          f"응답 model 문자열 전체: {', '.join(sorted(models))} (모든 레코드). 모든 호출 날짜는 2026-11-13 (UTC)."]
    L += src(f"{SEM}/{{out_id}}/batches.jsonl", f"{SEM}/{{out_id}}/grades.jsonl")

    # (3)
    L += ["## 3. 비용 (배치 단가 입력 $1/1M, 출력 $5/1M)", "",
          "| out_id | 입력 토큰 | 출력 토큰 | 호출당 입력 | 호출당 출력 | 비용 (USD) |", "|---|---|---|---|---|---|"]
    ti = to = 0
    for d in dirs:
        i = sum(r.get("input_tokens") or 0 for r in G[d]); o = sum(r.get("output_tokens") or 0 for r in G[d])
        ti += i; to += o; n = len(G[d])
        L.append(f"| {d} | {i} | {o} | {i / n:.1f} | {o / n:.1f} | {(i * PIN + o * POUT) / 1e6:.4f} |")
    L.append(f"| 합계 | {ti} | {to} | | | {(ti * PIN + to * POUT) / 1e6:.4f} |")
    L += ["", "잘림 레코드도 토큰이 과금되므로 포함했다. 표준 경로 시험 호출(probe-E1-R1, 20건)은 이전 보고",
          "(`clean_report_a2_e4.md`)에 있으며 이 합계에 넣지 않았다. 실제 청구액은 Anthropic 콘솔 기준으로 확인해야 한다."]
    L += src(f"{SEM}/{{out_id}}/grades.jsonl")

    # (4)
    p1 = {r["issue_id"]: r for r in G["E1-R1-sem-p1"]}
    p2 = {r["issue_id"]: r for r in G["E1-R1-sem-p2"]}
    ids = sorted(set(p1) & set(p2))
    a_inc = [label7(p1[i]) for i in ids]; b_inc = [label7(p2[i]) for i in ids]
    both = [i for i in ids if p1[i]["status"] == "ok" and p2[i]["status"] == "ok"]
    k_inc, po_inc = kappa(a_inc, b_inc)
    k_exc, po_exc = kappa([p1[i]["label"] for i in both], [p2[i]["label"] for i in both])
    L += ["## 4. E1-R1 pass1 대 pass2 라벨 일치", "",
          "| 범위 | 이슈 | 일치 | 일치율 | Cohen's kappa |", "|---|---|---|---|---|",
          f"| 포함: 6분류 + 잘림/파싱 실패/refusal 을 별도 범주로 | {len(ids)} | "
          f"{sum(x == y for x, y in zip(a_inc, b_inc))} | {fmt(po_inc)} | {fmt(k_inc)} |",
          f"| 제외: 두 회차 모두 성공한 이슈만 (6분류) | {len(both)} | "
          f"{round(po_exc * len(both))} | {fmt(po_exc)} | {fmt(k_exc)} |"]
    dis = Counter((x, y) for x, y in zip(a_inc, b_inc) if x != y)
    L += src(f"{SEM}/E1-R1-sem-p1/grades.jsonl", f"{SEM}/E1-R1-sem-p2/grades.jsonl")
    L += ["불일치 쌍 (pass1 → pass2, 건수):", "", "| pass1 | pass2 | 건수 |", "|---|---|---|"]
    L += [f"| {x} | {y} | {n} |" for (x, y), n in sorted(dis.items(), key=lambda t: (-t[1], t[0]))]
    L += src(f"{SEM}/E1-R1-sem-p1/grades.jsonl", f"{SEM}/E1-R1-sem-p2/grades.jsonl")

    # (5)
    dd = {r["issue_id"]: r for r in G["E1-R1-sem-desc-p1"]}
    ids5 = sorted(set(p1) & set(dd))
    a5 = [label7(p1[i]) for i in ids5]; b5 = [label7(dd[i]) for i in ids5]
    both5 = [i for i in ids5 if p1[i]["status"] == "ok" and dd[i]["status"] == "ok"]
    agree5 = sum(p1[i]["label"] == dd[i]["label"] for i in both5)
    L += ["## 5. E1-R1 pass1 (description + suggestion) 대 description-only 민감도", "",
          "| 범위 | 이슈 | 일치 | 일치율 |", "|---|---|---|---|",
          f"| 포함: 비성공 상태를 별도 범주로 | {len(ids5)} | {sum(x == y for x, y in zip(a5, b5))} | "
          f"{fmt(sum(x == y for x, y in zip(a5, b5)) / len(ids5))} |",
          f"| 제외: 두 채점 모두 성공 | {len(both5)} | {agree5} | {fmt(agree5 / len(both5))} |"]
    L += src(f"{SEM}/E1-R1-sem-p1/grades.jsonl", f"{SEM}/E1-R1-sem-desc-p1/grades.jsonl")
    dis5 = Counter((x, y) for x, y in zip(a5, b5) if x != y)
    L += ["불일치 쌍 (pass1 → description-only, 건수):", "", "| pass1 | desc-only | 건수 |", "|---|---|---|"]
    L += [f"| {x} | {y} | {n} |" for (x, y), n in sorted(dis5.items(), key=lambda t: (-t[1], t[0]))]
    L += src(f"{SEM}/E1-R1-sem-p1/grades.jsonl", f"{SEM}/E1-R1-sem-desc-p1/grades.jsonl")

    # (6)
    L += ["## 6. 이슈 단위 통합 표: 키워드 대 의미 채점 pass1 (유형별)", "",
          "키워드 = description 다중 라벨(`evaluate_performance_v5.CATEGORY_PHRASES`), 의미 = pass1 단일 라벨.",
          "의미 채점이 성공이 아닌 이슈는 어느 유형으로도 세지 않았다. 일치 = 둘 다 양성 + 둘 다 음성.", "",
          "| 원 run | 유형 | 이슈 | 둘 다 양성 | 둘 다 음성 | 키워드만 | 의미만 | 일치 | 불일치 |",
          "|---|---|---|---|---|---|---|---|---|"]
    tables = {}
    for o in PASS1:
        run = json.load(open(f"{SEM}/{o}/summary.json", encoding="utf-8"))["source_run"]
        rows = it.build_rows(run, o)
        tables[run] = rows
        for t in TYPES:
            c = Counter()
            for r in rows:
                k = t in r["keyword_types"].split(";")
                s = r["semantic_pass1_status"] == "ok" and r["semantic_pass1"] == t
                c[(k, s)] += 1
            L.append(f"| {run} | {SHORT[t]} | {len(rows)} | {c[(True, True)]} | {c[(False, False)]} | "
                     f"{c[(True, False)]} | {c[(False, True)]} | {c[(True, True)] + c[(False, False)]} | "
                     f"{c[(True, False)] + c[(False, True)]} |")
    L += src("results/revision/runs/{run}/reports.jsonl", f"{SEM}/{{run}}-sem-p1/grades.jsonl",
             "scoring/issue_table.py")
    L += ["### 6a. 표준 용어 위반: 키워드, 의미 pass1, string_match 세 판정의 조합", "",
          "조합 표기 = 키워드/의미/string_match (1 = 용어 위반 판정). 000 은 세 채점기 모두 음성.", "",
          "| 원 run | 이슈 | 000 | 001 | 010 | 011 | 100 | 101 | 110 | 111 | 의미 비성공 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    t = "Standard Terminology Violation"
    for run, rows in tables.items():
        c = Counter()
        for r in rows:
            k = int(t in r["keyword_types"].split(";"))
            s = int(r["semantic_pass1_status"] == "ok" and r["semantic_pass1"] == t)
            c[f"{k}{s}{r['string_match_term']}"] += 1
        nonok = sum(r["semantic_pass1_status"] != "ok" for r in rows)
        L.append(f"| {run} | {len(rows)} | " + " | ".join(str(c[f'{i:03b}']) for i in range(8)) + f" | {nonok} |")
    L += src("results/revision/runs/{run}/reports.jsonl", f"{SEM}/{{run}}-sem-p1/grades.jsonl",
             "scoring/string_match.py")
    L += ["### 6b. 표준 용어 위반 쌍별 일치 (이슈 단위)", "",
          "| 원 run | 키워드-의미 일치 | 불일치 | 키워드-string_match 일치 | 불일치 | 의미-string_match 일치 | 불일치 |",
          "|---|---|---|---|---|---|---|"]
    for run, rows in tables.items():
        v = [(int(t in r["keyword_types"].split(";")),
              int(r["semantic_pass1_status"] == "ok" and r["semantic_pass1"] == t), r["string_match_term"])
             for r in rows]
        pair = lambda i, j: (sum(x[i] == x[j] for x in v), sum(x[i] != x[j] for x in v))
        a, b, c = pair(0, 1), pair(0, 2), pair(1, 2)
        L.append(f"| {run} | {a[0]} | {a[1]} | {b[0]} | {b[1]} | {c[0]} | {c[1]} |")
    L += src("results/revision/runs/{run}/reports.jsonl", f"{SEM}/{{run}}-sem-p1/grades.jsonl",
             "scoring/string_match.py")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    long = [i + 1 for i, l in enumerate(L) if len(l) > 100]
    print(f"{OUT}: {len(L)} lines, lines over 100 chars: {long[:10]}")


if __name__ == "__main__":
    main()
