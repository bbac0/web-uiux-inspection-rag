# 합의 회의 결과 접수

작성: `experiments/revision/human_eval_consensus.py intake` (API 호출 없음). 2026-11-18.
정답 키(key/)와 자동 채점 결과는 읽지 않았다.

- 입력: `results/revision/human_eval/consensus/disagreement_for_consensus_filled.csv`
  SHA256 `fb442a4e9688c8ddc0e7679ce22b7a2ddb2d56cb9030836654a7cac2cf6b4b57`
  크기 26387 바이트. 접수 시 읽기 전용 속성 설정(내용은 바꾸지 않음), 커밋하지 않음.
- 원 불일치 파일: `results/revision/human_eval/consensus/disagreement_for_consensus.csv`
  SHA256 `4145b9f09ed6eee0ecbb2531f315b1944bfe835bce1dffacfc96d3d9c94bb794`

## 1. 점검

| 점검 | 결과 |
|---|---|
| 행 수 | 37 (기대 37) |
| 열 구성 | 원 파일과 같음 |
| 번호·issue_id·판정 열·본문·A/B 답이 원 파일과 같음 | 예 |
| 합의 답 빈칸 | 0 |
| 합의 불가 표시 | 0 |
| 합의 답 허용 값 밖 | 0 |
| 합의 사유 빈칸 | 0 |
| A·B 답이 지금 제출 CSV 와 같음 | 예 |

출처: 위 입력과 원 불일치 파일, 평가자 제출 CSV 4개(`intake_all.md`)

**문제 0건.**

## 2. 확인 필요: 합의 사유와 합의 답이 어긋나 보이는 행

사유 문장의 결론 표현(예: '코드에 있는 것으로', '보이지 않')과 합의 답을 기계적으로 대조했다.
어느 쪽이 맞는지는 판단하지 않았고 고치지 않았다. human_final 에는 합의 답을 그대로 썼다.

| 번호 | issue_id | 판정 열 | 합의 답 | 어긋난 점 |
|---|---|---|---|---|
| 8 | I524832a66a | 코드에 존재 | 아니오 | 사유에 '코드에 있는 것으로' 가 있으나 합의 답이 '아니오' |
| 30 | Ia0dac2d6c1 | 화면에서 보임 | 예 | 사유에 '보이지 않' 가 있으나 합의 답이 '예' |

출처: 위 입력의 합의 답·합의 사유 열
