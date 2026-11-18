# 결함 주입 절차 (코드에서 복원)

주입 스크립트가 저장소에 있다: `experiments/generate_200_testbed.py` (SHA-256 `0fd199edcb57956f6843bb738d867e06b7f14b7862f8890c5c1f69e242d21054`). 아래 내용은 이 스크립트와 `testbed_200/dataset_metadata.json` 을 읽어 자동 생성했다.

## 재현성 검증

- 메타데이터에 기록된 결함을 기록된 순서대로 템플릿에 다시 적용한 결과가 기존 200개 파일과 바이트 단위로 같은 페이지: **200/200** (불일치: 없음)
- 별도로 스크립트 전체를 임시 폴더에서 실행해 200개 파일 + 메타데이터가 모두 바이트 단위로 같음을 확인했다 (0단계 탐색 시, 기존 파일은 건드리지 않음).

## 생성 알고리즘

- 시드: `random.seed(42)` (Python `random`, 전역 상태 하나로 결함 여부·개수·유형을 모두 뽑음)
- 템플릿 배정: `page_i` 의 템플릿 = `BASE_TEMPLATES` 순서상 `(i-1) % 10` 번째 (무작위 아님). 따라서 템플릿마다 정확히 20페이지.
- 결함 여부: `random.random() > 0.2` 이면 결함 페이지 (기대 비율 80%).
- 결함 개수: `random.choice([1, 2])`, 유형: `random.sample(DEFECT_POOL, 개수)` (한 페이지에 같은 유형 중복 없음).
- 적용 순서: 뽑힌 순서대로 `apply` (메타데이터 `defects` 배열 순서와 같음). 각 규칙은 서로 다른 지점을 바꾸므로 순서가 결과에 영향을 주지 않는다.
- 템플릿 순서: `portal_main`, `board_list`, `login_page`, `detail_page`, `dashboard`, `search_result`, `faq_page`, `form_page`, `terms_page`, `contact_page`

## 유형별 주입 규칙

| ID | 유형 | 주입 방법 (코드 원문 요약) | 결함 위치 |
|---|---|---|---|
| DEF_VIS_01 | Poor Contrast Ratio | `</head>` 앞에 `<style>* { color: #e5e5e5 !important; background-color: #ffffff !important; }</style>` 삽입 | 페이지의 모든 요소 (전역 CSS). 대비비 = 1.26:1 (아래 계산) |
| DEF_VIS_02 | Mobile Layout Breakage | `</head>` 앞에 `html, body, div, main, header { width: 3000px !important; min-width: 3000px !important; overflow-x: scroll !important; }` 삽입 | 전역. 모바일 전용이 아니라 1280px 데스크톱에서도 가로 넘침이 생긴다 |
| DEF_VIS_03 | Button Area Clipping | `</head>` 앞에 `button, .btn, .login-btn, .apply-btn { height: 2px; font-size: 0px; line-height: 0; padding: 0; overflow: hidden; border: 1px solid red }` (모두 !important) 삽입 | `<button>` 요소. 버튼이 없는 템플릿에서는 화면상 효과 없음 (아래 표) |
| DEF_OPS_01 | Standard Terminology Violation | `html.replace('로그인', '접속하기')` (모든 출현을 치환, `href="/login"` 은 그대로) | 템플릿별 '로그인' 텍스트 위치 (아래 표). `form_page` 에는 '로그인'이 없어 주입이 일어나지 않음 |
| DEF_TEC_01 | Duplicate ID Markup Error | `<body>` 바로 뒤에 `<div id="main-banner"></div><div id="main-banner"></div>` 삽입 | body 첫 자식, 내용 없는 div 2개 (화면상 보이지 않음). `portal_main` 은 원래 `#main-banner` 가 있어 3개가 됨 |

