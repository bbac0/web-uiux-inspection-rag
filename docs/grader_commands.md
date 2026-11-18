# 의미 채점 실행 명령 (PowerShell, 연구자가 별도 창에서 직접 실행)

작성 2026-11-13. 의미 채점(Anthropic `claude-sonnet-5-5`)은 Claude Code 세션이 아니라 **연구자가 연 별도 PowerShell 창**에서만 실행한다.
API 키는 그 창의 환경변수 `ANTHROPIC_API_KEY` 에만 넣는다. 채점기는 키를 이 환경변수에서만 읽고 출력·기록하지 않는다.
**명령줄 인자나 파일에 키를 쓰지 않는다.**

## 0. 준비 (창을 열 때마다)

```powershell
cd <HOME>\OneDrive\Desktop\linkup-main
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # 이 창에서만 Activate.ps1 실행 허용
.\venv\Scripts\Activate.ps1
python -c "import anthropic; print(anthropic.__version__)"    # 2.8.0 (results/revision/env_anthropic_sdk.json 과 같아야 함)

# 키 입력: 화면과 명령 기록에 남지 않게 SecureString 으로 받아 이 창의 환경변수에만 넣는다
$s = Read-Host "ANTHROPIC_API_KEY" -AsSecureString
$env:ANTHROPIC_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
Remove-Variable s
```

끝나면 `Remove-Item Env:ANTHROPIC_API_KEY` 로 지우거나 창을 닫는다.

## 1. 20건 시험 호출 (표준 경로, 결과로 쓰지 않음)

```powershell
python scoring/probe_tokens.py --run-id E1-R1 --out-id probe-E1-R1 --n 20 --seed 20261115
```

- 결과 폴더: `results/revision/semantic_scores/probe-E1-R1/`
  - `probe.jsonl` (호출별 토큰, stop_reason, 모델 버전, 지연시간. 라벨과 원본 응답은 기록하지 않음)
  - `summary.json` (평균 입력/출력 토큰, stop_reason 분포, 모델 버전)
- 끝나면 이 폴더 경로를 Claude Code 세션에 알려 준다. Claude 가 읽어서 호출당 표준가 비용과 경로 판정(호출 수 8,874 기준, $10)을 보고한다.
- 402·429·크레딧 부족 오류가 나면 즉시 멈추고 폴더를 그대로 둔다.

## 2. 본 채점 대상 (analysis_plan 10절 2·3·13항)

| out_id | run | pass | 입력 | 비고 |
|---|---|---|---|---|
| `E1-R1-sem-p1` | E1-R1 | 1 | description + suggestion | 주 결과 |
| `E1-R1-sem-p2` | E1-R1 | 2 | description + suggestion | 안정성 (R1 만) |
| `E1-R1-sem-desc-p1` | E1-R1 | 1 | description 만 (`--input-fields description`) | 민감도 (R1 만) |
| `E1-R2-sem-p1`, `E1-R3b-sem-p1` | E1-R2, E1-R3b | 1 | description + suggestion | |
| `E2-A1-1-sem-p1`, `E2-A1-2-sem-p1`, `E2-A1-3-sem-p1` | E2-A1-1~3 | 1 | description + suggestion | |
| `E3-page-sem-p1`, `E3-oracle-sem-p1` | E3-page, E3-oracle(related-clause) | 1 | description + suggestion | 해당 run 이 끝난 뒤 |
| `E4-mobile-sem-p1` | E4-mobile | 1 | description + suggestion | 해당 run 이 끝난 뒤 |

- A2, A3 와 E9-4 보조는 의미 채점을 하지 않는다. E1-R3(aborted)은 채점하지 않는다.
- 한 out_id 는 한 경로(표준 또는 배치)로만 채점한다. 시험 호출 결과로 정한 경로를 모든 채점에 쓴다(섞지 않음).
- 결과 폴더: `results/revision/semantic_scores/{out_id}/` (`grades.jsonl`, `run_meta.json`, `summary.json`; 끝까지 채점하면 잠김)

## 3-A. 표준 경로 (총액 $10 이하로 판정된 경우)

```powershell
python scoring/semantic_grader_anthropic.py --run-id E1-R1 --out-id E1-R1-sem-p1 --pass 1
python scoring/semantic_grader_anthropic.py --run-id E1-R1 --out-id E1-R1-sem-p2 --pass 2
python scoring/semantic_grader_anthropic.py --run-id E1-R1 --out-id E1-R1-sem-desc-p1 --pass 1 --input-fields description
foreach ($r in "E1-R2","E1-R3b","E2-A1-1","E2-A1-2","E2-A1-3") {
    python scoring/semantic_grader_anthropic.py --run-id $r --out-id "$r-sem-p1" --pass 1
    if ($LASTEXITCODE -ne 0) { Write-Host "중단: $r (종료 코드 $LASTEXITCODE)"; break }
}
```

