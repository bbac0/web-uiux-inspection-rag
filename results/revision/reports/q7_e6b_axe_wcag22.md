# 확인 7: axe-core 추가 스캔 (WCAG 2.2 규칙 켬, 1280px 와 모바일 390px)

작성: `experiments/revision/e6b_axe_scan.py`(스캔), `experiments/revision/e6b_axe_report.py`(이 보고서).
사전 지정: `results/revision/analysis_plan_addendum_e6b.md` (스캔 전 커밋 65d2751). API 비용 없음(로컬 스캔).
axe-core 4.14.0, Chromium 151.0.7922.34, 대기 goto(wait_until='networkidle', timeout=30000) + 3000 ms.
스캔 오류 0건.
스캔 시각 2026-11-18T15:34:25Z ~ 2026-11-18T16:01:08Z. 페이지 수 {'1280': 200, '390': 200}.

## 1. 설정 C

- E6 설정 B(duplicate-id, duplicate-id-active, duplicate-id-aria 켬) +
  `axe.getRules(['wcag22a','wcag22aa'])` 규칙 전부 켬.
- 이 설치본에서 WCAG 2.2 태그로 켠 규칙: `target-size`.
- 유형별 대응 규칙은 E6 부록 (c) 그대로: 대비 color-contrast, 중복 ID duplicate-id 계열, 버튼 target-size,
  모바일·용어 없음.

## 2. 유형별 TP·FP 페이지 수

칸 = 페이지 수. 양성 = 그 라벨의 양성 페이지 수. inc = 대응 규칙이 incomplete 로만
보고된 페이지(위반으로 세지 않음). duplicate-id 계열 = duplicate-id, duplicate-id-active, duplicate-id-aria.
effective 는 스캔 뷰포트와 같은 뷰포트 라벨이다. 'E6 B' 열은 같은 뷰포트의 기존 설정 B 결과(TP / FP).

### 2.1a 설정 C, 1280, 라벨 nominal

| 유형 | 양성 | TP | FP | inc | E6 B (TP / FP) | 대응 규칙 |
|---|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | 44 / 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 0 / 0 | 없음 |
| 버튼 | 46 | 7 | 15 | 0 | 0 / 0 | target-size |
| 용어 | 45 | 0 | 0 | 0 | 0 / 0 | 없음 |
| 중복ID | 40 | 40 | 0 | 0 | 40 / 0 | duplicate-id 계열 |

출처: `results/revision/e6b/scan_C_1280.json`, `results/revision/e6/scan_B_1280.json`,
`results/revision/ground_truth.csv`

### 2.1b 설정 C, 1280, 라벨 effective_1280

| 유형 | 양성 | TP | FP | inc | E6 B (TP / FP) | 대응 규칙 |
|---|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | 44 / 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 0 / 0 | 없음 |
| 버튼 | 20 | 7 | 15 | 0 | 0 / 0 | target-size |
| 용어 | 42 | 0 | 0 | 0 | 0 / 0 | 없음 |
| 중복ID | 40 | 40 | 0 | 0 | 40 / 0 | duplicate-id 계열 |

출처: `results/revision/e6b/scan_C_1280.json`, `results/revision/e6/scan_B_1280.json`,
`results/revision/ground_truth.csv`

- 1280: target-size 가 실행된 페이지 200, 위반 22, incomplete 0.

### 2.2a 설정 C, 390, 라벨 nominal

| 유형 | 양성 | TP | FP | inc | E6 B (TP / FP) | 대응 규칙 |
|---|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | 44 / 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 0 / 0 | 없음 |
| 버튼 | 46 | 7 | 15 | 0 | 0 / 0 | target-size |
| 용어 | 45 | 0 | 0 | 0 | 0 / 0 | 없음 |
| 중복ID | 40 | 40 | 0 | 0 | 40 / 0 | duplicate-id 계열 |

출처: `results/revision/e6b/scan_C_390.json`, `results/revision/e6/scan_B_390.json`,
`results/revision/ground_truth.csv`

### 2.2b 설정 C, 390, 라벨 effective_390

| 유형 | 양성 | TP | FP | inc | E6 B (TP / FP) | 대응 규칙 |
|---|---|---|---|---|---|---|
| 대비 | 44 | 44 | 0 | 0 | 44 / 0 | color-contrast |
| 모바일 | 56 | 0 | 0 | 0 | 0 / 0 | 없음 |
| 버튼 | 20 | 7 | 15 | 0 | 0 / 0 | target-size |
| 용어 | 42 | 0 | 0 | 0 | 0 / 0 | 없음 |
| 중복ID | 40 | 40 | 0 | 0 | 40 / 0 | duplicate-id 계열 |

출처: `results/revision/e6b/scan_C_390.json`, `results/revision/e6/scan_B_390.json`,
`results/revision/ground_truth.csv`

- 390: target-size 가 실행된 페이지 200, 위반 22, incomplete 0.

## 3. target-size 와 버튼 결함 (규칙 × 페이지)

| 뷰포트 | 버튼 결함 페이지 | 위반 | incomplete | 나머지 페이지 | 위반 | incomplete |
|---|---|---|---|---|---|---|
| 1280 | 46 | 7 | 0 | 154 | 15 | 0 |
| 390 | 46 | 7 | 0 | 154 | 15 | 0 |

출처: `results/revision/e6b/scan_C_{1280,390}.json`, `results/revision/ground_truth.csv` (nominal)

- 두 뷰포트 결과가 같다. target-size 위반 22쪽(1280 기준)의 내역:
  - 버튼 결함 페이지 7쪽: 모두 `login_page` 템플릿, 지적 요소는 `<button class="login-btn">`(높이 2px 로 줄어든 로그인 버튼).
    effective 버튼 결함 20쪽 중 나머지 13쪽(`portal_main` 5, `form_page` 6, `detail_page` 2)의 줄어든 버튼은 잡히지 않았다.
  - 버튼 결함이 없는 15쪽: 모두 `portal_main` 템플릿, 지적 요소는 머리글의 로그인 링크 `<a href="/login">`
    (용어 결함 페이지에서는 '접속하기'). 주입과 무관한 작은 인라인 링크다.
- 따라서 이 설정에서 버튼 유형의 TP 7, FP 15 는 템플릿에 따라 갈린다. 줄어든 버튼이 잡히지 않은 이유(target-size 의
  간격 예외 등)는 노드별 판정 근거를 따로 보지 않아 확정하지 않았다.
- 이 axe 4.14.0 설치본에서 `wcag22a`·`wcag22aa` 태그로 켜진 규칙은 target-size 하나다(run_log.json).

출처: `results/revision/e6b/scan_C_1280.json` (violations 의 target-size 노드 html),
`results/revision/ground_truth.csv` (template_id)

## 4. 한계

- 사전 계획(E6 부록) 밖의 사후 추가 스캔이다(연구자 지시 2026-11-19). E6 결과는 바꾸지 않았다.
- 버튼 결함은 버튼 높이 2px·글자 크기 0으로 만든다. target-size 는 24×24 CSS px 기준의 크기·간격 검사라 대응 규칙으로
  보지만, 버튼이 없는 템플릿에서는 결함이 화면에 나타나지 않는다(`injection_procedure.md`).
- 모바일 레이아웃 깨짐과 표준 용어는 axe-core 에 대응 규칙이 없어 구조적으로 0이다.
- 페이지 단위 기술 집계이며 검정은 하지 않았다.
