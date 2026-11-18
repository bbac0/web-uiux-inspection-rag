# 재채점 제출 상태 (크레딧 거부 후, 읽기만 함)

작성 2026-11-13. API 호출 없음. 폴더와 파일은 읽기만 했고 수정·삭제하지 않았다.
재개 동작 확인은 임시 폴더에서 mock(가짜 배치 클라이언트)으로만 했다.

## 1. `-retry` 폴더 현황

`results/revision/semantic_scores/` 아래 `-retry` 폴더는 **1개**다. 나머지 10개 out_id 의 `-retry` 폴더는 없다.

| 항목 | 값 |
|---|---|
| 폴더 | `E1-R1-sem-p1-retry` |
| 파일 | `batches.jsonl` (401 B), `run_meta.json` (2,408 B) |
| 없는 파일 | `custom_ids.jsonl`, `grades.jsonl`, `summary.json`, `SHA256SUMS` |
| 잠금 | 안 됨 (SHA256SUMS 없음, 파일 쓰기 가능) |
| run_meta: retry_of | E1-R1-sem-p1 |
| run_meta: started_utc | 2026-11-13T14:24:42.062+00:00 |
| run_meta: targets | 11건 |
| config_sha256 | 744c4442…, 현재 `grader_config_retry800.json` 해시와 같음 |
| targets_sha256 | 1582620a…, 현재 `semantic_truncation_targets.csv` 해시와 같음 |
| run_meta: sessions, complete | 없음 (제출 성공 기록 없음) |
| batches.jsonl 이벤트 | `submit_failed` 1건뿐 (14:24:48.969Z, 요청 11, billing_stop true) |
| 오류 문구 | 400 invalid_request_error, "Your credit balance is too low ..." |
| `submitted` 이벤트 | **없음** → 배치가 만들어지지 않았다 (custom_ids.jsonl 도 없음) |

출처:
- `results/revision/semantic_scores/E1-R1-sem-p1-retry/run_meta.json`
- `results/revision/semantic_scores/E1-R1-sem-p1-retry/batches.jsonl`

결론: 아무것도 제출되지 않았다는 이해가 기록과 맞다. 채점 결과가 하나도 없으므로 '재채점 1회' 규칙
(`analysis_plan_addendum_semantic_retry.md` 2절 3항)은 아직 쓰이지 않았다.
제출 루프는 첫 out_id 에서 종료 코드 2 로 멈췄으므로 나머지 10개는 시도되지 않았다.

## 2. 같은 out_id 로 다시 submit 할 때의 동작 (`scoring/semantic_grader_retry.py`)

| 경우 | 동작 | 근거 |
|---|---|---|
| `--resume` 없이 같은 명령 | **오류** (`RunExistsError`, 폴더 있음), 제출 안 함 | `lw.create_run_dir` |
| `--resume` 붙임 | 확인 후 최종 상태가 아닌 대상(지금 11건 전부)을 새 배치로 제출 | `cmd_submit` resume 절 |
| `--resume` 확인 항목 | 폴더 있음, SHA256SUMS 없음, config_sha256·targets 가 처음과 같음, 회수 안 된 배치 없음 | 위 절 |
| `submit_failed` 이벤트 | 무시됨 → '회수 안 된 배치'로 세지 않아 재개를 막지 않음 | `gb.batch_state` |
| 빈 폴더 | 별도 처리 없음: 새 제출은 오류, run_meta 가 없으면 `--resume` 도 실패 | `cmd_submit` |
| 다른 10개 out_id | 폴더가 없으므로 `--resume` 없이 처음 명령 그대로 제출 | |

mock 확인 (임시 폴더, API 없음): 크레딧 거부 → 종료 코드 2, 폴더에 `batches.jsonl`·`run_meta.json` 만 남음 →
같은 명령 재실행은 `RunExistsError` → `--resume` 재실행은 종료 코드 0, 3건 제출 → `collect` 후 잠금, `verify_run` 이상 없음,
batches.jsonl 이벤트 순서 `submit_failed`, `submitted`, `collected`.

문서와의 관계: `docs/semantic_truncation_retry_plan.md` 3절은 "이미 있으면 오류: 같은 out_id 재사용 금지",
`docs/grader_commands.md` 5절은 "`--resume` 은 배치 처리 오류(api_error)용" 이라고만 적었다. 크레딧 거부로 배치가 만들어지지 않은
경우에도 코드상 `--resume` 이 그대로 동작한다(위 mock 확인). 문서와 코드는 수정하지 않았다.

## 3. 다시 제출하기 전에 할 일 (PowerShell, 연구자 창)

1. Anthropic 콘솔에서 크레딧을 충전한다(재채점 상한 추정 약 $0.73, `analysis_plan_addendum_semantic_retry.md` 4절).
2. 폴더는 **지우지 않는 것을 권한다.** `--resume` 으로 같은 폴더에 이어 쓰면 거부 기록(`submit_failed`)이 남는다.
3. 0절 준비(가상환경, 키 입력) 후 아래를 실행한다.

```powershell
cd <HOME>\OneDrive\Desktop\linkup-main
$t = "results/revision/semantic_truncation_targets.csv"
$c = "scoring/grader_config_retry800.json"

# (1) 거부된 첫 out_id: 같은 폴더에 재개
python scoring/semantic_grader_retry.py submit --orig-out-id E1-R1-sem-p1 `
    --targets $t --config $c --resume

# (2) 나머지 10개: 폴더가 없으므로 --resume 없이
$rest = "E1-R1-sem-p2","E1-R1-sem-desc-p1","E1-R2-sem-p1","E1-R3b-sem-p1","E2-A1-1-sem-p1",
        "E2-A1-2-sem-p1","E2-A1-3-sem-p1","E3-page-sem-p1","E3-oracle-sem-p1","E4-mobile-sem-p1"
foreach ($o in $rest) {
    python scoring/semantic_grader_retry.py submit --orig-out-id $o --targets $t --config $c
    if ($LASTEXITCODE -ne 0) { Write-Host "중단: $o (종료 코드 $LASTEXITCODE)"; break }
}

# (3) 상태와 회수 (11개 모두)
$orig = @("E1-R1-sem-p1") + $rest
foreach ($o in $orig) { python scoring/semantic_grader_retry.py status --out-id "$o-retry" }
foreach ($o in $orig) { python scoring/semantic_grader_retry.py collect --out-id "$o-retry" }
```

- 루프 중간에 다시 크레딧 거부가 나면 그 out_id 폴더가 새로 생긴다.
  그 out_id 는 (1) 처럼 `--resume` 을 붙여 재개하고,
  그 뒤의 out_id 는 `--resume` 없이 이어서 낸다.
- (참고, 실행하지 않음) 폴더를 지우고 처음부터 내고 싶다면 아래 명령이 있다. 지우면 거부 기록이 사라지므로 권하지 않는다.
  ```powershell
  Remove-Item -Recurse -Force results\revision\semantic_scores\E1-R1-sem-p1-retry
  ```
  삭제한 뒤에는 (1) 에서 `--resume` 을 빼고 낸다.

출처:
- `scoring/semantic_grader_retry.py` (`cmd_submit`, `cmd_collect`)
- `scoring/semantic_grader_batch.py` (`batch_state`)
- `docs/semantic_truncation_retry_plan.md`, `docs/grader_commands.md` 5절
