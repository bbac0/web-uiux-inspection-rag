# 정리 보고서: A2, A3, E3, E4 (2026-11-13)

API 호출 없음. 기술 집계만(통계 검정 없음). 모든 숫자는 각 표 아래 출처 파일에서 읽었다.
E3-oracle 은 문서상 관련 조항 제공(related-clause) 조건이다(플래그 이름만 oracle). E3-fixed = E1-R1 재사용.

## 1. run 표

| run | 상태 | 동시 | 요청 | 기록 | ok | 파싱 실패 | 오류율 |
|---|---|---|---|---|---|---|---|
| E2-A2 | complete | 2 | 200 | 200 | 200 | 0 | 0.0% |
| E2-A3 | complete | 2 | 200 | 200 | 200 | 0 | 0.0% |
| E3-page | complete | 2 | 84 | 84 | 84 | 0 | 0.0% |
| E3-oracle | complete | 2 | 84 | 84 | 84 | 0 | 0.0% |
| E4-mobile | complete | 2 | 95 | 95 | 95 | 0 | 0.0% |

동시 실행은 다섯 run 모두 계획(2건)과 같았다. 오류율 = (api/rag/acquisition 오류 기록 수) / 기록 수.

| run | 이슈 합계 | 페이지당 평균 | 범위 | 비용 | RAG 청크 | 조건 |
|---|---|---|---|---|---|---|
| E2-A2 | 898 | 4.49 | 2~8 | $1.6985 | 4청크×200 | modality=html |
| E2-A3 | 518 | 2.59 | 1~5 | $1.6356 | 4청크×200 | modality=screenshot |
| E3-page | 168 | 2.00 | 0~5 | $0.7719 | 4청크×84 | modality=both, query=page |
| E3-oracle | 98 | 1.17 | 0~3 | $0.7732 | 2청크×84 | modality=both, query=oracle |
| E4-mobile | 300 | 3.16 | 1~5 | $0.7714 | 4청크×95 | modality=both, viewport=390x844 |

출처: run 별 `results/revision/runs/{run}/` 의
`calls.jsonl`, `reports.jsonl`, `run_meta.json`, `summary.json`

## 2. A2(HTML만), A3(스크린샷만): 200페이지

A2·A3 는 의미 채점 대상이 아니다(사전 지정 13항). 키워드·string_match 만.

### TP 페이지 수 (1/2)

| 유형 | 라벨 | 양성 | R1 | R2 | R3b | A1-1 | A1-2 |
|---|---|---|---|---|---|---|---|
| 대비 | nominal | 44 | 44 | 44 | 44 | 44 | 44 |
| 대비 | effective | 44 | 44 | 44 | 44 | 44 | 44 |
| 모바일 | nominal | 56 | 56 | 56 | 56 | 56 | 56 |
| 모바일 | effective | 56 | 56 | 56 | 56 | 56 | 56 |
| 버튼 | nominal | 46 | 40 | 40 | 40 | 38 | 34 |
| 버튼 | effective | 20 | 20 | 20 | 20 | 20 | 20 |
| 용어 | nominal | 45 | 12 | 14 | 12 | 17 | 19 |
| 용어 | effective | 42 | 12 | 14 | 12 | 17 | 19 |
| 중복 ID | nominal | 40 | 34 | 37 | 33 | 31 | 34 |
| 중복 ID | effective | 40 | 34 | 37 | 33 | 31 | 34 |
| 용어 string_match | nominal | 45 | 12 | 14 | 12 | 17 | 19 |
| 용어 string_match | effective | 42 | 12 | 14 | 12 | 17 | 19 |

### TP 페이지 수 (2/2)

