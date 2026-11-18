# analysis_plan 부록: 의미 채점 잘림 건 재채점 (사전 지정)

작성 2026-11-13. 동결된 `results/revision/analysis_plan.md`(exp-freeze-v5)는 고치지 않고 이 부록으로 더한다.
**이 부록의 결정은 재채점 결과를 보기 전에 정했다.** 이 시점까지 재채점은 제출되지 않았고 재채점 라벨은 존재하지 않는다.
(원 채점의 잘림 분석 `results/revision/reports/semantic_truncation_report.md` 와 잠정 집계
`results/revision/reports/semantic_provisional_compare.md` 는 본 뒤다.)

## 1. 배경

- 의미 채점(claude-sonnet-5-5, JUDGE_PROMPT v1, max_tokens 100)에서 11개 out_id 5,576건 중 150건(2.7%)이
  stop_reason max_tokens 로 잘렸다. 150건 모두 JSON 앞에 판단 근거를 문장으로 쓰다가 100 토큰에서 끊겼다.
- 잘림은 무작위가 아니다(대비 페이지, '접속하기' 이슈에 몰림). analysis_plan 10절 1항의 규칙(비성공은 해당 유형으로
  세지 않음)만 쓰면 특정 유형의 의미 채점 양성이 줄어드는 쪽으로 치우칠 수 있다.

## 2. 결정 (2026-11-13 연구자)

1. **주 분석 = 재채점 포함.** 원 채점이 성공한 건은 원 라벨, 원 채점이 잘린 건은 재채점 라벨(재채점 성공 시).
   **민감도 분석:** (i) 원 규칙(잘림 = 음성, analysis_plan 10절 1항), (ii) 잘린 이슈가 있는 페이지를 그 run 의 셀에서 제외.
2. **max_tokens 800.** 설정 파일 `scoring/grader_config_retry800.json` = 동결된 `scoring/grader_config.json` 에서
   max_tokens 와 _notes 만 다르다. 모델, thinking between_tools, effort high, temperature 미지정, fallback 끔,
   JUDGE_PROMPT v1, 입력 필드(원 out_id 와 같음), 배치 경로는 같다.
   근거: 잘린 응답이 평균 107자(약 100 토큰)에서 근거를 쓰는 도중에 끊겼고 근거 전체가 250~400 토큰일 수 있어
   300 은 일부가 다시 잘릴 수 있다. 800 은 상한일 뿐이고 실제 쓴 토큰만 과금된다.
3. **재채점은 1회만 한다.** 대상 = `results/revision/semantic_truncation_targets.csv` 150건(원 grades.jsonl 에서
   truncated=true). 재채점에서 다시 잘리거나 파싱에 실패하거나 refusal 인 건은 '미해결'로 남기고 다시 채점하지 않는다.
   미해결 건은 주 분석에서 원 규칙과 같이 어느 유형으로도 세지 않고 건수를 보고한다.
   배치 처리 오류(errored, expired, canceled)는 채점 결과가 아니므로 같은 대상으로 다시 낼 수 있다(`--resume`).
4. 결과 폴더 `results/revision/semantic_scores/{원 out_id}-retry/`. 원 폴더(잠김)는 읽기만 하고 덮어쓰지 않는다.
   제출 전 각 대상의 입력·프롬프트 sha256 이 원 채점과 같은지 확인한다(`scoring/semantic_grader_retry.py`).
5. 통합 표: `scoring/issue_table_merged.py` (동결된 issue_table.py 열 + semantic_pass1_merged,
   semantic_pass1_source(original/retry/unresolved), semantic_pass1_filled_by_retry, semantic_retry_status).
   보고 표에는 '재채점으로 채운 건' 수를 run·유형별 별도 열로 적는다.
6. R1 pass1 대 pass2 일치(kappa)와 description-only 민감도는 원 기준(보고 완료)과 재채점 포함 기준을 둘 다 보고한다.

## 3. 한계 (보고서에 적는다)

- 150건만 max_tokens 800 으로, 나머지는 100 으로 채점되어 이슈마다 설정이 다르다. max_tokens 는 출력 상한이고
  원래 성공한 응답은 상한 근처에 가지 않았지만(최대 21 토큰) 완전히 같은 조건은 아니다.
- 재채점은 원 채점과 다른 시점의 별도 표본이다(temperature 미지정, 기본 샘플링).
- 대안(전체 5,576건을 800 으로 재채점)은 하지 않는다.

## 4. 비용 상한

150건 × (입력 약 880 토큰 × $1/1M + 출력 최대 800 토큰 × $5/1M) ≈ $0.73 (배치 단가). 실제는 쓴 토큰만 과금.
