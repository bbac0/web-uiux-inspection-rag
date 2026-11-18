# 의미 채점 잘림 150건 재채점 결과

작성: `experiments/revision/semantic_retry_report.py` (API 호출 없음, 기술 집계만, 통계 검정 없음).
사전 지정: `results/revision/analysis_plan_addendum_semantic_retry.md`
(주 분석 = 재채점 포함, max_tokens 800, 1회). 재채점 폴더는 읽기만 했다.
연구자 메시지의 '오류나 경고 [있음/없음]' 칸은 채워지지 않아 기록(batches.jsonl, grades.jsonl)으로만 확인했다.

## 1. out_id 별 재채점 건수와 상태

| 재채점 | 대상 | 기록 | ok | parse_err | refusal | api_err | 재잘림 | 미해결 | 잠금(검증) | 이벤트 |
|---|---|---|---|---|---|---|---|---|---|---|
| E1-R1-p1-rt | 11 | 11 | 11 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 실패, 제출, 회수 |
| E1-R1-p2-rt | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E1-R1-desc-p1-rt | 19 | 19 | 19 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E1-R2-p1-rt | 19 | 19 | 19 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E1-R3b-p1-rt | 22 | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E2-A1-1-p1-rt | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E2-A1-2-p1-rt | 17 | 17 | 17 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E2-A1-3-p1-rt | 17 | 17 | 17 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E3-page-p1-rt | 5 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E3-oracle-p1-rt | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |
| E4-mobile-p1-rt | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 잠김 (OK) | 제출, 회수 |

재채점 이름: `E1-R1-p1-rt` = `E1-R1-sem-p1-retry` (표 폭 때문에 줄임).

합계: 대상 150, 기록 150, ok 150, 미해결 0. stop_reason: {'end_turn': 150}.
E1-R1-sem-p1-retry 의 submit_failed(실패)는 첫 제출의 크레딧 거부 기록이다(`retry_submit_state.md`).
그 뒤 --resume 으로 제출됨.

출처:
- `results/revision/semantic_scores/{out_id}-retry/grades.jsonl`
- `results/revision/semantic_scores/{out_id}-retry/run_meta.json`
- `results/revision/semantic_scores/{out_id}-retry/batches.jsonl`

## 2. 재채점 라벨

### 2.1 out_id 별 라벨 분포

| 재채점 out_id | 대비 | 모바일 | 버튼 | 용어 | 중복ID | None | 비성공 |
|---|---|---|---|---|---|---|---|
| E1-R1-sem-p1-retry | 1 | 0 | 0 | 0 | 0 | 10 | 0 |
| E1-R1-sem-p2-retry | 1 | 0 | 0 | 0 | 0 | 13 | 0 |
| E1-R1-sem-desc-p1-retry | 0 | 0 | 0 | 0 | 0 | 19 | 0 |
| E1-R2-sem-p1-retry | 0 | 0 | 0 | 0 | 0 | 19 | 0 |
| E1-R3b-sem-p1-retry | 2 | 0 | 0 | 0 | 0 | 20 | 0 |
| E2-A1-1-sem-p1-retry | 0 | 0 | 0 | 6 | 0 | 14 | 0 |
| E2-A1-2-sem-p1-retry | 0 | 0 | 0 | 3 | 0 | 14 | 0 |
| E2-A1-3-sem-p1-retry | 0 | 0 | 1 | 1 | 0 | 15 | 0 |
| E3-page-sem-p1-retry | 0 | 0 | 0 | 2 | 0 | 3 | 0 |
| E3-oracle-sem-p1-retry | 0 | 0 | 1 | 0 | 0 | 2 | 0 |
| E4-mobile-sem-p1-retry | 0 | 0 | 0 | 1 | 0 | 2 | 0 |
| 합계 | 4 | 0 | 2 | 13 | 0 | 131 | 0 |

출처:
- `results/revision/semantic_scores/{out_id}-retry/grades.jsonl`

### 2.2 원래 잘린 응답의 참고값(label_if_parsed) → 재채점 라벨