| 유형 | 라벨 | 양성 | A1-3 | A2 | A3 |
|---|---|---|---|---|---|
| 대비 | nominal | 44 | 44 | 44 | 29 |
| 대비 | effective | 44 | 44 | 44 | 29 |
| 모바일 | nominal | 56 | 56 | 56 | 6 |
| 모바일 | effective | 56 | 56 | 56 | 6 |
| 버튼 | nominal | 46 | 38 | 40 | 0 |
| 버튼 | effective | 20 | 20 | 15 | 0 |
| 용어 | nominal | 45 | 12 | 7 | 14 |
| 용어 | effective | 42 | 12 | 7 | 14 |
| 중복 ID | nominal | 40 | 34 | 39 | 3 |
| 중복 ID | effective | 40 | 34 | 39 | 3 |
| 용어 string_match | nominal | 45 | 12 | 5 | 14 |
| 용어 string_match | effective | 42 | 12 | 5 | 14 |

### FP 페이지 수 (1/2)

| 유형 | 라벨 | 양성 | R1 | R2 | R3b | A1-1 | A1-2 |
|---|---|---|---|---|---|---|---|
| 대비 | nominal | 44 | 3 | 4 | 2 | 25 | 21 |
| 대비 | effective | 44 | 3 | 4 | 2 | 25 | 21 |
| 모바일 | nominal | 56 | 32 | 32 | 28 | 49 | 52 |
| 모바일 | effective | 56 | 32 | 32 | 28 | 49 | 52 |
| 버튼 | nominal | 46 | 0 | 0 | 0 | 0 | 0 |
| 버튼 | effective | 20 | 20 | 20 | 20 | 18 | 14 |
| 용어 | nominal | 45 | 0 | 0 | 0 | 0 | 0 |
| 용어 | effective | 42 | 0 | 0 | 0 | 0 | 0 |
| 중복 ID | nominal | 40 | 0 | 0 | 0 | 3 | 5 |
| 중복 ID | effective | 40 | 0 | 0 | 0 | 3 | 5 |
| 용어 string_match | nominal | 45 | 0 | 0 | 0 | 0 | 0 |
| 용어 string_match | effective | 42 | 0 | 0 | 0 | 0 | 0 |

### FP 페이지 수 (2/2)

| 유형 | 라벨 | 양성 | A1-3 | A2 | A3 |
|---|---|---|---|---|---|
| 대비 | nominal | 44 | 23 | 5 | 4 |
| 대비 | effective | 44 | 23 | 5 | 4 |
| 모바일 | nominal | 56 | 49 | 58 | 11 |
| 모바일 | effective | 56 | 49 | 58 | 11 |
| 버튼 | nominal | 46 | 0 | 0 | 0 |
| 버튼 | effective | 20 | 18 | 25 | 0 |
| 용어 | nominal | 45 | 0 | 0 | 0 |
| 용어 | effective | 42 | 0 | 0 | 0 |
| 중복 ID | nominal | 40 | 2 | 1 | 13 |
| 중복 ID | effective | 40 | 2 | 1 | 13 |
| 용어 string_match | nominal | 45 | 0 | 0 | 0 |
| 용어 string_match | effective | 42 | 0 | 0 | 0 |

출처:
- run 별 `results/revision/runs/{run}/reports.jsonl` (판정: `scoring/issue_table.py`)
- `results/revision/ground_truth.csv`

## 3. E3: 용어 위반 45 + 대조군 39 = 84페이지

같은 84페이지에서 기존 run 결과를 나란히 계산했다. R1 = E3-fixed.
용어 위반 페이지 중 일부에는 다른 유형 결함도 함께 주입되어 있어 다른 유형의 양성도 있다(양성 열).

### TP 페이지 수 (1/2)

