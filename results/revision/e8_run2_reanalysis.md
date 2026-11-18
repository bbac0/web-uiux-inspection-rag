# E8 레거시 run2 재분석

- 입력: `paper_results/run2` 리포트 200개 (SHA-256 은 `legacy_run2_manifest.csv`), 정답은 E0 `ground_truth.csv` (effective = 1280 뷰포트).
- 채점: `evaluate_performance_v5.py` 키워드 사전과 대상 페이지 필터를 그대로 사용 (다중 라벨).
- run2 는 빈 벡터 DB(0청크)로 실행되었다 → (iv).

## (i) 효과 없는 버튼 잘림 26페이지

- 키워드 채점이 Button Area Clipping 을 '탐지'로 센 페이지: **21/26 (80.8%)**
- 참고: 효과가 있는 버튼 잘림 페이지에서는 20/20 (100.0%)
- 상세: `e8_i_ineffective_button.csv`

## (ii) 미주입 용어 위반 3페이지 (form_page)

| page_id | 다른 nominal 결함 | 키워드 매칭 유형 | 용어 탐지 | 대상 이슈 수 | '로그인'/'접속' 언급 이슈 |
|---|---|---|---|---:|---:|
| page_028 | Duplicate ID Markup Error | Duplicate ID Markup Error | 아니오 | 5 | 0 |
| page_038 |  | Mobile Layout Breakage | 아니오 | 4 | 0 |
| page_168 | Poor Contrast Ratio | Poor Contrast Ratio | 아니오 | 3 | 0 |

- 이슈 원문: `e8_ii_noninjected_terminology.csv`

## (iii) 키워드 채점 유형별 결과: nominal vs effective

| 유형 | 라벨 | 양성 | TP | 재현율 | FP | 음성 | 특이도 |
|---|---|---:|---:|---:|---:|---:|---:|
| Poor Contrast Ratio | nominal | 44 | 44 | 1.000 | 25 | 156 | 0.840 |
| Poor Contrast Ratio | effective | 44 | 44 | 1.000 | 25 | 156 | 0.840 |
| Mobile Layout Breakage | nominal | 56 | 56 | 1.000 | 48 | 144 | 0.667 |
| Mobile Layout Breakage | effective | 56 | 56 | 1.000 | 48 | 144 | 0.667 |
| Button Area Clipping | nominal | 46 | 41 | 0.891 | 0 | 154 | 1.000 |
| Button Area Clipping | effective | 20 | 20 | 1.000 | 21 | 180 | 0.883 |
| Standard Terminology Violation | nominal | 45 | 14 | 0.311 | 0 | 155 | 1.000 |
| Standard Terminology Violation | effective | 42 | 14 | 0.333 | 0 | 158 | 1.000 |
| Duplicate ID Markup Error | nominal | 40 | 37 | 0.925 | 1 | 160 | 0.994 |
| Duplicate ID Markup Error | effective | 40 | 37 | 0.925 | 1 | 160 | 0.994 |

- 셀 단위(페이지×유형) 결과. effective 에서는 효과 없는 버튼 26셀·미주입 용어 3셀이 음성으로 바뀌므로 그 셀의 탐지는 FP 가 된다.

## (iv) rag_status 집계 (분석 360건)

| 대상 | enabled | ok | n_chunks | error | 건수 |
|---|---|---|---:|---|---:|
| linked(/login 등) | True | True | 0 | None | 160 |
| target | True | True | 0 | None | 200 |

## (v) 근거 필드 (source_file, page_number) — 이슈 전체

- 이슈 수: 1054 (대상 페이지 502, 링크된 페이지 552)
- 말뭉치 PDF 쪽수: gov_guide.pdf 1181쪽, gov_check.pdf 273쪽
- source_file 이 프롬프트 예시값 `gov_guide.pdf`: 660/1054 (62.6%)
- page_number 가 프롬프트 예시값 `[12]` 또는 `[12, 13]`: 372/1054 (35.3%); 12 를 포함: 381/1054 (36.1%)
- 파일과 쪽이 모두 프롬프트 예시값: 369/1054 (35.0%)
- 말뭉치에 없는 파일명: 394/1054 (37.4%)
- 말뭉치 파일이지만 쪽 번호가 범위 밖이거나 정수가 아님: 3/1054 (0.3%)
- run2 는 검색 컨텍스트가 비어 있었으므로 모든 인용은 모델이 컨텍스트 없이 만든 값이다.