- **중단된 경우(402·429·크레딧 부족, 창 닫힘 등) 같은 명령에 `--resume` 을 붙여 잇는다.** 이미 최종 상태(ok, parse_error, refusal)인 이슈는 건너뛴다.
  ```powershell
  python scoring/semantic_grader_anthropic.py --run-id E1-R1 --out-id E1-R1-sem-p1 --pass 1 --resume
  ```
  설정·입력 필드·pass 가 처음과 다르면 재개를 거부한다. 재개 기록은 `resume_log.jsonl` 과 `run_meta.json` 의 sessions 에 남는다.
- E3, E4 는 생성 run 이 끝난 뒤 같은 형식으로: `--run-id E3-page --out-id E3-page-sem-p1 --pass 1` 등.

## 3-B. 배치 경로 (총액 $10 초과로 판정된 경우, Message Batches, 50% 단가)

**먼저 1건짜리 확인 배치(연구자 승인 후, 결과는 쓰지 않음):** 배치가 `thinking: between_tools` 와 `output_config.effort=high` 를 받는지 확인한다.
```powershell
python scoring/semantic_grader_batch.py submit  --run-id E1-R1 --out-id batch-check-E1-R1 --pass 1 --limit 1
python scoring/semantic_grader_batch.py status  --out-id batch-check-E1-R1
python scoring/semantic_grader_batch.py collect --out-id batch-check-E1-R1
```
거부되면(배치 생성 실패 또는 결과가 errored/invalid_request) 사전 규칙에 따라 표준 경로로 확정한다.

**본 채점:** run 마다 제출 → 상태 확인 → 회수. 제출은 즉시 끝나고 처리는 보통 1시간 안(최대 24시간)이다.
```powershell
python scoring/semantic_grader_batch.py submit --run-id E1-R1 --out-id E1-R1-sem-p1 --pass 1
python scoring/semantic_grader_batch.py submit --run-id E1-R1 --out-id E1-R1-sem-p2 --pass 2
python scoring/semantic_grader_batch.py submit --run-id E1-R1 --out-id E1-R1-sem-desc-p1 --pass 1 --input-fields description
foreach ($r in "E1-R2","E1-R3b","E2-A1-1","E2-A1-2","E2-A1-3") {
    python scoring/semantic_grader_batch.py submit --run-id $r --out-id "$r-sem-p1" --pass 1
    if ($LASTEXITCODE -ne 0) { Write-Host "중단: $r (종료 코드 $LASTEXITCODE)"; break }
}

# 처리 상태 확인 (여러 번 해도 됨, API 조회만)
python scoring/semantic_grader_batch.py status --out-id E1-R1-sem-p1

# 회수: 끝난 배치의 결과를 grades.jsonl 에 붙인다. 종료 코드 3 = 아직 처리 중 → 나중에 다시 실행
$ids = "E1-R1-sem-p1","E1-R1-sem-p2","E1-R1-sem-desc-p1","E1-R2-sem-p1","E1-R3b-sem-p1","E2-A1-1-sem-p1","E2-A1-2-sem-p1","E2-A1-3-sem-p1"
foreach ($o in $ids) { python scoring/semantic_grader_batch.py collect --out-id $o }

# (2026-11-13 추가) E3·E4: 생성 run 이 끝났으므로 같은 방식으로 제출·회수한다 (pass1 만)
foreach ($r in "E3-page","E3-oracle","E4-mobile") {
    python scoring/semantic_grader_batch.py submit --run-id $r --out-id "$r-sem-p1" --pass 1
    if ($LASTEXITCODE -ne 0) { Write-Host "중단: $r (종료 코드 $LASTEXITCODE)"; break }
}
foreach ($o in "E3-page-sem-p1","E3-oracle-sem-p1","E4-mobile-sem-p1") { python scoring/semantic_grader_batch.py collect --out-id $o }
```

- 묶음과 단계별 순서는 `results/revision/reports/grader_batch_plan.md` 를 따른다(확인 배치 → 결과 확인 → 본 제출).
- 경로 판정 근거: `results/revision/reports/grader_path_decision.md` (호출당 표준가 × 8,874 = $16.96 > $10 → 배치).

