# 보충 시트 표본 건수

작성: `experiments/revision/supp_label_sample.py counts` (API 호출 없음).
규칙: `results/revision/analysis_plan_addendum_supp_label.md` (커밋 d594519).
모집단 이슈 2223건, 중복 제거 후 903건 (1320건 제거).

## 1. 층별 건수

| 층 | 모집단(중복 제거 전) | 모집단(중복 제거 후) | 목표 | 표본 |
|---|---|---|---|---|
| S1 | 75 | 43 | 전부 | 43 |
| S2 | 58 | 34 | 최대 40 | 34 |
| S3 | 2090 | 826 | 30 | 30 |
| 제외(라벨 없음) | 0 | 0 | - | 0 |
| 합계 | 2223 | 903 | | 107 |

출처: `results/revision/issue_tables_merged/{run}.csv`, `results/revision/runs/{run}/reports.jsonl`

## 2. 표본의 run 별 건수 (대표 이슈 기준)

| run | S1 | S2 | S3 | 합계 |
|---|---|---|---|---|
| E3-oracle | 20 | 15 | 1 | 36 |
| E3-page | 9 | 3 | 5 | 17 |
| E2-A1-1 | 8 | 12 | 18 | 38 |
| E2-A1-2 | 2 | 3 | 2 | 7 |
| E2-A1-3 | 0 | 0 | 3 | 3 |
| E4-mobile | 4 | 1 | 1 | 6 |

출처: `results/revision/human_eval/supp_label/key/sample_selection.csv`

## 3. 중복 묶음

- 두 건 이상 묶인 대표 이슈: 모집단 541건, 표본 51건.
- 묶음 안에서 의미 라벨이나 string_match 가 다른 대표 이슈: 모집단 2건, 표본 0건 (층은 대표 이슈 기준).
- 표본 중 E4-mobile 대표 이슈(스크린샷 390x844): 6건.
