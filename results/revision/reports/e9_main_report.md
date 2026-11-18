# E9 본 실험 보고서 (run 1, run 2; 2026-11-13)

- 입력: `testbed_e9/` 91페이지(v3, `exp-freeze-e9-v3`), 5조건 × 2회.
- 러너 `run_experiment_e9.py`, 순서 실행 `run_e9_main.py`.
- 채점: 정규식 주 지표(`scoring/e9_rules.py`)와 보조 분석(`scoring/e9_rules_aux.py`)만. E9 LLM 판정과 의미 채점은 하지 않았다.
- 기술 집계만(통계 검정 없음). 3회째와 E9-4 보조(390x844)는 실행하지 않았다.

## 1. run 표

| run | 상태 | 동시 | 기록 | ok | 파싱 실패 | 오류율 | 이슈 | 비용 |
|---|---|---|---|---|---|---|---|---|
| e9-main-norag-r1 | complete | 2 | 91 | 91 | 0 | 0.0% | 306 | 0.7666 |
| e9-main-fixed-r1 | complete | 2 | 91 | 91 | 0 | 0.0% | 226 | 0.8334 |
| e9-main-page-r1 | complete | 2 | 91 | 91 | 0 | 0.0% | 184 | 0.7273 |
| e9-main-related-r1 | complete | 2 | 91 | 91 | 0 | 0.0% | 105 | 0.7896 |
| e9-main-fixedlong-r1 | complete | 2 | 91 | 91 | 0 | 0.0% | 229 | 0.9055 |
| e9-main-norag-r2 | complete | 2 | 91 | 91 | 0 | 0.0% | 311 | 0.7995 |
| e9-main-fixed-r2 | complete | 2 | 91 | 91 | 0 | 0.0% | 219 | 0.8664 |
| e9-main-page-r2 | complete | 2 | 91 | 91 | 0 | 0.0% | 196 | 0.7975 |
| e9-main-related-r2 | complete | 2 | 91 | 91 | 0 | 0.0% | 107 | 0.8446 |
| e9-main-fixedlong-r2 | complete | 2 | 91 | 91 | 0 | 0.0% | 231 | 0.9094 |

E9 본 실험 비용 합계: $8.2399 (910호출).

출처: `results/revision/runs_e9/e9-main-{조건}-r{회차}/calls.jsonl`, `reports.jsonl`, `run_meta.json`

## 2. 5조건별 유형별 탐지 (정규식)

칸 = run 1 / run 2. 결함 = 탐지된 결함 페이지 수 / 그 유형 결함 페이지 수. 대조군 = 그 유형으로 탐지된 대조군 수 / 30.
E9-4 는 1280x800 실행에 포함된 보조 유형이며 주 지표가 아니다.

### 2.1a 주 지표 (그 페이지에 주입된 변형 문구만 인정): RAG 끔, 고정 질의, 페이지별 질의

| 유형 | 결함 페이지 | RAG 끔 결함 | RAG 끔 대조군 | 고정 질의 결함 | 고정 질의 대조군 | 페이지별 질의 결함 | 페이지별 질의 대조군 |
|---|---|---|---|---|---|---|---|
| E9-1 | 16 | 1/1 | 0/0 | 1/0 | 0/0 | 0/0 | 2/0 |
| E9-1a | 8 | 0/1 | 0/0 | 1/0 | 0/0 | 0/0 | 2/0 |
| E9-1b | 8 | 1/0 | 0/0 | 0/0 | 0/0 | 0/0 | 2/0 |
| E9-2 | 15 | 1/0 | 5/6 | 1/1 | 4/3 | 2/2 | 0/0 |
| E9-2 배너 | 7 | 1/0 | 5/6 | 1/0 | 4/3 | 2/1 | 0/0 |
| E9-2 헤더 | 4 | 0/0 | 5/6 | 0/1 | 4/3 | 0/0 | 0/0 |
| E9-2 푸터 | 4 | 0/0 | 5/6 | 0/0 | 4/3 | 0/1 | 0/0 |
| E9-3 | 15 | 3/7 | 0/0 | 1/1 | 0/0 | 5/5 | 0/0 |
| E9-4 (보조) | 15 | 8/7 | 0/0 | 3/3 | 0/0 | 4/5 | 0/0 |

