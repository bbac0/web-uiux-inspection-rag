# E9 사람 평가 표본 건수 (시트 생성 전)

작성: `experiments/revision/e9_human_sample.py counts` (API 호출 없음). 2026-11-18.
규칙: `results/revision/analysis_plan_addendum_e9_human.md` (ca021ba). 시드 페이지 20261201, 이슈 20261202.

## 1. 페이지 표본

| 페이지 층 | 전체 페이지 | 표본 페이지 |
|---|---|---|
| E9-1 | 16 | 15 |
| E9-2 | 15 | 15 |
| E9-3 | 15 | 15 |
| control | 30 | 15 |

출처: `testbed_e9/dataset_metadata_e9.json`. 두 조건에 같은 페이지 표본을 쓴다.

## 2. 이슈 건수 (모집단 = 그 층의 모든 페이지, 표본 = 표본 페이지에서 뽑은 이슈)

| 조건 run | 페이지 층 | 정규식 | 모집단 이슈 | 표본 이슈 |
|---|---|---|---|---|
| e9-main-related-r1 | E9-1 | 걸림 | 12 | 10 |
| e9-main-related-r1 | E9-1 | 안 걸림 | 8 | 7 |
| e9-main-related-r1 | E9-2 | 걸림 | 15 | 15 |
| e9-main-related-r1 | E9-2 | 안 걸림 | 2 | 2 |
| e9-main-related-r1 | E9-3 | 걸림 | 17 | 17 |
| e9-main-related-r1 | E9-3 | 안 걸림 | 9 | 9 |
| e9-main-related-r1 | control | 걸림 | 3 | 2 |
| e9-main-related-r1 | control | 안 걸림 | 19 | 15 |
| e9-main-norag-r1 | E9-1 | 걸림 | 1 | 1 |
| e9-main-norag-r1 | E9-1 | 안 걸림 | 63 | 30 |
| e9-main-norag-r1 | E9-2 | 걸림 | 2 | 2 |
| e9-main-norag-r1 | E9-2 | 안 걸림 | 46 | 30 |
| e9-main-norag-r1 | E9-3 | 걸림 | 3 | 3 |
| e9-main-norag-r1 | E9-3 | 안 걸림 | 52 | 28 |
| e9-main-norag-r1 | control | 걸림 | 5 | 2 |
| e9-main-norag-r1 | control | 안 걸림 | 96 | 30 |
| 합계 | | | 353 | 203 |

출처: `results/revision/runs_e9/{run}/reports.jsonl` (대상 페이지 이슈), `scoring/e9_rules.py`;
표본 목록 `results/revision/human_eval/e9_eval/key/sample_selection.csv`

## 3. 표본 페이지 상태

| 조건 run | 상태 | 페이지 |
|---|---|---|
| e9-main-norag-r1 | ok | 60 |
| e9-main-related-r1 | ok | 60 |

출처: 위 reports.jsonl

- 표본 안에서 같은 문장(설명 + 제안)이 2번 이상 나온 이슈: 29건(합치지 않음).
- **총 표본 이슈 203건: 150건을 넘는다. 시트를 만들기 전에 지시를 받는다.**
