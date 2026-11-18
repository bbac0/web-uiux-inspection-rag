# exp-freeze-v5 에 반영할 사전 지정 (2026-11-12 반영 완료 → analysis_plan.md 10절, README.md)

R1~A1 실행이 끝나고 사용자 승인을 받은 뒤 `analysis_plan.md` 와 `README.md` 에 그대로 옮기고 `exp-freeze-v5` 로 태그한다.
실행 중에는 동결 파일을 수정하지 않기 때문에 따로 적어 둔다. (결정일: 2026-11-12)

## analysis_plan.md 10절 (추가 예정)

### 10. 사전 지정 추가 — 의미 채점과 사람 평가 (2026-11-12, `exp-freeze-v5`)

1. **의미 채점 모델:** Anthropic `claude-sonnet-5-5` (provider anthropic). 범주 정의 프롬프트는 `JUDGE_PROMPT` v1 그대로.
   - **모델 사양상 temperature 지정 불가, 기본 샘플링 사용.** (claude-sonnet-5-5 는 기본값이 아닌 temperature 를 거부한다.)
   - 사고 설정: `thinking: {"type": "between_tools"}`, `output_config: {"effort": "high"}` 명시, `max_tokens` 100. 응답은 text 블록만 읽는다.
   - `stop_reason = max_tokens` 는 파싱 실패로 기록하고 건수를 보고한다. `stop_reason = refusal` 은 라벨 `refusal` 로 기록하고 건수를 보고한다.
     두 경우 모두 셀 예측에서는 해당 유형으로 세지 않는다(라벨 없음).
   - fallback(대체 모델)은 쓰지 않는다.
   - 입력: 이슈의 description(파이프라인이 붙인 `[URL]` 접두어 제거) + suggestion. 페이지 ID, 주입 라벨, 조건명은 넣지 않는다.
2. **반복 채점 (2026-11-12 수정):** 모든 run 의 이슈를 1회(pass1) 채점하며 **pass1 이 주 결과**다.
   **pass2 는 E1-R1 에만** 수행하고 안정성 보고용으로 쓴다(두 회차 라벨 일치율과 Cohen's kappa, 6분류 + refusal/파싱 실패를
   포함한 경우와 제외한 경우). 나머지 run(E1-R2, E1-R3b, E2-A1-1~3, E3, E4)은 pass1 만 수행한다. A2, A3 는 의미 채점을 하지 않는다(13항).
   - 채점 전 시험 호출: E1-R1 이슈 중 무작위 20건(시드 20261115)으로 호출당 입력/출력 토큰을 잰다(`scoring/probe_tokens.py`).
     라벨과 원본 응답은 기록하지 않고 결과로 쓰지 않는다. API 키 준비, R1~A1 종료, 사용자 승인 후 실행.
   - 중단·재개: 크레딧 소진·429·크레딧 부족 400 이 나오면 재시도 없이 즉시 멈추고 결과를 보존한다(폴더를 잠그지 않음).
     `--resume` 으로 (issue_id, pass) 가 이미 최종 상태(ok, parse_error, refusal)인 이슈를 건너뛰고 잇는다. 재개 사실은 `resume_log.jsonl`
     과 `run_meta.json` 의 sessions 에 남는다. 설정·입력 필드·pass 가 원래와 다르면 재개를 거부한다. 끝까지 채점하면 잠근다.
3. **민감도 채점 (유지):** E1-R1 에 한해 description 만 입력한 채점을 pass1 1회 추가로 실행하고, 주 채점(pass1)과의 일치도와
   셀 단위 지표 차이를 보고한다.
