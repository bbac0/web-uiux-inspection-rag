# Run e9-main-norag-r2 (E9-norag)

- 기간(UTC): 2026-11-13T05:35:47.059+00:00 → 2026-11-13T05:59:38.809+00:00
- 페이지: 요청 91, 기록 91, 기록 없음 0
- 상태: ok 91
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 61
- 총 비용 $0.7995 (호출당 평균 $0.00879); 구성: 입력(비캐시) $0.0336, 입력(cached) $0.0012, 출력+사고 $0.7647

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 153146 | 1682.9 |
| cached_content_token_count | 41188 | 452.6 |
| candidates_token_count | 54364 | 597.4 |
| total_token_count | 500211 | 5496.8 |
| thoughts_token_count_derived | 251513 | 2763.9 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 91 | 4.1427 | 4.1442 | 4.1646 |
| query_embedding | 0 | None | None | None |
| vector_search | 0 | None | None | None |
| upload | 91 | 4.146 | 4.1282 | 4.7479 |
| llm | 91 | 20.2849 | 19.9039 | 26.6123 |
| total | 91 | 30.3144 | 29.7305 | 36.4369 |

- RAG 청크 수 분포: {'0': 91}
- derived 사고 토큰 음수: 0건, cached>0: 33건, 스키마 문제 레코드: 0건
