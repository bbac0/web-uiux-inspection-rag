# 의미 채점 회수 결과 기술 집계

작성: `experiments/revision/semantic_scoring_report.py` (API 호출 없음). 기술 집계만 하며 통계 검정은 하지 않는다.
채점 모델 요청값 `claude-sonnet-5-5`, JUDGE_PROMPT v1, 입력 description + suggestion
(민감도 폴더만 description). 연구자가 별도 창에서 배치를 제출하고 회수했다.
사람 평가 시트는 만들지 않았다.

상태 정의: 성공 = status ok. 잘림 = stop_reason max_tokens(status parse_error, truncated true).
파싱 실패 = parse_error 중 잘림이 아닌 것. refusal, api_error 는 status 그대로.

## 1. out_id 별 채점 이슈 수와 상태

| out_id | 원 run | pass | 입력 | 이슈 | run 이슈 | 성공 | 파싱 실패 | refusal | 잘림 | api_error |
|---|---|---|---|---|---|---|---|---|---|---|
| E1-R1-sem-desc-p1 | E1-R1 | 1 | desc | 676 | 676 | 657 | 0 | 0 | 19 | 0 |
| E1-R1-sem-p1 | E1-R1 | 1 | desc+sugg | 676 | 676 | 665 | 0 | 0 | 11 | 0 |
| E1-R1-sem-p2 | E1-R1 | 2 | desc+sugg | 676 | 676 | 662 | 0 | 0 | 14 | 0 |
| E1-R2-sem-p1 | E1-R2 | 1 | desc+sugg | 674 | 674 | 655 | 0 | 0 | 19 | 0 |
| E1-R3b-sem-p1 | E1-R3b | 1 | desc+sugg | 651 | 651 | 629 | 0 | 0 | 22 | 0 |
| E2-A1-1-sem-p1 | E2-A1-1 | 1 | desc+sugg | 544 | 544 | 524 | 0 | 0 | 20 | 0 |
| E2-A1-2-sem-p1 | E2-A1-2 | 1 | desc+sugg | 579 | 579 | 562 | 0 | 0 | 17 | 0 |
| E2-A1-3-sem-p1 | E2-A1-3 | 1 | desc+sugg | 534 | 534 | 517 | 0 | 0 | 17 | 0 |
| E3-oracle-sem-p1 | E3-oracle | 1 | desc+sugg | 98 | 98 | 95 | 0 | 0 | 3 | 0 |
| E3-page-sem-p1 | E3-page | 1 | desc+sugg | 168 | 168 | 163 | 0 | 0 | 5 | 0 |
| E4-mobile-sem-p1 | E4-mobile | 1 | desc+sugg | 300 | 300 | 297 | 0 | 0 | 3 | 0 |
| batch-check-E1-R1 | E1-R1 | 1 | desc+sugg | 1 | 676 | 1 | 0 | 0 | 0 | 0 |
| 합계 | | | | 5577 | | 5427 | 0 | 0 | 150 | 0 |

run 이슈 = `scoring/issue_table.py` 가 원 run reports.jsonl 에서 뽑은 대상 페이지 이슈 수(대조용).
batch-check-E1-R1 은 배치 경로 확인용 1건(잠금 없음)이며 결과 분석에는 쓰지 않는다.
모든 레코드의 batch result_type 은 succeeded 였다.

출처:
- `results/revision/semantic_scores/{out_id}/grades.jsonl`
- `results/revision/semantic_scores/{out_id}/summary.json`

## 2. 모델 버전 문자열과 호출 날짜

| out_id | batch_id | 제출 (UTC) | 회수 (UTC) | 요청 수 | 응답 model |
|---|---|---|---|---|---|
| E1-R1-sem-desc-p1 | 7wdouvnA | 03:24:36 | 03:29:25 | 676 | claude-sonnet-5-5 |
| E1-R1-sem-p1 | aLGigELg | 03:24:18 | 03:29:13 | 676 | claude-sonnet-5-5 |
| E1-R1-sem-p2 | 3Lk88HaG | 03:24:27 | 03:29:19 | 676 | claude-sonnet-5-5 |
| E1-R2-sem-p1 | HPV8rhki | 03:24:48 | 03:29:32 | 674 | claude-sonnet-5-5 |
| E1-R3b-sem-p1 | bz3CaWNe | 03:24:55 | 03:29:39 | 651 | claude-sonnet-5-5 |
| E2-A1-1-sem-p1 | QpYzQ9ZP | 03:25:01 | 03:29:47 | 544 | claude-sonnet-5-5 |
| E2-A1-2-sem-p1 | zSrw3rJs | 03:25:08 | 03:29:53 | 579 | claude-sonnet-5-5 |
| E2-A1-3-sem-p1 | 4visXYbe | 03:25:15 | 03:29:59 | 534 | claude-sonnet-5-5 |
| E3-oracle-sem-p1 | cueHSDHG | 03:25:41 | 03:30:46 | 98 | claude-sonnet-5-5 |
| E3-page-sem-p1 | XZR5sz5d | 03:25:35 | 03:30:40 | 168 | claude-sonnet-5-5 |
| E4-mobile-sem-p1 | mxspWgai | 03:25:47 | 03:30:52 | 300 | claude-sonnet-5-5 |
| batch-check-E1-R1 | ZwYLmzmn | 03:19:44 | 03:23:26 | 1 | claude-sonnet-5-5 |

