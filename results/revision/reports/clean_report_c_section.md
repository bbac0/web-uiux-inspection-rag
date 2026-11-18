# 정리 보고서 C절 (2026-11-13)

API 호출 없음. 모든 숫자는 각 표 아래 출처 파일에서 읽었다. 6절은 사전 지정 뒤에 추가한 강건성 분석,
7·8절은 탐색적 분석(사전 지정 아님)이다. 통계 검정은 하지 않았다.

## 6. 유형별 짝 템플릿 군집 부트스트랩 (RAG 켬 − 끔)

분석 상태: **added after seeing replicate results, before semantic scoring**.
B = 10,000, numpy default_rng 시드 20261111, 같은 재표집 템플릿을 두 조건에 적용, 백분위수 95% 구간.
주 비교 R1 − A1-1 (사전 지정), R2 − A1-2 와 R3b − A1-3 은 반복 재현.

### 6.0 합산 MCC (5유형 셀 합산, 키워드)

| 비교 | 역할 | 라벨 | MCC 차이 | 95% 구간 | LOTO 범위 |
|---|---|---|---|---|---|
| R1 − A1-1 | 주 비교 (사전 지정) | nominal | 0.097 | [0.043, 0.147] | 0.082~0.110 |
| R1 − A1-1 | 주 비교 (사전 지정) | effective | 0.079 | [0.022, 0.129] | 0.069~0.095 |
| R2 − A1-2 | 반복 재현 | nominal | 0.109 | [0.048, 0.173] | 0.083~0.123 |
| R2 − A1-2 | 반복 재현 | effective | 0.070 | [-0.009, 0.140] | 0.047~0.096 |
| R3b − A1-3 | 반복 재현 | nominal | 0.107 | [0.052, 0.156] | 0.095~0.123 |
| R3b − A1-3 | 반복 재현 | effective | 0.089 | [0.027, 0.141] | 0.075~0.111 |

주: **합산 MCC 는 서로 성격이 다른 유형(대비, 모바일, 버튼, 용어, 중복 ID)을 섞은 값**이다.
유형별 차이는 아래 6.1~6.6 에서 본다.

출처: `results/revision/e7/paired_cluster_bootstrap.csv`

### 6.1 대비 (키워드)

nominal = effective (같은 라벨 값)

| 비교 | 라벨 | 특이도 차이 [95% 구간] | 정밀도 차이 [95% 구간] | 재현율 차이 [95% 구간] |
|---|---|---|---|---|
| R1 − A1-1 | nominal | 0.141 [0.062, 0.234] | 0.298 [0.149, 0.437] | 0.000 [0.000, 0.000] |
| R2 − A1-2 | nominal | 0.109 [0.021, 0.216] | 0.240 [0.052, 0.442] | 0.000 [0.000, 0.000] |
| R3b − A1-3 | nominal | 0.135 [0.060, 0.216] | 0.300 [0.154, 0.440] | 0.000 [0.000, 0.000] |

출처: `results/revision/e7/paired_cluster_bootstrap.csv`

### 6.2 모바일 (키워드)

nominal = effective (같은 라벨 값)

| 비교 | 라벨 | 특이도 차이 [95% 구간] | 정밀도 차이 [95% 구간] | 재현율 차이 [95% 구간] |
|---|---|---|---|---|
| R1 − A1-1 | nominal | 0.118 [0.020, 0.229] | 0.103 [0.018, 0.205] | 0.000 [0.000, 0.000] |
| R2 − A1-2 | nominal | 0.139 [-0.020, 0.282] | 0.118 [-0.019, 0.229] | 0.000 [0.000, 0.000] |
| R3b − A1-3 | nominal | 0.146 [0.034, 0.262] | 0.133 [0.031, 0.244] | 0.000 [0.000, 0.000] |

출처: `results/revision/e7/paired_cluster_bootstrap.csv`

### 6.3 버튼 (키워드, effective)

effective 양성 20페이지

| 비교 | 라벨 | 특이도 차이 [95% 구간] | 정밀도 차이 [95% 구간] | 재현율 차이 [95% 구간] |
|---|---|---|---|---|
| R1 − A1-1 | effective | -0.011 [-0.053, 0.027] | -0.026 [-0.109, 0.072] | 0.000 [0.000, 0.000] |
| R2 − A1-2 | effective | -0.033 [-0.082, 0.006] | -0.088 [-0.200, 0.019] | 0.000 [0.000, 0.000] |
| R3b − A1-3 | effective | -0.011 [-0.037, 0.012] | -0.026 [-0.075, 0.038] | 0.000 [0.000, 0.000] |

출처: `results/revision/e7/paired_cluster_bootstrap.csv`

