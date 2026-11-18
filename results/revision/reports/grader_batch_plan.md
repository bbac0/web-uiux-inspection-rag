# 의미 채점 배치 실행 계획 (2026-11-13, 제출하지 않음)

- 경로 판정: 배치 (`results/revision/reports/grader_path_decision.md`, 호출당 표준가 $0.001911 × 8,874 = $16.96 > $10).
- 실행은 연구자의 별도 PowerShell 창에서만 한다. 키는 그 창의 `ANTHROPIC_API_KEY` 에만 넣는다(`docs/grader_commands.md` 0절).
- 설정 점검 결과: 배치 요청 본문은 동결된 표준 채점기의 `build_request` 로 만든다. 설정 값은 다음과 같다.
  - `model: claude-sonnet-5-5`, `max_tokens: 100`
  - `thinking: {"type": "between_tools"}`, `output_config: {"effort": "high"}`
  - temperature 없음, fallback 없음
  - 입력은 description(URL 접두어 제거) + suggestion. 민감도 채점만 `--input-fields description`.
  - pass 는 out_id 별로 고정하고(`--pass 1|2`), 재개는 `--resume`.
  - 설치된 SDK(anthropic 2.8.0)의 `messages.batches.create(requests=[{custom_id, params}])` 형식과 맞는다.
- `docs/grader_commands.md` 배치 항목에서 **틀린 곳은 없었다.** 빠져 있던 E3·E4 제출·회수 명령만 추가했다.

## 1단계: 1건짜리 확인 배치 (결과는 채점에 쓰지 않음)

```powershell
cd <HOME>\OneDrive\Desktop\linkup-main
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
$s = Read-Host "ANTHROPIC_API_KEY" -AsSecureString
$env:ANTHROPIC_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
Remove-Variable s

python scoring/semantic_grader_batch.py submit  --run-id E1-R1 --out-id batch-check-E1-R1 --pass 1 --limit 1
python scoring/semantic_grader_batch.py status  --out-id batch-check-E1-R1      # processing_status 가 ended 가 될 때까지 가끔 다시
python scoring/semantic_grader_batch.py collect --out-id batch-check-E1-R1      # 종료 코드 3 = 아직 처리 중
```

- 보내는 요청: custom_id `E1-R1__page_001__00__p1`. params 는 messages 를 빼면
  `{"model": "claude-sonnet-5-5", "max_tokens": 100, "thinking": {"type": "between_tools"}, "output_config": {"effort": "high"}}`
  이고, 프롬프트는 1,055자다.
- 끝나면 폴더 경로(`results/revision/semantic_scores/batch-check-E1-R1/`)를 Claude 세션에 알린다. Claude 는 다음만 확인한다.
  - `result_type = succeeded`
  - `stop_reason` 이 end_turn
  - text 블록이 있다(파싱 성공)
  - `model_version`
  - 입력·출력 토큰이 시험 호출 범위와 비슷하다
  - 라벨 값은 보지 않고 쓰지 않는다.
- 거부되면 사전 규칙에 따라 표준 경로로 확정한다. 거부란 배치 생성이 실패하거나 `result_type = errored`(invalid_request 등)인 경우다.

## 2단계: 본 제출 — 묶음 (가)

(가) = E1·A1 pass1 6개 run + E1-R1 pass2 + E1-R1 description-only 민감도. **E3·E4 를 (가)에 합칠 수 있다.** 생성 run 이 이미 끝났고,
채점 범위(pass1 만)와 경로(배치)가 같으며, out_id 별로 배치가 따로라서 묶음을 합쳐도 결과는 같다.

