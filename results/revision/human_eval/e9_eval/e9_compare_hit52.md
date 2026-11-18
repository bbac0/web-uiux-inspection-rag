# E9 사람 평가(평가자 A) 대 정규식: 정밀도

작성: `experiments/revision/e9_human_compare.py` (API 호출 없음, 검정 없음).
평가자 A: `results/revision/human_eval/e9_eval/intake_hit52/eval_sheet_A_e9_hit52_filled_copy.csv`, key: `results/revision/human_eval/e9_eval/key/e9_key_hit52.csv`
부록 3 (94503ac): 정규식에 걸린 52건만 평가했다. 사람 기준은 평가자 A 1인이고 재평가는 없다.
단위는 (이슈, 잡은 유형) 쌍. 신뢰구간과 층을 넘는 검정은 내지 않는다.

## 1. 층별 (조건 run × 페이지 결함 유형 × 잡은 유형)

| 조건 run | 페이지 층 | 잡은 유형 | 쌍 | A '예' | A '아니오' | 빈 칸 | 정밀도(건수) |
|---|---|---|---|---|---|---|---|
| e9-main-norag-r1 | E9-1 | E9-1 | 1 | 0 | 1 | 0 | 1쌍 중 0쌍 |
| e9-main-norag-r1 | E9-2 | E9-2 | 2 | 0 | 2 | 0 | 2쌍 중 0쌍 |
| e9-main-norag-r1 | E9-3 | E9-3 | 3 | 3 | 0 | 0 | 3쌍 중 3쌍 |
| e9-main-norag-r1 | control | E9-2 | 2 | 0 | 2 | 0 | 2쌍 중 0쌍 |
| e9-main-related-r1 | E9-1 | E9-1 | 10 | 9 | 1 | 0 | 10쌍 중 9쌍 |
| e9-main-related-r1 | E9-1 | E9-2 | 1 | 1 | 0 | 0 | 1쌍 중 1쌍 |
| e9-main-related-r1 | E9-2 | E9-1 | 4 | 0 | 4 | 0 | 4쌍 중 0쌍 |
| e9-main-related-r1 | E9-2 | E9-2 | 15 | 15 | 0 | 0 | 15쌍 중 15쌍 |
| e9-main-related-r1 | E9-3 | E9-3 | 17 | 15 | 2 | 0 | 17쌍 중 15쌍 |
| e9-main-related-r1 | control | E9-3 | 2 | 0 | 2 | 0 | 2쌍 중 0쌍 |

출처: 위 입력 CSV 와 key

## 2. 조건 run × 잡은 유형 합계 (걸린 이슈 전수)

| 조건 run | 잡은 유형 | 쌍 | A '예' | A '아니오' | 빈 칸 | 정밀도(건수) |
|---|---|---|---|---|---|---|
| e9-main-norag-r1 | E9-1 | 1 | 0 | 1 | 0 | 1쌍 중 0쌍 |
| e9-main-norag-r1 | E9-2 | 4 | 0 | 4 | 0 | 4쌍 중 0쌍 |
| e9-main-norag-r1 | E9-3 | 3 | 3 | 0 | 0 | 3쌍 중 3쌍 |
| e9-main-related-r1 | E9-1 | 14 | 9 | 5 | 0 | 14쌍 중 9쌍 |
| e9-main-related-r1 | E9-2 | 16 | 16 | 0 | 0 | 16쌍 중 16쌍 |
| e9-main-related-r1 | E9-3 | 19 | 15 | 4 | 0 | 19쌍 중 15쌍 |

출처: 위와 같음

## 3. A 가 '아니오'로 본 쌍 (14건)

| issue_id | 조건 run | 페이지 층 | 잡은 유형 | banner/spec/login | 비고 |
|---|---|---|---|---|---|
| I634d2e3f92 | e9-main-related-r1 | E9-1 | E9-1 | 아니오/예/아니오 |  |
| I45fd324a75 | e9-main-related-r1 | E9-2 | E9-1 | 아니오/예/아니오 |  |
| I13475b2014 | e9-main-related-r1 | E9-2 | E9-1 | 아니오/예/아니오 |  |
| Ic2dfd8c2bc | e9-main-related-r1 | E9-2 | E9-1 | 아니오/예/아니오 |  |
| I558324d1ca | e9-main-related-r1 | E9-2 | E9-1 | 아니오/예/아니오 |  |
| I5defaf3687 | e9-main-related-r1 | E9-3 | E9-3 | 아니오/아니오/아니오 | 편의성 문제  |
| I5e2d9aa3ca | e9-main-related-r1 | E9-3 | E9-3 | 아니오/아니오/아니오 | 편의성 문제 |
| I610715c113 | e9-main-related-r1 | control | E9-3 | 아니오/아니오/아니오 | 편의성 문제 |
| I16fa4a6030 | e9-main-related-r1 | control | E9-3 | 아니오/아니오/아니오 | 회원가입 링크 추가 문제  |
| I932ebe2fc8 | e9-main-norag-r1 | E9-1 | E9-1 | 아니오/아니오/아니오 | 페이지 제목 문제  |
| I761bbfe9c1 | e9-main-norag-r1 | E9-2 | E9-2 | 아니오/아니오/아니오 | 접근성 문제  |
| I40d8ccb99d | e9-main-norag-r1 | E9-2 | E9-2 | 아니오/아니오/아니오 | 스타일 지적  |
| I35d21b764d | e9-main-norag-r1 | control | E9-2 | 아니오/아니오/아니오 | 접근성 문제 |
| I1dc33c6122 | e9-main-norag-r1 | control | E9-2 | 아니오/아니오/아니오 | 접근성 문제 |

출처: 위와 같음

## 4. 한계

- 재현 누락(정규식이 놓친 실제 결함)은 사람이 검증하지 않았다(부록 3 5절).
- 평가자 1인, 재평가 없음. 일부 층은 1~3쌍이라 건수로만 읽는다.
