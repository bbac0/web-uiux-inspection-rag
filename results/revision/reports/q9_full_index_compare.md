# 확인 9: gov_guide 전체(1,181쪽)를 색인한 새 인덱스와 실험 인덱스 비교

작성 2026-11-19. 연구자 승인(임베딩 비용 상한 $1)에 따라 임베딩 API 를 호출했다. 생성 모델 호출은 없다.
코드: `experiments/revision/full_index_compare.py` (build, compare).

## 0. 새 인덱스와 호출·비용

| 항목 | 값 |
|---|---|
| 새 인덱스 | `results/revision/full_index/chroma_db` (커밋 제외, `.gitignore` 의 `chroma_db/`) |
| 청크 | 1,485 (gov_check 288 + gov_guide 1,197), 예상과 같음 |
| 실험 인덱스 | 1,020 (gov_check 288 + gov_guide 732, 1~736쪽 중 721쪽) |
| 색인 호출 | 149회(배치 10개씩), 모두 성공, 재시도 0 |
| 질의 임베딩 호출 | 16회(고정 질의 1 + E3·E9 페이지별 질의 중 서로 다른 것) |
| 호출 합계 | 165회 |
| 비용 추정 상한 | **$0.0930** (글자 수를 토큰 수로 보고 $0.15/1M; 실제 토큰 수는 응답에 없어 상한으로만 적음) |
| 실행 시각 (UTC) | 색인 2026-11-18 16:18:46 ~ 16:26:06 |

출처: `results/revision/full_index/call_log.jsonl`, `build_meta.json`, `compare.json`

- 색인 방식은 `services/indexer.py` 와 같다(PyPDFLoader, 1000/100 분할, gov_check → gov_guide 순서,
  `models/gemini-embedding-001` task_type=retrieval_document, 배치 10). 다른 점은 실패한 배치를 건너뛰지 않고 재시도하게 한
  것뿐이다.
- 질의 검색은 프로덕션과 같은 `GoogleGenerativeAIEmbeddings(model)` 의 `embed_query` →
  `similarity_search_by_vector_with_relevance_scores`.
- 실험 인덱스는 sqlite 를 읽기 전용으로만 열었다. `services/chroma_db/chroma.sqlite3` SHA-256 은 동결 매니페스트(v5)와 같다.
- 두 인덱스의 청크 대응: 실험 인덱스 1,020개 중 1,001개는 공백을 지운 본문이 새 청크와 같다. 나머지 19개(주로 목차 쪽)는
  추출 본문이 조금 달라 같은 문서·쪽에서 가장 비슷한 청크로 맞췄다(유사도 0.80~0.999). E9 지정 조항 6청크는 모두 본문 일치.

## 1. 고정 질의("웹 UI/UX 표준 가이드라인 공통 규정")의 상위 4개

| 순위 | 실험 인덱스 | 새 인덱스 |
|---|---|---|
| 1 | gov_guide 9쪽 | gov_guide **780쪽** |
| 2 | gov_guide 15쪽 | gov_guide **816쪽** |
| 3 | gov_guide 218쪽 | gov_guide 9쪽 |
| 4 | gov_guide 1쪽 | gov_guide 15쪽 |

출처: `results/revision/full_index/compare.json` (fixed), `results/revision/runs/E1-R1/calls.jsonl`
(rag.chunks)

- **같지 않다.** 새 인덱스의 1·2위는 실험 인덱스에 없던 737쪽 이후 청크다. 실험 인덱스의 1·2위(9쪽, 15쪽)는 3·4위로 내려갔고,
  218쪽과 1쪽은 상위 4개에서 빠졌다.

## 2. 페이지별 질의: 상위 4개가 바뀐 페이지 수

| 실험 | 페이지 | 상위 4개 집합이 바뀜 | 순서만 바뀜 | 새로 들어온 청크 | 그중 이전에 색인되지 않았던 쪽 |
|---|---|---|---|---|---|
| E3-page | 84 | 73 | 0 | 143 | 143 |
| E9 page-r1 | 91 | 91 | 0 | 200 | 190 |
| E9 page-r2 | 91 | 91 | 0 | 200 | 190 |

출처: `results/revision/full_index/compare.json` (pages), `results/revision/runs/E3-page/calls.jsonl`,
`results/revision/runs_e9/e9-main-page-r{1,2}/calls.jsonl`

- 바뀐 페이지에 새로 들어온 청크는 대부분 실험 인덱스에 없던 gov_guide 775쪽 이후의 청크다(많이 나온 쪽: 861, 775, 884,
  1052, 778, 791, 795, 1097쪽).
- 예외: E9 에서 새로 들어온 청크 중 10개(r1, r2 각각)는 이전에도 색인된 쪽의 청크다. 모두 `정부24 메인 신청하기` 질의를 쓴
  10쪽이고, 들어온 청크는 gov_check 3쪽(목차)이다. 이 쪽 청크들은 두 인덱스의 추출 본문이 조금 달라 유사도로 대응시킨 것이라,
  재임베딩 차이인지 본문 차이인지는 확정하지 않았다.
- E3 의 바뀌지 않은 11쪽은 새로 추가된 쪽의 청크가 상위 4개에 들지 않은 질의의 페이지다.

## 3. E9 지정 조항 6청크의 recall@4 (새 인덱스)

| 질의 | recall@4 | 6청크 최고 순위 (새 / 실험) |
|---|---|---|
| 로그인 - 대한민국 정부 로그인 | 0.00 | 63 / 13 |
| 이용약관 | 0.00 | 62 / 67 |
| 고객센터 | 0.00 | 81 / 91 |
| 자주 묻는 질문 | 0.00 | 135 / 106 |
| 통합 검색 결과 | 0.00 | 164 / 63 |
| 마이페이지 대시보드 신청 처리 내역 | 0.00 | 219 / 134 |
| 공지사항 게시판 | 0.00 | 229 / 212 |
| 민원 신청서 작성 제출하기 | 0.00 | 417 / 306 |
| 정부24 메인 신청하기 | 0.00 | 546 / 341 |
| 민원 안내 상세 주민등록표등본 발급 발급 신청 | 0.00 | 658 / 333 |
| (고정 질의) 웹 UI/UX 표준 가이드라인 공통 규정 | 0.00 | 226 / 159 |

출처: `results/revision/full_index/compare.json` (recall),
`results/revision/reports/e9_page_query_retrieval_rank.md` (실험 인덱스 순위)

- **새 인덱스에서도 모든 질의의 recall@4 가 0.00이다.** 청크가 1,020 → 1,485개로 늘어 6청크의 순위는 대체로 더 뒤로 밀렸다.
- 6청크는 모두 gov_check 에 있어 두 인덱스에 다 들어 있다. 따라서 이 결과는 gov_guide 색인 누락과 무관하다.

## 4. 해석 주의

- 새 인덱스는 비교용이며 실험에 쓰지 않았다. 실험 결과(고정 질의·페이지별 질의 조건)는 실험 인덱스로 얻은 것이다.
- 새 인덱스는 이 컴퓨터의 pypdf 6.16.2 로 추출했고 임베딩을 다시 계산했다. 같은 본문의 임베딩이 원래 색인 시점과 완전히
  같다는 보장은 없다(2절 예외 참고).
