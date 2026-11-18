# 정리 보고서 (2026-11-13)

모든 숫자는 각 표 아래 출처 파일에서 읽은 값이다. API 호출 없음. 통계 검정은 사전 지정 범위 안에서만 보고한다.

## 1. run 전체 표 (pilot 제외)

| run | 상태 | 동시 | 요청 페이지 | 기록 | ok | 파싱 실패 | 오류율 |
|---|---|---|---|---|---|---|---|
| E1-R1 | complete | 1 | 200 | 200 | 200 | 0 | 0.0% |
| E2-A1-1 | complete | 4 | 200 | 200 | 200 | 0 | 0.0% |
| E1-R2 | complete | 4 | 200 | 200 | 200 | 0 | 0.0% |
| E2-A1-2 | complete | 4 | 200 | 200 | 200 | 0 | 0.0% |
| E1-R3 | aborted | 4 | 200 | 160 | 160 | 0 | 0.0% |
| E1-R3b | complete | 2 | 200 | 200 | 200 | 0 | 0.0% |
| E2-A1-3 | complete | 2 | 200 | 200 | 200 | 0 | 0.0% |

오류율 = (api/rag/acquisition 오류 기록 수) / 기록 수.

| run | 이슈 합계 | 이슈/페이지 평균 | 범위 | 비용 | RAG 청크 |
|---|---|---|---|---|---|
| E1-R1 | 676 | 3.38 | 1~6 | $2.0137 | 4청크×200 |
| E2-A1-1 | 544 | 2.72 | 0~10 | $1.4168 | 0청크×200 |
| E1-R2 | 674 | 3.37 | 1~6 | $1.6646 | 4청크×200 |
| E2-A1-2 | 579 | 2.90 | 0~10 | $1.4083 | 0청크×200 |
| E1-R3 | 532 | 3.33 | 1~6 | $1.2990 | 4청크×160 |
| E1-R3b | 651 | 3.25 | 1~6 | $1.8736 | 4청크×200 |
| E2-A1-3 | 534 | 2.67 | 0~9 | $1.4869 | 0청크×200 |

출처: run 별 `results/revision/runs/{run}/calls.jsonl`, `reports.jsonl`, `run_meta.json`
- E1-R3 은 160/200 에서 중단(aborted, 분석 제외): `results/revision/runs/E1-R3/ABORTED.json`

## 2. 페이지당 이슈 수 분포 (페이지 수)

| run | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | >10 | 평균 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | 0 | 9 | 25 | 90 | 42 | 25 | 9 | 0 | 0 | 0 | 0 | 0 | 3.38 |
| R2 | 0 | 11 | 27 | 82 | 45 | 27 | 8 | 0 | 0 | 0 | 0 | 0 | 3.37 |
| R3b | 0 | 15 | 26 | 87 | 40 | 29 | 3 | 0 | 0 | 0 | 0 | 0 | 3.25 |
| A1-1 | 7 | 33 | 62 | 39 | 46 | 6 | 1 | 3 | 0 | 1 | 2 | 0 | 2.72 |
| A1-2 | 3 | 31 | 58 | 40 | 47 | 15 | 1 | 2 | 0 | 1 | 2 | 0 | 2.90 |
| A1-3 | 3 | 37 | 62 | 46 | 34 | 14 | 1 | 2 | 0 | 1 | 0 | 0 | 2.67 |

출처: `results/revision/e7/exploratory_issue_counts.csv`

## 3. 유형별 탐지 페이지 수 (TP, FP)

키워드 = 키워드 사전(description). string_match = '접속하기' 언급 기반(용어 유형만).

### TP 페이지 수

