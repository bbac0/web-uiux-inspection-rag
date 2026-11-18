# analysis_plan 부록: E6 axe-core 스캔 (사전 지정)

작성 2026-11-13. **스캔 실행 전, 결과를 보기 전에** 고정한다. 동결된 `results/revision/analysis_plan.md` 7절 118행
("E6 axe-core v4.14.0 기본 설정, duplicate-id 계열 규칙을 켠 설정 두 가지로 200페이지 스캔. 유형별 탐지와 대조군 위반 수")을
구체화하며 그 파일은 고치지 않는다. 이 부록을 커밋한 뒤에 스캔한다. 결과가 어떻게 나와도 그대로 보고한다.

## (a) 스캔 설정과 axe-core 버전

- 설치본: 저장소 루트 `axe.min.js`, 머리말 `axe v4.14.0`, 실행 시 `axe.version` = **4.14.0** (2026-11-13 확인).
  SHA-256 `20c09fe157a8a34a30e241aaa1fcdade657734f08ab379ecfbeb7d45cc46e878`. E0 대조군 스캔과 같은 파일이다.
  스캔 중 `axe.version` 이 4.14.0 이 아니면 멈춘다.
- 설정 A: `axe.run(document)` 기본 설정(옵션 없음).
- 설정 B: `axe.run(document, {rules: {"duplicate-id": {enabled: true}, "duplicate-id-active": {enabled: true},
  "duplicate-id-aria": {enabled: true}}})`. 4.14.0 에서 duplicate-id, duplicate-id-active 는 deprecated 로 기본 꺼짐,
  duplicate-id-aria 는 기본 켜짐(확인값).

## (b) 뷰포트와 대상

- 1280x800, 390x844 각각. 대상 testbed_200 200페이지 전체(로컬 서버 `http://localhost:8080/testbed_200/`).
- 렌더링: Playwright Chromium, 프로덕션과 같은 UA, `networkidle` 후 3초 대기(기존 파이프라인과 같음), 그 뒤 `axe.min.js` 주입.
- 한 번 렌더링한 페이지에서 설정 A, B 를 차례로 실행한다(axe 는 DOM 을 바꾸지 않음). 출력은 설정 × 뷰포트 4개 스캔으로 나눈다.

## (c) 유형별 대응 규칙 (확정, 이후 수정하지 않음)

근거는 axe-core 4.14.0 `axe.getRules()` 의 규칙 설명(description)과 기본 활성 여부(`axe._audit.rules[].enabled`)다.

| 결함 유형 | 대응 규칙 (탐지로 셈) |
|---|---|
| 명도 대비 부족 | color-contrast |
| 중복 ID | duplicate-id, duplicate-id-active, duplicate-id-aria |
| 버튼 영역 잘림 | target-size (기본 꺼짐 → 설정 A, B 모두에서 실행되지 않음, 아래 참고) |
| 모바일 레이아웃 깨짐 | 없음 |
| 표준 용어 위반 | 없음 |

후보 규칙과 판정 (설명은 axe-core 4.14.0 원문 한 줄, 괄호는 기본 활성 여부):