label_if_parsed = 잘린 문장에서 유형 이름이 언급되어 원 채점기가 남긴 참고값(라벨로 쓰지 않았음).

| 원 참고값 | 재채점 라벨 | 건수 |
|---|---|---|
| (없음) | None | 122 |
| 용어 | 용어 | 9 |
| 용어 | None | 8 |
| (없음) | 대비 | 4 |
| (없음) | 용어 | 4 |
| 대비 | None | 1 |
| (없음) | 버튼 | 1 |
| 버튼 | 버튼 | 1 |

출처:
- `results/revision/semantic_scores/{out_id}/grades.jsonl`
- `results/revision/semantic_scores/{out_id}-retry/grades.jsonl`

### 2.3 키워드·string_match 판정 → 재채점 라벨

| 키워드 / string_match | 재채점 라벨 | 건수 |
|---|---|---|
| (키워드 없음) | None | 112 |
| sm=1(접속하기) | None | 19 |
| (키워드 없음) | 용어 | 12 |
| (키워드 없음) | 대비 | 3 |
| sm=1(접속하기) | 대비 | 1 |
| (키워드 없음) | 버튼 | 1 |
| sm=1(접속하기) | 용어 | 1 |
| sm=1(접속하기) | 버튼 | 1 |

출처:
- `scoring/issue_table.py`
- `results/revision/semantic_scores/{out_id}-retry/grades.jsonl`

### 2.4 이슈가 속한 페이지의 주입 유형 → 재채점 라벨 (주입 유형 2개면 둘 다 셈)

| 페이지 주입 유형 | 재채점 라벨 | 건수 |
|---|---|---|
| 버튼 | None | 18 |
| 버튼 | 버튼 | 2 |
| 중복ID | None | 15 |
| 중복ID | 용어 | 5 |
| 중복ID | 버튼 | 1 |
| 모바일 | None | 15 |
| 모바일 | 용어 | 2 |
| 모바일 | 대비 | 1 |
| 대비 | None | 69 |
| 대비 | 대비 | 4 |
| 용어 | None | 34 |
| 용어 | 용어 | 6 |
| 용어 | 대비 | 3 |
| 용어 | 버튼 | 1 |
| 대조군 | None | 11 |
| 대조군 | 용어 | 4 |

출처:
- `results/revision/ground_truth.csv`
- `results/revision/semantic_scores/{out_id}-retry/grades.jsonl`

## 3. 비용 (배치 단가 입력 $1/1M, 출력 $5/1M)

| 재채점 out_id | 건 | 입력 토큰 | 출력 토큰 | 최대 출력 | USD |
|---|---|---|---|---|---|
| E1-R1-sem-p1-retry | 11 | 10011 | 2123 | 243 | 0.0206 |
| E1-R1-sem-p2-retry | 14 | 12567 | 2139 | 224 | 0.0233 |
| E1-R1-sem-desc-p1-retry | 19 | 15011 | 3830 | 318 | 0.0342 |
| E1-R2-sem-p1-retry | 19 | 17124 | 3394 | 267 | 0.0341 |
| E1-R3b-sem-p1-retry | 22 | 19767 | 4286 | 308 | 0.0412 |
| E2-A1-1-sem-p1-retry | 20 | 17788 | 3399 | 356 | 0.0348 |
| E2-A1-2-sem-p1-retry | 17 | 15107 | 3287 | 313 | 0.0315 |
| E2-A1-3-sem-p1-retry | 17 | 15185 | 3081 | 303 | 0.0306 |
| E3-page-sem-p1-retry | 5 | 4355 | 964 | 319 | 0.0092 |
| E3-oracle-sem-p1-retry | 3 | 2561 | 227 | 200 | 0.0037 |
| E4-mobile-sem-p1-retry | 3 | 2531 | 192 | 163 | 0.0035 |
| 합계 | 150 | 132007 | 26922 | 356 | 0.2666 |

출력 토큰 최소/중앙/최대: 10 / 191.0 / 356 (max_tokens 800).

출처:
- `results/revision/semantic_scores/{out_id}-retry/grades.jsonl`

## 4. 모델 버전과 호출 날짜