| 유형 | 라벨 | 양성 | R1 | R2 | R3b | A1-1 | A1-2 | A1-3 |
|---|---|---|---|---|---|---|---|---|
| 대비 | nominal | 44 | 44 | 44 | 44 | 44 | 44 | 44 |
| 대비 | effective | 44 | 44 | 44 | 44 | 44 | 44 | 44 |
| 모바일 | nominal | 56 | 56 | 56 | 56 | 56 | 56 | 56 |
| 모바일 | effective | 56 | 56 | 56 | 56 | 56 | 56 | 56 |
| 버튼 | nominal | 46 | 40 | 40 | 40 | 38 | 34 | 38 |
| 버튼 | effective | 20 | 20 | 20 | 20 | 20 | 20 | 20 |
| 용어 | nominal | 45 | 12 | 14 | 12 | 17 | 19 | 12 |
| 용어 | effective | 42 | 12 | 14 | 12 | 17 | 19 | 12 |
| 중복 ID | nominal | 40 | 34 | 37 | 33 | 31 | 34 | 34 |
| 중복 ID | effective | 40 | 34 | 37 | 33 | 31 | 34 | 34 |
| 용어 string_match | nominal | 45 | 12 | 14 | 12 | 17 | 19 | 12 |
| 용어 string_match | effective | 42 | 12 | 14 | 12 | 17 | 19 | 12 |

### FP 페이지 수

| 유형 | 라벨 | 양성 | R1 | R2 | R3b | A1-1 | A1-2 | A1-3 |
|---|---|---|---|---|---|---|---|---|
| 대비 | nominal | 44 | 3 | 4 | 2 | 25 | 21 | 23 |
| 대비 | effective | 44 | 3 | 4 | 2 | 25 | 21 | 23 |
| 모바일 | nominal | 56 | 32 | 32 | 28 | 49 | 52 | 49 |
| 모바일 | effective | 56 | 32 | 32 | 28 | 49 | 52 | 49 |
| 버튼 | nominal | 46 | 0 | 0 | 0 | 0 | 0 | 0 |
| 버튼 | effective | 20 | 20 | 20 | 20 | 18 | 14 | 18 |
| 용어 | nominal | 45 | 0 | 0 | 0 | 0 | 0 | 0 |
| 용어 | effective | 42 | 0 | 0 | 0 | 0 | 0 | 0 |
| 중복 ID | nominal | 40 | 0 | 0 | 0 | 3 | 5 | 2 |
| 중복 ID | effective | 40 | 0 | 0 | 0 | 3 | 5 | 2 |
| 용어 string_match | nominal | 45 | 0 | 0 | 0 | 0 | 0 | 0 |
| 용어 string_match | effective | 42 | 0 | 0 | 0 | 0 | 0 | 0 |

출처: `results/revision/tables/e1_a1_type_detection.csv`

## 4. E7 (키워드 채점, 5유형 합산 셀; R1 vs A1-1)

### 4.1 MCC 와 템플릿 군집 부트스트랩 95% 구간

| 라벨 | 셀 | R1 MCC | R1 구간 | A1-1 MCC | A1-1 구간 |
|---|---|---|---|---|---|
| nominal | 1000 | 0.772 | [0.727, 0.826] | 0.675 | [0.616, 0.741] |
| effective | 1000 | 0.728 | [0.650, 0.799] | 0.650 | [0.590, 0.712] |
| grounded 명도 대비 | 200 | 0.958 | [0.899, 1.000] | 0.732 | [0.640, 0.833] |
| grounded 버튼 true | 400 | 0.828 | [0.718, 0.915] | 0.722 | [0.625, 0.817] |

출처: `results/revision/e7/cell_metrics.csv`

### 4.2 정밀도, 재현율, 특이도, 균형 정확도

| 라벨 | run | 정밀도 | 재현율 | 특이도 | 균형 정확도 | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|
| nominal | R1 | 0.842 | 0.805 | 0.954 | 0.880 | 186 | 35 | 45 | 734 |
| nominal | A1-1 | 0.707 | 0.805 | 0.900 | 0.853 | 186 | 77 | 45 | 692 |
| effective | R1 | 0.751 | 0.822 | 0.931 | 0.876 | 166 | 55 | 36 | 743 |
| effective | A1-1 | 0.639 | 0.832 | 0.881 | 0.856 | 168 | 95 | 34 | 703 |
| grounded 명도 대비 | R1 | 0.936 | 1.000 | 0.981 | 0.990 | 44 | 3 | 0 | 153 |
| grounded 명도 대비 | A1-1 | 0.638 | 1.000 | 0.840 | 0.920 | 44 | 25 | 0 | 131 |
| grounded 버튼 true | R1 | 0.736 | 1.000 | 0.932 | 0.966 | 64 | 23 | 0 | 313 |
| grounded 버튼 true | A1-1 | 0.598 | 1.000 | 0.872 | 0.936 | 64 | 43 | 0 | 293 |

