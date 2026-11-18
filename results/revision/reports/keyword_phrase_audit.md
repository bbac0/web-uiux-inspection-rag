# 키워드 사전 감사 (구문별)

작성: `experiments/revision/keyword_phrase_audit.py` (API 호출 없음, 사전 수정 없음, 기술 집계만).
사전 = `experiments/evaluate_performance_v5.CATEGORY_PHRASES` (동결). 매칭 = description 소문자에 구문 포함
(한 이슈가 여러 구문에 걸릴 수 있음). run = E1-R1·R2·R3b (RAG 켬), E2-A1-1~3 (RAG 끔), 3회 합계.
의미 = 의미 채점 pass1 라벨(잘림 등 비성공은 '비성공'). 페이지 유형 = nominal 주입 유형(2개면 둘 다 셈).

## 1. 전체 구문: 매칭 이슈 수

| 사전 유형 | 구문 | 켬 | 끔 | 의미 라벨이 사전 유형과 같음 | 매칭 페이지가 그 유형 주입 |
|---|---|---|---|---|---|
| 대비 | 명도 대비 | 138 | 140 | 273/278 | 275/278 |
| 대비 | 대비 비율 | 0 | 0 | 0/0 | 0/0 |
| 대비 | contrast ratio | 0 | 0 | 0/0 | 0/0 |
| 대비 | wcag | 80 | 171 | 188/251 | 188/251 |
| 대비 | 가독성 | 130 | 148 | 260/278 | 260/278 |
| 모바일 | 레이아웃이 깨 | 6 | 3 | 6/9 | 6/9 |
| 모바일 | 레이아웃 깨짐 | 0 | 0 | 0/0 | 0/0 |
| 모바일 | 가로 스크롤 | 163 | 198 | 361/361 | 356/361 |
| 모바일 | viewport | 6 | 68 | 0/74 | 9/74 |
| 모바일 | 모바일 화면 | 0 | 0 | 0/0 | 0/0 |
| 모바일 | 반응형 | 140 | 216 | 289/356 | 291/356 |
| 모바일 | overflow | 238 | 234 | 246/472 | 295/472 |
| 버튼 | 버튼이 잘 | 0 | 0 | 0/0 | 0/0 |
| 버튼 | 버튼 잘림 | 0 | 0 | 0/0 | 0/0 |
| 버튼 | 버튼 영역 | 0 | 0 | 0/0 | 0/0 |
| 버튼 | clipping | 0 | 0 | 0/0 | 0/0 |
| 버튼 | 겹침 | 0 | 0 | 0/0 | 0/0 |
| 버튼 | overlap | 0 | 0 | 0/0 | 0/0 |
| 버튼 | 클릭 영역 | 2 | 12 | 14/14 | 14/14 |
| 버튼 | 클릭할 수 없 | 47 | 38 | 85/85 | 85/85 |
| 버튼 | 클릭할수 없 | 0 | 0 | 0/0 | 0/0 |
| 버튼 | 상호작용이 불가능 | 12 | 21 | 33/33 | 33/33 |
| 버튼 | 시각적으로 거의 보이지 | 14 | 26 | 40/40 | 40/40 |
| 버튼 | font-size: 0px | 107 | 97 | 204/204 | 204/204 |
| 버튼 | height: 2px | 106 | 94 | 200/200 | 200/200 |
| 용어 | 표준 용어 | 0 | 0 | 0/0 | 0/0 |
| 용어 | 용어 위반 | 0 | 0 | 0/0 | 0/0 |
| 용어 | terminology | 0 | 0 | 0/0 | 0/0 |
| 용어 | 용어 불일치 | 0 | 0 | 0/0 | 0/0 |
| 용어 | 용어가 표준 | 0 | 0 | 0/0 | 0/0 |
| 용어 | 접속하기 | 51 | 52 | 16/103 | 103/103 |
| 중복ID | id가 중복 | 23 | 21 | 44/44 | 44/44 |
| 중복ID | 중복된 id | 0 | 0 | 0/0 | 0/0 |
| 중복ID | duplicate id | 0 | 0 | 0/0 | 0/0 |
| 중복ID | 동일한 id | 0 | 0 | 0/0 | 0/0 |
| 중복ID | id 속성이 중복 | 0 | 0 | 0/0 | 0/0 |
| 중복ID | wai-aria | 0 | 10 | 0/10 | 0/10 |
| 중복ID | 두 번 사용되어 | 39 | 40 | 79/79 | 79/79 |
| 중복ID | 중복 사용 | 65 | 59 | 124/124 | 124/124 |

