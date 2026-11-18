# exp-freeze-v4 → exp-freeze-v5 동결 해시 변경 목록 (2026-11-12)

- 항목 수: 234 → 261

## 바뀐 항목

| 항목 | v4 SHA-256 | v5 SHA-256 | 이유 |
|---|---|---|---|
| `results/revision/analysis_plan.md` | `de97900af039e754…` | `67d8c9b7a42de79e…` | 10절 추가, 4·5절 E3 명칭 related-clause |
| `results/revision/oracle_chunks.csv` | `50b41532b9af4e88…` | `257748b97bda633a…` | 헤더만 있던 파일 → 84페이지 × 2청크 (연구자 확정 청크) |
| `experiments/revision/freeze_manifest.py` | `4e0406afef6ea98e…` | `5959f8c2b31d8b36…` | 동결 목록에 채점기·라벨·E3/E9 입력 추가 |

## 새로 추가된 항목

| 항목 | v5 SHA-256 |
|---|---|
| `scoring/grader_config.json` | `290b6eadc2fef41f…` |
| `results/revision/ground_truth.csv` | `fe307fdcd57ba5de…` |
| `results/revision/guideline_grounding_decisions.csv` | `3e412bc3d06b80e9…` |
| `results/revision/fixed_long_selection.json` | `d91aaa3512dac43f…` |
| `results/revision/fixed_query_embedding/ranking.csv` | `c4d376a97990e1f9…` |
| `docs/rater_guidelines.md` | `254944de3e8c6642…` |
| `scoring/__init__.py` | `e3b0c44298fc1c14…` |
| `scoring/issue_table.py` | `b4a5f920328dd7d9…` |
| `scoring/mock_anthropic.py` | `bf28297e823ce74c…` |
| `scoring/probe_tokens.py` | `550eb8225f8c3172…` |
| `scoring/semantic_grader_anthropic.py` | `9dca86e9d5f776d5…` |
| `scoring/string_match.py` | `d61dedbc63911126…` |
| `experiments/revision/e1_a1_status_report.py` | `07556b07b48ebc92…` |
| `experiments/revision/e3_oracle_prep.py` | `fcedcf3ae665e15a…` |
| `experiments/revision/e8_definition_c.py` | `713c72fa26cc0a82…` |
| `experiments/revision/e8_reconcile.py` | `00a2f547967cf155…` |
| `experiments/revision/e8_v_definitions.py` | `9af0adeb5b3e0e72…` |
| `experiments/revision/fixed_long_selection.py` | `14dcc0f47fac0f49…` |
| `experiments/revision/guideline_grounding.py` | `358b936217a36fa5…` |
| `experiments/revision/label_layers.py` | `4c79ff276629f153…` |
| `experiments/revision/latency_table.py` | `01fad890b49e8b48…` |
| `experiments/revision/make_eval_sheets.py` | `cf762058adc44140…` |
| `experiments/revision/oracle_candidates.py` | `0897531009a9a83e…` |
| `experiments/revision/oracle_terminology_context.py` | `78f04745251b2d8c…` |
| `experiments/revision/run_e1_r3b_a1_3.py` | `bd71c95ec10a9032…` |
| `experiments/revision/spend_summary.py` | `c33209e494497d7d…` |
| `experiments/revision/terminology_basis.py` | `687d54a43b499fee…` |

## 빠진 항목

(없음)

그 밖의 모든 항목(프로덕션 analyzer·exp_config·llm_wrapper·cli, 테스트베드 200페이지, services/chroma_db, 가이드라인 PDF, 프롬프트 템플릿·키워드 사전·JUDGE_PROMPT 내용 해시)은 v4 와 같다.