batch_id 는 끝 8자만 적었다. 제출·회수 시각은 batches.jsonl, 응답 model 은 grades.jsonl 의
model_version(batches.jsonl 에는 모델 문자열이 없음). 제출·회수 열은 시각만 적었다.
응답 model 문자열 전체: claude-sonnet-5-5 (모든 레코드). 모든 호출 날짜는 2026-11-13 (UTC).

출처:
- `results/revision/semantic_scores/{out_id}/batches.jsonl`
- `results/revision/semantic_scores/{out_id}/grades.jsonl`

## 3. 비용 (배치 단가 입력 $1/1M, 출력 $5/1M)

| out_id | 입력 토큰 | 출력 토큰 | 호출당 입력 | 호출당 출력 | 비용 (USD) |
|---|---|---|---|---|---|
| E1-R1-sem-desc-p1 | 524164 | 10338 | 775.4 | 15.3 | 0.5759 |
| E1-R1-sem-p1 | 594379 | 9610 | 879.3 | 14.2 | 0.6424 |
| E1-R1-sem-p2 | 594379 | 9880 | 879.3 | 14.6 | 0.6438 |
| E1-R2-sem-p1 | 591505 | 10291 | 877.6 | 15.3 | 0.6430 |
| E1-R3b-sem-p1 | 572733 | 10306 | 879.8 | 15.8 | 0.6243 |
| E2-A1-1-sem-p1 | 476232 | 9293 | 875.4 | 17.1 | 0.5227 |
| E2-A1-2-sem-p1 | 505911 | 9447 | 873.8 | 16.3 | 0.5531 |
| E2-A1-3-sem-p1 | 466373 | 8974 | 873.4 | 16.8 | 0.5112 |
| E3-oracle-sem-p1 | 84005 | 1714 | 857.2 | 17.5 | 0.0926 |
| E3-page-sem-p1 | 145864 | 2466 | 868.2 | 14.7 | 0.1582 |
| E4-mobile-sem-p1 | 264521 | 4094 | 881.7 | 13.6 | 0.2850 |
| batch-check-E1-R1 | 895 | 17 | 895.0 | 17.0 | 0.0010 |
| 합계 | 4820961 | 86430 | | | 5.2531 |

잘림 레코드도 토큰이 과금되므로 포함했다. 표준 경로 시험 호출(probe-E1-R1, 20건)은 이전 보고
(`clean_report_a2_e4.md`)에 있으며 이 합계에 넣지 않았다. 실제 청구액은 Anthropic 콘솔 기준으로 확인해야 한다.

출처:
- `results/revision/semantic_scores/{out_id}/grades.jsonl`

## 4. E1-R1 pass1 대 pass2 라벨 일치

| 범위 | 이슈 | 일치 | 일치율 | Cohen's kappa |
|---|---|---|---|---|
| 포함: 6분류 + 잘림/파싱 실패/refusal 을 별도 범주로 | 676 | 671 | 0.993 | 0.985 |
| 제외: 두 회차 모두 성공한 이슈만 (6분류) | 661 | 661 | 1.000 | 1.000 |

출처:
- `results/revision/semantic_scores/E1-R1-sem-p1/grades.jsonl`
- `results/revision/semantic_scores/E1-R1-sem-p2/grades.jsonl`

불일치 쌍 (pass1 → pass2, 건수):

| pass1 | pass2 | 건수 |
|---|---|---|
| None | truncated | 3 |
| Poor Contrast Ratio | truncated | 1 |
| truncated | Poor Contrast Ratio | 1 |

출처:
- `results/revision/semantic_scores/E1-R1-sem-p1/grades.jsonl`
- `results/revision/semantic_scores/E1-R1-sem-p2/grades.jsonl`

## 5. E1-R1 pass1 (description + suggestion) 대 description-only 민감도

| 범위 | 이슈 | 일치 | 일치율 |
|---|---|---|---|
| 포함: 비성공 상태를 별도 범주로 | 676 | 666 | 0.985 |
| 제외: 두 채점 모두 성공 | 657 | 655 | 0.997 |

