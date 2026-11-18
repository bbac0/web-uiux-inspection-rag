# 확인 1: 페이지별 질의(page-specific query) 규칙과 관련 조항(related clause)

작성 2026-11-19. API 호출 없음. 코드와 실행 기록을 읽기만 했다.

## 1. 페이지별 질의 생성 규칙 (E3-page, E9 page 공통)

코드: `services/analyzer.py` 의 `build_page_query()` 와 `PAGE_SIGNALS_JS`. 두 실험 모두 `--query-mode page` 로
같은 함수를 쓴다(E3-page `run_meta.json` args, E9 `results/revision/e9/conditions_e9.json`).

1. 신호 수집: 페이지 로드(`networkidle` + 3초) 뒤 브라우저에서 다음을 문서 순서대로 읽는다.
   - `document.title`
   - `h1, h2, h3` 요소의 `textContent`
   - 버튼 라벨: `button`, `[role=button]` 의 `textContent`, `input[type=submit|button|reset]` 의 `value`
2. 순서: 제목 → 헤딩(h1~h3, 문서 순서) → 버튼 라벨(문서 순서).
3. 각 항목은 앞뒤 공백을 지우고 연속 공백을 한 칸으로 줄인다. 빈 항목은 버린다. 같은 문자열은 처음 것만 남긴다.
4. 남은 항목을 공백 한 칸으로 이어 붙인 것이 질의다. 결과가 비면 고정 질의 `웹 UI/UX 표준 가이드라인 공통 규정` 으로
   바꾸고 `query_fallback=True` 로 기록한다(E3-page 84회, E9 page r1·r2 각 91회 모두 대체 0건).
5. `textContent` 를 쓰므로 CSS 로 숨긴 버튼 라벨(`font-size:0` 등)도 들어간다.
6. 검색: 질의를 `gemini-embedding-001` `embed_query` 로 임베딩하고
   `similarity_search_by_vector_with_relevance_scores`
   로 K=4 청크를 가져온다(고정 질의와 같은 연산, 같은 DB `services/chroma_db` 1,020청크).

| 실험 | 서로 다른 질의 수 | 질의 예 |
|---|---|---|
| E3-page (84페이지) | 11 | `자주 묻는 질문 FAQ`, `공지사항 게시판 공지사항 목록`, `이용약관`, `고객센터 문의하기` |
| E9 page r1·r2 (91페이지) | 10 | `로그인 - 대한민국 정부 로그인`, `통합 검색 결과`, `민원 신청서 작성 제출하기` |

출처: `results/revision/runs/E3-page/calls.jsonl` (rag.query),
`results/revision/reports/e9_page_query_retrieval_rank.md`

- 질의는 템플릿(제목·헤딩·버튼)에서 나오므로 같은 템플릿의 페이지는 결함 유형과 무관하게 같은 질의가 된다
  (주입 문구가 제목·헤딩·버튼에 들어가는 경우만 달라진다).

## 2. 관련 조항 제공(related clause) 조건

코드상 `--query-mode oracle` 이다. `services/analyzer.py` `_retrieve_experiment()` 가 CSV 의 청크 ID 를
그 순서대로 DB 에서 가져와(`store.get(ids=...)`) 고정 질의와 같은 형식(`[파일 - N페이지]\n본문`)으로 넣는다.
질의 임베딩과 거리는 없다. 문서상 이름은 "관련 조항 제공(related-clause)"이다(정답 조항 주입이 아님;
`results/revision/analysis_plan.md` 10절 8항).

### 2.1 E3 (입력 `results/revision/oracle_chunks.csv`, 84페이지 × 2청크 = 168행)

| 순서 | 청크 ID | 문서 / 쪽 | 내용 | 본문 길이 |
|---|---|---|---|---|
| 1 | `b4c4ffd0-b39d-49ef-801d-487b44041b9b` | gov_check 29 | 링크 레이블은 연결된 목적지를 예측할 수 있게 제공 | 739자 |
| 2 | `87f08a4d-b8b6-427c-8fd5-2925b07b4d8a` | gov_check 208 | 로그인 링크는 항상 '로그인' 화면으로 연결 | 748자 |

출처: `results/revision/oracle_chunks.csv`, `results/revision/analysis_plan.md` 10절 11항,
`results/revision/README.md`

- **용어 결함 페이지(45쪽)와 대조군 페이지(39쪽)에 같은 두 청크를 같은 순서로 줬다.** CSV 를 확인한 결과 84페이지 모두
  위 두 청크 ID 조합 하나뿐이다(용어 45, 대조군 39). 페이지 라벨에 따라 청크를 달리 주지 않았다.
- 두 청크는 목표 항목 외에 인접 항목도 담는다(29쪽: 링크 체크리스트 1~10과 버튼 그룹, 208쪽: 로그인 기능 찾기 1의
  점검 절차와 3의 제목). 본문 합계 1,487자(프롬프트 형태 1,538자)로 고정 질의 4청크(1,552자, 1,653자)와 비슷하다.
- 색인된 문서에는 '로그인 → 접속하기' 치환을 직접 금지하는 조항이 없다. 208쪽 항목은 링크의 목적지를 규정한다
  (`analysis_plan.md` 10절 10항). 그래서 '관련 조항'이라 부른다.
- 실행 기록 확인: `E3-oracle` 첫 호출의 `rag.chunks` = gov_check 29쪽, 208쪽.

### 2.2 E9 (입력 `results/revision/e9/e9_related_clause_chunks.csv`, 91페이지 × 6청크 = 546행)

| 순서 | 청크 ID | 문서 / 쪽 | 내용 (대응 결함) | 본문 길이 |
|---|---|---|---|---|
| 1 | `906848de-bb99-4446-adb1-16a2dc61d34e` | gov_check 69 | 공식 배너 텍스트 (E9-1) | 632자 |
| 2 | `574b8c73-13b0-43e7-bbe8-abc31f41bb2c` | gov_check 68 | 공식 배너 스타일 (E9-2 배너) | 926자 |
| 3 | `265eeb6d-3e1a-43bc-99b7-d299c8ff4233` | gov_check 77 | 헤더 스타일 (E9-2 헤더) | 724자 |
| 4 | `1fff974d-ca33-444d-a3ac-8b93b5a8aadf` | gov_check 71 | 푸터 스타일 (E9-2 푸터) | 683자 |
| 5 | `87f08a4d-b8b6-427c-8fd5-2925b07b4d8a` | gov_check 208 | 로그인 링크 목적지 (E9-3) | 748자 |
| 6 | `905711bf-2989-473d-9cf8-47a3ed1dd8f9` | gov_check 209 | 작은 화면 로그인 링크 (E9-4) | 669자 |

출처: `results/revision/e9/e9_related_clause_chunks.csv`, `docs/e9_design.md` 4절

- 91페이지(결함 61, 대조군 30) 모두 같은 6청크를 같은 순서로 받았다(CSV 의 페이지별 조합이 하나뿐임을 확인).
- 합계 4,382자(프롬프트 형태 4,538자)로 고정 질의 컨텍스트의 약 2.7배라, 길이를 맞춘 fixed-long 조건을 따로 뒀다.
- 이 조건은 RAG 에 가장 유리한 상한 조건이다(1번 청크에 배너 정답 문구가 들어 있음; `docs/e9_design.md`).
