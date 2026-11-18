# 합의 회의 시트 정보 누출 점검

작성: `experiments/revision/human_eval_intake_all.py leak` (API 호출 없음). 2026-11-18.
검사 대상: `results/revision/human_eval/consensus/` 의 모든 파일. 이슈 설명·제안 본문은 평가자가 이미 본
LLM 문장이라 제외했다. 검색어: 결함 유형 영문명, 페이지 ID, 런 이름, 주입 식별자, 조건명, 채점기, 층 정보,
키 경로. 원 결과: `results/revision/human_eval/leak_audit_consensus.json`.

검사한 파일 25개.

## 1. 검색 결과

| 파일 | 위치 | 분류 | 일치 | 건수 | 판단 |
|---|---|---|---|---|---|
| - | - | - | - | 0 | - |

출처: `results/revision/human_eval/leak_audit_consensus.json`

## 2. 추가 점검

| 점검 | 결과 |
|---|---|
| CSV 의 합의 답·합의 사유 칸 중 값이 있는 칸 | 0 |
| CSV 열에 채점기 결과·정답 키·실험 조건·층 열 | 없음(열 구성 고정) |

출처: 위와 같음

**누출로 판단한 항목: 0건.**