출처:
- `results/revision/semantic_scores/E1-R1-sem-p1/grades.jsonl`
- `results/revision/semantic_scores/E1-R1-sem-desc-p1/grades.jsonl`

불일치 쌍 (pass1 → description-only, 건수):

| pass1 | desc-only | 건수 |
|---|---|---|
| None | truncated | 7 |
| None | Standard Terminology Violation | 2 |
| Poor Contrast Ratio | truncated | 1 |

출처:
- `results/revision/semantic_scores/E1-R1-sem-p1/grades.jsonl`
- `results/revision/semantic_scores/E1-R1-sem-desc-p1/grades.jsonl`

## 6. 이슈 단위 통합 표: 키워드 대 의미 채점 pass1 (유형별)

키워드 = description 다중 라벨(`evaluate_performance_v5.CATEGORY_PHRASES`), 의미 = pass1 단일 라벨.
의미 채점이 성공이 아닌 이슈는 어느 유형으로도 세지 않았다. 일치 = 둘 다 양성 + 둘 다 음성.

| 원 run | 유형 | 이슈 | 둘 다 양성 | 둘 다 음성 | 키워드만 | 의미만 | 일치 | 불일치 |
|---|---|---|---|---|---|---|---|---|
| E1-R1 | 대비 | 676 | 47 | 624 | 3 | 2 | 671 | 5 |
| E1-R1 | 모바일 | 676 | 57 | 578 | 41 | 0 | 635 | 41 |
| E1-R1 | 버튼 | 676 | 47 | 623 | 0 | 6 | 670 | 6 |
| E1-R1 | 용어 | 676 | 0 | 659 | 17 | 0 | 659 | 17 |
| E1-R1 | 중복 ID | 676 | 34 | 637 | 0 | 5 | 671 | 5 |
| E1-R2 | 대비 | 674 | 45 | 623 | 5 | 1 | 668 | 6 |
| E1-R2 | 모바일 | 674 | 57 | 576 | 41 | 0 | 633 | 41 |
| E1-R2 | 버튼 | 674 | 46 | 621 | 0 | 7 | 667 | 7 |
| E1-R2 | 용어 | 674 | 0 | 656 | 18 | 0 | 656 | 18 |
| E1-R2 | 중복 ID | 674 | 37 | 634 | 0 | 3 | 671 | 3 |
| E1-R3b | 대비 | 651 | 45 | 602 | 3 | 1 | 647 | 4 |
| E1-R3b | 모바일 | 651 | 57 | 555 | 39 | 0 | 612 | 39 |
| E1-R3b | 버튼 | 651 | 44 | 600 | 0 | 7 | 644 | 7 |
| E1-R3b | 용어 | 651 | 0 | 635 | 16 | 0 | 635 | 16 |
| E1-R3b | 중복 ID | 651 | 33 | 612 | 0 | 6 | 645 | 6 |
| E2-A1-1 | 대비 | 544 | 46 | 466 | 25 | 7 | 512 | 32 |
| E2-A1-1 | 모바일 | 544 | 63 | 422 | 59 | 0 | 485 | 59 |
| E2-A1-1 | 버튼 | 544 | 41 | 487 | 0 | 16 | 528 | 16 |
| E2-A1-1 | 용어 | 544 | 3 | 522 | 16 | 3 | 525 | 19 |
| E2-A1-1 | 중복 ID | 544 | 31 | 501 | 3 | 9 | 532 | 12 |
| E2-A1-2 | 대비 | 579 | 47 | 503 | 24 | 5 | 550 | 29 |
| E2-A1-2 | 모바일 | 579 | 68 | 447 | 64 | 0 | 515 | 64 |
| E2-A1-2 | 버튼 | 579 | 37 | 521 | 0 | 21 | 558 | 21 |
| E2-A1-2 | 용어 | 579 | 7 | 557 | 13 | 2 | 564 | 15 |
| E2-A1-2 | 중복 ID | 579 | 34 | 534 | 5 | 6 | 568 | 11 |
| E2-A1-3 | 대비 | 534 | 47 | 455 | 26 | 6 | 502 | 32 |
| E2-A1-3 | 모바일 | 534 | 67 | 408 | 59 | 0 | 475 | 59 |
| E2-A1-3 | 버튼 | 534 | 41 | 478 | 0 | 15 | 519 | 15 |
| E2-A1-3 | 용어 | 534 | 6 | 519 | 7 | 2 | 525 | 9 |
| E2-A1-3 | 중복 ID | 534 | 34 | 492 | 2 | 6 | 526 | 8 |
| E3-page | 대비 | 168 | 5 | 163 | 0 | 0 | 168 | 0 |
| E3-page | 모바일 | 168 | 8 | 150 | 10 | 0 | 158 | 10 |
| E3-page | 버튼 | 168 | 7 | 159 | 0 | 2 | 166 | 2 |
| E3-page | 용어 | 168 | 11 | 152 | 5 | 0 | 163 | 5 |
| E3-page | 중복 ID | 168 | 4 | 163 | 1 | 0 | 167 | 1 |
| E3-oracle | 대비 | 98 | 5 | 93 | 0 | 0 | 98 | 0 |
| E3-oracle | 모바일 | 98 | 10 | 83 | 5 | 0 | 93 | 5 |
| E3-oracle | 버튼 | 98 | 4 | 90 | 0 | 4 | 94 | 4 |
| E3-oracle | 용어 | 98 | 25 | 56 | 17 | 0 | 81 | 17 |
| E3-oracle | 중복 ID | 98 | 3 | 95 | 0 | 0 | 98 | 0 |
| E4-mobile | 대비 | 300 | 9 | 291 | 0 | 0 | 300 | 0 |
| E4-mobile | 모바일 | 300 | 56 | 233 | 11 | 0 | 289 | 11 |
| E4-mobile | 버튼 | 300 | 9 | 290 | 0 | 1 | 299 | 1 |
| E4-mobile | 용어 | 300 | 2 | 296 | 1 | 1 | 298 | 2 |
| E4-mobile | 중복 ID | 300 | 7 | 293 | 0 | 0 | 300 | 0 |