### 2.1b 주 지표 (그 페이지에 주입된 변형 문구만 인정): 관련 조항 제공, fixed-long

| 유형 | 결함 페이지 | 관련 조항 제공 결함 | 관련 조항 제공 대조군 | fixed-long 결함 | fixed-long 대조군 |
|---|---|---|---|---|---|
| E9-1 | 16 | 10/11 | 0/0 | 1/1 | 0/0 |
| E9-1a | 8 | 8/8 | 0/0 | 1/1 | 0/0 |
| E9-1b | 8 | 2/3 | 0/0 | 0/0 | 0/0 |
| E9-2 | 15 | 15/15 | 0/0 | 0/1 | 3/3 |
| E9-2 배너 | 7 | 7/7 | 0/0 | 0/1 | 3/3 |
| E9-2 헤더 | 4 | 4/4 | 0/0 | 0/0 | 3/3 |
| E9-2 푸터 | 4 | 4/4 | 0/0 | 0/0 | 3/3 |
| E9-3 | 15 | 15/15 | 3/4 | 2/2 | 0/0 |
| E9-4 (보조) | 15 | 15/15 | 0/0 | 6/3 | 0/0 |

### 2.2a 보조 분석 (6개 변형 문구를 모든 페이지에 적용): RAG 끔, 고정 질의, 페이지별 질의

| 유형 | 결함 페이지 | RAG 끔 결함 | RAG 끔 대조군 | 고정 질의 결함 | 고정 질의 대조군 | 페이지별 질의 결함 | 페이지별 질의 대조군 |
|---|---|---|---|---|---|---|---|
| E9-1 | 16 | 1/1 | 0/0 | 1/0 | 0/0 | 0/0 | 2/0 |
| E9-1a | 8 | 0/1 | 0/0 | 1/0 | 0/0 | 0/0 | 2/0 |
| E9-1b | 8 | 1/0 | 0/0 | 0/0 | 0/0 | 0/0 | 2/0 |
| E9-2 | 15 | 1/0 | 5/6 | 1/1 | 4/3 | 2/2 | 0/0 |
| E9-2 배너 | 7 | 1/0 | 5/6 | 1/0 | 4/3 | 2/1 | 0/0 |
| E9-2 헤더 | 4 | 0/0 | 5/6 | 0/1 | 4/3 | 0/0 | 0/0 |
| E9-2 푸터 | 4 | 0/0 | 5/6 | 0/0 | 4/3 | 0/1 | 0/0 |
| E9-3 | 15 | 3/7 | 0/0 | 1/1 | 0/0 | 5/5 | 0/0 |
| E9-4 (보조) | 15 | 8/7 | 0/0 | 3/3 | 0/0 | 4/5 | 0/0 |

### 2.2b 보조 분석 (6개 변형 문구를 모든 페이지에 적용): 관련 조항 제공, fixed-long

| 유형 | 결함 페이지 | 관련 조항 제공 결함 | 관련 조항 제공 대조군 | fixed-long 결함 | fixed-long 대조군 |
|---|---|---|---|---|---|
| E9-1 | 16 | 10/11 | 0/0 | 1/1 | 0/0 |
| E9-1a | 8 | 8/8 | 0/0 | 1/1 | 0/0 |
| E9-1b | 8 | 2/3 | 0/0 | 0/0 | 0/0 |
| E9-2 | 15 | 15/15 | 0/0 | 0/1 | 3/3 |
| E9-2 배너 | 7 | 7/7 | 0/0 | 0/1 | 3/3 |
| E9-2 헤더 | 4 | 4/4 | 0/0 | 0/0 | 3/3 |
| E9-2 푸터 | 4 | 4/4 | 0/0 | 0/0 | 3/3 |
| E9-3 | 15 | 15/15 | 3/4 | 2/2 | 0/0 |
| E9-4 (보조) | 15 | 15/15 | 0/0 | 6/3 | 0/0 |

출처:
- `results/revision/e9/tables_main/e9_regex_primary_vs_aux.csv`
  (`experiments/revision/e9_regex_table.py` 의 score_run 으로 계산)
- run 별 `reports.jsonl`

## 3. 구조적 탐지 불가 층

