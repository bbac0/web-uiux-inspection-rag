# E9 파일럿 보고서 (e9-pilot2, 2026-11-13)

- 대상: `testbed_e9_pilot/` 8페이지 × 5조건 × 1회. **파이프라인 점검용이며 모든 분석에서 제외한다.**
- 동결: `exp-freeze-e9-v3` (실행 전 동결 목록 대조 통과). Anthropic 의미 채점과 E9 LLM 판정은 쓰지 않았다.
- 러너 `experiments/revision/run_experiment_e9.py`, 순서 실행 `experiments/revision/run_e9_pilot.py`.
- oracle 입력: 본 실험 입력과 같은 청크·같은 순서를 파일럿 페이지 ID 로 옮긴 파일
  (`results/revision/e9_pilot/e9p_related_clause_chunks.csv`, `e9p_fixed_long_chunks.csv`).

## 1. 호출당 비용과 토큰, 총 비용

| 조건 | 호출 | 동시 | 입력/호출 | 캐시 입력/호출 | 출력+사고/호출 | 비용/호출 | 비용 |
|---|---|---|---|---|---|---|---|
| RAG 끔 | 8 | 1 | 1674 | 0 | 3928 | 0.01032 | 0.0826 |
| 고정 질의 | 8 | 1 | 2878 | 0 | 4526 | 0.01218 | 0.0974 |
| 페이지별 질의 | 8 | 1 | 2906 | 0 | 4619 | 0.01242 | 0.0994 |
| 관련 조항 제공 | 8 | 1 | 4375 | 0 | 4523 | 0.01262 | 0.1010 |
| fixed-long | 8 | 2 | 4218 | 186 | 4268 | 0.01194 | 0.0955 |

총 비용: $0.4758 (40호출). 단가: 입력 $0.30/1M, 캐시 $0.03/1M, 출력+사고 $2.50/1M.

출처: `results/revision/runs_e9_pilot/e9-pilot2-{조건}/calls.jsonl`, `run_meta.json`

## 2. 파싱 실패와 오류

| 조건 | ok | 파싱 실패 | 그 밖의 오류 | 재시도 | 오류 기록 | 모델 버전 |
|---|---|---|---|---|---|---|
| RAG 끔 | 8 | 0 | 0 | 0 | 0 | gemini-2.5-flash |
| 고정 질의 | 8 | 0 | 0 | 0 | 0 | gemini-2.5-flash |
| 페이지별 질의 | 8 | 0 | 0 | 0 | 0 | gemini-2.5-flash |
| 관련 조항 제공 | 8 | 0 | 0 | 0 | 0 | gemini-2.5-flash |
| fixed-long | 8 | 0 | 0 | 0 | 0 | gemini-2.5-flash |

출처: `results/revision/runs_e9_pilot/e9-pilot2-{조건}/calls.jsonl`

## 3. 가이드라인 컨텍스트가 프롬프트에 들어갔는가

프롬프트 파일(`prompts/{prompt_sha256}.txt`)의 '[1. 정부 표준 가이드라인]' 절 길이(글자). 페이지별 값의 최소~최대.

| 조건 | 청크 수 | 컨텍스트 글자 수 | 페이지 간 서로 다른 청크 목록 수 |
|---|---|---|---|
| RAG 끔 | 0청크×8 | 0~0 | 1 |
| 고정 질의 | 4청크×8 | 1653~1653 | 1 |
| 페이지별 질의 | 4청크×8 | 2539~3618 | 5 |
| 관련 조항 제공 | 6청크×8 | 4538~4538 | 1 |
| fixed-long | 9청크×8 | 4465~4465 | 1 |

RAG 끔은 컨텍스트 절이 비어 있어야 한다(0자). 관련 조항 제공·fixed-long 은 모든 페이지에 같은 청크 목록(1개)이어야 한다.

출처: `results/revision/runs_e9_pilot/e9-pilot2-{조건}/calls.jsonl`, `prompts/`

