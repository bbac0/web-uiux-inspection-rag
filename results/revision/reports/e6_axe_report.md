# E6 axe-core 스캔 보고서

작성: `experiments/revision/e6_axe_report.py` (API 호출 없음, 기술 집계만, 검정 없음).
사전 지정: `results/revision/analysis_plan_addendum_e6.md` (스캔 전 커밋 133a1a6).
axe-core 4.14.0, Chromium 151.0.7922.34, 대기 goto(wait_until='networkidle', timeout=30000) + 3000 ms.
스캔 오류 0건. 대응 규칙: 대비 color-contrast, 중복 ID duplicate-id·duplicate-id-active·duplicate-id-aria,
버튼 target-size(두 설정 모두 꺼짐), 모바일·용어 없음.

## 1. 스캔 4회 요약

| 설정 / 뷰포트 | 페이지 | 위반 있는 페이지 | incomplete 있는 페이지 | 위반 (규칙×페이지) | 위반 노드 | target-size 실행 페이지 |
|---|---|---|---|---|---|---|
| A / 1280 | 200 | 113 | 12 | 184 | 272 | 0 |
| B / 1280 | 200 | 131 | 12 | 224 | 312 | 0 |
| A / 390 | 200 | 113 | 12 | 184 | 272 | 0 |
| B / 390 | 200 | 131 | 12 | 224 | 312 | 0 |

출처:
- `results/revision/e6/scan_{A,B}_{1280,390}.json`
- `results/revision/e6/run_log.json`

### 1.1 규칙 ID별 위반 페이지 수 (상위 15, 4개 스캔)

| 규칙 | A/1280 | B/1280 | A/390 | B/390 | 대응 규칙 |
|---|---|---|---|---|---|
| page-has-heading-one | 100 | 100 | 100 | 100 | 아니오 |
| color-contrast | 44 | 44 | 44 | 44 | 예 |
| label | 40 | 40 | 40 | 40 | 아니오 |
| duplicate-id | 0 | 40 | 0 | 40 | 예 |

출처:
- `results/revision/e6/scan_{A,B}_{1280,390}.json`

## 2. 유형별 TP·FP 페이지 수

칸 = TP / FP. 양성 = 그 라벨의 양성 페이지 수. inc = 대응 규칙이 incomplete 로만 보고된 페이지(위반으로 세지 않음).
effective 는 스캔 뷰포트와 같은 뷰포트 라벨(1280 스캔 → effective_1280, 390 스캔 → effective_390).

### 2.1 설정 A, 1280, 라벨 nominal

| 유형 | 양성 | TP | FP | inc | 대응 규칙 |
|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 없음 |
| 버튼 | 46 | 0 | 0 | 0 | target-size |
| 용어 | 45 | 0 | 0 | 0 | 없음 |
| 중복ID | 40 | 0 | 0 | 0 | duplicate-id, duplicate-id-active, duplicate-id-aria |

### 2.1 설정 A, 1280, 라벨 effective_1280

| 유형 | 양성 | TP | FP | inc | 대응 규칙 |
|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 없음 |
| 버튼 | 20 | 0 | 0 | 0 | target-size |
| 용어 | 42 | 0 | 0 | 0 | 없음 |
| 중복ID | 40 | 0 | 0 | 0 | duplicate-id, duplicate-id-active, duplicate-id-aria |

### 2.2 설정 B, 1280, 라벨 nominal

| 유형 | 양성 | TP | FP | inc | 대응 규칙 |
|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 없음 |
| 버튼 | 46 | 0 | 0 | 0 | target-size |
| 용어 | 45 | 0 | 0 | 0 | 없음 |
| 중복ID | 40 | 40 | 0 | 0 | duplicate-id, duplicate-id-active, duplicate-id-aria |

### 2.2 설정 B, 1280, 라벨 effective_1280

