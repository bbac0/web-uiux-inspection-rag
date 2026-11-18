# E0 결함 주입 검증 요약

- 렌더링: Chromium(Playwright), 뷰포트 1280x800 / 390x844, UA 프로덕션과 같음, `networkidle` 후 측정. axe-core 4.14.0.
- 규칙: `analysis_plan.md` 1절 (대비 < 4.5:1, scrollWidth > innerWidth, 버튼 높이 ≤ 4px 또는 font-size 0, '접속하기' 존재, 같은 id ≥ 2).

## 유형별 nominal vs effective (페이지 수)

| 유형 | nominal | effective 1280 | effective 390 | nominal=1·eff1280=0 | nominal=0·eff1280=1 | nominal=1·eff390=0 | nominal=0·eff390=1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Poor Contrast Ratio | 44 | 44 | 44 | 0 | 0 | 0 | 0 |
| Mobile Layout Breakage | 56 | 56 | 56 | 0 | 0 | 0 | 0 |
| Button Area Clipping | 46 | 20 | 20 | 26 | 0 | 26 | 0 |
| Standard Terminology Violation | 45 | 42 | 42 | 3 | 0 | 3 | 0 |
| Duplicate ID Markup Error | 40 | 40 | 40 | 0 | 0 | 0 | 0 |

- 대비 결함 페이지 최소 대비비 값: [1.26]; 비결함 페이지 최소 대비비 범위: 9.398 ~ 21
- 모바일 결함 scrollWidth: 1280 → [3008], 390 → [3008]
- 정적 문자열 검사(HTML 원문에 주입 문자열이 있는가)와 nominal 의 불일치(알려진 form_page 용어 3건 제외): 0건

## nominal ≠ effective 목록

- 전체 58건 (페이지×유형×뷰포트), 이 중 0단계에서 보고한 알려진 원인: 58건, **새로운 불일치: 0건**

- Button Area Clipping @ 1280: 26건 — known: 버튼 없는 템플릿 (효과 없음)
- Button Area Clipping @ 390: 26건 — known: 버튼 없는 템플릿 (효과 없음)
- Standard Terminology Violation @ 1280: 3건 — known: form_page 에 '로그인' 없음 (미주입)
- Standard Terminology Violation @ 390: 3건 — known: form_page 에 '로그인' 없음 (미주입)

- 중복 ID 결함 40페이지의 중복 요소 화면 면적 합: [0, 26544, 63000] (0 이면 비가시)

## 대조군 axe-core 자연 발생 이슈 (1280x800, 기본 설정)

| rule_id | impact | 페이지 수 | 노드 합 |
|---|---|---:|---:|
| page-has-heading-one | moderate | 16 | 16 |
| label | critical | 9 | 9 |

대조군 39페이지 중 위반 0건인 페이지: 23