| 유형 | 라벨 | 양성 | R1 | R2 | R3b | E3-page | E3-oracle |
|---|---|---|---|---|---|---|---|
| 대비 | nominal | 5 | 5 | 5 | 5 | 5 | 4 |
| 대비 | effective | 5 | 5 | 5 | 5 | 5 | 4 |
| 모바일 | nominal | 10 | 10 | 10 | 10 | 8 | 10 |
| 모바일 | effective | 10 | 10 | 10 | 10 | 8 | 10 |
| 버튼 | nominal | 8 | 7 | 7 | 7 | 6 | 4 |
| 버튼 | effective | 3 | 3 | 3 | 3 | 3 | 3 |
| 용어 | nominal | 45 | 12 | 14 | 12 | 16 | 34 |
| 용어 | effective | 42 | 12 | 14 | 12 | 16 | 34 |
| 중복 ID | nominal | 5 | 5 | 5 | 4 | 4 | 3 |
| 중복 ID | effective | 5 | 5 | 5 | 4 | 4 | 3 |
| 용어 string_match | nominal | 45 | 12 | 14 | 12 | 16 | 34 |
| 용어 string_match | effective | 42 | 12 | 14 | 12 | 16 | 34 |

### TP 페이지 수 (2/2)

| 유형 | 라벨 | 양성 | A1-1 | A1-2 | A1-3 |
|---|---|---|---|---|---|
| 대비 | nominal | 5 | 5 | 5 | 5 |
| 대비 | effective | 5 | 5 | 5 | 5 |
| 모바일 | nominal | 10 | 10 | 10 | 10 |
| 모바일 | effective | 10 | 10 | 10 | 10 |
| 버튼 | nominal | 8 | 7 | 6 | 8 |
| 버튼 | effective | 3 | 3 | 3 | 3 |
| 용어 | nominal | 45 | 17 | 19 | 12 |
| 용어 | effective | 42 | 17 | 19 | 12 |
| 중복 ID | nominal | 5 | 4 | 5 | 5 |
| 중복 ID | effective | 5 | 4 | 5 | 5 |
| 용어 string_match | nominal | 45 | 17 | 19 | 12 |
| 용어 string_match | effective | 42 | 17 | 19 | 12 |

### FP 페이지 수 (1/2)

| 유형 | 라벨 | 양성 | R1 | R2 | R3b | E3-page | E3-oracle |
|---|---|---|---|---|---|---|---|
| 대비 | nominal | 5 | 3 | 4 | 2 | 0 | 0 |
| 대비 | effective | 5 | 3 | 4 | 2 | 0 | 0 |
| 모바일 | nominal | 10 | 10 | 10 | 8 | 9 | 5 |
| 모바일 | effective | 10 | 10 | 10 | 8 | 9 | 5 |
| 버튼 | nominal | 8 | 0 | 0 | 0 | 0 | 0 |
| 버튼 | effective | 3 | 4 | 4 | 4 | 3 | 1 |
| 용어 | nominal | 45 | 0 | 0 | 0 | 0 | 0 |
| 용어 | effective | 42 | 0 | 0 | 0 | 0 | 0 |
| 중복 ID | nominal | 5 | 0 | 0 | 0 | 1 | 0 |
| 중복 ID | effective | 5 | 0 | 0 | 0 | 1 | 0 |
| 용어 string_match | nominal | 45 | 0 | 0 | 0 | 0 | 0 |
| 용어 string_match | effective | 42 | 0 | 0 | 0 | 0 | 0 |

### FP 페이지 수 (2/2)

| 유형 | 라벨 | 양성 | A1-1 | A1-2 | A1-3 |
|---|---|---|---|---|---|
| 대비 | nominal | 5 | 10 | 8 | 8 |
| 대비 | effective | 5 | 10 | 8 | 8 |
| 모바일 | nominal | 10 | 26 | 30 | 28 |
| 모바일 | effective | 10 | 26 | 30 | 28 |
| 버튼 | nominal | 8 | 0 | 0 | 0 |
| 버튼 | effective | 3 | 4 | 3 | 5 |
| 용어 | nominal | 45 | 0 | 0 | 0 |
| 용어 | effective | 42 | 0 | 0 | 0 |
| 중복 ID | nominal | 5 | 1 | 4 | 1 |
| 중복 ID | effective | 5 | 1 | 4 | 1 |
| 용어 string_match | nominal | 45 | 0 | 0 | 0 |
| 용어 string_match | effective | 42 | 0 | 0 | 0 |