출처: `results/revision/e7/cell_metrics.csv`

### 4.3 R1 − A1-1 차이 (짝 템플릿 군집 부트스트랩, 확정)

added after seeing replicate results, before semantic scoring.

| 라벨 | MCC 차이 | 구간 | LOTO 범위 |
|---|---|---|---|
| nominal | 0.097 | [0.043, 0.147] | 0.082~0.110 |
| effective | 0.079 | [0.022, 0.129] | 0.069~0.095 |
| grounded 명도 대비 | 0.226 | [0.111, 0.336] | 0.193~0.261 |
| grounded 버튼 true | 0.106 | [0.016, 0.197] | 0.072~0.136 |

주: **합산 MCC 는 서로 성격이 다른 유형(대비, 모바일, 버튼, 용어, 중복 ID)을 섞은 값**이다.
유형별 차이는 `results/revision/reports/clean_report_c_section.md` 6절 참고.

| 라벨 | 정밀도 차이 [구간] | 특이도 차이 [구간] | 재현율 차이 [구간] |
|---|---|---|---|
| nominal | 0.134 [0.081, 0.192] | 0.055 [0.034, 0.074] | 0.000 [-0.056, 0.049] |
| effective | 0.112 [0.052, 0.172] | 0.050 [0.026, 0.072] | -0.010 [-0.053, 0.034] |
| grounded 명도 대비 | 0.298 [0.149, 0.437] | 0.141 [0.062, 0.234] | 0.000 [0.000, 0.000] |
| grounded 버튼 true | 0.138 [0.021, 0.255] | 0.060 [0.009, 0.116] | 0.000 [0.000, 0.000] |

출처: `results/revision/e7/paired_cluster_bootstrap.csv`

### 4.4 exact McNemar (셀 단위, 군집 미고려, 보조)

b = R1 만 맞음, c = A1-1 만 맞음. 주 검정의 Holm 가족(A1, A2, A3)은 A2·A3 미실행이라 미완성.

| 라벨 | 셀 | b | c | p (exact) | Holm 상한 3p |
|---|---|---|---|---|---|
| nominal | 1000 | 68 | 26 | 1.732e-05 | 5.196e-05 |
| effective | 1000 | 66 | 28 | 0.0001111 | 0.0003333 |
| grounded 명도 대비 | 200 | 25 | 3 | 2.744e-05 | 8.232e-05 |
| grounded 버튼 true | 400 | 28 | 8 | 0.001193 | 0.003579 |

출처: `results/revision/e7/mcnemar.csv`

### 4.5 string_match (용어 유형, mention-based) exact McNemar (탐색적, 보정 없음)

| 비교 | 라벨 | 셀 | b | c | p (exact) |
|---|---|---|---|---|---|
| E1-R1 vs E2-A1-1 | nominal | 200 | 4 | 9 | 0.2668 |
| E1-R1 vs E2-A1-1 | effective | 200 | 4 | 9 | 0.2668 |
| E1-R2 vs E2-A1-2 | nominal | 200 | 4 | 9 | 0.2668 |
| E1-R2 vs E2-A1-2 | effective | 200 | 4 | 9 | 0.2668 |
| E1-R3b vs E2-A1-3 | nominal | 200 | 7 | 7 | 1 |
| E1-R3b vs E2-A1-3 | effective | 200 | 7 | 7 | 1 |
| E1-majority vs A1-majority | nominal | 200 | 3 | 9 | 0.146 |
| E1-majority vs A1-majority | effective | 200 | 3 | 9 | 0.146 |

출처: `results/revision/e7/mcnemar.csv`

### 4.6 실행 간 변동 (조건 안 3회)