| source_file | 건수 | 비율 |
|---|---:|---:|
| `gov_guide.pdf` | 660 | 62.6% |
| `General web standards` | 176 | 16.7% |
| `General web accessibility guidelines` | 88 | 8.3% |
| `N/A` | 19 | 1.8% |
| `None` | 17 | 1.6% |
| `General Web Standards` | 13 | 1.2% |
| `정부 표준 가이드라인` | 12 | 1.1% |
| `general_ui_ux_principles.pdf` | 6 | 0.6% |
| `정부 표준 가이드라인 (기본 지침)` | 6 | 0.6% |
| `HTML 소스코드` | 5 | 0.5% |

| page_number | 건수 | 비율 |
|---|---:|---:|
| `[]` | 407 | 38.6% |
| `[12]` | 355 | 33.7% |
| `[15]` | 36 | 3.4% |
| `[1]` | 27 | 2.6% |
| `[20]` | 24 | 2.3% |
| `null` | 20 | 1.9% |
| `[25]` | 17 | 1.6% |
| `[12, 13]` | 17 | 1.6% |
| `[30]` | 14 | 1.3% |
| `[13]` | 13 | 1.2% |

## (vi) total_checked_count 분포

리포트의 `total_count` 는 분석한 페이지들의 `total_checked_count` 합이다. 1페이지 리포트(40개)만 값이 곧 모델 출력이다.

- 1페이지 리포트 40개: {'30': 23, '60': 0, '기타': 17} — 상세 {3: 1, 4: 4, 10: 2, 12: 2, 15: 5, 20: 2, 25: 1, 30: 23}
- 2페이지 리포트 160개 (두 값의 합): {'30': 0, '60': 101, '기타': 59} — 상세 {33: 1, 35: 2, 37: 2, 40: 7, 42: 5, 45: 27, 48: 2, 50: 7, 55: 6, 60: 101}
- 상세: `e8_vi_total_checked_count.csv`

## (v-b) 기존 수치(1,016건 중 289건)와의 차이

두 집계는 분모부터 다르다. E8 (v)는 run2 리포트 200개의 이슈 전체 1054건을 분모로 하고, source_file 이 JSON null(17건)이나
문자열 'N/A'(19건)인 이슈도 그대로 남겨 "말뭉치에 없는 파일명"에 넣었다(37.4%). 기존 수치의 분모 1,016건은
`experiments/audit_pipeline_artifacts.py` 의 기준(source_file 이 null, 빈 문자열, 'N/A' 가 아닌 이슈만)과 정확히 같다
(1054 − 17 − 19 − 2 = 1016; 2건은 빈 문자열). 두 집계 모두 대상 페이지 이슈만 고르지 않고 크롤러가 따라간
`/login` 404 페이지의 이슈(552건)를 포함하며, 파일명은 정규화하지 않았다(대소문자가 다른
'General web standards'와 'General Web Standards'를 별개로 셈). 분자 289건은 이 저장소의 어떤 스크립트도 출력하지 않으며, 같은 분모에서
단순한 조건 조합으로는 정확히 재현되지 않았다. 가장 가까운 후보는 (1) `/login` 이슈 중 gov_guide.pdf·[12] 를 단 288건(28.3%),
(2) gov_guide.pdf 이면서 쪽이 예시값이 아닌 291건, (3) 'General …' 계열 파일명 294건이다(`e8_v_reconciliation.csv`).
따라서 차이는 (a) null/'N/A' 처리(분모 1054 vs 1016)와 (b) 분자의 판정 기준이 문서화되어 있지 않은 데서 온다. 289건의 정의(어떤 조건을
센 것인지)를 확인해 주면 같은 기준으로 다시 계산해 이 절을 갱신한다. 이 절은 `experiments/revision/e8_reconcile.py` 가 덧붙였다.

## (v-c) 5.3절용: 근거 파일명 지표의 세 가지 정의

기존 수치(1,016건 중 289건, 28.4%)는 출처 스크립트와 판정 기준을 찾을 수 없어 논문 서술에서 폐기한다(2026-11-12 결정). 같은 run2 리포트 200개(이슈 1,054건: 대상 페이지 502, `/login` 404 페이지 552)로 다음 세 정의를 계산했다. 파일명은 정규화하지 않았다.

| 정의 | 분모 기준 | 분자 기준 | 분모 | 분자 | 비율 | 분자 내역: null | '' | 'N/A' | gov_check.pdf | 말뭉치 밖 파일명 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 기존 audit 기준: null/''/'N/A' 제외, /login 포함 | 말뭉치(gov_guide.pdf, gov_check.pdf)에 없는 파일명 | 1016 | 356 | 35.0% | 0 | 0 | 0 | 0 | 356 |
| B | E8 기준: 전체 이슈, /login 포함 | gov_guide.pdf 가 아님 (결측 표기 포함) | 1054 | 394 | 37.4% | 17 | 2 | 19 | 0 | 356 |
| C-A | 대상 페이지 이슈만, null/''/'N/A' 제외 | 말뭉치에 없는 파일명 | 464 | 92 | 19.8% | 0 | 0 | 0 | 0 | 92 |
| C-B | 대상 페이지 이슈만, 전체 | gov_guide.pdf 가 아님 (결측 표기 포함) | 502 | 130 | 25.9% | 17 | 2 | 19 | 0 | 92 |

