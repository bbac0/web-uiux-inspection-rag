# 조건별 프롬프트/입력 diff

기준: 프로덕션 조건 (RAG fixed, 스크린샷+HTML, 1280x800), 예시 페이지 `testbed_200/page_001.html`, 프롬프트 날짜 2026-01-01(예시).
검색 청크 본문은 자리표시 문자열이다. 이미지 입력은 `<<IMAGE ...>>` 로 표시했다.

| 조건 | 바뀐 줄 수 | 파일 |
|---|---:|---|
| E2-A1_no-rag | 12 | `E2-A1_no-rag.diff` |
| E2-A2_modality-html | 2 | `E2-A2_modality-html.diff` |
| E2-A3_modality-screenshot | 2 | `E2-A3_modality-screenshot.diff` |
| E3_query-page | 0 | `E3_query-page.diff` |
| E3_query-oracle | 14 | `E3_query-oracle.diff` |
| E4_viewport-mobile | 0 | `E4_viewport-mobile.diff` |

참고: E3 page/oracle 은 프롬프트 문구가 아니라 가이드라인 섹션에 들어가는 검색 결과만 바뀐다. 실제 청크 본문은 run 로그의 청크 ID 로 추적한다.
