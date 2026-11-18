# 리뷰어 대응 재실험 (results/revision/)

이 폴더는 MDPI 리뷰어 지적에 대응하는 재실험의 산출물이다. 기존 `results/` 의 작업 파일과
`paper_results/` 는 건드리지 않고 읽기 전용으로만 참조한다. 사전 분석 계획은 `analysis_plan.md` 에 있다 (실행 전 동결).

## 가장 먼저 알아야 할 사실

1. **1차 평가(run1/run2)는 빈 벡터 DB로 실행되었다.** `services/analyzer.py` 는 `./chroma_db` 를 쓰는데
   이 DB에는 임베딩이 0개다(가이드라인 1,020청크는 `services/chroma_db` 에 있다). 보관된 run2 리포트 200개(분석 360건)의
   `rag_status` 는 모두 `n_chunks: 0, ok: true` 였다. 즉 1차 결과의 프롬프트 가이드라인 섹션은 비어 있었다.
   run1 원본은 덮어써져 남아 있지 않지만 같은 코드와 같은 DB 경로로 실행되었다. 이번 재실험은 `--chroma-path services/chroma_db`
   로 실행하고, RAG 가 켜졌는데 0청크면 오류(`rag_empty`)로 기록한다. `--no-rag`(E2-A1)는 섹션 제목만 남기고 내용을 비우므로
   레거시 실행과 같은 형태다.
2. **평가는 `--max-pages 1` 로 한다.** 1차 평가는 시작 페이지에서 같은 도메인 링크를 따라가 최대 5페이지를 분석했고,
   테스트베드에서는 160페이지가 `/login`(로컬 서버의 404 페이지)까지 함께 분석되었다. 재실험은 시작 페이지만 분석하므로
   1차 평가와 설정이 다르다. `--max-pages 1` 에서는 링크 수집을 위한 사전 접속도 하지 않는다.

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `analysis_plan.md` | 사전 분석 계획 (실행 후 수정 금지) |
| `testbed_manifest.csv` | 테스트베드 HTML/메타데이터 SHA-256 (생성 규칙 재적용 결과와 200/200 일치) |
| `keyword_dictionary.md` | 키워드 사전 전문 (수정 없음) |
| `injection_procedure.md` | 결함 주입 절차 (코드에서 복원) |
| `legacy_run2_manifest.csv` | run2 사본 3곳(`paper_results/run2`, `results_run2`, `results`)의 SHA-256. 세 곳 201개 파일 모두 동일 |
| `prompt_diffs/` | 조건별 프롬프트/입력 diff |
| `oracle_chunks.csv` | E3 oracle 입력 (`page_id,chunk_id`, 한 페이지에 여러 줄 가능). 정답 청크 ID 는 연구자가 채운다 |
| `freeze_manifest.csv` | `exp-freeze-v1` 동결 대상 파일과 프롬프트의 SHA-256 |
| `runs/{run_id}/` | run 별 결과 (아래). 실행 후 읽기 전용으로 잠금 |

### run 폴더

| 파일 | 커밋 | 내용 |
|---|---|---|
| `run_meta.json` | O | 실행 인자, 페이지 목록, git HEAD/describe/dirty 파일, 동결 태그 커밋, 패키지 버전, 동결 설정 |
| `calls.jsonl` | O | LLM 호출(페이지 분석)당 1줄. append 전용 (`services/llm_wrapper.py` 의 스키마) |
| `reports.jsonl` | O | 페이지당 1줄, 프로덕션과 같은 형태의 병합 리포트 (채점 입력) |
| `summary.json`, `summary.md` | O | 성공/실패 수, 토큰, 비용, 지연시간(평균/중앙값/P95) |
| `SHA256SUMS` | O | 잠금 시점 모든 파일의 해시 (`shots/`, `prompts/` 포함) |
| `shots/`, `prompts/` | X | 스크린샷, 프롬프트 원문. 커밋하지 않고 해시만 SHA256SUMS 에 남는다 |