### 6.4 용어 (키워드)

nominal 양성 45, effective 양성 42

| 비교 | 라벨 | 특이도 차이 [95% 구간] | 정밀도 차이 [95% 구간] | 재현율 차이 [95% 구간] |
|---|---|---|---|---|
| R1 − A1-1 | nominal | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | -0.111 [-0.268, 0.054] |
| R1 − A1-1 | effective | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | -0.119 [-0.293, 0.057] |
| R2 − A1-2 | nominal | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | -0.111 [-0.304, 0.083] |
| R2 − A1-2 | effective | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | -0.119 [-0.326, 0.091] |
| R3b − A1-3 | nominal | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [-0.152, 0.176] |
| R3b − A1-3 | effective | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [-0.167, 0.189] |

출처: `results/revision/e7/paired_cluster_bootstrap.csv`

### 6.5 용어 (string_match, mention-based)

nominal 양성 45, effective 양성 42

| 비교 | 라벨 | 특이도 차이 [95% 구간] | 정밀도 차이 [95% 구간] | 재현율 차이 [95% 구간] |
|---|---|---|---|---|
| R1 − A1-1 | nominal | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | -0.111 [-0.268, 0.054] |
| R1 − A1-1 | effective | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | -0.119 [-0.293, 0.057] |
| R2 − A1-2 | nominal | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | -0.111 [-0.304, 0.083] |
| R2 − A1-2 | effective | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | -0.119 [-0.326, 0.091] |
| R3b − A1-3 | nominal | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [-0.152, 0.176] |
| R3b − A1-3 | effective | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [-0.167, 0.189] |

출처: `results/revision/e7/paired_cluster_bootstrap.csv`

### 6.6 중복 ID (키워드)

nominal = effective (같은 라벨 값)

| 비교 | 라벨 | 특이도 차이 [95% 구간] | 정밀도 차이 [95% 구간] | 재현율 차이 [95% 구간] |
|---|---|---|---|---|
| R1 − A1-1 | nominal | 0.019 [0.000, 0.038] | 0.088 [0.000, 0.188] | 0.075 [-0.067, 0.229] |
| R2 − A1-2 | nominal | 0.031 [0.000, 0.086] | 0.128 [0.000, 0.283] | 0.075 [0.000, 0.205] |
| R3b − A1-3 | nominal | 0.012 [0.000, 0.031] | 0.056 [0.000, 0.121] | -0.025 [-0.162, 0.097] |

출처: `results/revision/e7/paired_cluster_bootstrap.csv`

정밀도 차이가 0.000 [0.000, 0.000] 인 행은 두 조건 모두 위양성이 0 이라 정밀도가 1.000 으로 같은 경우다.

## 7. 용어 유형 탐색적 분석 (exploratory, 사전 지정 아님)

string_match = 이슈의 description 또는 suggestion 에 '접속하기' 포함 (mention-based).

### 7.1 string_match 가 탐지한 이슈의 카테고리 (건수, 비중)

| RAG | run | 탐지 이슈 | 디자인 | 운영 | 기술 | 기타 |
|---|---|---|---|---|---|---|
| 켬 | R1 | 17 | 12 (0.706) | 0 (0.000) | 5 (0.294) | 0 (0.000) |
| 켬 | R2 | 18 | 13 (0.722) | 0 (0.000) | 5 (0.278) | 0 (0.000) |
| 켬 | R3b | 16 | 13 (0.812) | 0 (0.000) | 3 (0.188) | 0 (0.000) |
| 끔 | A1-1 | 19 | 10 (0.526) | 2 (0.105) | 7 (0.368) | 0 (0.000) |
| 끔 | A1-2 | 20 | 11 (0.550) | 4 (0.200) | 5 (0.250) | 0 (0.000) |
| 끔 | A1-3 | 13 | 6 (0.462) | 2 (0.154) | 5 (0.385) | 0 (0.000) |
| 켬 | 합계 (3회) | 51 | 38 (0.745) | 0 (0.000) | 13 (0.255) | 0 (0.000) |
| 끔 | 합계 (3회) | 52 | 27 (0.519) | 8 (0.154) | 17 (0.327) | 0 (0.000) |

출처:
- `results/revision/runs/E1-R1/reports.jsonl`
- `results/revision/runs/E1-R2/reports.jsonl`
- `results/revision/runs/E1-R3b/reports.jsonl`
- `results/revision/runs/E2-A1-1/reports.jsonl`
- `results/revision/runs/E2-A1-2/reports.jsonl`
- `results/revision/runs/E2-A1-3/reports.jsonl`

### 7.2 용어 TP 페이지 수와 운영 카테고리 이슈 수

