# Run e9-pilot2-fixedlong (E9-pilot2-fixedlong)

- 기간(UTC): 2026-11-13T03:04:39.033+00:00 → 2026-11-13T03:07:00.012+00:00
- 페이지: 요청 8, 기록 8, 기록 없음 0
- 상태: ok 8
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 8
- 총 비용 $0.0955 (호출당 평균 $0.01194); 구성: 입력(비캐시) $0.0101, 입력(cached) $0.0000, 출력+사고 $0.0854

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 35224 | 4403 |
| cached_content_token_count | 1484 | 185.5 |
| candidates_token_count | 3293 | 411.6 |
| total_token_count | 70849 | 8856.1 |
| thoughts_token_count_derived | 30848 | 3856 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 8 | 4.1338 | 4.13 | 4.1461 |
| query_embedding | 0 | None | None | None |
| vector_search | 8 | 0.0088 | 0.0022 | 0.028 |
| upload | 8 | 4.4867 | 4.5097 | 4.8198 |
| llm | 8 | 22.3786 | 22.6415 | 25.9867 |
| total | 8 | 32.7722 | 33.1772 | 36.1546 |

- RAG 청크 수 분포: {'9': 8}
- derived 사고 토큰 음수: 0건, cached>0: 2건, 스키마 문제 레코드: 0건
