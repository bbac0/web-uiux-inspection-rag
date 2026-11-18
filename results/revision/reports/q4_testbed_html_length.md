# 확인 4: 테스트베드 HTML 길이와 주입 결함이 앞 5,000자 안에 있는가

작성 2026-11-19. API 호출 없음.

모델에 들어가는 HTML 은 원본 파일이 아니라 렌더링 후 `page.content()`(DOM 직렬화)의 앞 5,000자다
(`services/analyzer.py` 273행, `HTML_CHAR_LIMIT = 5000`). 실행 기록에 실제로 보낸 글자 수(`html_chars_sent`)가 있고,
보낸 프롬프트 전문이 `runs/{run}/prompts/{prompt_sha256}.txt` 에 있어 그 안에서 결함 위치를 찾았다.

## 1. HTML 길이 분포 (문자 수)

| 테스트베드 | 페이지 | 최소 | 25% | 중앙값 | 75% | 최대 | 평균 | 5,000자 초과 |
|---|---|---|---|---|---|---|---|---|
| testbed_200 원본 파일 | 200 | 188 | 274 | 342 | 428 | 637 | 352.0 | 0 |
| testbed_200 실제 보낸 HTML (E1-R1) | 200 | 188 | 274 | 346 | 435 | 648 | 356.2 | 0 |
| testbed_e9 원본 파일 | 91 | 1,710 | 1,743 | 1,786 | 1,801 | 1,908 | 1,782.3 | 0 |
| testbed_e9 실제 보낸 HTML (norag-r1) | 91 | 1,710 | - | - | - | 1,917 | - | 0 |

출처: `testbed_200/page_*.html`, `testbed_e9/e9_*.html`, `results/revision/runs/E1-R1/calls.jsonl`,
`results/revision/runs_e9/e9-main-norag-r1/calls.jsonl` (html_chars_sent)

- 두 테스트베드 모두 모든 페이지가 5,000자보다 짧다. `html_chars_sent` 가 5,000 인 호출은 0건이므로 **잘린 페이지가 없고,
  페이지 HTML 전체가 모델에 들어갔다.** 따라서 HTML 에 있는 결함은 모두 앞 5,000자 안에 있다.

## 2. testbed_200: 결함 유형별 주입 위치 (E1-R1 이 실제로 보낸 HTML 에서 찾음)

| 결함 유형 | 찾은 표지 | nominal 페이지 | 보낸 HTML 에 있음 | 위치 최대(글자) | 앞 5,000자 안 |
|---|---|---|---|---|---|
| 명도 대비 부족 | `color: #e5e5e5` (전역 CSS) | 44 | 44 | 312 | 44/44 |
| 모바일 레이아웃 깨짐 | `width: 3000px` (전역 CSS) | 56 | 56 | 339 | 56/56 |
| 버튼 영역 잘림 | `height: 2px` (버튼 CSS) | 46 | 46 | 268 | 46/46 |
| 표준 용어 위반 | `접속하기` (첫 출현) | 45 | 42 | 410 | 42/42 |
| 중복 ID | `<div id="main-banner"></div>` 두 번 | 40 | 40 | 316 | 40/40 |

출처: `results/revision/runs/E1-R1/prompts/*.txt`, `results/revision/ground_truth.csv`,
`results/revision/injection_procedure.md`

- 표준 용어 위반의 3쪽(page_028, page_038, page_168)은 `form_page` 템플릿이라 '로그인'이 없어 치환이 일어나지 않았다
  (주입 기록상 nominal 이지만 실제 HTML 에 결함 없음; effective 라벨 42와 같다).
- 표지 위치는 0부터 센 글자 위치다. 결함 CSS 는 모두 `</head>` 앞 `<style>` 에, 중복 ID 는 `<body>` 바로 뒤에 있다.

## 3. testbed_e9: 결함 유형별 (결정적 검증 기록 `in_first_5000`)

| 결함 유형 | 페이지 | 앞 5,000자 안 | 주입 끝 위치 최대 | 렌더링 HTML 길이 |
|---|---|---|---|---|
| E9-1a | 8 | 8 | 1,081 | 1,713~1,809 |
| E9-1b | 8 | 8 | 1,083 | 1,711~1,809 |
| E9-2 배너 | 7 | 7 | 325 | 1,710~1,792 |
| E9-2 푸터 | 4 | 4 | 895 | 1,733~1,798 |
| E9-2 헤더 | 4 | 4 | 591 | 1,744~1,815 |
| E9-3 | 15 | 15 | 1,337 | 1,713~1,816 |
| E9-4 | 15 | 15 | 997 | 1,810~1,913 |
| 대조군 | 30 | 해당 없음 | - | 1,712~1,815 |

출처: `results/revision/e9/ground_truth_e9.csv` (inj_offset_end, in_first_5000, rendered_html_chars)