- **재개(`--resume`):** 회수 결과에 errored/expired/canceled(상태 api_error)가 있거나, 제출이 중간에 멈춘 경우 같은 submit 명령에 `--resume` 을 붙인다.
  최종 상태가 아닌 이슈만 새 배치로 다시 낸다. 회수하지 않은 배치가 남아 있으면 재개를 거부하므로 먼저 `collect` 를 실행한다.
  ```powershell
  python scoring/semantic_grader_batch.py submit --run-id E1-R1 --out-id E1-R1-sem-p1 --pass 1 --resume
  python scoring/semantic_grader_batch.py collect --out-id E1-R1-sem-p1
  ```
- 회수한 결과에서 errored 등이 20% 를 넘으면 경고를 출력한다. 그때는 재제출 전에 Claude 세션에 알린다.
- 배치 생성이 크레딧 부족·402·429 로 거부되면 재시도 없이 종료 코드 2 로 멈춘다(`batches.jsonl` 에 기록).
- 배치 폴더의 추가 파일: `batches.jsonl`(제출·회수 기록, batch_id), `custom_ids.jsonl`(custom_id ↔ issue_id). 레코드에는 `mode: "batch"`,
  `pricing: "batch"`, `batch_id`, `custom_id`, `result_type` 이 붙고 요청 단위 지연시간은 null 이다.
- 결과는 Anthropic 쪽에서 생성 후 29일 동안 받을 수 있다. 그 안에 `collect` 한다.

## 4. 실행 후 Claude 세션에 알릴 것

- 시험 호출: `results/revision/semantic_scores/probe-E1-R1/` 경로.
- 본 채점: 끝난 out_id 목록과 각 명령의 마지막 출력 줄(종료 코드). Claude 가 `grades.jsonl` 과 `summary.json` 을 읽어 집계한다.

## 5. 잘림 건 재채점 (2026-11-13 추가, max_tokens 800, 1회 한정)

사전 지정: `results/revision/analysis_plan_addendum_semantic_retry.md`, 계획: `docs/semantic_truncation_retry_plan.md`.
태그 `exp-freeze-v6-semretry` 이후에 실행한다. 0절 준비(가상환경, 키 입력)를 먼저 한다.
대상 150건 = `results/revision/semantic_truncation_targets.csv`. 설정 = `scoring/grader_config_retry800.json`
(원 설정과 max_tokens 만 다름). 결과 폴더 = `results/revision/semantic_scores/{원 out_id}-retry/` (원 폴더는 읽기만 함).

```powershell
$orig = "E1-R1-sem-p1","E1-R1-sem-p2","E1-R1-sem-desc-p1","E1-R2-sem-p1","E1-R3b-sem-p1",
        "E2-A1-1-sem-p1","E2-A1-2-sem-p1","E2-A1-3-sem-p1","E3-page-sem-p1","E3-oracle-sem-p1","E4-mobile-sem-p1"
$t = "results/revision/semantic_truncation_targets.csv"
$c = "scoring/grader_config_retry800.json"

# 제출 (11개 배치, 합계 150건). 입력 sha256 이 원 채점과 다르거나 설정이 max_tokens 외에 다르면 제출하지 않고 멈춘다
foreach ($o in $orig) {
    python scoring/semantic_grader_retry.py submit --orig-out-id $o --targets $t --config $c
    if ($LASTEXITCODE -ne 0) { Write-Host "중단: $o (종료 코드 $LASTEXITCODE)"; break }
}

# 상태 확인 (API 조회만, 여러 번 해도 됨)
foreach ($o in $orig) { python scoring/semantic_grader_retry.py status --out-id "$o-retry" }

# 회수 (종료 코드 3 = 아직 처리 중 → 나중에 다시). 대상이 모두 최종 상태이면 폴더를 잠근다
foreach ($o in $orig) { python scoring/semantic_grader_retry.py collect --out-id "$o-retry" }

Remove-Item Env:ANTHROPIC_API_KEY
```

- 재채점은 1회만 한다. 다시 잘리거나 파싱 실패인 건은 최종(미해결)이며 다시 내지 않는다.
- 배치 처리 오류(errored/expired/canceled → api_error)만 같은 submit 명령에 `--resume` 을 붙여 다시 낸다.
- 402·429·크레딧 부족이면 종료 코드 2 로 멈춘다. 같은 out_id 폴더가 이미 있으면 새로 제출하지 않는다(오류).
- 끝나면 회수한 out_id 목록과 각 명령의 마지막 출력 줄을 Claude 세션에 알린다.
