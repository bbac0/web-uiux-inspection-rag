# E7 통계 (2026-11-13, `exp-freeze-v5` 이후, API 호출 없음)

- 스크립트: `experiments/revision/e7_stats.py` (사전 지정: analysis_plan.md 2·3·5·9·10절). 다시 실행하면 같은 값이 나온다(부트스트랩 시드 20261111).
- 대상: E1-R1, E1-R2, E1-R3b (RAG 켬) / E2-A1-1, A1-2, A1-3 (RAG 끔), 각 조건 3회 다수결. E1-R3(aborted)은 제외.
- 채점기: 키워드(description, 다중 라벨), string_match(mention-based, 용어 유형만). **의미 채점은 아직 실행하지 않아 포함되지 않았다.**
- 라벨: nominal, effective(1280), guideline_grounded(주: 버튼 false → 명도 대비 200셀), guideline_grounded_btn_true(민감도, 400셀).
- E2 Holm 가족(A1, A2, A3 vs R1)은 A2·A3 미실행이라 아직 완성되지 않았다. `mcnemar.csv` 의 주 검정 p 는 보정 전 값이고 Holm 상한(3p)을 함께 적었다.

| 파일 | 내용 |
|---|---|
| `cell_metrics.csv`, `cell_metrics_{label}.tex` | 셀 단위 정밀도·재현율·특이도·균형 정확도·MCC, 95% CI(템플릿 군집 부트스트랩), LOTO 범위, jackknife SE |
| `pair_differences.csv`, `pair_differences_primary.tex` | RAG 켬 − 끔 지표 차이와 CI (주: R1−A1-1, 보조: R2−A1-2, R3b−A1-3, 다수결) |
| `mcnemar.csv`, `mcnemar.tex` | exact McNemar (b, c, p). 유형별은 탐색적(보정 없음) |
| `run_variability.csv`, `run_variability.tex` | 조건 내 실행 간 변동: 탐지 셀 수 평균·SD·범위, 3회 일치 비율, Fleiss kappa, 쌍별 Cohen kappa |
| `condition_mean_vs_within_sd.csv` | 9절 (iv) 조건 간 평균 차이 vs 조건 내 SD |
| `nine_pair_differences.csv` | 9절 (v) 3×3 실행 쌍 9개의 차이 분포 |
| `page_level_legacy.csv`, `.tex` | 기존 논문 방식 페이지 단위 결과 |
| `score_recompute.csv`, `score_auc.csv`, `.tex` | 점수 재계산(반올림)과 결함/대조군 분리 AUC |
| `total_checked_count.csv`, `.tex` | total_checked_count 분포(30, 60, 기타) |
| `exploratory_*.csv`, `exploratory_*.tex` | **exploratory (사전 지정 아님)**: 페이지당 이슈 수, 카테고리 분포, 프롬프트 예시 구조 수렴 |
| `run_status_counts.csv` | run 별 페이지 상태 (오류 페이지 수) |