결정적 검증(`results/revision/e9/ground_truth_e9.csv`)에서 구조적 탐지 불가
(앞 5,000자 밖 또는 1280x800 뷰포트 밖) 결함은 **0페이지**다.
따라서 이 층은 비어 있고, 2절의 결함 페이지는 모두 '탐지 가능' 층이다. E9-3(목적지만 바뀜)과 E9-4(768px 이하에서만 숨김)는
정의상 화면만으로는 보이지 않는 결함이지만, 링크 요소와 주입 문자열은 HTML 앞 5,000자와 뷰포트 안에 있다(설계 §3).

## 4. 반복 규칙 (analysis_plan_e9.md 2절, 정규식 주 지표, 주 지표 유형 E9-1·E9-2·E9-3)

### 4.1 탐지율 (run 1 / run 2 / 평균)

| 유형 | RAG 끔 | 고정 질의 | 페이지별 질의 |
|---|---|---|---|
| E9-1 | 0.062 / 0.062 / 0.062 | 0.062 / 0.000 / 0.031 | 0.000 / 0.000 / 0.000 |
| E9-2 | 0.067 / 0.000 / 0.033 | 0.067 / 0.067 / 0.067 | 0.133 / 0.133 / 0.133 |
| E9-3 | 0.200 / 0.467 / 0.333 | 0.067 / 0.067 / 0.067 | 0.333 / 0.333 / 0.333 |

| 유형 | 관련 조항 제공 | fixed-long |
|---|---|---|
| E9-1 | 0.625 / 0.688 / 0.656 | 0.062 / 0.062 / 0.062 |
| E9-2 | 1.000 / 1.000 / 1.000 | 0.000 / 0.067 / 0.033 |
| E9-3 | 1.000 / 1.000 / 1.000 | 0.133 / 0.133 / 0.133 |

### 4.2 D_cond 와 D_run

| 유형 | 비교 쌍 | D_cond | D_run | D_cond < D_run |
|---|---|---|---|---|
| E9-1 | 관련 조항 제공 vs RAG 끔 | 0.594 | 0.062 | 아니오 |
| E9-1 | 관련 조항 제공 vs 고정 질의 | 0.625 | 0.062 | 아니오 |
| E9-1 | 관련 조항 제공 vs fixed-long | 0.594 | 0.062 | 아니오 |
| E9-1 | fixed-long vs RAG 끔 | 0.000 | 0.062 | 예 |
| E9-2 | 관련 조항 제공 vs RAG 끔 | 0.967 | 0.067 | 아니오 |
| E9-2 | 관련 조항 제공 vs 고정 질의 | 0.933 | 0.067 | 아니오 |
| E9-2 | 관련 조항 제공 vs fixed-long | 0.967 | 0.067 | 아니오 |
| E9-2 | fixed-long vs RAG 끔 | 0.000 | 0.067 | 예 |
| E9-3 | 관련 조항 제공 vs RAG 끔 | 0.667 | 0.267 | 아니오 |
| E9-3 | 관련 조항 제공 vs 고정 질의 | 0.933 | 0.267 | 아니오 |
| E9-3 | 관련 조항 제공 vs fixed-long | 0.867 | 0.267 | 아니오 |
| E9-3 | fixed-long vs RAG 끔 | 0.200 | 0.267 | 예 |

- **판정: 3회째 규칙 발동** (D_cond < D_run 인 경우 3건).
- 3회째는 연구자 승인 후에만 실행한다(자동으로 시작하지 않았다).

출처: `results/revision/e9/tables_main/e9_regex_primary_vs_aux.csv`, run 별 `reports.jsonl`

## 5. 지출 합계

| 항목 | 비용 (USD) |
|---|---|
| Gemini: testbed_200 run (pilot·aborted 포함) | 16.9058 |
| Gemini: E9 파일럿 2회 | 0.8845 |
| Gemini: E9 본 실험 (이 보고서 1절) | 8.2399 |
| **Gemini 합계** | **26.0302** |
| Anthropic: 의미 채점 시험 호출 20건 (표준가) | 0.0382 |

- E1-R3 미기록 과금 가능 추정 $0.0081~$0.0435 는 위 합계에 넣지 않았다.
- 고정 질의 임베딩 1회와 File API 업로드는 비용 기록 대상이 아니다.