## 4. 페이지별 모델 보고 이슈 요약

주 지표 정규식으로 걸린 유형과, 그 유형에 걸린 첫 이슈(없으면 첫 이슈)의 설명 앞부분(URL 접두어 제거, 40자).

### 4.1 RAG 끔

| 페이지 | 주입 | 이슈 | 정규식 탐지 | 핵심 한 줄 |
|---|---|---|---|---|
| e9p_001 | E9-1a | 3 | - | 푸터의 저작권 표기에 연도가 명시되어 있지 않아 콘텐츠의 최신성을 명확히 |
| e9p_002 | control | 4 | - | 푸터의 저작권 표기(© 정부 서비스. All rights reserved |
| e9p_003 | E9-2-footer | 2 | - | HTML `<head>` 태그 내에 뷰포트 메타 태그가 누락되어 있어,  |
| e9p_004 | E9-4 | 3 | E9-4 | 모바일 화면(최대 768px)에서 로그인 링크가 CSS `display: |
| e9p_005 | E9-1b | 3 | E9-2 | 푸터에 명시된 저작권 정보 "© 정부 서비스. All rights res |
| e9p_006 | E9-3 | 2 | - | CSS에 반응형 디자인을 위한 미디어 쿼리 또는 유동적인 단위(rem,  |
| e9p_007 | E9-2-banner | 3 | - | 푸터의 저작권 표시에 연도가 명시되어 있지 않아 콘텐츠의 최신성을 파악하 |
| e9p_008 | control | 3 | - | 푸터의 저작권 표기에 연도가 명시되어 있지 않아 콘텐츠의 최신성을 파악하 |

출처: `results/revision/runs_e9_pilot/e9-pilot2-norag/reports.jsonl`

### 4.2 고정 질의

| 페이지 | 주입 | 이슈 | 정규식 탐지 | 핵심 한 줄 |
|---|---|---|---|---|
| e9p_001 | E9-1a | 1 | E9-2 | 헤더 및 푸터 내 링크가 일반 텍스트와 동일한 색상이며 밑줄이 없어 시각 |
| e9p_002 | control | 4 | - | 웹 접근성 향상을 위한 '탐색 건너뛰기 링크'가 누락되었습니다. gov_ |
| e9p_003 | E9-2-footer | 3 | - | 웹 접근성 필수 요소인 '탐색 건너뛰기 링크'가 누락되었습니다. <bod |
| e9p_004 | E9-4 | 1 | - | 푸터에 명시된 저작권 정보에 연도가 포함되어 있지 않아 정보의 최신성을  |
| e9p_005 | E9-1b | 1 | - | 디지털 정부서비스 UI/UX 가이드라인(p.218)에 명시된 '탐색 건너 |
| e9p_006 | E9-3 | 0 | - | - |
| e9p_007 | E9-2-banner | 1 | - | 디지털 정부서비스 UI/UX 가이드라인(p.218)에 명시된 '탐색 건너 |
| e9p_008 | control | 1 | - | 디지털 정부서비스 UI/UX 가이드라인(p.218)에 명시된 '탐색 건너 |

출처: `results/revision/runs_e9_pilot/e9-pilot2-fixed/reports.jsonl`

### 4.3 페이지별 질의

| 페이지 | 주입 | 이슈 | 정규식 탐지 | 핵심 한 줄 |
|---|---|---|---|---|
| e9p_001 | E9-1a | 5 | E9-2 | 메인 콘텐츠 영역의 '전화번호: 110'과 푸터의 '대표전화 110 (평 |
| e9p_002 | control | 0 | - | - |
| e9p_003 | E9-2-footer | 4 | - | 검색 결과 화면에서 통합 검색 입력 필드와 검색 실행 버튼이 직접 제공되 |
| e9p_004 | E9-4 | 2 | E9-4 | 모바일 환경(화면 너비 768px 이하)에서 로그인 링크가 `displa |
| e9p_005 | E9-1b | 3 | - | 검색 결과 화면을 포함한 모든 화면에서 통합검색 입력 필드와 검색 실행  |
| e9p_006 | E9-3 | 2 | - | 푸터의 서비스 내비게이션이 기본 내비게이션(메인 메뉴)과 동일하게 제공되 |
| e9p_007 | E9-2-banner | 3 | - | 검색 결과 화면을 포함한 모든 화면에서 통합검색 입력 필드와 검색 실행  |
| e9p_008 | control | 0 | - | - |

출처: `results/revision/runs_e9_pilot/e9-pilot2-page/reports.jsonl`

### 4.4 관련 조항 제공

| 페이지 | 주입 | 이슈 | 정규식 탐지 | 핵심 한 줄 |
|---|---|---|---|---|
| e9p_001 | E9-1a | 2 | E9-1 | 공식 배너의 텍스트 내용이 가이드라인과 다릅니다. 가이드라인은 '이 누리 |
| e9p_002 | control | 1 | - | 헤더에 정부상징 로고 대신 텍스트 '정부 서비스'를 사용하고 있습니다.  |
| e9p_003 | E9-2-footer | 3 | E9-1,E9-2 | 공식 배너의 국기 아이콘과 텍스트 간 간격이 가이드라인(10px)과 다르 |
| e9p_004 | E9-4 | 2 | E9-4 | 가로 768px 이하의 작은 화면 너비에서 로그인 링크가 CSS `dis |
| e9p_005 | E9-1b | 1 | E9-1 | 공식 배너 텍스트의 띄어쓰기가 가이드라인과 다릅니다. 공식 배너 텍스트를 |
| e9p_006 | E9-3 | 1 | E9-3 | '로그인' 링크가 회원가입 페이지('/signup')로 연결되어 있습니다 |
| e9p_007 | E9-2-banner | 1 | E9-1,E9-2 | 공식 배너 텍스트 색상이 가이드라인에 명시된 색상과 다릅니다. 공식 배너 |
| e9p_008 | control | 1 | - | 운영기관 식별자 로고 영역에 상위 기관의 로고(정부상징 로고)가 제공되지 |

출처: `results/revision/runs_e9_pilot/e9-pilot2-related/reports.jsonl`

### 4.5 fixed-long

| 페이지 | 주입 | 이슈 | 정규식 탐지 | 핵심 한 줄 |
|---|---|---|---|---|
| e9p_001 | E9-1a | 1 | - | 푸터의 저작권 표기에 연도가 명시되어 있지 않아 최신성이 부족합니다. 현 |
| e9p_002 | control | 3 | - | 콜투액션(Call to Action) 역할을 하는 '신청하기' 버튼의 시 |
| e9p_003 | E9-2-footer | 3 | E9-2 | 푸터의 저작권 연도가 최신화되지 않았습니다. 현재 시점(2026년 11월 |
| e9p_004 | E9-4 | 2 | - | 현재 페이지의 위치를 파악할 수 있는 '현재 위치 표시'(예: Bread |
| e9p_005 | E9-1b | 2 | - | 사용자가 현재 페이지의 위치를 쉽게 파악할 수 있도록 돕는 '현재 위치  |
| e9p_006 | E9-3 | 2 | E9-2 | 현재 보고 있는 페이지('이용약관')가 내비게이션(푸터 포함)에서 시각적 |
| e9p_007 | E9-2-banner | 2 | - | CSS 스타일이 HTML 문서 내 `<style>` 블록에 인라인으로 정 |
| e9p_008 | control | 1 | - | 헤더 및 푸터 내비게이션 링크가 <ul><li> 구조 없이 직접 <nav |

출처: `results/revision/runs_e9_pilot/e9-pilot2-fixedlong/reports.jsonl`

## 5. 정규식 주 지표와 보조 분석 (조건별, 유형별, 대조군 위양성)

주 지표 = 그 페이지에 주입된 변형 문구만 인정. 보조 = 6개 변형 문구를 모든 페이지에 적용. 파일럿은 유형별 결함 1페이지, 대조군 2페이지.

### 5.1 RAG 끔

| 유형 | 규칙 | 탐지/결함 | 대조군 탐지/대조군 |
|---|---|---|---|
| E9-1 | 주 지표 | 0/2 | 0/2 |
| E9-1 | 보조 | 0/2 | 0/2 |
| E9-1a | 주 지표 | 0/1 | 0/2 |
| E9-1a | 보조 | 0/1 | 0/2 |
| E9-1b | 주 지표 | 0/1 | 0/2 |
| E9-1b | 보조 | 0/1 | 0/2 |
| E9-2 | 주 지표 | 0/2 | 0/2 |
| E9-2 | 보조 | 0/2 | 0/2 |
| E9-3 | 주 지표 | 0/1 | 0/2 |
| E9-3 | 보조 | 0/1 | 0/2 |
| E9-4 | 주 지표 | 1/1 | 0/2 |
| E9-4 | 보조 | 1/1 | 0/2 |

출처: `results/revision/e9_pilot/tables_e9-pilot2/e9_regex_primary_vs_aux.csv`

### 5.2 고정 질의

| 유형 | 규칙 | 탐지/결함 | 대조군 탐지/대조군 |
|---|---|---|---|
| E9-1 | 주 지표 | 0/2 | 0/2 |
| E9-1 | 보조 | 0/2 | 0/2 |
| E9-1a | 주 지표 | 0/1 | 0/2 |
| E9-1a | 보조 | 0/1 | 0/2 |
| E9-1b | 주 지표 | 0/1 | 0/2 |
| E9-1b | 보조 | 0/1 | 0/2 |
| E9-2 | 주 지표 | 0/2 | 0/2 |
| E9-2 | 보조 | 0/2 | 0/2 |
| E9-3 | 주 지표 | 0/1 | 0/2 |
| E9-3 | 보조 | 0/1 | 0/2 |
| E9-4 | 주 지표 | 0/1 | 0/2 |
| E9-4 | 보조 | 0/1 | 0/2 |

출처: `results/revision/e9_pilot/tables_e9-pilot2/e9_regex_primary_vs_aux.csv`

### 5.3 페이지별 질의

| 유형 | 규칙 | 탐지/결함 | 대조군 탐지/대조군 |
|---|---|---|---|
| E9-1 | 주 지표 | 0/2 | 0/2 |
| E9-1 | 보조 | 0/2 | 0/2 |
| E9-1a | 주 지표 | 0/1 | 0/2 |
| E9-1a | 보조 | 0/1 | 0/2 |
| E9-1b | 주 지표 | 0/1 | 0/2 |
| E9-1b | 보조 | 0/1 | 0/2 |
| E9-2 | 주 지표 | 0/2 | 0/2 |
| E9-2 | 보조 | 0/2 | 0/2 |
| E9-3 | 주 지표 | 0/1 | 0/2 |
| E9-3 | 보조 | 0/1 | 0/2 |
| E9-4 | 주 지표 | 1/1 | 0/2 |
| E9-4 | 보조 | 1/1 | 0/2 |

출처: `results/revision/e9_pilot/tables_e9-pilot2/e9_regex_primary_vs_aux.csv`

### 5.4 관련 조항 제공

| 유형 | 규칙 | 탐지/결함 | 대조군 탐지/대조군 |
|---|---|---|---|
| E9-1 | 주 지표 | 2/2 | 0/2 |
| E9-1 | 보조 | 2/2 | 0/2 |
| E9-1a | 주 지표 | 1/1 | 0/2 |
| E9-1a | 보조 | 1/1 | 0/2 |
| E9-1b | 주 지표 | 1/1 | 0/2 |
| E9-1b | 보조 | 1/1 | 0/2 |
| E9-2 | 주 지표 | 2/2 | 0/2 |
| E9-2 | 보조 | 2/2 | 0/2 |
| E9-3 | 주 지표 | 1/1 | 0/2 |
| E9-3 | 보조 | 1/1 | 0/2 |
| E9-4 | 주 지표 | 1/1 | 0/2 |
| E9-4 | 보조 | 1/1 | 0/2 |

출처: `results/revision/e9_pilot/tables_e9-pilot2/e9_regex_primary_vs_aux.csv`

### 5.5 fixed-long

| 유형 | 규칙 | 탐지/결함 | 대조군 탐지/대조군 |
|---|---|---|---|
| E9-1 | 주 지표 | 0/2 | 0/2 |
| E9-1 | 보조 | 0/2 | 0/2 |
| E9-1a | 주 지표 | 0/1 | 0/2 |
| E9-1a | 보조 | 0/1 | 0/2 |
| E9-1b | 주 지표 | 0/1 | 0/2 |
| E9-1b | 보조 | 0/1 | 0/2 |
| E9-2 | 주 지표 | 1/2 | 0/2 |
| E9-2 | 보조 | 1/2 | 0/2 |
| E9-3 | 주 지표 | 0/1 | 0/2 |
| E9-3 | 보조 | 0/1 | 0/2 |
| E9-4 | 주 지표 | 0/1 | 0/2 |
| E9-4 | 보조 | 0/1 | 0/2 |

출처: `results/revision/e9_pilot/tables_e9-pilot2/e9_regex_primary_vs_aux.csv`

## 6. 관련 조항 제공 조건: 대조군 이슈가 조항 청크 문구를 그대로 인용했는가

검사: (a) 미준수 사례 문구 "대한민국 공식 전자정부 웹사이트입니다", (b) 규정 배너 문구, (c) 6청크 본문과 공백 제거 후
15자 이상 연속 일치. 비교를 위해 같은 검사를 다른 조건의 대조군 이슈에도 적용했다.

| 조건 | 대조군 | 이슈 | (a) 미준수 사례 인용 | (b) 규정 문구 인용 | (c) 15자+ 일치 이슈 |
|---|---|---|---|---|---|
| RAG 끔 | e9p_002 | 4 | 0 | 0 | 0 |
| RAG 끔 | e9p_008 | 3 | 0 | 0 | 0 |
| 고정 질의 | e9p_002 | 4 | 0 | 0 | 0 |
| 고정 질의 | e9p_008 | 1 | 0 | 0 | 0 |
| 페이지별 질의 | e9p_002 | 0 | 0 | 0 | 0 |
| 페이지별 질의 | e9p_008 | 0 | 0 | 0 | 0 |
| 관련 조항 제공 | e9p_002 | 1 | 0 | 0 | 0 |
| 관련 조항 제공 | e9p_008 | 1 | 0 | 0 | 0 |
| fixed-long | e9p_002 | 3 | 0 | 0 | 0 |
| fixed-long | e9p_008 | 1 | 0 | 0 | 0 |

출처: `services/chroma_db/chroma.sqlite3` (읽기 전용, 6청크 본문)
및 `results/revision/runs_e9_pilot/e9-pilot2-{조건}/reports.jsonl`

## 7. E9-3, E9-4 페이지: HTML 근거로 탐지되는가 (보고 내용 기준 관찰)

시스템은 스크린샷과 HTML 을 함께 받는다(modality both). 아래는 이슈 문구에 코드 근거
(href, signup, @media, display:none, max-width, 768px, a 태그)가 들어 있는지 본 관찰이며 판정이 아니다.

| 조건 | 페이지 | 유형 | 이슈 | 정규식 탐지 이슈 | 그중 코드 근거 | 결함 관련어 언급 이슈 |
|---|---|---|---|---|---|---|
| RAG 끔 | e9p_004 | E9-4 | 3 | 1 | 1 | 1 |
| RAG 끔 | e9p_006 | E9-3 | 2 | 0 | 0 | 0 |
| 고정 질의 | e9p_004 | E9-4 | 1 | 0 | 0 | 0 |
| 고정 질의 | e9p_006 | E9-3 | 0 | 0 | 0 | 0 |
| 페이지별 질의 | e9p_004 | E9-4 | 2 | 1 | 1 | 1 |
| 페이지별 질의 | e9p_006 | E9-3 | 2 | 0 | 0 | 0 |
| 관련 조항 제공 | e9p_004 | E9-4 | 2 | 1 | 1 | 1 |
| 관련 조항 제공 | e9p_006 | E9-3 | 1 | 1 | 1 | 1 |
| fixed-long | e9p_004 | E9-4 | 2 | 0 | 0 | 0 |
| fixed-long | e9p_006 | E9-3 | 2 | 0 | 0 | 0 |

출처: `results/revision/runs_e9_pilot/e9-pilot2-{조건}/reports.jsonl`

## 8a. 이전 파일럿과 비교

이전 = `e9-pilot` (`exp-freeze-e9-v2` 입력),
이번 = `e9-pilot2` (`exp-freeze-e9-v3` 입력: 국기 그림, portal_main 본문 문구).
같은 8페이지, 같은 5조건, 각 1회. 표본이 작아(대조군 2페이지) 차이를 해석하지 않고 기록만 한다.

### 8a.1 대조군 위양성 페이지 수 (대조군 2페이지 중, 이전→이번)

| 조건 | 규칙 | E9-1 | E9-2 | E9-3 | E9-4 |
|---|---|---|---|---|---|
| RAG 끔 | 주 지표 | 1→0 | 1→0 | 0→0 | 0→0 |
| RAG 끔 | 보조 | 1→0 | 1→0 | 0→0 | 0→0 |
| 고정 질의 | 주 지표 | 1→0 | 0→0 | 0→0 | 0→0 |
| 고정 질의 | 보조 | 1→0 | 0→0 | 0→0 | 0→0 |
| 페이지별 질의 | 주 지표 | 0→0 | 0→0 | 0→0 | 0→0 |
| 페이지별 질의 | 보조 | 0→0 | 0→0 | 0→0 | 0→0 |
| 관련 조항 제공 | 주 지표 | 0→0 | 1→0 | 0→0 | 0→0 |
| 관련 조항 제공 | 보조 | 0→0 | 1→0 | 0→0 | 0→0 |
| fixed-long | 주 지표 | 0→0 | 0→0 | 0→0 | 0→0 |
| fixed-long | 보조 | 0→0 | 0→0 | 0→0 | 0→0 |

출처: `results/revision/e9_pilot/tables/e9_regex_primary_vs_aux.csv` (이전),
`results/revision/e9_pilot/tables_e9-pilot2/e9_regex_primary_vs_aux.csv` (이번)

### 8a.2 대조군에서 정규식에 걸린 이슈의 원인별 건수 (관찰용 문구 분류, 이전→이번)

분류: 문구에 국기|flag|플래그|태극 → 국기 자리; '배너' + 플레이스홀더|자리 표시|임시 → 본문 자리 표시; 나머지 → 그 밖.

| 조건 | 국기 자리 | 본문 자리 표시 '배너' | 그 밖 | 합계 |
|---|---|---|---|---|
| RAG 끔 | 1→0 | 1→0 | 0→0 | 2→0 |
| 고정 질의 | 0→0 | 1→0 | 0→0 | 1→0 |
| 페이지별 질의 | 0→0 | 0→0 | 0→0 | 0→0 |
| 관련 조항 제공 | 1→0 | 0→0 | 0→0 | 1→0 |
| fixed-long | 0→0 | 0→0 | 0→0 | 0→0 |
| **합계** | 2→0 | 2→0 | 0→0 | 4→0 |

출처:
- `results/revision/runs_e9_pilot/e9-pilot-{조건}/reports.jsonl`
- `results/revision/runs_e9_pilot/e9-pilot2-{조건}/reports.jsonl`

### 8a.3 이슈 수 변화 (대상 페이지 이슈 합계, 이전→이번)

| 조건 | 전체 8페이지 | 대조군 2페이지 | 결함 6페이지 |
|---|---|---|---|
| RAG 끔 | 23→23 | 8→7 | 15→16 |
| 고정 질의 | 20→12 | 6→5 | 14→7 |
| 페이지별 질의 | 21→19 | 3→0 | 18→19 |
| 관련 조항 제공 | 9→12 | 2→2 | 7→10 |
| fixed-long | 16→16 | 5→4 | 11→12 |

출처:
- `results/revision/runs_e9_pilot/e9-pilot-{조건}/reports.jsonl`
- `results/revision/runs_e9_pilot/e9-pilot2-{조건}/reports.jsonl`

## 8. 수정이 필요해 보이는 점

재파일럿을 보고 관찰한 내용이다. **사전 규칙(수정 1회·재파일럿 1회)에 따라 더 이상 아무것도 수정하지 않는다.**
본 실험은 `exp-freeze-e9-v3` 입력으로 진행한다(연구자 신호 후). 정규식 규칙은 바꾸지 않았다.

**(1) 대조군 위양성:** 주 지표와 보조 분석 모두 4건에서 0건이 되었다(8a.1, 8a.2).
- 국기 자리를 지적한 이슈는 2건에서 0건, 본문 '배너'를 자리 표시로 지적한 이슈도 2건에서 0건이다.
- 대조군 이슈 자체는 남아 있다(조건별 0~7건). 다만 어느 규칙에도 걸리지 않았다.
- 대조군이 2페이지뿐이므로 본 실험(대조군 30페이지)에서 위양성이 없다는 뜻은 아니다.

**(2) 관련 조항 제공 조건의 조항 인용:** 대조군 이슈가 미준수 사례 문구나 규정 배너 문구를 인용한 경우는 없었다.
조항 청크 본문과 15자 이상 일치하는 대조군 이슈도 이번에는 0건이다(6절).

**(3) 결함 탐지(1페이지씩이라 해석하지 않음):**
- 관련 조항 제공 조건은 E9-1 2/2, E9-2 2/2, E9-3 1/1, E9-4 1/1 을 탐지했다.
- 다른 조건에서는 E9-4(RAG 끔·페이지별 질의)와 E9-2 1건(fixed-long)만 탐지했다.
- E9-1b(띄어쓰기)는 관련 조항 제공 조건에서 이번에 탐지되었다(이전 파일럿에서는 어느 조건에서도 탐지되지 않음).

**(4) 그 밖의 점검:**
- 40호출 모두 성공했고, 파싱 실패와 재시도는 0이다. 컨텍스트 길이는 5조건 모두 설계값과 같다(3절).
- 고정 질의 조건의 E9-3 페이지(e9p_006)는 대상 이슈가 0건이었다. 모델이 이 페이지에서 문제를 보고하지 않은 것이며,
  파이프라인 오류는 없었다.
- 호출당 평균 비용은 $0.0119 로 이전 파일럿($0.0102)보다 높다. 본 실험 910호출 기준 약 $10.8 이다(설계 추정 $8.6).
- 동시 실행: 남은 메모리 4.49~4.89GB 로 RAG 끔·고정 질의·페이지별 질의·관련 조항 제공은 1건, fixed-long 은 2건으로 실행했다
  (`results/revision/memory_logs/concurrency_deviations.jsonl`, README 계획 이탈 기록). 결과에는 영향이 없다.

## 9. 이 보고서에 사용한 파일

| 경로 | SHA-256 앞 16자리 |
|---|---|
| `testbed_e9_pilot/dataset_metadata_e9_pilot.json` | f809cbb5aee0ddd2 |
| `results/revision/runs_e9_pilot/e9-pilot2-norag/calls.jsonl` | 3039066b2ec065c1 |
| `results/revision/runs_e9_pilot/e9-pilot2-fixed/calls.jsonl` | 2b11e3b975283978 |
| `results/revision/runs_e9_pilot/e9-pilot2-page/calls.jsonl` | 5031aade922bc326 |
| `results/revision/runs_e9_pilot/e9-pilot2-related/calls.jsonl` | 9692d099993f4b2b |
| `results/revision/runs_e9_pilot/e9-pilot2-fixedlong/calls.jsonl` | 6a1622b60f44bdf6 |
| `results/revision/runs_e9_pilot/e9-pilot2-norag/reports.jsonl` | 17e92450d0a07146 |
| `results/revision/runs_e9_pilot/e9-pilot2-fixed/reports.jsonl` | 2bc6b0a0e1eccaf6 |
| `results/revision/runs_e9_pilot/e9-pilot2-page/reports.jsonl` | 3216ad2bb14d3120 |
| `results/revision/runs_e9_pilot/e9-pilot2-related/reports.jsonl` | e4dd0d220e6b10cc |
| `results/revision/runs_e9_pilot/e9-pilot2-fixedlong/reports.jsonl` | 69d9811be6a82f3a |
| `results/revision/runs_e9_pilot/e9-pilot2-norag/run_meta.json` | 90fb40b495225a78 |
| `results/revision/runs_e9_pilot/e9-pilot2-fixed/run_meta.json` | 43503db68e90a644 |
| `results/revision/runs_e9_pilot/e9-pilot2-page/run_meta.json` | b1e3460c9014e82b |
| `results/revision/runs_e9_pilot/e9-pilot2-related/run_meta.json` | 80a1c7c1de69ba0e |
| `results/revision/runs_e9_pilot/e9-pilot2-fixedlong/run_meta.json` | 1bd3d0596e96be48 |
| `results/revision/e9_pilot/tables_e9-pilot2/e9_regex_primary_vs_aux.csv` | 3cb78183deb4874f |
| `services/chroma_db/chroma.sqlite3` | b3fed16a5f4b65a2 |
| `results/revision/e9_pilot/tables/e9_regex_primary_vs_aux.csv` | 8f0d75118124d4fc |
| `results/revision/runs_e9_pilot/e9-pilot-norag/reports.jsonl` | fe09f4dbf70ff206 |
| `results/revision/runs_e9_pilot/e9-pilot-fixed/reports.jsonl` | 6f8a2841892f2ae7 |
| `results/revision/runs_e9_pilot/e9-pilot-page/reports.jsonl` | 454383453633bf6d |
| `results/revision/runs_e9_pilot/e9-pilot-related/reports.jsonl` | 60abbf101ecc8fd2 |
| `results/revision/runs_e9_pilot/e9-pilot-fixedlong/reports.jsonl` | f6b917c20b7cc6de |
| `results/revision/runs_e9_pilot/e9-pilot2-norag/SHA256SUMS` | 1c90afa7f3464b7c |
| `results/revision/runs_e9_pilot/e9-pilot2-fixed/SHA256SUMS` | f7929485c363dd15 |
| `results/revision/runs_e9_pilot/e9-pilot2-page/SHA256SUMS` | ff0392b57093de26 |
| `results/revision/runs_e9_pilot/e9-pilot2-related/SHA256SUMS` | 236452752b81e92e |
| `results/revision/runs_e9_pilot/e9-pilot2-fixedlong/SHA256SUMS` | dd6c4cc3087a02a4 |

프롬프트 파일은 각 run 의 `SHA256SUMS` 에 해시가 있다. 생성 스크립트: `experiments/revision/e9_pilot_report.py`