| 유형 | 후보 규칙 | 설명 | 판정 |
|---|---|---|---|
| 대비 | color-contrast (켜짐) | Ensure the contrast ... meets WCAG 2 AA minimum contrast ratio thresholds | 대응 |
| 대비 | color-contrast-enhanced (꺼짐) | ... meets WCAG 2 AAA enhanced contrast ratio thresholds | 대응 아님 (AAA, 기본 꺼짐) |
| 대비 | link-in-text-block (켜짐) | Ensure links are distinguished from surrounding text ... not rely on color | 대응 아님 (글자-배경 대비가 아님) |
| 중복 ID | duplicate-id (꺼짐) | Ensure every id attribute value is unique | 대응 |
| 중복 ID | duplicate-id-active (꺼짐) | Ensure every id attribute value of active elements is unique | 대응 |
| 중복 ID | duplicate-id-aria (켜짐) | Ensure every id attribute value used in ARIA and in labels is unique | 대응 |
| 버튼 | target-size (꺼짐) | Ensure touch targets have sufficient size and space | 대응 (크기 부족을 직접 검사) |
| 버튼 | button-name (켜짐) | Ensure buttons have discernible text | 대응 아님 (접근 가능한 이름 검사, 시각 크기 무관) |
| 버튼 | input-button-name (켜짐) | Ensure input buttons have discernible text | 대응 아님 (위와 같음) |
| 버튼 | aria-command-name (켜짐) | Ensure every ARIA button, link and menuitem has an accessible name | 대응 아님 (위와 같음) |
| 버튼 | nested-interactive (켜짐) | Ensure interactive controls are not nested ... | 대응 아님 |
| 모바일 | meta-viewport (켜짐) | Ensure <meta name="viewport"> does not disable text scaling and zooming | 대응 아님 (확대 금지 검사) |
| 모바일 | meta-viewport-large (켜짐) | Ensure <meta name="viewport"> can scale a significant amount | 대응 아님 (위와 같음) |
| 모바일 | css-orientation-lock (켜짐, experimental) | Ensure content is not locked to any specific display orientation ... | 대응 아님 (방향 고정 검사) |
| 모바일 | scrollable-region-focusable (켜짐) | Ensure elements that have scrollable content are accessible by keyboard in Safari | 대응 아님 (키보드 접근 검사) |
| 모바일 | avoid-inline-spacing (켜짐) | Ensure that text spacing set through style attributes can be adjusted ... | 대응 아님 |
| 용어 | link-name (켜짐) | Ensure links have discernible text | 대응 아님 (이름 존재 여부, 문구 적절성 아님) |
| 용어 | identical-links-same-purpose (꺼짐) | Ensure that links with the same accessible name serve a similar purpose | 대응 아님 |
| 용어 | label-content-name-mismatch (켜짐, experimental) | ... visible text as part of their accessible name | 대응 아님 |

- 버튼 영역 잘림의 대응 규칙 target-size 는 4.14.0 에서 기본 꺼짐이고, 계획된 두 설정(A 기본, B 기본 + duplicate-id 계열)은
  이것을 켜지 않는다. 따라서 **두 설정 모두에서 버튼 유형은 구조적으로 탐지 0** 이며 그대로 보고한다(설정을 바꾸지 않는다).
- axe-core 에는 리플로(WCAG 1.4.10, 가로 스크롤) 검사 규칙이 없어 모바일 유형의 대응 규칙은 없다.
  표준 용어(레이블 문구의 적절성)를 검사하는 규칙도 없다.

## (d) 판정

- 페이지 × 유형 셀: 그 유형의 대응 규칙이 그 페이지에서 `violations` 로 보고되면 탐지(1). 대응 규칙이 없거나 실행되지 않으면 0.
- `incomplete`(needs review)는 위반으로 세지 않고 별도 열로 센다. 대응 규칙 밖의 위반은 별도 표(규칙 ID별 페이지 수)로 보고한다.

## (e) 라벨

- nominal(`ground_truth.csv` nominal_injected), effective 1280(effective_1280, 1280 스캔에 적용), effective 390
  (effective_390, 390 스캔에 적용). 대조군 = nominal 주입 유형 없음(39페이지).
- 기술 집계만 한다(TP, FP 페이지 수). 검정은 하지 않는다. 기존 LLM 결과(E1-R1, E2-A1-1, 키워드 채점)와 같은 형식으로 나란히 둔다.

## 출력

`results/revision/e6/` (스캔 원본 JSON 4개, SHA256SUMS, README.md), 보고서 `results/revision/reports/e6_axe_report.md`,
스크립트 `experiments/revision/e6_axe_scan.py`, `experiments/revision/e6_axe_report.py`.