`calls.jsonl` 한 줄의 주요 필드: `run_id, condition, page_id, template_id, url, ts_start_utc, ts_end_utc, status`
(`ok|parse_error|api_error|rag_empty|rag_error|acquisition_error`), `prompt_date, model_name, model_version,
prompt_sha256, image_sha256, modality, viewport, html_chars_sent`,
`rag{enabled, query_mode, query, query_fallback, chroma_path, n_chunks, chunks[{id, distance, source, page}], error, embedding_attempts}`,
`usage{prompt_token_count, cached_content_token_count, candidates_token_count, total_token_count, thoughts_token_count_derived}`,
`cost_usd{input, output, total}`, `latency_sec{acquisition, query_embedding, vector_search, upload, llm, total}`,
`attempts, retries, errors[], raw_response_text, parsed, parse_error, result`.

## 실행 방법

```bash
# 터미널 1 (저장소 루트): 테스트베드 서빙
python -m http.server 8080 --bind 127.0.0.1

# 터미널 2: API 키는 환경변수로만 (.env 는 읽지 않는다)
export GEMINI_API_KEY=...            # PowerShell: $env:GEMINI_API_KEY="..."
python experiments/revision/run_experiment.py --run-id E1-R1 --condition E1 --pages all \
    --max-pages 1 --chroma-path services/chroma_db --prompt-date <YYYY-MM-DD> --concurrency 1
```

| run_id | 추가 플래그 |
|---|---|
| E1-R1 | (위 명령 그대로, `--concurrency 1`) |
| (순서 실행) | `python experiments/revision/run_e1_a1_sequence.py` : R1 → 관문(오류율 ≤5%, 파싱 실패 ≤2%) → A1-1 → R2 → A1-2 → R3 → A1-3 |
| E1-R2, E1-R3 | `--concurrency 4` |
| E2-A1-1, E2-A1-2, E2-A1-3 | `--no-rag --concurrency 4` (3회, 계획 9절 사전 수정) |
| E2-A2 | `--modality html` |
| E2-A3 | `--modality screenshot` |
| E3-page | `--pages terminology+controls --query-mode page` |
| E3-oracle | `--pages terminology+controls --query-mode oracle --oracle-chunks results/revision/oracle_chunks.csv` |
| E4-mobile | `--pages mobile+controls --viewport-extra mobile` |

API 없이 파이프라인을 점검할 때는 `--mock-llm --runs-base <임시폴더>` (가짜 LLM/벡터 DB, 실험에 쓰지 않음).
단위 테스트: `python -m unittest tests.test_revision_infra -v`.

## 플래그 (기본값 = 기존 동작)

`cli.py` 와 `run_experiment.py` 에 같은 이름으로 있다.

| 플래그 | 기본값 | 의미 |
|---|---|---|
| `--max-pages N` | 5 | 시작 페이지 포함 분석할 최대 페이지 수. 1이면 시작 페이지만 |
| `--no-rag` | 꺼짐 | 가이드라인 섹션 제목은 두고 내용만 비움 |
| `--modality {both,html,screenshot}` | both | html: 이미지 입력 제외, screenshot: HTML 블록 제목만 두고 내용 비움 |
| `--viewport-extra mobile` | 없음 (1280x800) | 해당 run 의 뷰포트를 390x844 로 바꿈. User-Agent 는 프로덕션과 같은 데스크톱 문자열 그대로 |
| `--query-mode {fixed,page,oracle}` | fixed | 검색 질의 방식 (아래) |
| `--oracle-chunks PATH` | 없음 | oracle 모드 입력 CSV |
| `--chroma-path PATH` | `./chroma_db` | 벡터 DB 경로. 실험은 `services/chroma_db`. 러너는 원본을 직접 열지 않고 run 마다 임시 폴더로 복사해 쓰며, 복사 시점 원본의 파일별 SHA-256 을 `run_meta.json` 의 `chroma` 에 남긴다. 복사본은 run 종료 후 삭제 |
| `--prompt-date YYYY-MM-DD` | 실행 당일 | 프롬프트 날짜 고정. 러너에서는 필수. 실제 실행 시각은 로그에 따로 기록 |
| `--run-id ID` | 없음 | 로그 폴더 이름. 이미 있으면 오류로 중단 |
| `--concurrency N` | cli: 제한 없음 / 러너: 1 | 동시 분석 수 (러너는 1~4만 허용) |

