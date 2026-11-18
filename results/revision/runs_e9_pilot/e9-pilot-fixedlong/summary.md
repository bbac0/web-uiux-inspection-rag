# Run e9-pilot-fixedlong (E9-pilot-fixedlong)

- 기간(UTC): 2026-11-12T16:22:46.709+00:00 → 2026-11-12T16:25:10.987+00:00
- 페이지: 요청 8, 기록 8, 기록 없음 0
- 상태: ok 8
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 8
- 총 비용 $0.0925 (호출당 평균 $0.01156); 구성: 입력(비캐시) $0.0099, 입력(cached) $0.0001, 출력+사고 $0.0825

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 35174 | 4396.8 |
| cached_content_token_count | 2224 | 278 |
| candidates_token_count | 3222 | 402.8 |
| total_token_count | 70411 | 8801.4 |
| thoughts_token_count_derived | 29791 | 3723.9 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 8 | 3.9246 | 3.9212 | 3.9554 |
| query_embedding | 0 | None | None | None |
| vector_search | 8 | 0.0113 | 0.0029 | 0.0407 |
| upload | 8 | 4.6208 | 4.608 | 4.8897 |
| llm | 8 | 22.668 | 22.4802 | 30.0897 |
| total | 8 | 33.2055 | 33.263 | 41.2749 |

- RAG 청크 수 분포: {'9': 8}
- derived 사고 토큰 음수: 0건, cached>0: 3건, 스키마 문제 레코드: 0건
