# Run e9-main-norag-r1 (E9-norag)

- 기간(UTC): 2026-11-13T03:31:41.436+00:00 → 2026-11-13T03:54:45.307+00:00
- 페이지: 요청 91, 기록 91, 기록 없음 0
- 상태: ok 91
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 61
- 총 비용 $0.7666 (호출당 평균 $0.00842); 구성: 입력(비캐시) $0.0317, 입력(cached) $0.0014, 출력+사고 $0.7334

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 153146 | 1682.9 |
| cached_content_token_count | 47357 | 520.4 |
| candidates_token_count | 53573 | 588.7 |
| total_token_count | 493879 | 5427.2 |
| thoughts_token_count_derived | 239803 | 2635.2 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 91 | 4.1404 | 4.1404 | 4.1592 |
| query_embedding | 0 | None | None | None |
| vector_search | 0 | None | None | None |
| upload | 91 | 4.4073 | 4.1604 | 4.6688 |
| llm | 91 | 18.9619 | 18.3486 | 25.4528 |
| total | 91 | 29.225 | 28.5115 | 35.8107 |

- RAG 청크 수 분포: {'0': 91}
- derived 사고 토큰 음수: 0건, cached>0: 37건, 스키마 문제 레코드: 0건