| 유형 | 양성 | TP | FP | inc | 대응 규칙 |
|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 없음 |
| 버튼 | 20 | 0 | 0 | 0 | target-size |
| 용어 | 42 | 0 | 0 | 0 | 없음 |
| 중복ID | 40 | 40 | 0 | 0 | duplicate-id, duplicate-id-active, duplicate-id-aria |

### 2.3 설정 A, 390, 라벨 nominal

| 유형 | 양성 | TP | FP | inc | 대응 규칙 |
|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 없음 |
| 버튼 | 46 | 0 | 0 | 0 | target-size |
| 용어 | 45 | 0 | 0 | 0 | 없음 |
| 중복ID | 40 | 0 | 0 | 0 | duplicate-id, duplicate-id-active, duplicate-id-aria |

### 2.3 설정 A, 390, 라벨 effective_390

| 유형 | 양성 | TP | FP | inc | 대응 규칙 |
|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 없음 |
| 버튼 | 20 | 0 | 0 | 0 | target-size |
| 용어 | 42 | 0 | 0 | 0 | 없음 |
| 중복ID | 40 | 0 | 0 | 0 | duplicate-id, duplicate-id-active, duplicate-id-aria |

### 2.4 설정 B, 390, 라벨 nominal

| 유형 | 양성 | TP | FP | inc | 대응 규칙 |
|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 없음 |
| 버튼 | 46 | 0 | 0 | 0 | target-size |
| 용어 | 45 | 0 | 0 | 0 | 없음 |
| 중복ID | 40 | 40 | 0 | 0 | duplicate-id, duplicate-id-active, duplicate-id-aria |

### 2.4 설정 B, 390, 라벨 effective_390

| 유형 | 양성 | TP | FP | inc | 대응 규칙 |
|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 없음 |
| 버튼 | 20 | 0 | 0 | 0 | target-size |
| 용어 | 42 | 0 | 0 | 0 | 없음 |
| 중복ID | 40 | 40 | 0 | 0 | duplicate-id, duplicate-id-active, duplicate-id-aria |


출처:
- `results/revision/e6/scan_{A,B}_{1280,390}.json`
- `results/revision/ground_truth.csv`

## 3. 대조군 39페이지의 위반 규칙 (자연 발생 이슈)

칸 = 위반 페이지 수 (위반 노드 수 합계).

| 규칙 | A/1280 | B/1280 | A/390 | B/390 |
|---|---|---|---|---|
| label | 9 (9) | 9 (9) | 9 (9) | 9 (9) |
| page-has-heading-one | 16 (16) | 16 (16) | 16 (16) | 16 (16) |

대조군 중 위반이 하나도 없는 페이지: A/1280 23, B/1280 23, A/390 23, B/390 23.

출처:
- `results/revision/e6/scan_{A,B}_{1280,390}.json`
- `results/revision/ground_truth.csv`

## 4. 대응 규칙 밖의 위반 (규칙 × 페이지 주입 유형, 위반 페이지 수)

페이지 유형 = nominal 주입 유형(2개면 둘 다 셈), 대조군 = 주입 없음.

### 4.1 설정 A, 1280

| 규칙 | 대비 | 모바일 | 버튼 | 용어 | 중복ID | 대조군 | 전체 |
|---|---|---|---|---|---|---|---|
| label | 12 | 15 | 8 | 4 | 7 | 9 | 40 |
| page-has-heading-one | 31 | 32 | 20 | 18 | 18 | 16 | 100 |

### 4.2 설정 B, 1280

| 규칙 | 대비 | 모바일 | 버튼 | 용어 | 중복ID | 대조군 | 전체 |
|---|---|---|---|---|---|---|---|
| label | 12 | 15 | 8 | 4 | 7 | 9 | 40 |
| page-has-heading-one | 31 | 32 | 20 | 18 | 18 | 16 | 100 |

### 4.3 설정 A, 390