응답 model 문자열: claude-sonnet-5-5 (모든 레코드), 요청 max_tokens: [800].

| 재채점 out_id | 이벤트 | batch_id 끝 8자 | 시각 (UTC) |
|---|---|---|---|
| E1-R1-sem-p1-retry | submitted | CEZuBHw9 | 2026-11-13T17:38:47 |
| E1-R1-sem-p1-retry | collected | CEZuBHw9 | 2026-11-13T17:45:24 |
| E1-R1-sem-p2-retry | submitted | kUYcwWdB | 2026-11-13T17:39:28 |
| E1-R1-sem-p2-retry | collected | kUYcwWdB | 2026-11-13T17:45:35 |
| E1-R1-sem-desc-p1-retry | submitted | t8qqEVxX | 2026-11-13T17:39:36 |
| E1-R1-sem-desc-p1-retry | collected | t8qqEVxX | 2026-11-13T17:45:47 |
| E1-R2-sem-p1-retry | submitted | XBcsnJBd | 2026-11-13T17:39:44 |
| E1-R2-sem-p1-retry | collected | XBcsnJBd | 2026-11-13T17:45:56 |
| E1-R3b-sem-p1-retry | submitted | yCcUhmrq | 2026-11-13T17:39:52 |
| E1-R3b-sem-p1-retry | collected | yCcUhmrq | 2026-11-13T17:46:05 |
| E2-A1-1-sem-p1-retry | submitted | nQQo3uRJ | 2026-11-13T17:40:00 |
| E2-A1-1-sem-p1-retry | collected | nQQo3uRJ | 2026-11-13T17:46:13 |
| E2-A1-2-sem-p1-retry | submitted | xeCcW2iG | 2026-11-13T17:40:07 |
| E2-A1-2-sem-p1-retry | collected | xeCcW2iG | 2026-11-13T17:46:22 |
| E2-A1-3-sem-p1-retry | submitted | sQmEjhdG | 2026-11-13T17:40:14 |
| E2-A1-3-sem-p1-retry | collected | sQmEjhdG | 2026-11-13T17:46:30 |
| E3-page-sem-p1-retry | submitted | 7ayFtk4F | 2026-11-13T17:40:22 |
| E3-page-sem-p1-retry | collected | 7ayFtk4F | 2026-11-13T17:46:38 |
| E3-oracle-sem-p1-retry | submitted | CcWrkyBM | 2026-11-13T17:40:29 |
| E3-oracle-sem-p1-retry | collected | CcWrkyBM | 2026-11-13T17:46:47 |
| E4-mobile-sem-p1-retry | submitted | 8TtPbEcJ | 2026-11-13T17:40:37 |
| E4-mobile-sem-p1-retry | collected | 8TtPbEcJ | 2026-11-13T17:46:55 |

출처:
- `results/revision/semantic_scores/{out_id}-retry/batches.jsonl`
- `results/revision/semantic_scores/{out_id}-retry/grades.jsonl`

## 5. 병합 통합 표: 재채점으로 채운 건수 (pass1, 유형별)

`scoring/issue_table_merged.py` 로 run 별 CSV 를 `results/revision/issue_tables_merged/{run}.csv` 에 썼다.

| run | 이슈 | 재채점으로 채움 | 대비 | 모바일 | 버튼 | 용어 | 중복ID | None | 미해결 |
|---|---|---|---|---|---|---|---|---|---|
| E1-R1 | 676 | 11 | 1 | 0 | 0 | 0 | 0 | 10 | 0 |
| E1-R2 | 674 | 19 | 0 | 0 | 0 | 0 | 0 | 19 | 0 |
| E1-R3b | 651 | 22 | 2 | 0 | 0 | 0 | 0 | 20 | 0 |
| E2-A1-1 | 544 | 20 | 0 | 0 | 0 | 6 | 0 | 14 | 0 |
| E2-A1-2 | 579 | 17 | 0 | 0 | 0 | 3 | 0 | 14 | 0 |
| E2-A1-3 | 534 | 17 | 0 | 0 | 1 | 1 | 0 | 15 | 0 |
| E3-page | 168 | 5 | 0 | 0 | 0 | 2 | 0 | 3 | 0 |
| E3-oracle | 98 | 3 | 0 | 0 | 1 | 0 | 0 | 2 | 0 |
| E4-mobile | 300 | 3 | 0 | 0 | 0 | 1 | 0 | 2 | 0 |

