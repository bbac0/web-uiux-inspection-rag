# Run e9-pilot-norag (E9-pilot-norag)

- 기간(UTC): 2026-11-12T16:13:12.517+00:00 → 2026-11-12T16:15:33.420+00:00
- 페이지: 요청 8, 기록 8, 기록 없음 0
- 상태: ok 8
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 8
- 총 비용 $0.0763 (호출당 평균 $0.00953); 구성: 입력(비캐시) $0.0040, 입력(cached) $0.0000, 출력+사고 $0.0723

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 13342 | 1667.8 |
| cached_content_token_count | 0 | 0 |
| candidates_token_count | 3923 | 490.4 |
| total_token_count | 42243 | 5280.4 |
| thoughts_token_count_derived | 24978 | 3122.2 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 8 | 3.9175 | 3.916 | 3.9364 |
| query_embedding | 0 | None | None | None |
| vector_search | 0 | None | None | None |
| upload | 8 | 5.0057 | 5.1327 | 5.3363 |
| llm | 8 | 19.6819 | 18.3088 | 26.0769 |
| total | 8 | 30.5932 | 29.1419 | 37.2661 |

- RAG 청크 수 분포: {'0': 8}
- derived 사고 토큰 음수: 0건, cached>0: 0건, 스키마 문제 레코드: 0건