출처:
- `results/revision/tables/spend_summary.json`
- `results/revision/runs_e9_pilot/{run}/calls.jsonl`
- `results/revision/runs_e9/{run}/calls.jsonl`
- `results/revision/semantic_scores/probe-E1-R1/probe.jsonl`

## 6. 이 보고서에 사용한 파일

| 경로 | SHA-256 앞 16자리 |
|---|---|
| `testbed_e9/dataset_metadata_e9.json` | 8fa62ab82ab808ba |
| `results/revision/runs_e9/e9-main-norag-r1/calls.jsonl` | e2c3b8058589cb4e |
| `results/revision/runs_e9/e9-main-norag-r1/reports.jsonl` | d9b9d11cb4c1198e |
| `results/revision/runs_e9/e9-main-norag-r1/run_meta.json` | 6057a7b37ed111ae |
| `results/revision/runs_e9/e9-main-fixed-r1/calls.jsonl` | 2169f822c6868dd6 |
| `results/revision/runs_e9/e9-main-fixed-r1/reports.jsonl` | 7bbe41998d1b45d7 |
| `results/revision/runs_e9/e9-main-fixed-r1/run_meta.json` | 2557358acc2a5dac |
| `results/revision/runs_e9/e9-main-page-r1/calls.jsonl` | 6dcc1b58a71d9d45 |
| `results/revision/runs_e9/e9-main-page-r1/reports.jsonl` | bc189795de4e1523 |
| `results/revision/runs_e9/e9-main-page-r1/run_meta.json` | 052d8f3adea03984 |
| `results/revision/runs_e9/e9-main-related-r1/calls.jsonl` | b14cdb49cbb88992 |
| `results/revision/runs_e9/e9-main-related-r1/reports.jsonl` | 7b14e14898e129e7 |
| `results/revision/runs_e9/e9-main-related-r1/run_meta.json` | 3cb830fa348f9383 |
| `results/revision/runs_e9/e9-main-fixedlong-r1/calls.jsonl` | 8d4bdd794fbd03be |
| `results/revision/runs_e9/e9-main-fixedlong-r1/reports.jsonl` | ef48dab803f008d0 |
| `results/revision/runs_e9/e9-main-fixedlong-r1/run_meta.json` | d750f672580d45ee |
| `results/revision/runs_e9/e9-main-norag-r2/calls.jsonl` | 185db4a9f06dc285 |
| `results/revision/runs_e9/e9-main-norag-r2/reports.jsonl` | 95b7d8970ad1e61f |
| `results/revision/runs_e9/e9-main-norag-r2/run_meta.json` | d37c26aff9c0977e |
| `results/revision/runs_e9/e9-main-fixed-r2/calls.jsonl` | e548fbab5a005c71 |
| `results/revision/runs_e9/e9-main-fixed-r2/reports.jsonl` | 4352d6fb532f7d19 |
| `results/revision/runs_e9/e9-main-fixed-r2/run_meta.json` | 6b0f1f50fa2227fb |
| `results/revision/runs_e9/e9-main-page-r2/calls.jsonl` | d91f454996f40b02 |
| `results/revision/runs_e9/e9-main-page-r2/reports.jsonl` | ccabb948fde1a1a5 |
| `results/revision/runs_e9/e9-main-page-r2/run_meta.json` | 48d15c219176753b |
| `results/revision/runs_e9/e9-main-related-r2/calls.jsonl` | 5f7aebea21794b21 |
| `results/revision/runs_e9/e9-main-related-r2/reports.jsonl` | 03cea4d9985f4b75 |
| `results/revision/runs_e9/e9-main-related-r2/run_meta.json` | 961d433f390dd480 |
| `results/revision/runs_e9/e9-main-fixedlong-r2/calls.jsonl` | 8b4c91b367fd7f13 |
| `results/revision/runs_e9/e9-main-fixedlong-r2/reports.jsonl` | 64b88152539586f6 |
| `results/revision/runs_e9/e9-main-fixedlong-r2/run_meta.json` | 15896c5322852265 |
| `results/revision/e9/tables_main/e9_regex_primary_vs_aux.csv` | 0c3373e65eb23a62 |
| `results/revision/e9/ground_truth_e9.csv` | 58eb2583a5f94d97 |
| `results/revision/tables/spend_summary.json` | ad440e312b8e63d5 |

생성 스크립트: `experiments/revision/e9_main_report.py`

