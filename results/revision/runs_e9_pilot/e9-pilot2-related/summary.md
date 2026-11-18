# Run e9-pilot2-related (E9-pilot2-related)

- 기간(UTC): 2026-11-13T03:00:09.687+00:00 → 2026-11-13T03:04:38.095+00:00
- 페이지: 요청 8, 기록 8, 기록 없음 0
- 상태: ok 8
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 8
- 총 비용 $0.1010 (호출당 평균 $0.01262); 구성: 입력(비캐시) $0.0105, 입력(cached) $0.0000, 출력+사고 $0.0905

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 35000 | 4375 |
| cached_content_token_count | 0 | 0 |
| candidates_token_count | 2282 | 285.2 |
| total_token_count | 71181 | 8897.6 |
| thoughts_token_count_derived | 33899 | 4237.4 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 8 | 4.1283 | 4.1258 | 4.1451 |
| query_embedding | 0 | None | None | None |
| vector_search | 8 | 0.0051 | 0.002 | 0.0193 |
| upload | 8 | 4.262 | 4.3152 | 4.5172 |
| llm | 8 | 21.8799 | 21.4119 | 27.6875 |
| total | 8 | 31.9837 | 31.763 | 37.545 |

- RAG 청크 수 분포: {'6': 8}
- derived 사고 토큰 음수: 0건, cached>0: 0건, 스키마 문제 레코드: 0건