출처:
- run 별 `results/revision/runs/{run}/reports.jsonl` (판정: `scoring/issue_table.py`)
- `results/revision/ground_truth.csv`

## 4. E4: 모바일 결함 56 + 대조군 39 = 95페이지

effective 라벨은 run 뷰포트 기준: E4 는 390x844(effective_390), 나머지는 1280(effective_1280). 양성 열은 1280/390 순.

### TP 페이지 수 (1/2)

| 유형 | 라벨 | 양성 (1280/390) | R1 | R2 | R3b | E4 | A1-1 |
|---|---|---|---|---|---|---|---|
| 대비 | nominal | 8/8 | 8 | 8 | 8 | 8 | 8 |
| 대비 | effective | 8/8 | 8 | 8 | 8 | 8 | 8 |
| 모바일 | nominal | 56/56 | 56 | 56 | 56 | 56 | 56 |
| 모바일 | effective | 56/56 | 56 | 56 | 56 | 56 | 56 |
| 버튼 | nominal | 10/10 | 10 | 10 | 10 | 9 | 9 |
| 버튼 | effective | 3/3 | 3 | 3 | 3 | 3 | 3 |
| 용어 | nominal | 10/10 | 0 | 1 | 1 | 3 | 1 |
| 용어 | effective | 10/10 | 0 | 1 | 1 | 3 | 1 |
| 중복 ID | nominal | 7/7 | 5 | 7 | 5 | 7 | 5 |
| 중복 ID | effective | 7/7 | 5 | 7 | 5 | 7 | 5 |
| 용어 string_match | nominal | 10/10 | 0 | 1 | 1 | 3 | 1 |
| 용어 string_match | effective | 10/10 | 0 | 1 | 1 | 3 | 1 |

### TP 페이지 수 (2/2)

| 유형 | 라벨 | 양성 (1280/390) | A1-2 | A1-3 |
|---|---|---|---|---|
| 대비 | nominal | 8/8 | 8 | 8 |
| 대비 | effective | 8/8 | 8 | 8 |
| 모바일 | nominal | 56/56 | 56 | 56 |
| 모바일 | effective | 56/56 | 56 | 56 |
| 버튼 | nominal | 10/10 | 9 | 9 |
| 버튼 | effective | 3/3 | 3 | 3 |
| 용어 | nominal | 10/10 | 2 | 0 |
| 용어 | effective | 10/10 | 2 | 0 |
| 중복 ID | nominal | 7/7 | 7 | 7 |
| 중복 ID | effective | 7/7 | 7 | 7 |
| 용어 string_match | nominal | 10/10 | 2 | 0 |
| 용어 string_match | effective | 10/10 | 2 | 0 |

### FP 페이지 수 (1/2)

| 유형 | 라벨 | 양성 (1280/390) | R1 | R2 | R3b | E4 | A1-1 |
|---|---|---|---|---|---|---|---|
| 대비 | nominal | 8/8 | 1 | 1 | 1 | 0 | 16 |
| 대비 | effective | 8/8 | 1 | 1 | 1 | 0 | 16 |
| 모바일 | nominal | 56/56 | 3 | 2 | 1 | 3 | 12 |
| 모바일 | effective | 56/56 | 3 | 2 | 1 | 3 | 12 |
| 버튼 | nominal | 10/10 | 0 | 0 | 0 | 0 | 0 |
| 버튼 | effective | 3/3 | 7 | 7 | 7 | 6 | 6 |
| 용어 | nominal | 10/10 | 0 | 0 | 0 | 0 | 0 |
| 용어 | effective | 10/10 | 0 | 0 | 0 | 0 | 0 |
| 중복 ID | nominal | 7/7 | 0 | 0 | 0 | 0 | 3 |
| 중복 ID | effective | 7/7 | 0 | 0 | 0 | 0 | 3 |
| 용어 string_match | nominal | 10/10 | 0 | 0 | 0 | 0 | 0 |
| 용어 string_match | effective | 10/10 | 0 | 0 | 0 | 0 | 0 |

