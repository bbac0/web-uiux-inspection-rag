"""
E9 재파일럿과 이전 파일럿 비교 절 (API 호출 없음). e9_pilot_report.py --compare OLD_PREFIX 에서 불린다.

- 대조군 위양성(정규식 주 지표, 보조 분석): 조건 × 유형, 이전 → 이번.
- 원인별 집계: 대조군 페이지에서 어느 규칙(주 또는 보조)에든 걸린 이슈를 문구로 분류(관찰용 휴리스틱, 판정 아님).
  국기 자리(국기|flag|플래그|태극), 본문 자리 표시 '배너'(배너 + 플레이스홀더|자리 표시|임시), 그 밖.
- 이슈 수 변화: 조건별 대상 페이지 이슈 합계(전체, 대조군).
"""
import csv
import json
import re

from scoring import e9_rules as primary
from scoring import e9_rules_aux as aux
from experiments.revision import e9_regex_table as tbl

RUNS = "results/revision/runs_e9_pilot"
FLAG = re.compile(r"(국기|flag|플래그|태극)", re.I)
PLACEHOLDER = re.compile(r"(플레이스홀더|자리\s*표시|임시)", re.I)


def _issues(prefix, cond):
    out = {}
    for l in open(f"{RUNS}/{prefix}-{cond}/reports.jsonl", encoding="utf-8"):
        r = json.loads(l)
        out[r["page_id"]] = tbl.target_issues(r.get("report") if r["status"] == "ok" else None, r["page_id"])
    return out


def _cause(text):
    if FLAG.search(text):
        return "국기 자리"
    if "배너" in text and PLACEHOLDER.search(text):
        return "본문 자리 표시 '배너'"
    return "그 밖"


def section(old, new, conds, cname, meta, tables):
    controls = sorted(p for p, m in meta.items() if m["defect_id"] is None)
    L = ["## 8a. 이전 파일럿과 비교", "",
         f"이전 = `{old}` (`exp-freeze-e9-v2` 입력),",
         f"이번 = `{new}` (`exp-freeze-e9-v3` 입력: 국기 그림, portal_main 본문 문구).",
         "같은 8페이지, 같은 5조건, 각 1회. 표본이 작아(대조군 2페이지) 차이를 해석하지 않고 기록만 한다.", ""]
    rows = []
    for c in conds:
        for rule in ("primary", "aux"):
            o = {r["type"]: r for r in tables[old] if r["run"] == f"{old}-{c}" and r["rule"] == rule}
            n = {r["type"]: r for r in tables[new] if r["run"] == f"{new}-{c}" and r["rule"] == rule}
            rows.append([cname[c], "주 지표" if rule == "primary" else "보조"] +
                        [f"{o[t]['control_detected']}→{n[t]['control_detected']}" for t in ("E9-1", "E9-2", "E9-3", "E9-4")])
    L += ["### 8a.1 대조군 위양성 페이지 수 (대조군 2페이지 중, 이전→이번)", ""]
    L += ["| 조건 | 규칙 | E9-1 | E9-2 | E9-3 | E9-4 |", "|---|---|---|---|---|---|"]
    L += ["| " + " | ".join(r) + " |" for r in rows]
    L += ["", "출처: `results/revision/e9_pilot/tables/e9_regex_primary_vs_aux.csv` (이전),",
          f"`results/revision/e9_pilot/tables_{new}/e9_regex_primary_vs_aux.csv` (이번)", ""]
    L += ["### 8a.2 대조군에서 정규식에 걸린 이슈의 원인별 건수 (관찰용 문구 분류, 이전→이번)", "",
          "분류: 문구에 국기|flag|플래그|태극 → 국기 자리; '배너' + 플레이스홀더|자리 표시|임시 → 본문 자리 표시; 나머지 → 그 밖.", ""]
    L += ["| 조건 | 국기 자리 | 본문 자리 표시 '배너' | 그 밖 | 합계 |", "|---|---|---|---|---|"]
    tot = {old: {}, new: {}}
    for c in conds:
        cnt = {}
        for pfx in (old, new):
            iss = _issues(pfx, c)
            k = {"국기 자리": 0, "본문 자리 표시 '배너'": 0, "그 밖": 0}
            for pid in controls:
                for i in iss.get(pid, []):
                    pm, am = primary.match_issue(i, None), aux.match_issue(i)
                    if any(pm.values()) or any(am.values()):
                        k[_cause(primary.issue_text(i))] += 1
            cnt[pfx] = k
            for kk, v in k.items():
                tot[pfx][kk] = tot[pfx].get(kk, 0) + v
        L.append(f"| {cname[c]} | " + " | ".join(f"{cnt[old][k]}→{cnt[new][k]}" for k in cnt[old]) +
                 f" | {sum(cnt[old].values())}→{sum(cnt[new].values())} |")
    L.append("| **합계** | " + " | ".join(f"{tot[old][k]}→{tot[new][k]}" for k in tot[old]) +
             f" | {sum(tot[old].values())}→{sum(tot[new].values())} |")
    L += ["", "출처:", f"- `{RUNS}/{old}-{{조건}}/reports.jsonl`", f"- `{RUNS}/{new}-{{조건}}/reports.jsonl`", ""]
    L += ["### 8a.3 이슈 수 변화 (대상 페이지 이슈 합계, 이전→이번)", ""]
    L += ["| 조건 | 전체 8페이지 | 대조군 2페이지 | 결함 6페이지 |", "|---|---|---|---|"]
    for c in conds:
        io, inew = _issues(old, c), _issues(new, c)
        f = lambda d, pages: sum(len(d.get(p, [])) for p in pages)
        defects = [p for p in meta if p not in controls]
        L.append(f"| {cname[c]} | {f(io, meta)}→{f(inew, meta)} | {f(io, controls)}→{f(inew, controls)} | "
                 f"{f(io, defects)}→{f(inew, defects)} |")
    L += ["", "출처:", f"- `{RUNS}/{old}-{{조건}}/reports.jsonl`", f"- `{RUNS}/{new}-{{조건}}/reports.jsonl`", ""]
    return L


def load_table(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))
