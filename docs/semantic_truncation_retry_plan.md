# 의미 채점 잘림 150건 재채점 계획 (확정, 제출 전)

작성 2026-11-13, 같은 날 연구자 결정으로 갱신(주 분석 = 재채점 포함, max_tokens 800).
**아무것도 제출하지 않았다.** 3절 코드는 mock 시험만 거쳐 작성했다(`tests/test_semantic_grader_retry.py`).
사전 지정: `results/revision/analysis_plan_addendum_semantic_retry.md`.
제출은 연구자가 별도 PowerShell 창에서 한다. 이 세션은 ANTHROPIC_API_KEY 를 다루지 않는다.

근거: `results/revision/reports/semantic_truncation_report.md`
(잘림 150건 모두 출력 100 토큰에서 끊김, 모두 JSON 전에 설명 문장으로 시작, 용어·대비 쪽에 몰림).

## 1. 대상

- 목록: `results/revision/semantic_truncation_targets.csv` (150행, API 없이 grades.jsonl 에서 뽑음).
  열: out_id, retry_out_id, source_run, pass, input_fields, issue_id, orig_input_tokens.
- 대상 조건: 원 grades.jsonl 에서 `truncated == true` (stop_reason max_tokens). 다른 비성공은 없다(0건).

| 원 out_id | 재채점 out_id | pass | 입력 | 건수 |
|---|---|---|---|---|
| E1-R1-sem-p1 | E1-R1-sem-p1-retry | 1 | description + suggestion | 11 |
| E1-R1-sem-p2 | E1-R1-sem-p2-retry | 2 | description + suggestion | 14 |
| E1-R1-sem-desc-p1 | E1-R1-sem-desc-p1-retry | 1 | description | 19 |
| E1-R2-sem-p1 | E1-R2-sem-p1-retry | 1 | description + suggestion | 19 |
| E1-R3b-sem-p1 | E1-R3b-sem-p1-retry | 1 | description + suggestion | 22 |
| E2-A1-1-sem-p1 | E2-A1-1-sem-p1-retry | 1 | description + suggestion | 20 |
| E2-A1-2-sem-p1 | E2-A1-2-sem-p1-retry | 1 | description + suggestion | 17 |
| E2-A1-3-sem-p1 | E2-A1-3-sem-p1-retry | 1 | description + suggestion | 17 |
| E3-page-sem-p1 | E3-page-sem-p1-retry | 1 | description + suggestion | 5 |
| E3-oracle-sem-p1 | E3-oracle-sem-p1-retry | 1 | description + suggestion | 3 |
| E4-mobile-sem-p1 | E4-mobile-sem-p1-retry | 1 | description + suggestion | 3 |

출처: `results/revision/semantic_truncation_targets.csv`

## 2. 설정 (max_tokens 만 바꿈)

- 새 설정 파일 `scoring/grader_config_retry800.json`: `scoring/grader_config.json`(동결)을 그대로 복사하고
  `max_tokens` 100 → 800, `_notes` 에 재채점 사유 한 줄만 추가. 원 설정 파일은 고치지 않는다.
- 그대로 두는 것: model `claude-sonnet-5-5`, thinking `between_tools`, effort high, temperature 보내지 않음,
  fallback 끔, JUDGE_PROMPT v1(해시 d4567e76…), 입력 필드(원 out_id 와 같게: desc-p1 만 description),
  URL 접두어 제거·누출 검사(`semantic_grader_anthropic.build_input`), pass 번호(원 out_id 와 같게), 배치 경로.
- 800 의 근거 (연구자 결정): 잘린 응답이 평균 107자(약 100 토큰)에서 판단 근거를 쓰는 도중에 끊겼고,
  근거 전체가 250~400 토큰일 수 있어 300 은 일부가 다시 잘릴 수 있다. 800 은 상한일 뿐이고 실제 쓴 토큰만 과금된다.

## 3. 코드 (승인 후 새 파일로만 작성; 동결 파일은 고치지 않음)

`scoring/semantic_grader_batch.py` 의 submit 은 run 전체 이슈를 대상으로 하고, collect 의 완료 판정도 run 전체
기준이라 부분 재채점 폴더를 잠그지 못한다. 그래서 새 파일 `scoring/semantic_grader_retry.py` 를 둔다.