E8 (v)의 '말뭉치에 없는 파일명 394건(37.4%)'은 정의 B 와 같은 값이며, 그 안에 결측 표기 38건(JSON null 17, 빈 문자열 2, 'N/A' 19)이 포함되어 있다. gov_check.pdf 를 인용한 이슈는 0건이라 정의 B 의 '말뭉치 밖'과 'gov_guide.pdf 아님'이 같은 값이 된다.

정의 차이: 정의 A 는 결측 표기를 분모에서 빼고 실제 파일명이 적힌 이슈만 대상으로 '말뭉치에 없는 이름'을 세므로 356/1016(35.0%)이고, 정의 B 는 결측 표기까지 분모와 분자에 넣어 394/1054(37.4%)로 높아진다. 두 정의 모두 크롤러가 따라간 `/login` 404 페이지의 이슈를 포함하는데, 이 552건 중 264건이 말뭉치 밖 파일명(정의 A 분자의 74%)이고 나머지는 모두 gov_guide.pdf·[12]여서 결과를 크게 좌우한다. 대상 페이지 이슈만 세는 정의 C 에서는 결측 제외 시 92/464(19.8%), 결측 포함 시 130/502(25.9%)이다. 테스트베드 페이지에 대한 시스템의 근거 기록을 평가한다는 목적에는 정의 C 가 가장 가깝고, 이번 재실험(`--max-pages 1`)의 수치도 정의 C 와 같은 범위(대상 페이지만)로 계산된다. 모든 정의에서 run2 는 검색 컨텍스트가 비어 있었으므로 적힌 파일명은 모두 컨텍스트 없이 모델이 만든 값이다. 이 절은 `experiments/revision/e8_v_definitions.py` 가 덧붙였고 수치는 `e8_v_definitions.csv` 에 있다.

## (v-d) 5.3절 확정 표: 정의 C (대상 페이지 이슈만)

run2 대상 페이지 이슈 502건 (링크된 `/login` 404 페이지 이슈 제외). 파일명은 정규화하지 않았다.

| 지표 | 분자 | 분모 | 비율 |
|---|---:|---:|---:|
| (a) 파일명 결측 (null, '', 'N/A') | 38 | 502 | 7.6% |
| (b) 프롬프트 예시값과 일치 (gov_guide.pdf 이면서 page_number [12] 또는 [12, 13]) | 81 | 502 | 16.1% |
| (c-1) 말뭉치에 없는 파일명 — 파일명이 있는 이슈 기준 | 92 | 464 | 19.8% |
| (c-2) 말뭉치에 없는 파일명 — 대상 이슈 전체 기준 (결측은 분자에 넣지 않음) | 92 | 502 | 18.3% |
| (c-3) 말뭉치에 없는 파일명 + 결측 — 대상 이슈 전체 기준 | 130 | 502 | 25.9% |
| (d) gov_check.pdf 를 인용한 이슈 | 0 | 502 | 0.0% |

- 결측 내역: {"'N/A'": 19, 'JSON null': 17, "''": 2}
- 말뭉치에 없는 파일명 상위: {'General Web Standards': 13, '정부 표준 가이드라인': 12, 'general_ui_ux_principles.pdf': 6, '정부 표준 가이드라인 (기본 지침)': 6, 'HTML 소스코드': 5, 'General Web Accessibility and Responsive Design Standards': 4}
- 고정 질의 검색 결과(실행 로그 65건: pilot-02, E1-R1): 청크 조합 1종, 출처 {'gov_guide.pdf': 260} → 4개 청크가 모두 gov_guide.pdf 이다.
- gov_check.pdf 청크(288개)가 고정 질의 상위 K 에 들어갈 가능성: 실행 로그에는 상위 4개의 거리(0.4518~0.4626)만 있으므로, gov_check.pdf 청크의 최상위 거리는 0.4626 이상이고 순위는 5위 이하라는 것만 확정된다. 정확한 최상위 거리와 순위는 고정 질의 임베딩이 필요해 Gemini 임베딩 API 1회 호출이 있어야 계산할 수 있다(API 호출 없이 하라는 지시에 따라 계산하지 않음).

이 절은 `experiments/revision/e8_definition_c.py` 가 덧붙였고 수치는 `e8_definition_c.csv` 에 있다.