4. **사람 평가 방법:**
   - 평가자 A: 전체 시트(대조군 39 + 용어 위반 45 + 나머지 4개 유형 각 12, 총 132페이지의 E1-R1 대상 페이지 이슈 전체).
   - 평가자 B: A 의 층화 무작위 부분집합 약 60페이지(층 = 표본 추출 층: 대조군, 용어, 대비, 모바일, 버튼, 중복 ID).
     층화 기준은 주입 라벨과 대조군 여부뿐이며 채점 결과와 채점기 간 불일치는 표본 추출에 쓰지 않는다.
   - 질문: 6분류(5개 유형 + 해당 없음), (a) 코드(HTML/CSS)에 존재하는가, (b) 렌더링된 화면에서 보이는가, 비고(빈 칸).
   - 평가자 간 일치도는 B 부분집합에서 Cohen's kappa 로 계산한다. **A·B 판정이 다른 항목은 중재자 1명이 정하고, 중재자는
     주입 라벨과 채점 결과를 보지 않는다 (2026-11-12 승인).** 사람 기준 표준 = B 범위는 A·B 일치 항목 + 중재 결과,
     B 범위 밖은 A 판정 (A 판정만 쓴 범위임을 표에 표시).
   - **표본 추출 시드:** A 페이지 선택·토큰·행 섞기 20261112, B 표본 추출·행 섞기 20261113.
     (`experiments/revision/make_eval_sheets.py --seed-a 20261112 --seed-b 20261113`)
5. **사람 평가 결과를 본 뒤 채점 모델, 프롬프트, 설정, 키워드 사전을 바꾸지 않는다.**
6. **라벨 3층:** 모든 셀 단위 지표를 nominal / effective / guideline_grounded 세 층으로 계산한다
   (`experiments/revision/label_layers.py`).
   - guideline_grounded = 현재 색인된 문서(gov_guide.pdf, gov_check.pdf)에 그 결함을 위반으로 판정할 근거 조항이 있는가 (유형 단위).
     판정이 true 인 유형은 effective 라벨을 그대로 쓰고, false 인 유형의 셀은 이 층의 평가에서 제외한다(음성으로 세지 않음).
   - **판정 규칙 (2026-11-12 고정):** true 조건은 (a) 색인된 문서에 규범형('~한다')으로 쓰인 명시적 조항이 있고,
     (b) 특정 컴포넌트에 한정되지 않은 일반 조항이며, (c) 주입된 결함이 그 조항을 명백히 위반하는 것이다. '권장' 수준은 해당하지 않는다.
   - **연구자 확정 (2026-11-12, `guideline_grounding_decisions.csv` decision 칸):** 명도 대비 true, 모바일 레이아웃 false,
     버튼 잘림 false, 중복 ID false, 표준 용어 false. 버튼 잘림 메모: "컴포넌트 전용 규범문 있음(gov_guide 520쪽, 권장 수치 44px),
     사전 규칙 (b) 일반 조항 아님".
   - **사전 지정 민감도:** guideline_grounded 층의 모든 결과를 버튼 잘림 false(주)와 true(민감도) 양쪽으로 보고한다
     (`label_layers.load_labels(..., grounded_override={"Button Area Clipping": True})`). 계산만 바뀌므로 추가 API 비용은 없다.
     주 분석에서 이 층의 평가 셀은 명도 대비 200셀(양성 44)이고, 민감도 분석에서는 400셀(양성 64)이다.
   - `ground_truth.csv` 에 `guideline_grounded`, `guideline_grounded_candidate`, `label_guideline_grounded`(1280),
     `label_guideline_grounded_390` 열을 추가했다(기존 열은 그대로).
7. **세 번째 채점기 string_match (결정적, API 없음):** 이슈의 description 또는 suggestion 에 문자열 '접속하기' 가 포함되면
   표준 용어 위반을 탐지한 것으로 본다. 규칙은 이 한 줄이며 결과를 보고 수정하지 않는다(`scoring/string_match.py`).
   다른 4개 유형은 판정하지 않는다. 키워드 채점, 의미 채점(pass1), string_match 의 판정은 이슈 단위 표
   (`scoring/issue_table.py`, issue_id = `{run_id}:{page_id}:{issue_index}`)에 함께 모아 보고한다.
8. **E3 'oracle' 조건의 명칭 변경:** "정답 조항 주입"이 아니라 **"관련 조항 제공(related-clause provision)"** 조건이다.
   색인된 문서에 용어 위반의 직접 근거 조항이 없기 때문이다. 코드의 플래그 이름 `--query-mode oracle` 과 입력 파일
   `oracle_chunks.csv` 는 동결된 이름이라 그대로 두고, 문서와 표에서는 'related-clause (관련 조항 제공)' 로 부른다.
   청크 ID 는 연구자가 정한다.
