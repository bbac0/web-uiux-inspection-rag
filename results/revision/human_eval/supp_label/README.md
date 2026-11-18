# 추가 평가 세트 (연구자용, 평가자에게 주지 않음)

작성 2026-11-16. API 호출 없음. 규칙: `results/revision/analysis_plan_addendum_supp_label.md` (d594519).
표본: `key/sample_selection.csv` (1bf93c8, S1 43 / S2 34 / S3 30, 합계 107). 연구자 승인 2026-11-16.
생성: `experiments/revision/build_supp_label.py build`, 누출 점검 `... leak`.

## 1. 평가자에게 주는 것

| 평가자 | 폴더 | 이슈 | 스크린샷 | 함께 주는 문서 |
|---|---|---|---|---|
| A | `rater_A_supp/` | 107 | 64 | `supp_howto.md`, `../viewer_howto.md` |
| B | `rater_B_supp/` | 107 | 64 | `supp_howto.md`, `../viewer_howto.md` |

출처: `key/supp_manifest.json`

- 뷰어는 본 시트와 같은 코드(`build_human_eval.make_viewer`, CSV 불러오기 포함)다. 저장 키는
  `human_eval_A_supp`, `human_eval_B_supp` 로 본 시트(`human_eval_A`, `human_eval_B`)와 섞이지 않는다.
- 지침서: `docs/rater_guidelines_v2.md` 를 그대로 복사.
- 예상 소요: 건당 30~60초 가정, 평가자마다 107건 → 약 54~107분.

## 2. 순서와 시드

| 용도 | 시드 |
|---|---|
| 공통 기준 순서(층 섞기) | 20261122 |
| 평가자 A 순서 | 20261127 |
| 평가자 B 순서 | 20261128 |
| issue_id·스크린샷 토큰 | "supp-tokens-20261122" (기존 시트 토큰과 겹치지 않게 검사) |

출처: `key/supp_manifest.json`. 이슈별 기준 순서·A 위치·B 위치는 `key/supp_key.csv`.

## 3. 스크린샷 바꿈 (E4-mobile 대표 이슈 6건)

- 6건 모두 E1-R1, E1-R2, E1-R3b 에 같은 페이지·같은 문장의 이슈가 없었다. 지시한 조건(같은 문장)을 채우는 run 이 없어서,
  그 페이지에 이슈가 있는 첫 run 인 E1-R1 의 1280x800 스크린샷을 썼다.
  6개 페이지 모두 E1-R1, E1-R2, E1-R3b 스크린샷의 SHA256 이 같아서 어느 run 을 써도 같은 그림이다.
- 6건의 문장은 모두 링크·버튼 문구, 헤더 구성, 스타일에 관한 것이고 모바일 화면(좁은 폭, 가로 스크롤 등)을 전제로 한 이슈는 없다.
  1280 스크린샷으로 확인이 안 되는 이슈 목록: 없음.
- 목록(key 쪽 식별자, 원래 크기, 쓴 run, SHA256): `key/screenshot_substitution.csv`.

## 4. 중복 문장

- 같은 설명·제안 문장이 모집단 6개 run 에 나온 횟수는 `key/supp_key.csv` 의 `dup_n_total`, `dup_by_run` 열.
- 표본 107건 중 51건이 2회 이상 나온 문장이다(최대 9회).

## 5. 누출 점검

- `leak_audit_supp.md`: 누출로 판단한 항목 0건. 일치한 것은 6분류 선택지 문구, 지침서 v2 본문, CSS `position:fixed`,
  지침서 파일명뿐이다. 스크린샷 128개 모두 1280x800, PNG 텍스트 메타데이터 없음.
- `supp_howto.md` 에는 '추가 평가 세트'라는 이름만 쓰고 '레이블 관련', '용어', '접속하기', '보충' 같은 표현이 없다
  (`tests/test_supp_label_sheets.py`).

## 6. 분석 도구

- `experiments/revision/human_eval_compare_robust.py`: 일치율, Cohen's kappa, PABAK, Gwet AC1, 관찰 값 수.
  값이 한 가지뿐인 열은 kappa '계산 불가(값 한 가지)'. `--groups` 로 층별 표(층 파일은 key 에서 만든다).
- 계획대로 이 세트는 본 평가와 합치지 않고 층별로 따로 보고한다.