### FP 페이지 수 (2/2)

| 유형 | 라벨 | 양성 (1280/390) | A1-2 | A1-3 |
|---|---|---|---|---|
| 대비 | nominal | 8/8 | 10 | 12 |
| 대비 | effective | 8/8 | 10 | 12 |
| 모바일 | nominal | 56/56 | 15 | 13 |
| 모바일 | effective | 56/56 | 15 | 13 |
| 버튼 | nominal | 10/10 | 0 | 0 |
| 버튼 | effective | 3/3 | 6 | 6 |
| 용어 | nominal | 10/10 | 0 | 0 |
| 용어 | effective | 10/10 | 0 | 0 |
| 중복 ID | nominal | 7/7 | 5 | 2 |
| 중복 ID | effective | 7/7 | 5 | 2 |
| 용어 string_match | nominal | 10/10 | 0 | 0 |
| 용어 string_match | effective | 10/10 | 0 | 0 |

출처:
- run 별 `results/revision/runs/{run}/reports.jsonl` (판정: `scoring/issue_table.py`)
- `results/revision/ground_truth.csv`

## 5. 지출 합계

### 5.1 Gemini (생성 호출, 누적)

| run | 조건 | 상태 | 기록 호출 | 비용 (USD) |
|---|---|---|---|---|
| pilot-01 | pilot | complete | 10 | 0.0000 |
| pilot-02 | pilot | complete | 10 | 0.0923 |
| E1-R1 | E1 | complete | 200 | 2.0137 |
| E2-A1-1 | E2-A1 | complete | 200 | 1.4168 |
| E1-R2 | E1 | complete | 200 | 1.6646 |
| E2-A1-2 | E2-A1 | complete | 200 | 1.4083 |
| E1-R3 | E1 | aborted | 160 | 1.2990 |
| E1-R3b | E1 | complete | 200 | 1.8736 |
| E2-A1-3 | E2-A1 | complete | 200 | 1.4869 |
| E2-A2 | E2-A2 | complete | 200 | 1.6985 |
| E2-A3 | E2-A3 | complete | 200 | 1.6356 |
| E3-page | E3-page | complete | 84 | 0.7719 |
| E3-oracle | E3-oracle | complete | 84 | 0.7732 |
| E4-mobile | E4-mobile | complete | 95 | 0.7714 |
| e9-pilot-fixed | E9 pilot | complete | 8 | 0.0839 |
| e9-pilot-fixedlong | E9 pilot | complete | 8 | 0.0925 |
| e9-pilot-norag | E9 pilot | complete | 8 | 0.0763 |
| e9-pilot-page | E9 pilot | complete | 8 | 0.0822 |
| e9-pilot-related | E9 pilot | complete | 8 | 0.0738 |

- Gemini 기록 합계: $17.3145 (testbed_200 run $16.9058 + E9 파일럿 $0.4087)
- E1-R3 미기록 추정 포함 범위: $17.3226 (가능성 높은 값) ~ $17.3580 (상한)
- 고정 질의 임베딩 1회, File API 업로드는 비용 기록 대상이 아니다.

출처:
- `results/revision/tables/spend_summary.json` (`experiments/revision/spend_summary.py` 로 갱신)
- `results/revision/runs_e9_pilot/{run}/calls.jsonl`

### 5.2 Anthropic (의미 채점 시험 호출, 표준가 입력 $2/1M, 출력 $10/1M)

