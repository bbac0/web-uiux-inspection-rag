# 파일럿 점검: pilot-02

## 1. 실행 상태

- 상태: {'ok': 10}, 파싱 실패 0, 재시도 합계 0
- model_version: ['gemini-2.5-flash'], 프롬프트 날짜 2026-11-11, git exp-freeze-v3
- 실제 실행 시각(UTC): 2026-11-12T00:27:05.514+00:00 → 2026-11-12T00:32:47.228+00:00
- 로그 스키마 문제 레코드: 0/10
- SHA256SUMS 대조 불일치: 없음

- 잠금: 쓰기 거부됨 (정상)
- chroma 원본 복사 시점 해시(파일 6개 결합): `95165c227ef7567f9bc99b0d132b0de45a0828c82565b3ce9cf72e5bd8ebaae1`; 복사본 정리: {'deleted': True, 'warning': None}

## 2. 토큰, 비용, 지연시간 (호출 평균)

| 항목 | 평균 | 최소 | 최대 |
|---|---:|---:|---:|
| prompt_token_count | 2262.0 | 2225 | 2317 |
| candidates_token_count | 631.5 | 305 | 804 |
| thoughts_token_count_derived | 2788.7 | 1999 | 3420 |
| thoughts_check_without_cached_subtraction | 2788.7 | 1999 | 3420 |
| cached_content_token_count | 0.0 | 0 | 0 |
| total_token_count | 5682.2 | 4559 | 6360 |
| 비용 (USD) | 0.00923 | 0.00644 | 0.01086 |
| 지연 acquisition (초) | 3.979 | 3.879 | 4.217 |
| 지연 query_embedding (초) | 0.613 | 0.504 | 1.170 |
| 지연 vector_search (초) | 0.022 | 0.000 | 0.084 |
| 지연 upload (초) | 6.493 | 4.651 | 14.727 |
| 지연 llm (초) | 17.527 | 12.534 | 20.729 |
| 지연 total (초) | 30.858 | 26.706 | 38.570 |

- derived 사고 토큰 음수: 없음; cached>0: 없음; 계산식 두 가지 불일치: 없음
- 사고/출력 토큰 비: 3.11 ~ 9.19 (평균 4.84)
- run 총비용 $0.0923 (입력 비캐시 $0.0068, cached $0.0000, 출력+사고 $0.0855)

## 3. RAG 검색

- n_chunks 분포: {4: 10}; 질의: `웹 UI/UX 표준 가이드라인 공통 규정`
- 페이지별 청크 ID 순서 조합 종류: 1 (1 이면 모든 페이지가 같은 4개를 같은 순서로 받음)

| 순위 | 청크 ID | 파일 | 쪽 | L2 거리 (페이지 간 범위) | 첫 100자 |
|---:|---|---|---:|---|---|
| 1 | `ce334282-62d0-4346-81ba-237ca8ef4d57` | gov_guide.pdf | 9 | 0.4518~0.4518 | 디지털 정부서비스 UI/UX 가이드라인 /   1 . 가 이 드 라 인 의   소 개 ' 디 지 털   정 부 서 비 스   UI / UX   가 이 드 라 인 ' 은   디 지  |
| 2 | `ffd48677-a4cc-405b-aacd-15820a7f65f0` | gov_guide.pdf | 15 | 0.4572~0.4572 | 디지털 정부서비스 UI/UX 가이드라인 /   15 가이드라인	소개		/		개요 적용 대상 및 기준 행정/공공기관이 구축 운영하는 모든 웹사이트, 모바일 웹·앱은 본 가이드라인의  |
| 3 | `654c214c-448d-4030-862a-67c5899520ca` | gov_guide.pdf | 218 | 0.4593~0.4593 | 디지털 정부서비스 UI/UX 가이드라인 /   1.	아이덴티티 공식 배너, 운영기관 식별자, 헤더, 푸터 2.	탐색 건너뛰기 링크 , 메인 메뉴, 브레드크럼, 사이드 메뉴, 콘텐츠 |
| 4 | `c1f2ba02-03ef-4962-a6c8-532bd1e0171c` | gov_guide.pdf | 1 | 0.4626~0.4626 | 디지털 정부서비스   UI/UX 가이드라인 2025.08 |

### 프롬프트 길이 (RAG 켬 vs run2 와 같은 빈 컨텍스트)

- 검색 컨텍스트 길이: 1653~1653자 (모든 페이지 같은 내용)
- 프롬프트 텍스트 길이: RAG 켬 평균 3656자 → 컨텍스트를 비우면 평균 2003자
- 프롬프트 텍스트 중 컨텍스트 비율(문자 기준): 45.2%
- 입력 토큰 평균 2262 (스크린샷 이미지 토큰 포함). 토크나이저를 따로 부르지 않았으므로 청크 4개의 정확한 토큰 수는 E2-A1(--no-rag)과 E1-R1 의 같은 페이지 입력 토큰 차이로 확정한다.

## 4. 모델이 보고한 근거와 검색 청크의 일치