- `submit --orig-out-id X --targets CSV [--config scoring/grader_config_retry800.json] [--mock]`
  - 대상 = CSV 에서 out_id == X 인 issue_id. 폴더 `results/revision/semantic_scores/X-retry/` 새로 만듦
    (이미 있으면 오류: 같은 out_id 재사용 금지).
  - 요청 본문은 `semantic_grader_anthropic.build_input` / `build_request` 그대로(max_tokens 만 새 설정 값).
  - **입력 동일성 확인:** 각 이슈의 input_sha256 이 원 폴더 custom_ids.jsonl 의 input_sha256 과 같은지 확인하고,
    하나라도 다르면 제출하지 않고 멈춘다. prompt_sha256 도 같아야 한다(프롬프트 본문에는 max_tokens 가 없음).
  - run_meta.json 에 `retry_of: X`, `targets_sha256`, `config_sha256`(새 설정), `orig_config_sha256` 기록.
  - 402·429·크레딧 부족이면 재시도 없이 종료 코드 2 (기존 규칙과 같음).
- `status --out-id X-retry`: 기존 `semantic_grader_batch.cmd_status` 재사용.
- `collect --out-id X-retry`: 응답 해석은 기존 `record_from_message` 재사용(같은 상태·라벨 규칙).
  완료 판정 = 대상 issue_id 가 모두 최종 상태(ok, parse_error, refusal). 완료되면 잠근다.
  각 레코드에 `retry_of`, `orig_status`("parse_error"), `orig_truncated`(true) 를 붙인다.
- 원본 grades.jsonl 은 읽기만 한다(잠긴 폴더, 덮어쓰지 않음).
- 테스트 `tests/test_semantic_grader_retry.py` (mock, API 없음): 대상만 제출, 입력 해시 불일치 시 거부,
  max_tokens 만 다른 요청 본문, 완료 시 잠금, 원 폴더 무변경.

## 4. 재채점 결과의 처리 규칙 (결과를 보기 전에 정할 것)

- **재채점은 1회만 한다.** 800 에서도 잘리거나 파싱 실패이면 그 이슈는 '미해결'로 남고 다시 채점하지 않는다.
- 통합 표: 동결된 `scoring/issue_table.py` 는 그대로 두고, 새 파일 `scoring/issue_table_merged.py` 가
  기존 열 + 다음 열을 더한 표를 `results/revision/issue_tables_merged/{run}.csv` 로 쓴다.

| 열 | 값 |
|---|---|
| semantic_pass1_merged | 원 라벨(원 상태 ok) 또는 재채점 라벨(재채점 상태 ok) 또는 빈 칸 |
| semantic_pass1_source | original / retry / unresolved |
| semantic_pass1_filled_by_retry | 1 = 재채점으로 채운 건, 0 = 그 밖 |
| semantic_retry_status | 재채점 상태(ok, parse_error, refusal, api_error) 또는 빈 칸 |

- 보고 표에는 "재채점으로 채운 건" 수를 run·유형별 별도 열로 적는다.
- **연구자 결정 (2026-11-13, 재채점 결과를 보기 전):** (A) 를 택했다.
  - (A) 채택: 재채점으로 채운 표를 주 분석, 원 규칙(비성공 = 음성)과 잘림 페이지 제외를 민감도로 보고.
    이유: 잘림이 무작위가 아니고(용어·대비에 몰림) max_tokens 부족이라는 기술적 원인이 확인됨.
    재채점 라벨은 아직 보지 않았으므로 지금 정하면 결과를 보고 고르는 것이 아니다.
  - (B) 택하지 않음: 원 규칙(analysis_plan 10절 1항)을 주 분석으로 유지.
- 한계로 적을 것: 150건만 max_tokens 800 으로 채점되어 이슈마다 설정이 다르다. max_tokens 는 출력 상한일 뿐이고
  원래 성공한 응답은 상한 근처에 가지 않았지만(최대 21), 완전히 같은 조건은 아니다.
  대안: 전체 5,576건을 800 으로 다시 채점(배치 단가 기준 약 $5.3)하면 조건이 같아지지만 이 계획의 범위가 아니다.