| 항목 | 호출 | 입력 토큰 합 | 출력 토큰 합 | 비용 (USD) |
|---|---|---|---|---|
| probe-E1-R1 (시험 호출, 채점 결과 아님) | 20 | 17,842 | 254 | 0.0382 |

출처: `results/revision/semantic_scores/probe-E1-R1/probe.jsonl`

## 6. 이 보고서에 사용한 파일

| 경로 | SHA-256 앞 16자리 |
|---|---|
| `results/revision/runs/E3-page/run_meta.json` | fabeadb47bdcfb8e |
| `results/revision/runs/E4-mobile/run_meta.json` | d94adb9b7d10228b |
| `results/revision/runs/E3-oracle/run_meta.json` | a6c0162daf77f4a3 |
| `results/revision/runs/E2-A2/calls.jsonl` | 063ad65fa65e4009 |
| `results/revision/runs/E2-A2/reports.jsonl` | 4bc77de321158274 |
| `results/revision/runs/E2-A2/run_meta.json` | 4cc2a2dcd7d2f56e |
| `results/revision/runs/E2-A2/summary.json` | f18fa4e2848ada39 |
| `results/revision/runs/E2-A3/calls.jsonl` | 1731d237070c1a22 |
| `results/revision/runs/E2-A3/reports.jsonl` | 5503e3d4501e15c8 |
| `results/revision/runs/E2-A3/run_meta.json` | 246e2fe480e16c81 |
| `results/revision/runs/E2-A3/summary.json` | c41e45d334ef5110 |
| `results/revision/runs/E3-page/calls.jsonl` | 363620cb6e8d64d2 |
| `results/revision/runs/E3-page/reports.jsonl` | 3706396731770d7b |
| `results/revision/runs/E3-page/summary.json` | 7973a01ce11f3b92 |
| `results/revision/runs/E3-oracle/calls.jsonl` | e3d13fcc738ef111 |
| `results/revision/runs/E3-oracle/reports.jsonl` | 1197b94fe179024c |
| `results/revision/runs/E3-oracle/summary.json` | 81706dc47d24c200 |
| `results/revision/runs/E4-mobile/calls.jsonl` | 0b8555e0b4e3a5ff |
| `results/revision/runs/E4-mobile/reports.jsonl` | a951a944c9ddbe7c |
| `results/revision/runs/E4-mobile/summary.json` | ee3765b7abafff43 |
| `results/revision/ground_truth.csv` | fe307fdcd57ba5de |
| `results/revision/runs/E1-R1/reports.jsonl` | ff84acd8d72e2f22 |
| `results/revision/runs/E1-R2/reports.jsonl` | 06340b5e11edee0a |
| `results/revision/runs/E1-R3b/reports.jsonl` | 93486a70477d20a3 |
| `results/revision/runs/E2-A1-1/reports.jsonl` | 577034366177ce2e |
| `results/revision/runs/E2-A1-2/reports.jsonl` | c24815495b66cde1 |
| `results/revision/runs/E2-A1-3/reports.jsonl` | 13a3311d63098f14 |
| `results/revision/tables/spend_summary.json` | ad440e312b8e63d5 |
| `results/revision/runs_e9_pilot/e9-pilot-fixed/calls.jsonl` | a70ebede07b7ae09 |
| `results/revision/runs_e9_pilot/e9-pilot-fixedlong/calls.jsonl` | 7818e3b4a7b27835 |
| `results/revision/runs_e9_pilot/e9-pilot-norag/calls.jsonl` | 6ec35e0e2648a081 |
| `results/revision/runs_e9_pilot/e9-pilot-page/calls.jsonl` | a45bffd918f1485f |
| `results/revision/runs_e9_pilot/e9-pilot-related/calls.jsonl` | 8abae09b78dd75f2 |
| `results/revision/semantic_scores/probe-E1-R1/probe.jsonl` | c0c6157f94a6ab11 |

생성 스크립트: `experiments/revision/clean_report_a2_e4.py`

