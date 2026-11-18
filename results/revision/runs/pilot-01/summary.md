# Run pilot-01 (pilot)

- 기간(UTC): 2026-11-11T06:42:32.014+00:00 → 2026-11-11T06:43:25.610+00:00  **중단됨: error rate 10/10 > 20%**
- 페이지: 요청 10, 기록 10, 기록 없음 0
- 상태: rag_error 10
- 실패 페이지 10개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: -; 서로 다른 프롬프트 해시 0
- 총 비용 $0.0000 (호출당 평균 $0.00000); 구성: 입력(비캐시) $0.0000, 입력(cached) $0.0000, 출력+사고 $0.0000

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 0 | None |
| cached_content_token_count | 0 | None |
| candidates_token_count | 0 | None |
| total_token_count | 0 | None |
| thoughts_token_count_derived | 0 | None |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 10 | 3.8861 | 3.8862 | 3.9076 |
| query_embedding | 0 | None | None | None |
| vector_search | 0 | None | None | None |
| upload | 0 | None | None | None |
| llm | 0 | None | None | None |
| total | 10 | 4.1966 | 4.0085 | 5.072 |

- RAG 청크 수 분포: {'None': 10}
- derived 사고 토큰 음수: 0건, cached>0: 0건, 스키마 문제 레코드: 0건