| 묶음 | out_id | 호출 수 (실제 대상 이슈) |
|---|---|---|
| (가) | E1-R1-sem-p1, E1-R2-sem-p1, E1-R3b-sem-p1 | 676 + 674 + 651 = 2,001 |
| (가) | E2-A1-1-sem-p1, E2-A1-2-sem-p1, E2-A1-3-sem-p1 | 544 + 579 + 534 = 1,657 |
| (가) | E1-R1-sem-p2 | 676 |
| (가) | E1-R1-sem-desc-p1 | 676 |
| **(가) 소계** | | **5,010** (배치 약 $4.79) |
| (가)에 합칠 경우 | E3-page-sem-p1, E3-oracle-sem-p1, E4-mobile-sem-p1 | 168 + 98 + 300 = 566 |
| **(가) + E3·E4** | | **5,576** (배치 약 $5.33) |
| (나) 나머지 | E9 본 실험 pass1 (E9 본 실험 후) | 약 2,912 (추정) |

출처: 호출 수는 `results/revision/runs/{run}/reports.jsonl` 의 대상 페이지 이슈 수, 비용은 시험 호출 평균 토큰 기준 배치 단가(표준가의 50%).

```powershell
# (가) 제출
python scoring/semantic_grader_batch.py submit --run-id E1-R1 --out-id E1-R1-sem-p1 --pass 1
python scoring/semantic_grader_batch.py submit --run-id E1-R1 --out-id E1-R1-sem-p2 --pass 2
python scoring/semantic_grader_batch.py submit --run-id E1-R1 --out-id E1-R1-sem-desc-p1 --pass 1 --input-fields description
foreach ($r in "E1-R2","E1-R3b","E2-A1-1","E2-A1-2","E2-A1-3") {
    python scoring/semantic_grader_batch.py submit --run-id $r --out-id "$r-sem-p1" --pass 1
    if ($LASTEXITCODE -ne 0) { Write-Host "중단: $r (종료 코드 $LASTEXITCODE)"; break }
}
# (선택) E3·E4 를 (가)에 합칠 때
foreach ($r in "E3-page","E3-oracle","E4-mobile") {
    python scoring/semantic_grader_batch.py submit --run-id $r --out-id "$r-sem-p1" --pass 1
    if ($LASTEXITCODE -ne 0) { Write-Host "중단: $r (종료 코드 $LASTEXITCODE)"; break }
}
```

## 3단계: 상태 확인과 회수

```powershell
$ids = "E1-R1-sem-p1","E1-R1-sem-p2","E1-R1-sem-desc-p1","E1-R2-sem-p1","E1-R3b-sem-p1",
       "E2-A1-1-sem-p1","E2-A1-2-sem-p1","E2-A1-3-sem-p1"
# E3·E4 를 합쳤다면: $ids += "E3-page-sem-p1","E3-oracle-sem-p1","E4-mobile-sem-p1"
foreach ($o in $ids) { python scoring/semantic_grader_batch.py status --out-id $o }
foreach ($o in $ids) { python scoring/semantic_grader_batch.py collect --out-id $o }   # 3 = 처리 중 → 나중에 다시
```

- 모든 이슈가 최종 상태(ok, parse_error, refusal)가 되면 폴더가 자동으로 잠긴다(`SHA256SUMS`).

## 4단계: 실패분 재개 (필요할 때만)

```powershell
# collect 결과에 api_error(errored/expired/canceled)가 있으면, 회수를 마친 뒤 그 out_id 만 --resume 으로 다시 제출
python scoring/semantic_grader_batch.py submit --run-id E1-R2 --out-id E1-R2-sem-p1 --pass 1 --resume
python scoring/semantic_grader_batch.py collect --out-id E1-R2-sem-p1
```

- 회수 결과의 errored 등이 20% 를 넘으면 경고가 나온다. 그때는 재제출 전에 Claude 세션에 알린다.
- 크레딧 부족·402·429 로 배치 생성이 거부되면 재시도 없이 종료 코드 2 로 멈춘다(`batches.jsonl` 에 기록).

## 5단계: Claude 세션에 알릴 것

- 끝난 out_id 목록과 각 collect 의 마지막 출력 줄. Claude 가 `grades.jsonl`, `summary.json` 을 읽어 집계한다.