출처:
- `results/revision/issue_tables_merged/{run}.csv`
- `scoring/issue_table_merged.py`

## 6. 유형별 TP / FP 페이지 수: 재채점 포함(주), 원 규칙(잘림 = 음성), 잘림 페이지 제외

라벨 nominal, 페이지 = run_meta pages, 실패 페이지 음성. 잘림 페이지 제외 = 원 채점에서 잘린 이슈가 있는 페이지를
그 run 의 모든 셀에서 뺌(양성 수도 그 집합 기준).

| run | 유형 | 양성 | 재채점 포함 TP/FP (주) | 원 규칙 TP/FP | 양성(제외 후) | 잘림 제외 TP/FP |
|---|---|---|---|---|---|---|
| E1-R1 | 대비 | 44 | 44 / 0 | 44 / 0 | 35 | 35 / 0 |
| E1-R1 | 모바일 | 56 | 56 / 0 | 56 / 0 | 56 | 56 / 0 |
| E1-R1 | 버튼 | 46 | 46 / 0 | 46 / 0 | 46 | 46 / 0 |
| E1-R1 | 용어 | 45 | 0 / 0 | 0 / 0 | 41 | 0 / 0 |
| E1-R1 | 중복ID | 40 | 39 / 0 | 39 / 0 | 40 | 39 / 0 |
| E1-R2 | 대비 | 44 | 44 / 0 | 44 / 0 | 35 | 35 / 0 |
| E1-R2 | 모바일 | 56 | 56 / 0 | 56 / 0 | 54 | 54 / 0 |
| E1-R2 | 버튼 | 46 | 46 / 0 | 46 / 0 | 45 | 45 / 0 |
| E1-R2 | 용어 | 45 | 0 / 0 | 0 / 0 | 41 | 0 / 0 |
| E1-R2 | 중복ID | 40 | 40 / 0 | 40 / 0 | 40 | 40 / 0 |
| E1-R3b | 대비 | 44 | 44 / 0 | 44 / 0 | 30 | 30 / 0 |
| E1-R3b | 모바일 | 56 | 56 / 0 | 56 / 0 | 50 | 50 / 0 |
| E1-R3b | 버튼 | 46 | 46 / 0 | 46 / 0 | 44 | 44 / 0 |
| E1-R3b | 용어 | 45 | 0 / 0 | 0 / 0 | 40 | 0 / 0 |
| E1-R3b | 중복ID | 40 | 39 / 0 | 39 / 0 | 40 | 39 / 0 |
| E2-A1-1 | 대비 | 44 | 44 / 0 | 44 / 0 | 39 | 39 / 0 |
| E2-A1-1 | 모바일 | 56 | 56 / 2 | 56 / 2 | 53 | 53 / 1 |
| E2-A1-1 | 버튼 | 46 | 46 / 0 | 46 / 0 | 42 | 42 / 0 |
| E2-A1-1 | 용어 | 45 | 5 / 7 | 3 / 3 | 40 | 3 / 3 |
| E2-A1-1 | 중복ID | 40 | 40 / 0 | 40 / 0 | 35 | 35 / 0 |
| E2-A1-2 | 대비 | 44 | 44 / 0 | 44 / 0 | 38 | 38 / 0 |
| E2-A1-2 | 모바일 | 56 | 56 / 1 | 56 / 1 | 56 | 56 / 0 |
| E2-A1-2 | 버튼 | 46 | 46 / 0 | 46 / 0 | 42 | 42 / 0 |
| E2-A1-2 | 용어 | 45 | 9 / 3 | 8 / 1 | 42 | 8 / 1 |
| E2-A1-2 | 중복ID | 40 | 40 / 0 | 40 / 0 | 35 | 35 / 0 |
| E2-A1-3 | 대비 | 44 | 44 / 0 | 44 / 0 | 37 | 37 / 0 |
| E2-A1-3 | 모바일 | 56 | 56 / 2 | 56 / 2 | 55 | 55 / 2 |
| E2-A1-3 | 버튼 | 46 | 46 / 0 | 46 / 0 | 41 | 41 / 0 |
| E2-A1-3 | 용어 | 45 | 7 / 2 | 6 / 2 | 43 | 6 / 2 |
| E2-A1-3 | 중복ID | 40 | 40 / 0 | 40 / 0 | 34 | 34 / 0 |
| E3-page | 대비 | 5 | 5 / 0 | 5 / 0 | 5 | 5 / 0 |
| E3-page | 모바일 | 10 | 8 / 0 | 8 / 0 | 9 | 7 / 0 |
| E3-page | 버튼 | 8 | 8 / 0 | 8 / 0 | 8 | 8 / 0 |
| E3-page | 용어 | 45 | 13 / 0 | 11 / 0 | 40 | 11 / 0 |
| E3-page | 중복ID | 5 | 4 / 0 | 4 / 0 | 5 | 4 / 0 |
| E3-oracle | 대비 | 5 | 4 / 0 | 4 / 0 | 5 | 4 / 0 |
| E3-oracle | 모바일 | 10 | 10 / 0 | 10 / 0 | 10 | 10 / 0 |
| E3-oracle | 버튼 | 8 | 7 / 0 | 7 / 0 | 6 | 5 / 0 |
| E3-oracle | 용어 | 45 | 24 / 0 | 24 / 0 | 42 | 24 / 0 |
| E3-oracle | 중복ID | 5 | 3 / 0 | 3 / 0 | 4 | 3 / 0 |
| E4-mobile | 대비 | 8 | 8 / 0 | 8 / 0 | 8 | 8 / 0 |
| E4-mobile | 모바일 | 56 | 56 / 0 | 56 / 0 | 54 | 54 / 0 |
| E4-mobile | 버튼 | 10 | 10 / 0 | 10 / 0 | 10 | 10 / 0 |
| E4-mobile | 용어 | 10 | 2 / 2 | 2 / 1 | 10 | 2 / 1 |
| E4-mobile | 중복ID | 7 | 7 / 0 | 7 / 0 | 6 | 6 / 0 |