켬 = E1-R1, R2, R3b. 끔 = E2-A1-1, A1-2, A1-3. 3회 동일 = 세 run 예측이 모두 같은 셀 비율.

| 조건 | 채점기 | 유형 | 탐지 셀 (3회) | SD | 3회 동일 | Fleiss kappa |
|---|---|---|---|---|---|---|
| 켬 | keyword | Contrast | 47;48;46 | 1.00 | 0.990 | 0.981 |
| 켬 | keyword | Mobile | 88;88;84 | 2.31 | 0.945 | 0.925 |
| 켬 | keyword | Button | 40;40;40 | 0.00 | 0.975 | 0.948 |
| 켬 | keyword | Terminology | 12;14;12 | 1.15 | 0.970 | 0.831 |
| 켬 | keyword | DupID | 34;37;33 | 2.08 | 0.975 | 0.942 |
| 켬 | keyword | micro (5 types) | 221;227;215 | 6.00 | 0.971 | 0.944 |
| 켬 | string_match | Terminology | 12;14;12 | 1.15 | 0.970 | 0.831 |
| 끔 | keyword | Contrast | 69;65;67 | 2.00 | 0.840 | 0.761 |
| 끔 | keyword | Mobile | 105;108;105 | 1.73 | 0.875 | 0.833 |
| 끔 | keyword | Button | 38;34;38 | 2.31 | 0.960 | 0.911 |
| 끔 | keyword | Terminology | 17;19;12 | 3.61 | 0.950 | 0.774 |
| 끔 | keyword | DupID | 34;39;36 | 2.52 | 0.940 | 0.865 |
| 끔 | keyword | micro (5 types) | 263;265;258 | 3.61 | 0.913 | 0.850 |
| 끔 | string_match | Terminology | 17;19;12 | 3.61 | 0.950 | 0.774 |

| 조건 | 채점기 | 유형 | 쌍별 Cohen kappa (1-2;1-3;2-3) |
|---|---|---|---|
| 켬 | keyword | Contrast | 0.986;0.986;0.972 |
| 켬 | keyword | Mobile | 0.919;0.939;0.918 |
| 켬 | keyword | Button | 0.969;0.937;0.937 |
| 켬 | keyword | Terminology | 0.836;0.823;0.836 |
| 켬 | keyword | DupID | 0.949;0.946;0.931 |
| 켬 | keyword | micro (5 types) | 0.948;0.947;0.936 |
| 켬 | string_match | Terminology | 0.836;0.823;0.836 |
| 끔 | keyword | Contrast | 0.753;0.777;0.751 |
| 끔 | keyword | Mobile | 0.809;0.860;0.829 |
| 끔 | keyword | Button | 0.898;0.935;0.898 |
| 끔 | keyword | Terminology | 0.878;0.740;0.687 |
| 끔 | keyword | DupID | 0.883;0.827;0.885 |
| 끔 | keyword | micro (5 types) | 0.851;0.857;0.842 |
| 끔 | string_match | Terminology | 0.878;0.740;0.687 |

출처: `results/revision/e7/run_variability.csv`

## 5. 이슈 카테고리 비중과 프롬프트 예시 구조 (exploratory, 사전 지정 아님)

| RAG | run | 이슈 | 디자인 건수 (비중) | 운영 건수 (비중) | 기술 건수 (비중) |
|---|---|---|---|---|---|
| 켬 | R1 | 676 | 343 (0.507) | 22 (0.033) | 311 (0.460) |
| 켬 | R2 | 674 | 347 (0.515) | 25 (0.037) | 302 (0.448) |
| 켬 | R3b | 651 | 328 (0.504) | 27 (0.041) | 296 (0.455) |
| 켬 | 합계 (3회) | 2001 | 0.509 | 0.037 | 0.454 |
| 끔 | A1-1 | 544 | 140 (0.257) | 64 (0.118) | 340 (0.625) |
| 끔 | A1-2 | 579 | 152 (0.263) | 71 (0.123) | 356 (0.615) |
| 끔 | A1-3 | 534 | 143 (0.268) | 58 (0.109) | 333 (0.624) |
| 끔 | 합계 (3회) | 1657 | 0.263 | 0.116 | 0.621 |

