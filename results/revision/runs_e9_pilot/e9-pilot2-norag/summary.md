# Run e9-pilot2-norag (E9-pilot2-norag)

- 기간(UTC): 2026-11-13T02:46:24.973+00:00 → 2026-11-13T02:50:43.752+00:00
- 페이지: 요청 8, 기록 8, 기록 없음 0
- 상태: ok 8
- 실패 페이지 0개, 파싱 실패 0개, 재시도 합계 0
- 모델 버전: gemini-2.5-flash; 서로 다른 프롬프트 해시 8
- 총 비용 $0.0826 (호출당 평균 $0.01032); 구성: 입력(비캐시) $0.0040, 입력(cached) $0.0000, 출력+사고 $0.0786

| 토큰 | 합계 | 평균 |
|---|---:|---:|
| prompt_token_count | 13392 | 1674 |
| cached_content_token_count | 0 | 0 |
| candidates_token_count | 4167 | 520.9 |
| total_token_count | 44818 | 5602.2 |
| thoughts_token_count_derived | 27259 | 3407.4 |

| 지연시간(초) | n | 평균 | 중앙값 | P95 |
|---|---:|---:|---:|---:|
| acquisition | 8 | 4.1311 | 4.1287 | 4.1547 |
| query_embedding | 0 | None | None | None |
| vector_search | 0 | None | None | None |
| upload | 8 | 4.2032 | 4.3142 | 4.4632 |
| llm | 8 | 20.6926 | 21.7317 | 25.0683 |
| total | 8 | 30.7609 | 31.7168 | 35.2682 |

- RAG 청크 수 분포: {'0': 8}
- derived 사고 토큰 음수: 0건, cached>0: 0건, 스키마 문제 레코드: 0건