출처:
- `results/revision/runs/{run}/run_meta.json`
- `results/revision/ground_truth.csv`
- `results/revision/issue_tables_merged/{run}.csv`

## 7. E1-R1 pass1 대 pass2, pass1 대 description-only

포함 = 비성공(잘림 등)을 별도 범주로 둠, 제외 = 두 쪽 모두 6분류 라벨이 있는 이슈만. Cohen's kappa 는 기술 지표(검정 아님).

| 비교 | 기준 | 이슈(포함) | 일치율 | kappa | 이슈(제외) | 일치율 | kappa |
|---|---|---|---|---|---|---|---|
| pass1 대 pass2 | 원 기준 | 676 | 0.993 | 0.985 | 661 | 1.000 | 1.000 |
| pass1 대 pass2 | 재채점 포함 | 676 | 1.000 | 1.000 | 676 | 1.000 | 1.000 |
| pass1 대 description-only | 원 기준 | 676 | 0.985 | 0.971 | 657 | 0.997 | 0.994 |
| pass1 대 description-only | 재채점 포함 | 676 | 0.994 | 0.988 | 676 | 0.994 | 0.988 |

재채점 포함 기준 불일치 쌍:

| 비교 | pass1 | 상대 | 건수 |
|---|---|---|---|
| desc-only | 대비 | None | 2 |
| desc-only | None | 용어 | 2 |

출처:
- `results/revision/semantic_scores/E1-R1-sem-p1/grades.jsonl`
- `results/revision/semantic_scores/E1-R1-sem-p2/grades.jsonl`
- `results/revision/semantic_scores/E1-R1-sem-desc-p1/grades.jsonl`
- `results/revision/semantic_scores/{위 3개}-retry/grades.jsonl`