합계 행의 비중은 3회 합산 이슈 기준.

출처:
- `results/revision/e7/exploratory_category_shares_on_off.csv`
- `results/revision/e7/exploratory_categories.csv`

| RAG | run | 페이지 | 이슈 정확히 3건 | 3건 + 카테고리별 1건 | 비율 | 카테고리 각 1건 이상 |
|---|---|---|---|---|---|---|
| 켬 | R1 | 200 | 90 | 6 | 0.030 | 20 |
| 켬 | R2 | 200 | 82 | 5 | 0.025 | 23 |
| 켬 | R3b | 200 | 87 | 7 | 0.035 | 24 |
| 끔 | A1-1 | 200 | 39 | 9 | 0.045 | 38 |
| 끔 | A1-2 | 200 | 40 | 5 | 0.025 | 43 |
| 끔 | A1-3 | 200 | 46 | 7 | 0.035 | 35 |
| 켬 | 합계 (3회) | 600 | 259 | 18 | 0.030 | 67 |
| 끔 | 합계 (3회) | 600 | 125 | 21 | 0.035 | 116 |

출처: `results/revision/e7/exploratory_prompt_structure_convergence.csv`

## 6. E9 테스트베드

### 6.1 본 실험 91페이지 (`testbed_e9/`, 시드 20261116)

| 유형 | 페이지 | 검증 통과 | 구조적 탐지 불가 |
|---|---|---|---|
| E9-1a 배너 문구 단어 변경 | 8 | 8 | 0 |
| E9-1b 배너 문구 띄어쓰기 변경 | 8 | 8 | 0 |
| E9-2 배너 규격값 | 7 | 7 | 0 |
| E9-2 헤더 규격값 | 4 | 4 | 0 |
| E9-2 푸터 규격값 | 4 | 4 | 0 |
| E9-3 로그인 링크 → /signup | 15 | 15 | 0 |
| E9-4 768px 이하 로그인 숨김 (보조) | 15 | 15 | 0 |
| 대조군 | 30 | 30 | - |
| **합계** | 91 | 91 | 0 |

출처:
- `testbed_e9/dataset_metadata_e9.json`
- `results/revision/e9/e9_verify_summary.json`

### 6.2 파일럿 8페이지 (`testbed_e9_pilot/`, 시드 20261117, 분석 제외)

| 페이지 | 유형 | 본문 템플릿 | 변형 | 검증 | 본 실험과 같은 HTML |
|---|---|---|---|---|---|
| e9p_001 | E9-1a | contact_page | replace_whole | 1 | 아니오 |
| e9p_002 | control | portal_main | - | 1 | e9_036 |
| e9p_003 | E9-2-footer | search_result | .ft-copy font-weight:700 | 1 | 아니오 |
| e9p_004 | E9-4 | faq_page | hide login link at max-width 768px | 1 | e9_079 |
| e9p_005 | E9-1b | search_result | space_i_nurijip | 1 | 아니오 |
| e9p_006 | E9-3 | terms_page | href /login -> /signup | 1 | e9_088 |
| e9p_007 | E9-2-banner | search_result | .gov-banner color:#000000 | 1 | 아니오 |
| e9p_008 | control | contact_page | - | 1 | e9_055 |

검증 통과 8/8.

출처:
- `testbed_e9_pilot/dataset_metadata_e9_pilot.json`
- `results/revision/e9_pilot/ground_truth_e9.csv`
- `results/revision/e9_pilot/e9_verify_summary.json`

## 7. 지출 합계 (Gemini 생성 호출 기준)

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

- 기록된 합계: $11.2552
- 분석 대상 완료 run 소계(pilot·aborted 제외): $9.8639
- E1-R3 미기록 과금 가능 생성 호출: 0~3건 (가능성 높은 값 1건)
- 미기록 추정 비용: $0.0081 (가능성 높은 값) ~ $0.0435 (상한)
- 추정 포함 총액 범위: $11.2552 ~ $11.2987
- 고정 질의 임베딩 1회와 File API 업로드는 비용 기록 대상이 아니다.