- 이슈 32건. 검색 청크 (파일, 쪽): [('gov_guide.pdf', 1), ('gov_guide.pdf', 9), ('gov_guide.pdf', 15), ('gov_guide.pdf', 218)]
- source_file 이 검색 청크 파일 중 하나: 30/32 (93.8%)
- (파일, 쪽) 쌍이 검색 청크와 하나 이상 일치: 30/32 (93.8%); 모든 쪽이 일치: 30/32 (93.8%)
- 프롬프트 예시값(gov_guide.pdf, [12] 또는 [12, 13]) 그대로: 0/32 (0.0%)
- source_file 분포: {'gov_guide.pdf': 30, 'N/A': 1, 'None': 1}
- page_number 분포: {'[15, 218]': 12, '[15]': 10, '[218]': 3, '[9]': 3, '[9, 15]': 2, '[]': 2}

## 5. 페이지별 결과 (키워드 채점, 참고용)

| page_id | nominal 결함 | effective 결함 | 이슈 수 | 키워드 매칭 유형 |
|---|---|---|---:|---|
| page_105 | Poor(Contrast) | Poor(Contrast) | 1 | Poor(Contrast) |
| page_075 | Mobile(Layout) | Mobile(Layout) | 3 | Mobile(Layout) |
| page_135 | Button(Area) | - | 4 | Mobile(Layout) |
| page_077 | Standard(Terminology) | Standard(Terminology) | 1 | Standard(Terminology) |
| page_081 | Duplicate(ID) | Duplicate(ID) | 4 | Duplicate(ID) |
| page_123 | Mobile(Layout), Duplicate(ID) | Mobile(Layout), Duplicate(ID) | 5 | Duplicate(ID), Mobile(Layout) |
| page_028 | Standard(Terminology), Duplicate(ID) | Duplicate(ID) | 3 | Duplicate(ID) |
| page_054 | Poor(Contrast), Mobile(Layout) | Poor(Contrast), Mobile(Layout) | 3 | Mobile(Layout), Poor(Contrast) |
| page_033 | - | - | 4 | - |
| page_027 | - | - | 4 | - |

### page_135: 효과 없는 버튼 잘림 (dashboard, 버튼 없음)

요약: 제공된 웹사이트는 디지털 정부서비스 UI/UX 가이드라인의 필수 요소를 심각하게 위반하고 있습니다. 기본적인 정부 아이덴티티 요소와 스타일이 부재하며, 핵심적인 접근성 기능이 누락되어 있습니다. 또한, 전역 CSS 규칙으로 인해 버튼 요소의 사용성과 접근성이 심각하게 저해되고 있습니다.

| # | category | 키워드 매칭 | description (앞 220자) | source_file / page |
|---:|---|---|---|---|
| 1 | 기술 | Mobile Layout Breakage | 전역 CSS 규칙이 `button`, `.btn`, `.login-btn`, `.apply-btn` 요소의 `height`, `font-size`, `line-height`, `padding`, `overflow` 속성을 비정상적으로 설정하여 버튼의 시각적 표현과 상호작용을 불가능하게 만듭니다. 이는 심각한 접근성 및 사용성 문제입니다. | gov_guide.pdf / [15, 218] |
| 2 | 기술 | - | 키보드 사용자 및 스크린 리더 사용자의 편의를 위한 '탐색 건너뛰기 링크'가 누락되어 있습니다. 이는 웹 접근성 표준을 위반하며, 주요 콘텐츠로의 빠른 이동을 방해합니다. | gov_guide.pdf / [218] |
| 3 | 디자인 | - | 디지털 정부서비스 아이덴티티 요소(공식 배너, 헤더, 푸터) 및 스타일 가이드(색상, 서체, 형태, 배치, 아이콘)가 전혀 적용되지 않아 정부 서비스로서의 일관된 UI/UX를 제공하지 못하고 있습니다. | gov_guide.pdf / [15, 218] |
| 4 | 운영 | - | 페이지의 콘텐츠가 '로그인' 링크와 '신청 처리 내역' 제목 외에 거의 없어, 정부 서비스로서 사용자에게 제공해야 할 최소한의 정보나 기능 구성이 미흡합니다. | gov_guide.pdf / [9, 15] |

### page_028: 미주입 용어 위반 (form_page) + 중복 ID

요약: 제공된 웹사이트는 HTML ID 중복 및 레이블-입력 필드 간 명시적 연결 부재와 같은 기본적인 기술적 문제점을 가지고 있습니다. 또한, 디지털 정부서비스 UI/UX 가이드라인에서 제시하는 표준 컴포넌트 스타일을 준수하지 않아 사용자 경험 일관성이 부족합니다. 전반적인 웹 접근성과 디자인 표준 준수 노력이 필요합니다.

| # | category | 키워드 매칭 | description (앞 220자) | source_file / page |
|---:|---|---|---|---|
| 1 | 기술 | Duplicate ID Markup Error | HTML 문서 내 `id` 속성 값 (`main-banner`)이 중복 사용되었습니다. `id`는 문서 내에서 고유해야 합니다. | gov_guide.pdf / [9] |
| 2 | 디자인 | - | 텍스트 입력 필드와 버튼 컴포넌트가 디지털 정부서비스 UI/UX 가이드라인의 스타일을 준수하지 않고 기본 브라우저 스타일로 표시됩니다. | gov_guide.pdf / [15, 218] |
| 3 | 기술 | - | `<label>` 요소가 `<input>` 요소와 `for` 및 `id` 속성을 사용하여 명시적으로 연결되어 있지 않습니다. 이는 웹 접근성 측면에서 중요합니다. | gov_guide.pdf / [9] |