9. **고정 질의 임베딩 1회 (사용자 승인 후):** gov_check.pdf 청크의 고정 질의 대비 최상위 거리와 순위를 계산하기 위해
   Gemini 임베딩 API 를 1회 호출하고(`gemini-embedding-001`, 프로덕션과 같은 embed_query), 호출을 로그에 남긴다.

10. **용어 유형의 세 가지 해석 (2026-11-12 사전 지정, 결과를 보기 전에 고정하고 결과를 보고 수정하지 않는다):**
    연구자가 gov_check 208쪽 "로그인 링크가 항상 '로그인' 화면으로 연결되고 있다" 항목을 확인한 결과, 이 항목은 링크의
    **목적지**를 규정하며(미준수 사례: 회원가입 화면으로 이동), 점검 요소 예시에 "로그인하러 가기"가 로그인 링크/버튼으로
    들어 있다. 따라서 '로그인 → 접속하기' 치환은 이 항목의 위반이 아니다. 용어 유형의 탐지는 다음 세 해석으로 따로 보고한다.
    - **언급 기반(mention-based):** 이슈의 description 또는 suggestion 에 문자열 '접속하기' 가 포함됨 (string_match, 7항).
      (이전 초안의 명칭 '엄격(strict)'을 2026-11-12 에 '언급 기반'으로 바꿨다. 규칙은 같다. 이 규칙은 '접속하기'를 지적 대상이 아니라
      단순히 언급한 이슈도 탐지로 센다.)
    - **레이블 모호성(label ambiguity):** 이슈가 로그인 링크 레이블의 문구나 의미 명확성을 지적함.
      사람 평가: 시트의 `login_link_label_concern` = 예. 의미 채점: pass1 라벨이 Standard Terminology Violation.
    - **해당 없음(not applicable):** 색인된 문서에 근거 조항이 없으므로 이 유형을 가이드라인 위반 탐지 지표에서 제외
      (guideline_grounded 층에서 false, 6항).
    - 논문 서술에서는 이 유형을 **"Login-link label deviation (formerly: Standard Terminology Violation)"** 로 부른다.
      코드, 기존 키워드 사전, 채점 프롬프트(JUDGE_PROMPT v1), 데이터 파일의 라벨 이름(Standard Terminology Violation)은 바꾸지 않는다.
11. **E3 관련 조항 제공(related-clause) 청크 (연구자 확정, 2026-11-12):** gov_check.pdf 29쪽 `b4c4ffd0-b39d-49ef-801d-487b44041b9b`
    (링크 레이블은 연결된 목적지 정보를 예측할 수 있는 내용으로 제공) + 208쪽 `87f08a4d-b8b6-427c-8fd5-2925b07b4d8a`
    (로그인 링크는 항상 '로그인' 화면으로 연결). 용어 위반 45 + 대조군 39 = 84페이지 모두에 같은 두 청크를 이 순서로 넣는다.
    `oracle_chunks.csv` 는 동결 파일이므로 R1~A1 종료 후 승인을 받아 `e3_oracle_prep.py expand --chunks <두 ID>` 로 만들고 새 태그를 붙인다.

12. **의미 채점 경로(배치 vs 표준) 규칙 (2026-11-12 사전 지정, 결과를 보기 전에 고정):**
    - 20건 시험 호출(표준 경로, `scoring/probe_tokens.py`, 시드 20261115)로 호출당 평균 입력·출력 토큰을 잰다.
    - 호출당 평균 비용 = 평균 입력 토큰 × $2/1M + 평균 출력 토큰 × $10/1M (표준가).
    - 전체 의미 채점 호출 수 = 핵심 채점(E1-R1~R3, E2-A1-1~3 의 pass1 + E1-R1 pass2 + E1-R1 description-only 민감도
      + E3 page·related-clause + E4) + E9 채점(본 실험 2회 pass1; 3회째는 규칙이 발동하면 추가). 범위는 13항(A2·A3·E9-4 의미 채점 없음,
      E9 pass2 없음)을 따른다. (2026-11-12 13항과 맞춤. E1-R3 은 aborted 로 제외하고 E1-R3b 가 그 자리를 대신한다.)
      호출 수는 각 run 의 대상 페이지 이슈 수로 계산하고, 아직 실행하지 않은 run 은 파일럿 평균 이슈 수(페이지당 3.2건)로 추정한다.
    - **총액(호출 수 × 호출당 평균 비용)이 $10 이하이면 모든 의미 채점을 표준 경로로, 초과하면 모든 의미 채점(pass1, pass2, 민감도 포함)을
      배치 경로(Message Batches)로 한다. 경로를 섞지 않는다.**
    - 배치 요청이 `thinking: {"type": "between_tools"}` 와 `output_config: {"effort": "high"}` 를 지원하지 않으면 표준 경로로 확정한다.
      (2026-11-12 문서 확인: 지원됨 — `docs/batch_api_review.md` §5. 배치 경로를 쓰게 되면 첫 배치 전에 1건짜리 확인 배치로 실제 수락 여부를 확인하고,
      거부되면 표준 경로로 확정한다.)
    - 시험 호출 20건은 표준 경로로 하며 채점 결과로 쓰지 않는다(라벨 미기록).
