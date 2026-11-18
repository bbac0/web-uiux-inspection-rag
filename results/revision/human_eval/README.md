# 사람 평가 시트 (E1-R1)

작성: `experiments/revision/build_human_eval.py` → 동결된 `make_eval_sheets.build` 호출 (API 호출 없음).
시드: A 표본·토큰·섞기 20261112, B 표본·섞기 20261113 (analysis_plan.md 10절 4항).
**평가자에게는 `rater_A/` 또는 `rater_B/` 폴더만 준다.** `key/` 와 이 README 는 주지 않는다.

## 표본 크기

| 시트 | 페이지 | 이슈 | 예상 소요 (행당 2~3분) |
|---|---|---|---|
| A | 132 | 444 | 14.8~22.2시간 |
| B | 60 | 204 | 6.8~10.2시간 |

행당 2~3분은 `docs/rater_guidelines.md` 4절의 목표 시간이다(연습 문항 시간 제외).

## 표본 층 (페이지 수)

| 층 | A | B |
|---|---|---|
| control | 39 | 18 |
| terminology | 45 | 20 |
| Poor Contrast Ratio | 12 | 6 |
| Mobile Layout Breakage | 12 | 6 |
| Button Area Clipping | 12 | 5 |
| Duplicate ID Markup Error | 12 | 5 |

## 주입 유형별 포함 페이지 수 (nominal, 한 페이지에 유형 2개면 둘 다 셈)

| 유형 | A | B |
|---|---|---|
| 명도 대비 | 21 | 9 |
| 모바일 | 29 | 18 |
| 버튼 잘림 | 28 | 11 |
| 표준 용어 | 45 | 20 |
| 중복 ID | 24 | 11 |
| 대조군 (주입 없음) | 39 | 18 |

이슈가 없는 A 페이지: 0개 (시트에 행이 없음; key/sampling_manifest.json).
위 페이지 수는 이슈가 없는 페이지를 포함한 표본 전체 기준이다(같은 시드로 표본 함수를 다시 호출해 셈).

## 가림 확인

- 시트·뷰어에는 issue_id(무작위 토큰), 스크린샷 경로(무작위 토큰), 설명, 제안, 판정 칸만 있다.
- 뷰어의 HTML 원문은 testbed_200 원본 파일 그대로다(페이지 ID·주입 표기 없음, 테스트로 확인).
- 테스트: `tests/test_human_eval_blinding.py`.

출처:
- `results/revision/human_eval/key/sampling_manifest.json`
- `results/revision/human_eval/key/eval_key.csv`

