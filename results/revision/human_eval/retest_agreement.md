# 평가자 A 자기 일치도 (본 평가 vs 재판정, 강건 지표 포함)

작성: `experiments/revision/human_eval_consensus.py retest` (API 호출 없음, 검정 없음). 2026-11-18.
비교·불일치 목록은 `human_eval_retest_compare.py` 의 read/compare, PABAK·AC1 은
`human_eval_compare_robust.agreement` 로 계산했다. 정답 키·채점 결과 미사용.
같은 입력의 kappa 까지 보고는 `retest_agreement_A.md`(55eed97) 에 있고, 이 파일은 PABAK·AC1 을 더한 판이다.

## 0. 접수 점검

- 재판정: `results/revision/human_eval/rater_A_retest/eval_sheet_A_retest_filled.csv`
  SHA256 `48fdd2422b2b197e50b8032a5067441b7e7a8dbcd69c4f52ab49d62a786d57bc`, 읽기 전용 예, 커밋하지 않음.
- 본 평가: `results/revision/human_eval/rater_A/eval_sheet_A_filled.csv`
  SHA256 `14dcc061cafd1adb89587142716537367863e028e9e93110c66cdd040c495fcf`
- 점검: 행 40 (기대 40), 열 구성·issue_id·순서·본문, 중복, 판정 4열 빈칸, 허용 값 밖 → 문제 0건.
- issue_id 집합이 `retest_sampling.json` 표본 40건과 같음.

## 1. 열별 일치

| 열 | 비교 건 | 일치 | 일치율 | kappa | PABAK | AC1 | 관찰 값 수 |
|---|---|---|---|---|---|---|---|
| 6분류 | 40 | 39 | 0.975 | 0.943 | 0.970 | 0.973 | 5 |
| 코드에 존재 | 40 | 39 | 0.975 | 0.939 | 0.962 | 0.969 | 2 |
| 화면에서 보임 | 40 | 39 | 0.975 | 0.787 | 0.962 | 0.973 | 2 |
| 로그인 레이블 지적 | 40 | 40 | 1.000 | 계산 불가(값 한 가지) | 1.000 | 1.000 | 1 |

출처: 0절의 두 CSV. PABAK·AC1 의 q 는 허용 값 수(6분류 6, 코드·화면 3, 로그인 레이블 2).

## 2. 불일치 목록 (2건)

| issue_id | 열 | 본 평가 | 재판정 | 본 평가 비고 | 재판정 비고 |
|---|---|---|---|---|---|
| I0c435296bd | 코드에 존재 | 예 | 아니오 |  | 부재형 |
| I0c435296bd | 화면에서 보임 | 예 | 아니오 |  | 부재형 |
| I575cd93a5f | 6분류 | 중복 ID | 해당 없음 | 부재형 | 부재형 |

출처: 0절의 두 CSV