출처:
- `results/revision/tables/spend_summary.json`
- `results/revision/runs/E1-R3/ABORTED.json`

## 8. 이 보고서에 사용한 파일

| 경로 | SHA-256 앞 16자리 |
|---|---|
| `results/revision/runs/E1-R1/calls.jsonl` | 230f926f4e27e8d4 |
| `results/revision/runs/E1-R1/reports.jsonl` | ff84acd8d72e2f22 |
| `results/revision/runs/E1-R1/run_meta.json` | 22019a7a49821779 |
| `results/revision/runs/E2-A1-1/calls.jsonl` | a5e9cc4481019e69 |
| `results/revision/runs/E2-A1-1/reports.jsonl` | 577034366177ce2e |
| `results/revision/runs/E2-A1-1/run_meta.json` | cc1c03b1f3f336da |
| `results/revision/runs/E1-R2/calls.jsonl` | 3d13d50ac28a72f0 |
| `results/revision/runs/E1-R2/reports.jsonl` | 06340b5e11edee0a |
| `results/revision/runs/E1-R2/run_meta.json` | d706ba9017530a98 |
| `results/revision/runs/E2-A1-2/calls.jsonl` | 370fe3051006d4d9 |
| `results/revision/runs/E2-A1-2/reports.jsonl` | c24815495b66cde1 |
| `results/revision/runs/E2-A1-2/run_meta.json` | 3f3a48907004a890 |
| `results/revision/runs/E1-R3/calls.jsonl` | 2529611698c76a9c |
| `results/revision/runs/E1-R3/reports.jsonl` | 2842bccd10da4c59 |
| `results/revision/runs/E1-R3/run_meta.json` | e94b9a4574b27ce4 |
| `results/revision/runs/E1-R3/ABORTED.json` | 4ae4bda9b8b5b875 |
| `results/revision/runs/E1-R3b/calls.jsonl` | ccf6a61489fcda6d |
| `results/revision/runs/E1-R3b/reports.jsonl` | 93486a70477d20a3 |
| `results/revision/runs/E1-R3b/run_meta.json` | bdd63587f1029d6e |
| `results/revision/runs/E2-A1-3/calls.jsonl` | ab211b19d6a21309 |
| `results/revision/runs/E2-A1-3/reports.jsonl` | 13a3311d63098f14 |
| `results/revision/runs/E2-A1-3/run_meta.json` | 46a1da50ff9c25cc |
| `results/revision/e7/exploratory_issue_counts.csv` | 1286c0ee26eca907 |
| `results/revision/tables/e1_a1_type_detection.csv` | de71927222096e8d |
| `results/revision/e7/cell_metrics.csv` | 4953c4af724b1365 |
| `results/revision/e7/paired_cluster_bootstrap.csv` | eb7936a17bf8b4dd |
| `results/revision/e7/mcnemar.csv` | 36b9a8fa66fbb331 |
| `results/revision/e7/run_variability.csv` | 865af3bbef749ea6 |
| `results/revision/e7/exploratory_category_shares_on_off.csv` | 739d137644843d4e |
| `results/revision/e7/exploratory_categories.csv` | 92affaa98f071e1f |
| `results/revision/e7/exploratory_prompt_structure_convergence.csv` | 1f69a85e1e0686c5 |
| `testbed_e9/dataset_metadata_e9.json` | c64fcfe4643fbe8f |
| `results/revision/e9/e9_verify_summary.json` | bca057bd82cd4be0 |
| `testbed_e9_pilot/dataset_metadata_e9_pilot.json` | 315a4fbec31c1645 |
| `results/revision/e9_pilot/e9_verify_summary.json` | 688d4a26954925d0 |
| `results/revision/e9_pilot/ground_truth_e9.csv` | 2ce0f936e56960d2 |
| `results/revision/tables/spend_summary.json` | 2629d7a7d338379f |

생성 스크립트: `experiments/revision/clean_report.py`