출처:
- `results/revision/runs/{run}/reports.jsonl`
- `results/revision/semantic_scores/{run}-sem-p1/grades.jsonl`
- `scoring/issue_table.py`

### 6a. 표준 용어 위반: 키워드, 의미 pass1, string_match 세 판정의 조합

조합 표기 = 키워드/의미/string_match (1 = 용어 위반 판정). 000 은 세 채점기 모두 음성.

| 원 run | 이슈 | 000 | 001 | 010 | 011 | 100 | 101 | 110 | 111 | 의미 비성공 |
|---|---|---|---|---|---|---|---|---|---|---|
| E1-R1 | 676 | 659 | 0 | 0 | 0 | 0 | 17 | 0 | 0 | 11 |
| E1-R2 | 674 | 656 | 0 | 0 | 0 | 0 | 18 | 0 | 0 | 19 |
| E1-R3b | 651 | 635 | 0 | 0 | 0 | 0 | 16 | 0 | 0 | 22 |
| E2-A1-1 | 544 | 522 | 0 | 3 | 0 | 0 | 16 | 0 | 3 | 20 |
| E2-A1-2 | 579 | 557 | 0 | 2 | 0 | 0 | 13 | 0 | 7 | 17 |
| E2-A1-3 | 534 | 519 | 0 | 2 | 0 | 0 | 7 | 0 | 6 | 17 |
| E3-page | 168 | 152 | 0 | 0 | 0 | 0 | 5 | 0 | 11 | 5 |
| E3-oracle | 98 | 56 | 0 | 0 | 0 | 0 | 17 | 0 | 25 | 3 |
| E4-mobile | 300 | 296 | 0 | 1 | 0 | 0 | 1 | 0 | 2 | 3 |

출처:
- `results/revision/runs/{run}/reports.jsonl`
- `results/revision/semantic_scores/{run}-sem-p1/grades.jsonl`
- `scoring/string_match.py`

### 6b. 표준 용어 위반 쌍별 일치 (이슈 단위)

| 원 run | 키워드-의미 일치 | 불일치 | 키워드-string_match 일치 | 불일치 | 의미-string_match 일치 | 불일치 |
|---|---|---|---|---|---|---|
| E1-R1 | 659 | 17 | 676 | 0 | 659 | 17 |
| E1-R2 | 656 | 18 | 674 | 0 | 656 | 18 |
| E1-R3b | 635 | 16 | 651 | 0 | 635 | 16 |
| E2-A1-1 | 525 | 19 | 544 | 0 | 525 | 19 |
| E2-A1-2 | 564 | 15 | 579 | 0 | 564 | 15 |
| E2-A1-3 | 525 | 9 | 534 | 0 | 525 | 9 |
| E3-page | 163 | 5 | 168 | 0 | 163 | 5 |
| E3-oracle | 81 | 17 | 98 | 0 | 81 | 17 |
| E4-mobile | 298 | 2 | 300 | 0 | 298 | 2 |

출처:
- `results/revision/runs/{run}/reports.jsonl`
- `results/revision/semantic_scores/{run}-sem-p1/grades.jsonl`
- `scoring/string_match.py`

