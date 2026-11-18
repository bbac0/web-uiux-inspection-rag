# Run e9-main-norag-r3 (E9-norag)

- 기간(UTC): 2026-11-13T12:56:53.013+00:00 → 2026-11-13T13:20:45.566+00:00
- 페이지: 요청 91, 기록 91, 기록 없음 0
- 상태: ok 91
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 61
- 총 비용 $0.7663 (호출당 평균 $0.00842); 구성: 입력(비캐시) $0.0354, 입력(cached) $0.0010, 출력+사고 $0.7298

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 153146 | 1682.9 |
| cached_content_token_count | 35000 | 384.6 |
| candidates_token_count | 52168 | 573.3 |
| total_token_count | 480059 | 5275.4 |
| thoughts_token_count_derived | 239745 | 2634.6 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 91 | 4.1413 | 4.1404 | 4.1635 |
| query_embedding | 0 | None | None | None |
| vector_search | 0 | None | None | None |
| upload | 91 | 4.5523 | 4.3909 | 5.0146 |
| llm | 91 | 19.5976 | 19.0459 | 25.8788 |
| total | 91 | 30.1149 | 29.5377 | 37.1725 |

- RAG 청크 수 분포: {'0': 91}
- derived 사고 토큰 음수: 0건, cached>0: 28건, 스키마 문제 레코드: 0건