출처:
- `experiments/evaluate_performance_v5.py`
- `results/revision/runs/{run}/reports.jsonl`
- `results/revision/semantic_scores/{run}-sem-p1/grades.jsonl`
- `results/revision/ground_truth.csv`

## 2. 모바일 구문 상세 (overflow, viewport, 반응형, 레이아웃이 깨)

### 'overflow'

| RAG | 매칭 이슈 | 의미 라벨 분포 | 페이지 주입 유형 분포 |
|---|---|---|---|
| 켬 | 238 | 모바일 123 / 버튼 113 / None 2 | 대비 33 / 모바일 144 / 버튼 122 / 용어 47 / 중복ID 37 |
| 끔 | 234 | 모바일 123 / 버튼 111 | 대비 27 / 모바일 151 / 버튼 124 / 용어 45 / 중복ID 42 |

### 'viewport'

| RAG | 매칭 이슈 | 의미 라벨 분포 | 페이지 주입 유형 분포 |
|---|---|---|---|
| 켬 | 6 | None 6 | 대조군 6 |
| 끔 | 68 | None 68 | 대비 2 / 모바일 9 / 용어 16 / 중복ID 9 / 대조군 40 |

### '반응형'

| RAG | 매칭 이슈 | 의미 라벨 분포 | 페이지 주입 유형 분포 |
|---|---|---|---|
| 켬 | 140 | 모바일 134 / None 6 | 대비 15 / 모바일 134 / 버튼 24 / 용어 25 / 중복ID 13 / 대조군 6 |
| 끔 | 216 | 모바일 155 / None 61 | 대비 23 / 모바일 157 / 버튼 30 / 용어 48 / 중복ID 26 / 대조군 34 |

### '레이아웃이 깨'

| RAG | 매칭 이슈 | 의미 라벨 분포 | 페이지 주입 유형 분포 |
|---|---|---|---|
| 켬 | 6 | 모바일 6 | 대비 4 / 모바일 6 / 용어 2 |
| 끔 | 3 | None 3 | 용어 3 |


출처:
- `results/revision/runs/{run}/reports.jsonl`
- `results/revision/semantic_scores/{run}-sem-p1/grades.jsonl`
- `results/revision/ground_truth.csv`

### 2a. 'overflow' 매칭 이슈의 문맥 (description 안 'overflow' 앞뒤 문자열, 상위 8개)

| 문자열 | 이슈 내 등장 수 |
|---|---|
| `overflow-x:scroll` | 246 |
| `overflow:hidden` | 208 |

출처:
- `results/revision/runs/{run}/reports.jsonl`

## 3. 주입 CSS 원문의 'overflow'

`experiments/generate_200_testbed.py` 에서 'overflow' 가 들어 있는 줄:

- 29행:
  `html, body, div, main, header { width: 3000px !important; min-width: 3000px !important; ov`
  `erflow-x: scroll !important; }`
- 34행:
  `button, .btn, .login-btn, .apply-btn { height: 2px !important; font-size: 0px !important; `
  `line-height: 0 !important; padding: 0 !important; overflow: hidden !important; border: 1px`
  ` solid red !important; }`
- 27행 유형 표기: `"id": "DEF_VIS_02", "category": "Visual", "type": "Mobile Layout Breakage",`
- 32행 유형 표기: `"id": "DEF_VIS_03", "category": "Visual", "type": "Button Area Clipping",`

testbed_200 페이지 HTML 에서 주입 문자열 확인 (nominal 라벨과 대조):

| 문자열 | 들어 있는 페이지 | 그중 버튼 주입 | 그중 모바일 주입 |
|---|---|---|---|
| `overflow: hidden !important` | 46 | 46 | 10 |
| `overflow-x: scroll !important` | 56 | 10 | 56 |

nominal 버튼 주입 페이지 46, 모바일 주입 페이지 56.
버튼 잘림 주입 CSS 에 `overflow: hidden !important` 가 들어 있어, 모델이 이 CSS 를 인용하면 모바일 사전 구문
'overflow' 에 걸린다. 모바일 주입 CSS 에도 `overflow-x: scroll !important` 가 있다.

출처:
- `experiments/generate_200_testbed.py`
- `testbed_200/page_*.html`
- `results/revision/ground_truth.csv`