13. **의미 채점 범위 축소 (2026-11-12 사전 지정, 비용 절감):**
    - pass2 는 E1-R1 에서만 수행한다(2항과 같음). **E9 의 의미 채점은 pass1 만** 수행한다.
    - **E9-4 보조(390x844)는 결정적 정규식 규칙만** 쓰고 의미 채점을 하지 않는다.
    - **E2-A2, E2-A3 는 의미 채점을 하지 않는다.** 이 두 조건은 키워드 채점, string_match, 결정적 규칙으로만 E1-R1 과 비교한다
      (analysis_plan 5절의 E2 Holm 검정 가족 중 A2, A3 검정은 키워드 채점 기준으로 계산하고 그렇게 표시한다).
    - 의미 채점 대상 호출 수 (페이지당 3.2건 가정, 실행 후 실제 이슈 수로 다시 계산):

      | 대상 | 페이지 | 회차 | 호출 수 |
      |---|---:|---|---:|
      | E1-R1, R2, R3 pass1 | 200 × 3 | 1 | 1,920 |
      | E2-A1-1, A1-2, A1-3 pass1 | 200 × 3 | 1 | 1,920 |
      | E1-R1 pass2 | 200 | 1 | 640 |
      | E1-R1 description-only 민감도 | 200 | 1 | 640 |
      | E3 page, related-clause | 84 × 2 | 1 | 538 |
      | E4 | 95 | 1 | 304 |
      | **핵심 채점 소계** | | | **5,962** |
      | E9 본 실험 2회 pass1 (91 × 5조건 × 2) | 910 | 1 | 2,912 |
      | **합계 (E9 3회째 없음)** | | | **8,874** |
      | E9 3회째 (규칙 발동 시) | 455 | 1 | +1,456 → 10,330 |

    - 12항 규칙(시험 호출 평균 비용 × 위 합계, 표준가 $10 기준)은 그대로 적용한다. 합계에는 E9 3회째를 넣지 않고 판단하며,
      3회째가 발동하면 이미 정한 경로를 그대로 쓴다(경로를 섞지 않음).

14. **E1-R3 중단과 E1-R3b 대체 (2026-11-12 연구자 결정):**
    - E1-R3 은 160/200 페이지에서 Claude Code 의 메모리 부족 강제 종료로 중단되었다. `ABORTED.json` 으로 표시해 잠근 채 보존하며
      **분석에서 제외한다**(삭제하지 않음). 임시 스크린샷 3개의 목록·해시와 미기록 과금 가능 호출 추정은 `ABORTED.json` 의 amendments 에 기록했다.
    - 새 run_id **E1-R3b** 로 200페이지를 처음부터 다시 실행하고, analysis_plan 의 'E1-R3' 자리는 모두 E1-R3b 로 읽는다.
    - 재개 순서: E1-R3b → 관문(오류율 ≤ 5%, 파싱 실패 ≤ 2%) → E2-A1-3. 드라이버는 새 파일 `experiments/revision/run_e1_r3b_a1_3.py`
      (기존 순서 드라이버는 동결 상태 그대로).
    - 실행 조건 변경: **동시 실행 2건**(E1-R1 은 1건, E2-A1-1, E1-R2, E2-A1-2 는 4건이었음; 모두 사전 규칙 '4건 이하' 안).
      동시 실행 수는 지연시간에만 영향을 주며 지연시간 표는 순차 실행인 E1-R1 로만 만든다. 결과 표에는 run 별 동시 실행 수를 함께 적는다.
    - 각 run 시작 전 남은 물리 메모리가 5GB 미만이면 실행하지 않고 보고한다. 실행 중에는 기록 5건마다 남은 메모리를
      `results/revision/memory_logs/{run_id}.jsonl` 에 남긴다.

