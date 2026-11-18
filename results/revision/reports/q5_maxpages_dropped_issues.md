# 확인 5: `--max-pages 1` 실행에서 다른 URL 의 이슈를 몇 건 버렸는가

작성 2026-11-19. API 호출 없음.

## 1. 결론

- **E1-R1 에서 버려진 이슈는 0건이다.** 리포트 200개의 이슈 676건이 모두 그 페이지 URL(`testbed_200/{page_id}.html`)을
  description 앞에 달고 있어 전부 대상 페이지 이슈로 남았다.
- 다른 URL 의 이슈를 버렸다는 기록은 **기존 run2(1차 평가 방식, `--max-pages` 5)** 의 재분석에 있다. 그 실행은
  크롤러가 시작 페이지의 링크(`/login`, 404 페이지)까지 따라가 분석해, 이슈 1,054건 중 552건이 `/login` 페이지 이슈였고
  대상 페이지 이슈는 502건이었다. 근거 필드 분석(E8, 5.3절)은 이 552건을 빼고 대상 페이지 이슈만 셌다.
- `--max-pages 1` 에서는 링크를 따라가지 않으므로(`results/revision/README.md` 14~16행) 다른 페이지의 리포트가 생기지 않는다.

## 2. run 별 이슈 수 (전체 대 대상 페이지 이슈)

| run | 이슈 전체 | 대상 페이지 이슈 | 버려진 이슈 |
|---|---|---|---|
| E1-R1 | 676 | 676 | 0 |
| E1-R2 | 674 | 674 | 0 |
| E1-R3 (중단) | 532 | 532 | 0 |
| E1-R3b | 651 | 651 | 0 |
| E2-A1-1 / A1-2 / A1-3 | 544 / 579 / 534 | 544 / 579 / 534 | 0 / 0 / 0 |
| E2-A2 / E2-A3 | 898 / 518 | 898 / 518 | 0 / 0 |
| E3-page / E3-oracle | 168 / 98 | 168 / 98 | 0 / 0 |
| E4-mobile | 300 | 300 | 0 |
| E9 본 실험 12 run | 105~311 | 같음 | 모두 0 |
| (참고) 기존 run2, `--max-pages` 5 | 1,054 | 502 | 552 (`/login` 404 페이지) |

출처: `results/revision/runs/{run}/reports.jsonl`, `results/revision/runs_e9/{run}/reports.jsonl`,
`results/revision/reports/paper_numbers.md` 2.1절, `results/revision/e8_run2_reanalysis.md` 49행·107행

- 대상 페이지 이슈 판정: description 의 `[URL]` 접두어에 `/{page_id}.html` 이 있는 이슈
  (`scoring/semantic_grader_anthropic.iter_run_issues`,
  `experiments/revision/e9_regex_table.target_issues`).
  이 필터는 `--max-pages 1` run 에서는 아무것도 걸러내지 않았다.