- R1 pass1 대 pass2 일치와 description-only 민감도는 원 기준(이미 보고)과 재채점 기준을 둘 다 적는다.

## 5. 비용 추정

- 150건 × 입력 약 880 토큰 × $1/1M ≈ $0.13, 출력 최대 800 토큰 × $5/1M × 150 ≈ $0.60. **상한 약 $0.73.**
  실제 출력은 이보다 적을 것으로 예상(추정).

## 6. 사전 지정 문서에 필요한 변경

| 문서 | 변경 | 방법 |
|---|---|---|
| `results/revision/analysis_plan.md` | 동결(exp-freeze-v5 해시 67d8c9b7…). 고치지 않는다 | 새 파일 `results/revision/analysis_plan_addendum_semantic_retry.md` 에 4절 규칙, 주 분석 선택, max_tokens 800, 1회 한정을 적었다 |
| `results/revision/README.md` 계획 이탈 기록 | 행 1개 추가 | "의미 채점 max_tokens 100 에서 150건(2.7%) 잘림 → 해당 건만 max_tokens 800 으로 1회 재채점, 원 결과 보존" |
| `docs/grader_commands.md` | 재채점 절 추가 | 7절의 명령. 연구자 승인 후 붙인다 |
| `scoring/grader_config.json` | 변경 없음 | 해시 290b6ead… 유지. 재채점 폴더의 config_sha256 은 새 설정 파일 해시 |

- 동결 해시 영향: exp-freeze-v5 목록의 파일은 하나도 바뀌지 않으므로 `freeze_manifest.py --check` 는 그대로 통과해야 한다.
  JUDGE_PROMPT 해시도 그대로다. 새 파일(설정, 재채점기, 테스트, 통합 표 스크립트, 부록, 대상 CSV)은
  새 태그(예: `exp-freeze-v6-semretry`)의 목록에 넣고, 그 태그를 찍은 뒤에 제출한다.
- 기존 보고서(`semantic_scoring_report.md`, `semantic_truncation_report.md`)는 고치지 않고, 재채점 결과는 새 보고서로 낸다.

## 7. PowerShell 명령 (`docs/grader_commands.md` 5절에도 있음; 태그 `exp-freeze-v6-semretry` 이후 유효)

```powershell
cd <HOME>\OneDrive\Desktop\linkup-main
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
$s = Read-Host "ANTHROPIC_API_KEY" -AsSecureString
$env:ANTHROPIC_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
Remove-Variable s

$orig = "E1-R1-sem-p1","E1-R1-sem-p2","E1-R1-sem-desc-p1","E1-R2-sem-p1","E1-R3b-sem-p1",
        "E2-A1-1-sem-p1","E2-A1-2-sem-p1","E2-A1-3-sem-p1","E3-page-sem-p1","E3-oracle-sem-p1","E4-mobile-sem-p1"
$t = "results/revision/semantic_truncation_targets.csv"
$c = "scoring/grader_config_retry800.json"

# 제출 (11개 배치, 합계 150건)
foreach ($o in $orig) {
    python scoring/semantic_grader_retry.py submit --orig-out-id $o --targets $t --config $c
    if ($LASTEXITCODE -ne 0) { Write-Host "중단: $o (종료 코드 $LASTEXITCODE)"; break }
}

# 상태 확인 (API 조회만)
foreach ($o in $orig) { python scoring/semantic_grader_retry.py status --out-id "$o-retry" }

# 회수 (종료 코드 3 = 아직 처리 중 → 나중에 다시)
foreach ($o in $orig) { python scoring/semantic_grader_retry.py collect --out-id "$o-retry" }

Remove-Item Env:ANTHROPIC_API_KEY
```

- 끝나면 회수한 out_id 목록과 각 명령의 마지막 출력 줄을 Claude 세션에 알린다.

## 8. 진행 순서 (각 단계 연구자 승인)

1. 주 분석 선택(4절 A/B)과 max_tokens 값 확정. → 완료 (A, 800).
2. 3절 코드·테스트(mock) 작성, 부록·README 행 작성, 새 태그 → Claude 세션. → 완료.
3. 제출·상태·회수 → 연구자 창.
4. 통합 표(병합)와 재채점 보고서 → Claude 세션 (API 없음).