## analysis_plan.md 기존 문구 수정 예정

- 4절 표의 E3-oracle 행: `--query-mode oracle` (사용자가 지정한 정답 용어 규칙 청크 주입) →
  `--query-mode oracle` = **관련 조항 제공(related-clause provision)**: 연구자가 고른 관련 조항 청크를 직접 넣는다
  (색인된 문서에 용어 위반의 직접 근거 조항은 없음).
- 5절 E3 검정 문구의 'oracle' → 'related-clause'.

## README.md 추가 예정 문구

- E3 `--query-mode oracle` 은 문서상 **"관련 조항 제공(related-clause)"** 조건이다(정답 조항 주입이 아님). 플래그 이름은 동결되어 그대로다.
- 세 채점기: 키워드(description), 의미 채점(description + suggestion, Anthropic claude-sonnet-5-5, 2회), string_match('접속하기', 용어 위반만).
- 라벨 3층(nominal / effective / guideline_grounded)과 `ground_truth.csv` 의 추가 열 설명. guideline_grounded 판정 규칙(a~c)과 유형별 결정.
- string_match 해석의 명칭은 **언급 기반(mention-based)** 이다(규칙: description 또는 suggestion 에 '접속하기' 포함).
- 용어 유형 수치 메모: 논문 Table 3 의 17건은 run1 의 수치이고, 15건은 run2 의 대상 페이지 이슈 수(14페이지)다.
  15건 중 4건만 로그인 링크 레이블을 실제로 지적한다는 분류는 사전 지정 없이 읽고 나눈 값이다 — **exploratory, not pre-registered** —
  결과 표에는 쓰지 않는다.
- E3 관련 조항 제공(related-clause) 청크 확정: `b4c4ffd0-b39d-49ef-801d-487b44041b9b` (gov_check 29쪽, 739자),
  `87f08a4d-b8b6-427c-8fd5-2925b07b4d8a` (gov_check 208쪽, 748자). 두 청크는 목표 조항 외에 인접 항목을 함께 담고 있다
  (29쪽: 링크 체크리스트 1~10과 버튼 그룹 항목, 208쪽: 로그인 기능 찾기 1의 점검 절차와 3의 제목). 두 청크 본문 합계는 1,487자로
  고정 질의 4청크의 본문 합계 1,552자와 비슷하다. 프롬프트에 들어가는 형태(`[파일 - N페이지]` 머리글 포함)로는 1,538자 대 1,653자다. `oracle_chunks.csv` 는 R1~A1 종료 후 승인을 받아 새 태그와 함께 만든다.

- 의미 채점(`scoring/semantic_grader_anthropic.py`, 설정 `scoring/grader_config.json`)은 이슈의 **description + suggestion** 을 입력으로 쓴다
  (사람 평가자가 시트에서 보는 정보와 같게). **키워드 채점은 기존 정의대로 description 만 쓴다.** 두 채점기의 입력 범위가 다르다.
- 의미 채점 입력에서는 `[http://…]` 접두어(파이프라인이 붙인 페이지 URL, 페이지 ID 포함)를 지운다.
  **1차 평가(run1)의 의미 채점(`paper_results/run1/semantic_scoring_run1.json`, Gemini)은 이 접두어를 지우지 않고 보냈다.**
- 의미 채점은 temperature 를 보내지 않는다(모델 사양상 지정 불가). pass1 이 주 결과이며 pass2 는 E1-R1 에서만 한다(2항·13항).
- anthropic SDK 는 R1~A1 종료 후 사용자 승인을 받아 설치하고 버전을 실행 기록에 남긴다.