TP 페이지 = string_match 탐지 이슈가 있는 nominal 용어 양성 페이지. 운영 이슈 = 그 run 의 전체 운영 카테고리 이슈.

| RAG | run | 용어 TP 페이지 | 운영 이슈 (전체) | 운영 이슈 중 string_match 탐지 | string_match 탐지 이슈 |
|---|---|---|---|---|---|
| 켬 | R1 | 12 | 22 | 0 | 17 |
| 켬 | R2 | 14 | 25 | 0 | 18 |
| 켬 | R3b | 12 | 27 | 0 | 16 |
| 끔 | A1-1 | 17 | 64 | 2 | 19 |
| 끔 | A1-2 | 19 | 71 | 4 | 20 |
| 끔 | A1-3 | 12 | 58 | 2 | 13 |

출처:
- `results/revision/runs/E1-R1/reports.jsonl`
- `results/revision/runs/E1-R2/reports.jsonl`
- `results/revision/runs/E1-R3b/reports.jsonl`
- `results/revision/runs/E2-A1-1/reports.jsonl`
- `results/revision/runs/E2-A1-2/reports.jsonl`
- `results/revision/runs/E2-A1-3/reports.jsonl`
- `results/revision/ground_truth.csv`

## 8. 페이지당 카테고리 구성 분포 (exploratory, 사전 지정 아님)

각 페이지의 이슈에 나타난 카테고리 조합별 페이지 수.

### 8.1 조합 1~4

| RAG | run | 없음 | 디자인만 | 운영만 | 기술만 |
|---|---|---|---|---|---|
| 켬 | R1 | 0 | 17 | 0 | 9 |
| 켬 | R2 | 0 | 21 | 0 | 13 |
| 켬 | R3b | 0 | 21 | 0 | 14 |
| 끔 | A1-1 | 7 | 3 | 1 | 54 |
| 끔 | A1-2 | 3 | 5 | 2 | 45 |
| 끔 | A1-3 | 3 | 9 | 1 | 51 |
| 켬 | 합계 (3회) | 0 | 59 | 0 | 36 |
| 끔 | 합계 (3회) | 13 | 17 | 4 | 150 |

출처:
- `results/revision/runs/E1-R1/reports.jsonl`
- `results/revision/runs/E1-R2/reports.jsonl`
- `results/revision/runs/E1-R3b/reports.jsonl`
- `results/revision/runs/E2-A1-1/reports.jsonl`
- `results/revision/runs/E2-A1-2/reports.jsonl`
- `results/revision/runs/E2-A1-3/reports.jsonl`

### 8.2 조합 5~8

| RAG | run | 디자인+운영 | 디자인+기술 | 운영+기술 | 세 카테고리 모두 |
|---|---|---|---|---|---|
| 켬 | R1 | 1 | 153 | 0 | 20 |
| 켬 | R2 | 2 | 141 | 0 | 23 |
| 켬 | R3b | 1 | 140 | 0 | 24 |
| 끔 | A1-1 | 1 | 80 | 16 | 38 |
| 끔 | A1-2 | 1 | 83 | 18 | 43 |
| 끔 | A1-3 | 1 | 83 | 17 | 35 |
| 켬 | 합계 (3회) | 4 | 434 | 0 | 67 |
| 끔 | 합계 (3회) | 3 | 246 | 51 | 116 |

출처:
- `results/revision/runs/E1-R1/reports.jsonl`
- `results/revision/runs/E1-R2/reports.jsonl`
- `results/revision/runs/E1-R3b/reports.jsonl`
- `results/revision/runs/E2-A1-1/reports.jsonl`
- `results/revision/runs/E2-A1-2/reports.jsonl`
- `results/revision/runs/E2-A1-3/reports.jsonl`

## 9. 이 보고서에 사용한 파일

| 경로 | SHA-256 앞 16자리 |
|---|---|
| `results/revision/e7/paired_cluster_bootstrap.csv` | eb7936a17bf8b4dd |
| `results/revision/ground_truth.csv` | fe307fdcd57ba5de |
| `results/revision/runs/E1-R1/reports.jsonl` | ff84acd8d72e2f22 |
| `results/revision/runs/E1-R2/reports.jsonl` | 06340b5e11edee0a |
| `results/revision/runs/E1-R3b/reports.jsonl` | 93486a70477d20a3 |
| `results/revision/runs/E2-A1-1/reports.jsonl` | 577034366177ce2e |
| `results/revision/runs/E2-A1-2/reports.jsonl` | c24815495b66cde1 |
| `results/revision/runs/E2-A1-3/reports.jsonl` | 13a3311d63098f14 |

생성 스크립트: `experiments/revision/clean_report_c.py`