### `--query-mode page` 질의 생성 규칙 (`services/analyzer.py: build_page_query`)

1. 순서: `<title>` → `h1`~`h3` 헤딩(문서 순서) → 버튼 라벨(문서 순서).
   버튼 라벨은 `<button>` 의 textContent, `input[type=submit|button|reset]` 의 value, `[role=button]` 의 textContent.
2. 각 항목은 공백을 정리(앞뒤 제거, 연속 공백 한 칸)하고, 빈 항목과 중복 문자열(처음 것만 남김)을 뺀다.
3. 공백 한 칸으로 이어 붙인다. 결과가 비면 고정 질의로 대체하고 `query_fallback: true` 로 기록한다.
4. 렌더링 후 DOM 에서 뽑는다. textContent 를 쓰므로 CSS 로 숨겨진(font-size 0 등) 버튼의 라벨도 들어간다.
   용어 위반 페이지에서는 주입된 `접속하기` 가 질의에 포함될 수 있다 (페이지 내용이므로 그대로 둔다).

### 검색, 재시도, 비용

- fixed/page: `embed_query` → `similarity_search_by_vector_with_relevance_scores(k=4)`. 프로덕션
  `similarity_search` 와 같은 연산을 두 단계로 나눠 시간을 재고 청크 ID 와 L2 거리를 남긴다.
- oracle: CSV 의 청크 ID 를 그대로 가져와 같은 형식(`[파일 - N페이지]\n본문`)으로 넣는다. 질의 임베딩과 거리는 없다.
- 재시도: 일시적 오류(429/rate/quota/503/unavailable/overloaded/deadline)만 호출당 최대 3회, 지수 백오프 `min(30, 2^n) + U(0,1)`초.
  질의 임베딩, 이미지 업로드, 생성 호출 각각에 적용한다.
- 오류율 중단: 완료 페이지 10개 이상에서 (api_error + rag_empty + rag_error + acquisition_error) / 완료 > 20% 이면 중단.
  parse_error 는 오류율에 넣지 않고 따로 집계한다. 실패 페이지도 로그와 요약에 남는다.
- 비용: cached 입력(`cached_content_token_count`) × $0.03/1M + 나머지 입력(`prompt_token_count − cached`) × $0.30/1M
  + (`candidates_token_count` + derived 사고 토큰) × $2.50/1M. `cost_usd` 에 `input_uncached`, `input_cached`, `output` 을 따로 기록한다.
  점검용으로 `thoughts_check_without_cached_subtraction = total − prompt − candidates` 도 남긴다.
  derived 사고 토큰 = `total − prompt − candidates − cached` (SDK 0.8.6 이 `thoughts_token_count` 를 주지 않음).
  음수가 나오면 그대로 기록하고 비용 계산에서만 0으로 둔다. 임베딩 호출 비용은 계산하지 않는다(지연시간만 기록).

## exp-freeze-v5 추가 사항 (2026-11-12)

- 분석 계획 10절에 사전 지정을 추가했다(의미 채점 모델·설정, 반복 채점 범위, 사람 평가, 라벨 3층, string_match, E3 related-clause,
  용어 유형 세 해석, 채점 경로 규칙, 채점 범위 축소, E1-R3 중단과 R3b 대체).
- **이 태그 시점에 의미 채점은 실행하지 않았다.**

- E3 `--query-mode oracle` 은 문서상 **"관련 조항 제공(related-clause)"** 조건이다(정답 조항 주입이 아님). 플래그 이름은 동결되어 그대로다.
- 세 채점기: 키워드(description), 의미 채점(description + suggestion, Anthropic claude-sonnet-5-5, pass1; pass2 는 E1-R1 만), string_match('접속하기', 용어 위반만).
- 라벨 3층(nominal / effective / guideline_grounded)과 `ground_truth.csv` 의 추가 열 설명. guideline_grounded 판정 규칙(a~c)과 유형별 결정.
- string_match 해석의 명칭은 **언급 기반(mention-based)** 이다(규칙: description 또는 suggestion 에 '접속하기' 포함).
- 용어 유형 수치 메모: 논문 Table 3 의 17건은 run1 의 수치이고, 15건은 run2 의 대상 페이지 이슈 수(14페이지)다.
  15건 중 4건만 로그인 링크 레이블을 실제로 지적한다는 분류는 사전 지정 없이 읽고 나눈 값이다 — **exploratory, not pre-registered** —
  결과 표에는 쓰지 않는다.
