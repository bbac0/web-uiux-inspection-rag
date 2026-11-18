# 키워드 사전 (원본 그대로, 수정 없음)

- 출처: `experiments/evaluate_performance_v5.py` 의 `CATEGORY_PHRASES` (파일 SHA-256 `4f3ab78fe93e9af4a962fabd97964bb9ff34e7fac169e154d26fc58b5d765eeb`)
- `experiments/semantic_issue_classifier.py` 에 있는 사본과 동일 여부: **동일**
- 이 문서는 스크립트가 사전을 import 해서 자동 생성했다 (`experiments/revision/stage0_inventory.py`).

## 매칭 규칙 (코드에서 읽은 그대로)

1. 리포트의 `issues[]` 중 `description` 에 `testbed_200/{page_id}.html` 문자열이 들어간 이슈만 채점한다 (크롤러가 따라간 `/login` 등 다른 URL에 대한 이슈는 제외).
2. `description` 필드만 본다. `summary`, `suggestion`, `category` 는 쓰지 않는다.
3. `description.lower()` 안에 구문의 `lower()` 가 부분 문자열로 들어 있으면 해당 유형으로 매칭한다.
4. 한 이슈가 여러 유형에 동시에 매칭될 수 있다 (다중 라벨). 단 `semantic_issue_classifier.keyword_label()` 은 사전 순서상 첫 매칭 유형 하나만 돌려준다 (이슈 단위 단일 라벨이 필요할 때의 기존 동작).
5. 페이지 판정: 매칭된 유형이 하나라도 있으면 '결함 탐지'. 유형별 탐지율은 정답 유형이 매칭 집합에 있는지로 계산.

## Poor Contrast Ratio (5개)

| # | 구문 | 비고 |
|---|---|---|
| 1 | `명도 대비` |  |
| 2 | `대비 비율` |  |
| 3 | `contrast ratio` |  |
| 4 | `wcag` | 포괄 구문: 무관한 언급과도 매칭될 수 있음 |
| 5 | `가독성` | 포괄 구문: 무관한 언급과도 매칭될 수 있음 |

## Mobile Layout Breakage (7개)

| # | 구문 | 비고 |
|---|---|---|
| 1 | `레이아웃이 깨` |  |
| 2 | `레이아웃 깨짐` |  |
| 3 | `가로 스크롤` |  |
| 4 | `viewport` | 포괄 구문: 무관한 언급과도 매칭될 수 있음 |
| 5 | `모바일 화면` |  |
| 6 | `반응형` | 포괄 구문: 무관한 언급과도 매칭될 수 있음 |
| 7 | `overflow` | 포괄 구문: 무관한 언급과도 매칭될 수 있음 |

## Button Area Clipping (13개)

| # | 구문 | 비고 |
|---|---|---|
| 1 | `버튼이 잘` |  |
| 2 | `버튼 잘림` |  |
| 3 | `버튼 영역` |  |
| 4 | `clipping` |  |
| 5 | `겹침` | 포괄 구문: 무관한 언급과도 매칭될 수 있음 |
| 6 | `overlap` |  |
| 7 | `클릭 영역` |  |
| 8 | `클릭할 수 없` |  |
| 9 | `클릭할수 없` |  |
| 10 | `상호작용이 불가능` |  |
| 11 | `시각적으로 거의 보이지` |  |
| 12 | `font-size: 0px` |  |
| 13 | `height: 2px` |  |

## Standard Terminology Violation (6개)

| # | 구문 | 비고 |
|---|---|---|
| 1 | `표준 용어` |  |
| 2 | `용어 위반` |  |
| 3 | `terminology` |  |
| 4 | `용어 불일치` |  |
| 5 | `용어가 표준` |  |
| 6 | `접속하기` |  |

## Duplicate ID Markup Error (8개)

| # | 구문 | 비고 |
|---|---|---|
| 1 | `id가 중복` |  |
| 2 | `중복된 id` |  |
| 3 | `duplicate id` |  |
| 4 | `동일한 id` |  |
| 5 | `id 속성이 중복` |  |
| 6 | `wai-aria` | 포괄 구문: 무관한 언급과도 매칭될 수 있음 |
| 7 | `두 번 사용되어` |  |
| 8 | `중복 사용` | 포괄 구문: 무관한 언급과도 매칭될 수 있음 |