| 규칙 | 대비 | 모바일 | 버튼 | 용어 | 중복ID | 대조군 | 전체 |
|---|---|---|---|---|---|---|---|
| label | 12 | 15 | 8 | 4 | 7 | 9 | 40 |
| page-has-heading-one | 31 | 32 | 20 | 18 | 18 | 16 | 100 |

### 4.4 설정 B, 390

| 규칙 | 대비 | 모바일 | 버튼 | 용어 | 중복ID | 대조군 | 전체 |
|---|---|---|---|---|---|---|---|
| label | 12 | 15 | 8 | 4 | 7 | 9 | 40 |
| page-has-heading-one | 31 | 32 | 20 | 18 | 18 | 16 | 100 |


출처:
- `results/revision/e6/scan_{A,B}_{1280,390}.json`
- `results/revision/ground_truth.csv`

## 5. 기존 LLM 결과와 비교 (nominal, 1280, 유형별 TP / FP 페이지 수, 검정 없음)

LLM 열: 키워드 채점과 의미 채점 pass1(원 규칙, 잘림 = 음성; 재채점 전), string_match(용어만).

| 유형 | 양성 | axe A | axe B | R1 키워드 | R1 의미 | A1-1 키워드 | A1-1 의미 | R1 sm |
|---|---|---|---|---|---|---|---|---|
| 대비 | 44 | 44 / 0 | 44 / 0 | 44 / 3 | 44 / 0 | 44 / 25 | 44 / 0 | - |
| 모바일 | 56 | 0 / 0 | 0 / 0 | 56 / 32 | 56 / 0 | 56 / 49 | 56 / 2 | - |
| 버튼 | 46 | 0 / 0 | 0 / 0 | 40 / 0 | 46 / 0 | 38 / 0 | 46 / 0 | - |
| 용어 | 45 | 0 / 0 | 0 / 0 | 12 / 0 | 0 / 0 | 17 / 0 | 3 / 3 | 12 / 0 |
| 중복ID | 40 | 0 / 0 | 40 / 0 | 34 / 0 | 39 / 0 | 31 / 3 | 40 / 0 | - |

R1 = E1-R1(RAG 켬), A1-1 = E2-A1-1(RAG 끔). LLM 의 실패 페이지는 음성.

출처:
- `results/revision/e6/scan_A_1280.json`
- `results/revision/e6/scan_B_1280.json`
- `results/revision/runs/{E1-R1,E2-A1-1}/reports.jsonl`
- `results/revision/semantic_scores/{E1-R1,E2-A1-1}-sem-p1/grades.jsonl`
- `results/revision/ground_truth.csv`

## 6. 한계

- 규칙 매핑: 모바일 레이아웃 깨짐(리플로)과 표준 용어(레이블 문구 적절성)는 axe-core 에 대응 규칙이 없어 구조적으로 0이다.
  버튼 잘림의 대응 규칙 target-size 는 4.14.0 에서 기본 꺼짐이라 사전 지정된 두 설정 모두에서 실행되지 않았다.
  따라서 axe 와 LLM 의 비교는 대비와 중복 ID 두 유형에서만 의미가 있다.
- 대응 규칙 밖 위반(4절)은 자동 탐지 범위 밖의 '자연 발생' 접근성 문제로, 주입 결함의 탐지로 세지 않았다.
- 렌더링 시점: networkidle 후 3초에 한 번 스캔했다. 지연 로드나 상호작용 후 상태는 보지 않는다.
  설정 A, B 는 같은 렌더링에서 차례로 실행했다(axe 는 DOM 을 바꾸지 않는다).
- color-contrast 는 계산할 수 없는 경우(배경 이미지, 겹침 등) incomplete 로 보고하며 위반으로 세지 않았다(2절 inc 열).
- duplicate-id 계열 중 duplicate-id, duplicate-id-active 는 4.14.0 에서 deprecated 다.
- 페이지 단위 기술 집계이며 CI·검정은 하지 않았다. LLM 의미 채점은 재채점 전 값이다.