- E3 관련 조항 제공(related-clause) 청크 확정: `b4c4ffd0-b39d-49ef-801d-487b44041b9b` (gov_check 29쪽, 739자),
  `87f08a4d-b8b6-427c-8fd5-2925b07b4d8a` (gov_check 208쪽, 748자). 두 청크는 목표 조항 외에 인접 항목을 함께 담고 있다
  (29쪽: 링크 체크리스트 1~10과 버튼 그룹 항목, 208쪽: 로그인 기능 찾기 1의 점검 절차와 3의 제목). 두 청크 본문 합계는 1,487자로
  고정 질의 4청크의 본문 합계 1,552자와 비슷하다. 프롬프트에 들어가는 형태(`[파일 - N페이지]` 머리글 포함)로는 1,538자 대 1,653자다. `oracle_chunks.csv` 는 2026-11-12 승인 후 만들었다(84페이지 × 2청크, `exp-freeze-v5`).

- 의미 채점(`scoring/semantic_grader_anthropic.py`, 설정 `scoring/grader_config.json`)은 이슈의 **description + suggestion** 을 입력으로 쓴다
  (사람 평가자가 시트에서 보는 정보와 같게). **키워드 채점은 기존 정의대로 description 만 쓴다.** 두 채점기의 입력 범위가 다르다.
- 의미 채점 입력에서는 `[http://…]` 접두어(파이프라인이 붙인 페이지 URL, 페이지 ID 포함)를 지운다.
  **1차 평가(run1)의 의미 채점(`paper_results/run1/semantic_scoring_run1.json`, Gemini)은 이 접두어를 지우지 않고 보냈다.**
- 의미 채점은 temperature 를 보내지 않는다(모델 사양상 지정 불가). pass1 이 주 결과이며 pass2 는 E1-R1 에서만 한다(2항·13항).
- anthropic SDK 는 R1~A1 종료 후 사용자 승인을 받아 설치하고 버전을 실행 기록에 남긴다.

## 동결 설정

모델 `models/gemini-2.5-flash`, temperature 0, `response_mime_type=application/json`, 청크 1000자/중첩 100자,
고정 질의 `"웹 UI/UX 표준 가이드라인 공통 규정"`, k=4, 뷰포트 1280x800, 렌더링 DOM 앞 5,000자, 프롬프트 문구
(원본 커밋 `6bee028` 과 바이트 단위로 같음을 단위 테스트로 확인), 키워드 사전, 의미 채점 프롬프트(`JUDGE_PROMPT` v1).

동결 태그: `exp-freeze-v1` (1단계) → `exp-freeze-v2` (API 호출 전, 사용자 승인: 분석 계획에 사람 평가 기준 표준 문장 추가,
cached 단가 추가, 벡터 DB 복사 사용). 이후 실험은 `exp-freeze-v2` 기준이다.
`exp-freeze-v3`: 러너 변경(아래 알려진 제한). `exp-freeze-v4`: 분석 계획 9절 사전 수정(A1 3회). `exp-freeze-v5`: 분석 계획 10절 추가(아래 'exp-freeze-v5 추가 사항'), `oracle_chunks.csv`, `fixed_long_selection.json`, 동결 목록에 채점기 파일 추가.

## 실행 기록

| run_id | 실행 날짜(UTC) | 프롬프트 날짜 | model_version | 비고 |
|---|---|---|---|---|
| pilot-01 | 2026-11-11 | 2026-11-11 | - | 파일럿, 임베딩 402(크레딧 소진)로 10페이지 모두 rag_error, 비교 제외 |
| pilot-02 | 2026-11-12 | 2026-11-11 | gemini-2.5-flash | 파일럿 10페이지, 비교 제외 |
| E1-R1 | 2026-11-12 | 2026-11-11 | gemini-2.5-flash | 순차(동시 1), 지연시간 표 |
| E2-A1-1 | 2026-11-12 | 2026-11-11 | gemini-2.5-flash | 동시 4 |
| E1-R2 | 2026-11-12 | 2026-11-11 | gemini-2.5-flash | 동시 4 |
| E2-A1-2 | 2026-11-12 | 2026-11-11 | gemini-2.5-flash | 동시 4 |
| E1-R3 | 2026-11-12 | 2026-11-11 | gemini-2.5-flash | **aborted** 160/200 (메모리 부족 강제 종료), 분석 제외, ABORTED.json |
| E1-R3b | 2026-11-12 | 2026-11-11 | gemini-2.5-flash | R3 대체, 동시 2 |
| E2-A1-3 | 2026-11-12 | 2026-11-11 | gemini-2.5-flash | 동시 2 |

