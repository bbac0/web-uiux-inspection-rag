# Run e9-pilot-related (E9-pilot-related)

- 기간(UTC): 2026-11-12T16:20:35.784+00:00 → 2026-11-12T16:22:45.663+00:00
- 페이지: 요청 8, 기록 8, 기록 없음 0
- 상태: ok 8
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 8
- 총 비용 $0.0738 (호출당 평균 $0.00923); 구성: 입력(비캐시) $0.0098, 입력(cached) $0.0001, 출력+사고 $0.0639

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 34950 | 4368.8 |
| cached_content_token_count | 2221 | 277.6 |
| candidates_token_count | 1946 | 243.2 |
| total_token_count | 62749 | 7843.6 |
| thoughts_token_count_derived | 23632 | 2954 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 8 | 3.9241 | 3.9223 | 3.9535 |
| query_embedding | 0 | None | None | None |
| vector_search | 8 | 0.0148 | 0.0058 | 0.0481 |
| upload | 8 | 4.6524 | 4.6291 | 5.0903 |
| llm | 8 | 17.3726 | 17.3554 | 19.5005 |
| total | 8 | 28.3469 | 28.1206 | 31.3445 |

- RAG 청크 수 분포: {'6': 8}
- derived 사고 토큰 음수: 0건, cached>0: 3건, 스키마 문제 레코드: 0건