대비비 계산: L(#e5e5e5) = 0.7835, L(#ffffff) = 1.0 → (1.05)/(0.8335) = **1.26:1** (WCAG 1.4.3 기준 4.5:1 미달).

## 템플릿별 주입 위치

| 템플릿 | `<button>` 있음 | '로그인' 출현 위치 (용어 위반 시 '접속하기'로 바뀜) | 기존 `#main-banner` |
|---|---|---|---|
| `portal_main` | 예 | `<a>로그인` (1회) | 예 |
| `board_list` | **아니오** | `<a>로그인` (1회) | 아니오 |
| `login_page` | 예 | `<title>로그인 - 대한민국 정부`, `<h2>로그인`, `<button>로그인` (3회) | 아니오 |
| `detail_page` | 예 | `<a>로그인` (1회) | 아니오 |
| `dashboard` | **아니오** | `<a>로그인` (1회) | 아니오 |
| `search_result` | **아니오** | `<a>로그인` (1회) | 아니오 |
| `faq_page` | **아니오** | `<a>로그인` (1회) | 아니오 |
| `form_page` | 예 | **없음 (주입 불가)** (0회) | 아니오 |
| `terms_page` | **아니오** | `<a>로그인` (1회) | 아니오 |
| `contact_page` | **아니오** | `<a>로그인` (1회) | 아니오 |

## 분포

- 결함 페이지 161개, 대조군 39개
- 페이지당 결함 수: 0개 → 39페이지, 1개 → 91페이지, 2개 → 70페이지
- 유형별 페이지 수: Poor Contrast Ratio 44, Mobile Layout Breakage 56, Button Area Clipping 46, Standard Terminology Violation 45, Duplicate ID Markup Error 40

### 템플릿 × 유형 (페이지 수)

| 템플릿 | Poor Contrast Ratio | Mobile Layout Breakage | Button Area Clipping | Standard Terminology Violation | Duplicate ID Markup Error | 결함 페이지 | 대조군 |
|---|---|---|---|---|---|---|---|
| `portal_main` | 1 | 5 | 5 | 4 | 8 | 17 | 3 |
| `board_list` | 3 | 6 | 5 | 6 | 2 | 15 | 5 |
| `login_page` | 6 | 6 | 7 | 6 | 3 | 18 | 2 |
| `detail_page` | 7 | 4 | 2 | 4 | 5 | 16 | 4 |
| `dashboard` | 6 | 7 | 3 | 4 | 3 | 19 | 1 |
| `search_result` | 9 | 9 | 2 | 1 | 2 | 16 | 4 |
| `faq_page` | 3 | 3 | 6 | 5 | 2 | 14 | 6 |
| `form_page` | 3 | 6 | 6 | 3 | 5 | 15 | 5 |
| `terms_page` | 3 | 4 | 6 | 6 | 5 | 15 | 5 |
| `contact_page` | 3 | 6 | 4 | 6 | 5 | 16 | 4 |

### 결함 조합 (페이지 수)

| 조합 | 페이지 |
|---|---|
| Poor Contrast Ratio | 22 |
| Mobile Layout Breakage | 21 |
| Button Area Clipping | 17 |
| Standard Terminology Violation | 17 |
| Duplicate ID Markup Error | 14 |
| Mobile Layout Breakage + Standard Terminology Violation | 10 |
| Button Area Clipping + Mobile Layout Breakage | 10 |
| Button Area Clipping + Duplicate ID Markup Error | 8 |
| Button Area Clipping + Standard Terminology Violation | 8 |
| Mobile Layout Breakage + Poor Contrast Ratio | 8 |
| Duplicate ID Markup Error + Mobile Layout Breakage | 7 |
| Duplicate ID Markup Error + Poor Contrast Ratio | 6 |
| Duplicate ID Markup Error + Standard Terminology Violation | 5 |
| Poor Contrast Ratio + Standard Terminology Violation | 5 |
| Button Area Clipping + Poor Contrast Ratio | 3 |

## 주의가 필요한 페이지 (주입이 의도대로 드러나지 않는 경우)

1. **용어 위반이 실제로 주입되지 않은 페이지 3개**: `page_028.html` (form_page), `page_038.html` (form_page), `page_168.html` (form_page). 메타데이터상 정답은 Standard Terminology Violation 이지만 파일에는 '로그인'/'접속하기'가 없다.
2. **버튼이 없는 템플릿에 Button Area Clipping 이 기록된 페이지 26개**: CSS 규칙만 들어 있고 대상 요소가 없어 화면상 결함이 없다. HTML 원문에는 `height: 2px` 등의 CSS 문자열이 남으므로 모델이 소스를 읽고 '탐지'할 수는 있다: `page_009.html`, `page_017.html`, `page_026.html`, `page_029.html`, `page_035.html`, `page_037.html`, `page_050.html`, `page_052.html`, `page_059.html`, `page_079.html`, `page_082.html`, `page_092.html`, `page_096.html`, `page_097.html`, `page_107.html`, `page_115.html`, `page_129.html`, `page_130.html`, `page_135.html`, `page_137.html`, `page_139.html`, `page_140.html`, `page_142.html`, `page_162.html`, `page_180.html`, `page_197.html`
3. **Mobile Layout Breakage 는 모바일 전용 결함이 아니다**: 3000px 고정 폭이라 1280x800 데스크톱에서도 가로 스크롤이 생긴다.
4. **Duplicate ID 는 화면에 보이지 않는다**: 빈 div 2개이므로 스크린샷으로는 탐지할 수 없고 HTML 로만 탐지 가능.
5. 위 1, 2 는 5단계 E0 (결정적 검증)에서 `ground_truth.csv` 의 `검증 통과 여부` 로 다시 확인한다. 이 문서는 정답 라벨을 바꾸지 않는다.

## 복원이 불완전한 부분

- 없음. 주입 스크립트와 시드가 남아 있고, 규칙 재적용 결과가 200개 파일 모두와 일치한다.
- 다만 `testbed/` (지연시간 측정용 50페이지)의 생성 스크립트는 `_archive/make_testbed.py` 로 보이며 이번 범위에서는 해시만 기록했다.
