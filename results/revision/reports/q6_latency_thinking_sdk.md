# 확인 6: 단계별 지연 시간 최댓값, thinking budget, 실제 호출 SDK

작성 2026-11-19. API 호출 없음.

## 1. 단계별 지연 시간 (E1-R1, 순차 실행, 초)

| 단계 | n | 평균 | 중앙값 | p95 | 최댓값 | 최댓값 페이지 |
|---|---|---|---|---|---|---|
| 수집 (로드 + 3초 대기 + 스크린샷 + DOM) | 200 | 3.955 | 3.925 | 3.974 | 7.784 | page_075 |
| 질의 임베딩 | 200 | 0.554 | 0.515 | 0.681 | 3.515 | page_161 |
| 벡터 검색 | 200 | 0.009 | 0.006 | 0.014 | 0.300 | page_097 |
| 이미지 업로드 (File API) | 200 | 5.106 | 4.962 | 6.231 | 13.077 | page_097 |
| LLM 생성 | 200 | 18.682 | 18.476 | 25.023 | 26.704 | page_036 |
| 기타 (합계 − 위 단계) | 200 | 1.744 | 1.681 | 2.097 | 4.595 | page_001 |
| 합계 | 200 | 30.050 | 29.713 | 36.412 | 38.875 | page_098 |

출처: `results/revision/tables/latency_E1-R1.csv`, 최댓값 페이지는 `results/revision/runs/E1-R1/calls.jsonl`
(latency_sec)

- 표의 최댓값은 calls.jsonl 에서 다시 계산한 값과 같다.

## 2. Gemini 호출의 thinking budget

- **설정하지 않았다.** 생성 호출의 설정은 `genai.types.GenerationConfig(temperature=0.0,
  response_mime_type="application/json")` 뿐이고 thinking 관련 인자가 없다(`services/analyzer.py` 331~339행).
  저장소 코드에서 thinking budget 을 지정하는 곳은 없다. 따라서 `gemini-2.5-flash` 의 기본 동작(모델이 사고 토큰 양을 정함)이다.
- 실제 사고 토큰(실행 기록, `thoughts_token_count_derived` = total − prompt − candidates − cached):

| 범위 | 호출 | 중앙값 | 평균 | 최대 | 0 인 호출 | 음수(계산 이상) |
|---|---|---|---|---|---|---|
| E1-R1 | 200 | 3,005 | 3,076.5 | 4,924 | 0 | 0 |
| testbed_200 run 전체 | 2,033 | 2,561 | 2,540.0 | 6,710 | 0 | 5 |
| E9 본 실험 12 run | 1,092 | 3,224.5 | 3,053.2 | 8,070 | 0 | 64 |

출처: `results/revision/runs/*/calls.jsonl`, `results/revision/runs_e9/*/calls.jsonl` (usage; 중앙값·평균은
0 이상만)

- 0 인 호출이 없어 사고가 꺼져 있지 않았다. 음수 값(69건)은 응답의 토큰 합계에서 거꾸로 계산한 값이라 생긴 이상값이며,
  원인은 기록만으로 확정할 수 없다. 비용은 이 값이 아니라 출력 토큰(사고 포함) 기록으로 계산했다.

## 3. 실제 호출에 쓴 SDK

| 용도 | SDK (버전) | 코드 (모델 `models/gemini-2.5-flash`) |
|---|---|---|
| 생성(분석) 호출 | **google-generativeai 0.8.6** | `genai.GenerativeModel(...).generate_content` |
| 스크린샷 업로드·삭제 | google-generativeai 0.8.6 | `genai.upload_file`, `genai.delete_file` (File API) |
| 질의 임베딩 (RAG) | **langchain-google-genai 4.3.5** | `GoogleGenerativeAIEmbeddings` |
| 벡터 DB | langchain-chroma 1.1.0, chromadb 1.5.9 | `Chroma.similarity_search_by_vector_...` |

출처: `services/analyzer.py` 1·15·16·265·331~349행, `results/revision/runs/E1-R1/run_meta.json`
(env.packages)

- 임베딩 모델은 `models/gemini-embedding-001` 이다.
- 생성 호출은 langchain 을 거치지 않고 google-generativeai 를 직접 쓴다. langchain-google-genai 는 임베딩에만 쓴다.
- 실행 기록의 응답 모델 버전은 `gemini-2.5-flash` 다(`calls.jsonl` 의 model_version).