환경: Windows 11, Python 3.11.5, google-generativeai 0.8.6, google-ai-generativelanguage 0.6.15,
langchain-google-genai 4.3.5, langchain-chroma 1.1.0, chromadb 1.5.9, playwright 1.62.0 (run 별 정확한 값은 `run_meta.json`).

## 알려진 제한

- `--max-pages 1` 은 1차 평가 설정과 다르다 (위 참고).
- 사고 토큰은 계산값이다. 묵시적 캐시가 생기면(`cached > 0`) 계산식에 따라 값이 달라질 수 있어 요약에 따로 센다.
- Windows 에서는 잠금이 파일 읽기 전용 속성만 바꾸고 폴더는 보호하지 못한다. `SHA256SUMS` 로 변조 여부를 확인한다
  (`services.llm_wrapper.verify_run`).
- 렌더링 대기는 프로덕션과 같이 `networkidle` 후 3초다.
- `exp-freeze-v3` (사용자 승인, 러너만 변경): Chroma 클라이언트를 닫은 뒤 임시 복사본 삭제(실패 시 경고만), 402/429/크레딧 소진 오류가 기록되면 오류율과 별개로 즉시 중단(페이지 단위로 확인하며 호출 재시도 정책은 그대로).

## 계획 이탈 기록

| 날짜 | 내용 | 이유 |
|---|---|---|
| 2026-11-12 | E1-R3 이 160/200 에서 중단됨. aborted 로 보존(분석 제외)하고 새 run_id E1-R3b 로 200페이지 재실행 | Claude Code 가 시스템 메모리 부족으로 백그라운드 프로세스를 강제 종료(러너·API 오류 아님). 4절 '중단된 run 은 새 run_id 로' 규칙 적용 |
| 2026-11-12 | E1-R3b, E2-A1-3 은 동시 실행 2건 (계획: 4건 이하) | 메모리 부족 재발 방지. 계획 범위 안이며 생성 결과에는 영향 없음, 지연시간 표는 순차 실행 E1-R1 로만 작성 |
| 2026-11-12 | 순서 실행 드라이버를 새 파일 `run_e1_r3b_a1_3.py` 로 실행(기존 드라이버는 동결 그대로) | 동결 파일 수정 금지 규칙. 시작 전 메모리 5GB 확인, 5건마다 메모리 기록, 4GB 미만이면 멈춤 |
| 2026-11-13 | E9 입력 수정 (`exp-freeze-e9-v3`): (c1) 공식 배너 국기 자리 회색 상자 → 국기 그림(`/flag.svg`, 24×16), (c2) portal_main 본문 `<div id="main-banner">배너</div>` → `<div id="main-notice">주요 소식</div>`. (c3) 푸터 연도 추가는 제외. 같은 시드로 재생성, 정규식 규칙·판정 프롬프트·주입 코드·분석 계획은 그대로 | 파일럿 대조군 위양성 4건의 원인이 입력의 자리 표시 요소임이 로그로 확인되었고, 이 요소는 모든 조건에 같은 영향을 주었다. (c2)는 '기존 템플릿 본문 그대로 재사용' 원칙에서 한 군데 더 벗어난다. (c3)는 위양성 원인이 아니고 모든 페이지의 이슈 구성을 바꾸므로 제외. 수정 1회·재파일럿 1회로 끝낸다 |
| 2026-11-13 | E9 재파일럿(e9-pilot2) 4개 조건(RAG 끔, 고정 질의, 페이지별 질의, 관련 조항 제공)을 동시 실행 1건으로 실행 (fixed-long 은 2건) | 시작 전 남은 메모리 4.49~4.89GB (연구자 규칙: 4.0~5.0GB 이면 1건). 생성 결과에는 영향 없음. `memory_logs/concurrency_deviations.jsonl` |
| 2026-11-13 | E9 동결 목록을 만드는 스크립트 `experiments/revision/freeze_manifest_e9.py` 가 `exp-freeze-e9-v1`·`v2` 동결 목록에 들어 있지 않았다. **다음 E9 태그 때 목록에 넣는다**(지금은 수정·태그하지 않음) | 목록 작성 도구 자체를 대상에 넣지 않은 누락. 목록 내용(130개 파일 해시)은 v2 태그 커밋에 그대로 있다 |
| 2026-11-13 | 의미 채점 max_tokens 100 에서 150건(2.7%)이 잘림 → 해당 건만 max_tokens 800 (`scoring/grader_config_retry800.json`, 그 밖 설정 동일)으로 1회 배치 재채점, 별도 폴더 `{out_id}-retry`, 원 결과 보존. 주 분석 = 재채점 포함, 원 규칙(잘림 = 음성)과 잘림 페이지 제외 = 민감도. 재채점 결과를 보기 전에 결정 (`analysis_plan_addendum_semantic_retry.md`, 태그 `exp-freeze-v6-semretry`) | 잘린 150건 모두 JSON 앞 근거 문장에서 100 토큰에 끊김. 잘림이 대비·용어 쪽에 몰려 원 규칙만으로는 치우칠 수 있음 |
| 2026-11-13 | E9 반복 규칙(3회째 다섯 조건 모두)을 바꿔 **fixed-long 과 RAG 끔에서만 3회째** 실행, 나머지 세 조건은 2회 보고. D_run 은 기존 정의(두 조건은 3회 최대 차이), D_cond 는 3회 평균으로 계산(3회째 결과 전 결정). E9 LLM 판정과 E9-4 보조(390x844)는 수행하지 않음. 1·2회차 결과를 본 뒤의 수정임 (`analysis_plan_e9.md` 사전 수정, 태그 `exp-freeze-e9-v4`) | 발동한 세 건이 모두 fixed-long vs RAG 끔 쌍이고, 관련 조항 제공과 다른 조건의 차이(E9-2 1.000 대 0.033~0.133, E9-3 1.000 대 0.067~0.333)는 이미 실행 간 차이보다 큼. 예산 제약(연구 총액 5만 원) |
| 2026-11-14 | 사람 평가 뷰어 3개(A, B, 시범)에 'CSV 불러오기' 추가. 변경 전 뷰어는 `human_eval/viewer_backup_before_import/` 에 해시와 함께 보관, 저장 키(human_eval_A/B/pilot)·저장 구조·데이터·자동 저장·내보내기는 그대로(스크립트가 같음을 확인). 실제 Chromium 시험(`tests/test_viewer_import.py`): 변경 전 입력 유지, 내보내기→삭제→복원, 충돌 기본 유지, 다른 시트 거부 | 시범 단계에서 평가자가 약 10건 입력한 뒤 저장소 유실 대비가 필요했음(기존 뷰어는 불러오기 없음) |
| 2026-11-14 | 평가자 지침서 3절 보완(부재형 = '아니오' + 비고 '부재형', 값 부적절 = '예', 전반적 지적 = '판단 불가', 틀린 지적 = '아니오', 판단 불가 절에 한 줄). `docs/rater_guidelines.md` 는 exp-freeze-v5/v6 동결 목록에 있어 고치지 않고 `docs/rater_guidelines_v2.md` 로 만들었으며, rater_A/B·pilot_rater 의 `rater_guidelines.md` 복사본을 v2 로 바꿈 | 시범 중 '없음'을 지적하는 이슈의 판정 기준이 없었음(`rater_guidelines_review.md` 8번). 평가자의 시범 입력 약 10건은 v1 기준으로 입력되었을 수 있다 |
| 2026-11-14 | 평가자 간 비교 스크립트 `experiments/revision/human_eval_pilot_compare.py` 추가(열별 일치율, Cohen's kappa, 불일치 목록; 입력은 평가자 CSV 두 개만, 시범 `--merge same`, 본 평가 `--merge overlap`). 가짜 CSV 로만 시험, 실제 평가 결과에는 아직 실행하지 않음 | 시범 결과 비교 준비 |

| 2026-11-16 | 시범 평가자 A 가 I010a049fdb 의 '로그인 레이블 지적'을 '예'에서 '아니오'로 고쳐 같은 파일 이름으로 다시 내보냄(입력 실수 정정, 지침 3-1절 기준). 첫 비교 `human_eval/pilot_agreement.md` 는 그대로 두고, 고친 파일로 `human_eval/pilot_agreement_v2.md` 를 새로 만듦. 로그인 레이블 점검은 `human_eval/login_label_scan.md`. |
| 2026-11-16 | 추가 평가 세트(`human_eval/supp_label/`) 생성: 표본 규칙 부록(d594519) 뒤 표본 107건(1bf93c8) 승인. E4-mobile 대표 이슈 6건은 390x844 대신 1280x800 스크린샷으로 바꿈(연구자 지시). 지시 조건인 '같은 페이지·같은 문장 이슈가 있는 E1-R1/R2/R3b run' 은 6건 모두 없어서, 그 페이지에 이슈가 있는 첫 run(E1-R1) 의 스크린샷을 씀(세 run 의 스크린샷이 바이트까지 같음). 평가자별 순서 시드 20261127(A), 20261128(B) 추가. 강건판 비교 스크립트 `human_eval_compare_robust.py` 추가(원 스크립트 그대로). |
| 2026-11-16 | 평가자 A 본 평가 접수(`human_eval/intake_A.md`, 입력 CSV 는 읽기 전용·미커밋, SHA256 기록). 계획에 없던 자기 일치도 재판정 시트 `human_eval/rater_A_retest/` 추가(연구자 지시): A 444건 중 40건(시드 20261125), 순서 시드 20261126, 스크린샷 새 토큰, 입력 칸 비움, issue_id 는 본 시트와 같음. 표본 목록은 `human_eval/retest_sampling.json`. 비교 스크립트 `human_eval_retest_compare.py` 추가(가짜 CSV 로만 시험, 실행 안 함). |
| 2026-11-18 | 사람 평가 결과 접수(`human_eval/intake_all.md`): 지시문의 `results_A/`, `results_B/` 폴더가 없어 각 시트 폴더에 평가자가 둔 제출 CSV 4개를 그 자리에서 접수(읽기 전용·미커밋, SHA256 기록). A·B 시트의 issue_id 가 같아 key/ 를 읽지 않고 대응. 일치도에 계획에 없던 이슈 단위 부트스트랩 95% 구간(2000회, 시드 20261118)과 코드·화면·로그인 열 혼동 행렬을 덧붙임. 합의 시트는 지시한 열에 번호, issue_id, 판정 열, 스크린샷 경로를 더하고 `human_eval/consensus/` 에 스크린샷 사본과 페이지 코드(평가자 뷰어에서 가져옴)를 함께 둠. 층 정보 미사용. |
| 2026-11-18 | 연구자 요청으로 평가자 B 본 평가 CSV 의 비고 2칸(I76b83632d8, Id264e6a970)에 잘못 들어간 평가와 무관한 문자열을 지움(판정 값 불변, 두 이슈 모두 불일치 목록에 없어 일치도·합의 시트 영향 없음). `intake_all.md` 를 다시 만들고 정정 전후 SHA256 기록. 문자열이 기록에 남지 않도록 아직 push 하지 않은 직전 커밋을 고쳐 씀. |
| 2026-11-18 | 평가자 A 재판정(40건) 접수와 자기 일치도(`human_eval/retest_agreement_A.md`): 입력 CSV 읽기 전용·미커밋, SHA256 기록, 점검 문제 0건. 비교 스크립트 출력에 접수 절(0절)을 손으로 덧붙임. 정답 키·채점 결과 미사용. |
| 2026-11-18 | 합의 회의 결과 접수(`human_eval/intake_consensus.md`, 입력 읽기 전용·미커밋, 문제 0, 사유·답 어긋남 의심 2건 표시만). 불일치는 계획(10.4, 부록 6절)의 중재자 1명이 아니라 A·B 합의 회의로 정함. human_final 은 A 단독 240건을 source=A_only 로 따로 표시하고 주 결과와 합치지 않기로 함(계획 10.4 는 A 판정 사용·표시). 합의 후 일치율은 계산하지 않음. 재판정 강건 지표판 `retest_agreement.md` 추가(기존 `retest_agreement_A.md` 유지). E5b 는 계획 문서만(`e5b_plan.md`). |
| 2026-11-18 | E5b 실행(`human_eval/e5b/`, 보고 `reports/e5b_report.md`): 승인한 계획 `human_eval/e5b_plan.md` 의 사전 지정 이탈 8개와 실행 세부 사항을 `results/revision/e5b_deviations.md` (문서 날짜 2026-11-18)에 정리. 이 단계에서 처음 key/ 대응표와 issue_tables_merged 를 열었고, 채점기·키워드 사전·결과는 바꾸지 않음(10절 5항). |
| 2026-11-18 | E7 최종(`e7_final/`, 보고 `reports/e7_final_report.md`): 주 채점기를 키워드에서 의미 채점(재채점 병합)으로 바꿔 다시 계산. 사람 평가 E5b 에서 키워드 약점을 본 뒤의 결정이며, 비교 구조·지표·라벨 층·부트스트랩은 사전 지정과 기존 E7 그대로, 키워드는 보조 표로 나란히 둠. 채점기·사전은 바꾸지 않음(10절 5항). 기존 `e7/` 는 그대로, 채점기와 무관한 표는 다시 계산하지 않음. McNemar 는 다시 하지 않음. A2·A3 는 의미 채점이 없어 키워드 참고용만. |
| 2026-11-18 | E9 사람 평가(`human_eval/e9_eval/`): 부록 ca021ba 표본 203건이 150건 기준을 넘어 부록 2(c737a9c)로 안 걸린 이슈를 (페이지, 조건)당 1건으로 줄이고 평가자를 A 1인으로 바꿈. 연구자 지시로 `key/sample_selection.csv` 를 갱신(이전 판 09d6e91). 부록에 없던 행 순서 시드(본 20261205, 재평가 20261206)와 토큰 시드 'e9-tokens-20261203'을 key/e9_manifest.json 에 기록. 재평가 시트 issue_id 는 본 시트와 같음(안내문에 찾아보지 말라고 적음). 지침서 판정 규칙(구체 없음·일반 주장·DOM 불일치)은 이번에 정함. 비교 스크립트는 가짜 CSV 시험만. |
| 2026-11-18 | E9 사람 평가 범위 축소(부록 3, 94503ac): 평가자 시간 부족으로 정규식 걸린 52건만 평가, 안 걸린 86건과 재평가 20건은 실시 안 함(재현 누락 미검증, 자기 일치도 없음). 새 시트 `rater_A_e9_hit52/`(행 순서 시드 20261207, 부록에 없던 토큰 시드 'e9-hit52-tokens-20261207', issue_id 는 기존 시트와 같음). 기존 시트 `rater_A_e9/`, `rater_A_e9_retest/` 는 그대로 두고 쓰지 않음. 정밀도 단위를 (이슈, 잡은 유형) 쌍으로 정하고 보조 규칙은 쓰지 않음(부록 3). `e9_howto.md` 를 52건 기준으로 고치고 `e9_human_compare.py` 를 정밀도만 내도록 고침(둘 다 실제 결과 전, 비교 스크립트는 가짜 CSV 시험만). 부분 입력 9건 매핑 스크립트는 생성만 함. |
| 2026-11-18 | E9 사람 평가 보조 분석(부록 4, 210e56b): A 의 52건 판정을 본 뒤 연구자 지시로 추가한 사후 보조 분석. 표본 페이지 단위 검출 하한 (가) 유형 일치, (나) 유형 무시와 대조군 걸린 이슈의 A 판정을 층별로만 보고(`reports/e9_human_report_supp.md`). 주 결과(정규식 기준)를 대체하지 않으며 정규식·지표·동결 규칙은 바꾸지 않음. 대조군 '정규식' 칸은 세 유형 중 하나라도 걸린 쪽수로 정함. |
