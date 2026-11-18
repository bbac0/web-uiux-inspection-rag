# 의미 채점 재채점 준비와 exp-freeze-v6-semretry 동결 목록

작성 2026-11-13. 재채점은 제출하지 않았다(연구자가 별도 창에서 제출). API 호출 없음.

## 1. 결정과 문서

- 주 분석 = 재채점 포함. 민감도 = 원 규칙(잘림 = 음성), 잘림 페이지 제외. 재채점 1회 한정, 다시 실패하면 미해결.
- max_tokens 800: `scoring/grader_config_retry800.json`
  (동결 `scoring/grader_config.json` 과 max_tokens, _notes 만 다름).
- 사전 지정 부록: `results/revision/analysis_plan_addendum_semantic_retry.md` (재채점 결과를 보기 전에 작성).
- README 계획 이탈 기록 1행 추가, `docs/semantic_truncation_retry_plan.md` 갱신(retry800, 결정 A),
  `docs/grader_commands.md` 5절(제출, 상태, 회수) 추가.

## 2. 코드와 mock 시험

- `scoring/semantic_grader_retry.py` (submit/status/collect), `scoring/issue_table_merged.py`,
  `tests/test_semantic_grader_retry.py` (8개 시험, mock 만).
- 시험 항목: 대상만 제출(max_tokens 800, thinking·effort 동일), 입력 sha256 불일치 시 거부·폴더 미생성,
  잘리지 않은 대상 거부, max_tokens 외 설정 차이 거부, 원 폴더 무변경(파일 해시 비교), 완료 시 잠금과 SHA256SUMS 검증,
  처리 중이면 잠그지 않음, 다시 잘리면 미해결, 통합 표 병합 열.
- 결과: tests.test_semantic_grader_retry + test_semantic_grader_batch + test_semantic_grader 33개 통과.
- 실제 대상 사전 점검(API 없음, 제출 없음): 11개 원 out_id 의 150건 모두 입력·프롬프트 sha256 이 원 채점과 같고,
  설정 차이는 max_tokens 뿐이며, 요청 max_tokens 800 확인. `-retry` 폴더는 아직 없다.

## 3. v5 대비 해시 변경 목록

v5 목록 항목 261개(파일 + 내용 해시)는 모두 그대로다(변경 0, 누락 0). 추가 37개:

| 추가 파일 | sha256 (앞 16자) |
|---|---|
| `experiments/revision/clean_report.py` | 0827284943975d18 |
| `experiments/revision/clean_report_a2_e4.py` | 3cdf0e532ccd847a |
| `experiments/revision/clean_report_c.py` | c4f9984a6cdaafba |
| `experiments/revision/e7_paired_cluster.py` | 78df258f36032ed9 |
| `experiments/revision/e7_stats.py` | 9a7948e07ffbb8f0 |
| `experiments/revision/e7_supplement_tables.py` | 456394d66d7d6fae |
| `experiments/revision/e7_total_checked_source.py` | 35ba1ec21cc41a10 |
| `experiments/revision/e9_generate.py` | a582ab59835d6b8a |
| `experiments/revision/e9_generate_pilot.py` | a390e891f4ec13ed |
| `experiments/revision/e9_main_report.py` | d960a316dba64be7 |
| `experiments/revision/e9_main_retrieval_check.py` | dbabafae338443a3 |
| `experiments/revision/e9_pilot_compare.py` | a29df141cd51503e |
| `experiments/revision/e9_pilot_report.py` | 1aa7f55a87bcec6b |
| `experiments/revision/e9_regex_table.py` | f9b4b3ccfa1f3062 |
| `experiments/revision/e9_verify.py` | 62418a94538b4099 |
| `experiments/revision/freeze_manifest_e9.py` | f2f0a72cb1b17d8e |
| `experiments/revision/freeze_manifest_v6.py` | 9736d17892fb1843 |
| `experiments/revision/grader_path_decision.py` | 0a90e210d49ff9d8 |
| `experiments/revision/run_e9_main.py` | 36f71f4d94755b84 |
| `experiments/revision/run_e9_pilot.py` | 2c57974a203a6eb6 |
| `experiments/revision/run_experiment_e9.py` | 3dfe69eb4f75b056 |
| `experiments/revision/run_remaining.py` | e5d3820935771c16 |
| `experiments/revision/semantic_provisional_compare.py` | e3a5fef31cb6af0a |
| `experiments/revision/semantic_scoring_report.py` | 846b6a8fb8d5972f |
| `experiments/revision/semantic_truncation_report.py` | 0284468291d5190d |
| `scoring/e9_judge_prompt.py` | bdd60c5df5a7226e |
| `scoring/e9_rules.py` | 2782df4e53484ccd |
| `scoring/e9_rules_aux.py` | 2ef2a98e87b7a440 |
| `scoring/issue_table_merged.py` | 3b2206943ce84d05 |
| `scoring/mock_anthropic_batch.py` | bb17425dc08d4bc8 |
| `scoring/semantic_grader_batch.py` | 14e63a5f9dd4c7e5 |
| `scoring/semantic_grader_retry.py` | c2c526d70150545d |
| `scoring/grader_config_retry800.json` | 744c4442fcc80dc5 |
| `results/revision/analysis_plan_addendum_semantic_retry.md` | 1cae09286512edff |
| `results/revision/semantic_truncation_targets.csv` | 1582620ada73b5fb |
| `tests/test_semantic_grader_retry.py` | 869e6901010d25e1 |
| `docs/semantic_truncation_retry_plan.md` | 3bdc5f3a9195e7a9 |

v5 이후 E7·E9·채점 작업에서 만든 파일(이미 커밋됨)도 v5 범위의 glob 에 새로 잡혀 추가로 들어갔다.
v5 의 `freeze_manifest.py --check` 는 이런 추가 파일도 CHANGED 로 표시하므로, 이후 대조는
`freeze_manifest_v6.py --check` 를 쓴다(v5 항목 변경과 추가 파일 변경을 모두 확인).

출처:
- `results/revision/freeze_manifest_v6.csv`
- `results/revision/freeze_manifest.csv` (v5, 동결)
- `experiments/revision/freeze_manifest_v6.py`

