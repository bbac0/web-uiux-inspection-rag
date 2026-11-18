# 분석 계획 부록: 사람 평가 보충 시트 (로그인 레이블·용어 위반)

작성일: 2026-11-16. 표본을 뽑기 전, 보충 시트의 결과와 평가자 입력을 보기 전에 커밋한다.
API 호출 없음.

## 1. 배경

- 본 사람 평가 시트(E1-R1 기반, `results/revision/human_eval/rater_A`, `rater_B`)에는 로그인 링크 레이블
  문구를 지적한 이슈가 없다(`results/revision/human_eval/login_label_scan.md`). 그래서
  `login_link_label_concern` 열은 두 평가자가 모두 '아니오'만 고를 가능성이 높고 kappa 를 계산할 수 없다.
- 의미 채점이 표준 용어 위반으로 본 이슈는 E3-oracle, E3-page, E2-A1-1~3, E4-mobile 에 있지만
  사람 평가 시트에는 없다. 이 부록은 그 이슈를 사람이 판정하는 보충 시트의 표본 규칙을 정한다.
- 이 문서를 쓰기 전에 본 것: 각 run 의 의미 라벨별 건수와 string_match 건수(이미 보고한 집계).
  층별 중복 제거 후 건수와 개별 표본은 이 문서를 커밋한 뒤에 계산한다.

## 2. 모집단

- run: E3-oracle, E3-page, E2-A1-1, E2-A1-2, E2-A1-3, E4-mobile (6개).
- 이슈: 재채점 병합 통합표 `results/revision/issue_tables_merged/{run}.csv` 의 행 전체
  (= 각 run 의 대상 페이지 이슈, description 에 `testbed_200/{page_id}.html` 포함).
- 이슈 문장: `results/revision/runs/{run}/reports.jsonl` 의 `report.issues[issue_index]`.
  description 은 본 시트와 같은 `make_eval_sheets.clean_text` 로 앞의 URL 표기를 지운다. suggestion 은 앞뒤 공백만 지운다.

## 3. 중복 제거

- 지운 description 과 suggestion 이 둘 다 같은 이슈는 하나로 본다.
- 대표 이슈: 같은 문장 묶음 안에서 (run 순서 E3-oracle, E3-page, E2-A1-1, E2-A1-2, E2-A1-3, E4-mobile,
  page_id, issue_index) 순으로 첫 번째. 층과 스크린샷은 대표 이슈의 것을 쓴다.
- 묶음 안에서 의미 라벨이나 string_match 가 서로 다른 경우가 있으면 건수를 key/ 와 보고서에 적는다
  (층은 대표 이슈 기준 그대로).

## 4. 층과 표본

라벨은 주 분석 기준인 `semantic_pass1_merged`(재채점 포함 pass1)를 쓴다.

| 층 | 정의 | 표본 |
|---|---|---|
| S1 | `semantic_pass1_merged` = Standard Terminology Violation | 전부 |
| S2 | `string_match_term` = 1 이고 S1 이 아님 | 무작위 최대 40건, 시드 20261120 |
| S3 | S1 도 S2 도 아님 | 무작위 30건, 시드 20261121 |

- 무작위 추출: 각 층의 대표 이슈를 (run 순서, page_id, issue_index) 로 정렬한 뒤
  `random.Random(시드).sample(목록, min(목표, 건수))`.
- 세 층을 합친 뒤 `random.Random(20261122).shuffle` 로 섞는다. 이 순서가 시트 순서다.
- `semantic_pass1_merged` 가 비어 있는(unresolved) 이슈는 어느 층에도 넣지 않고 건수만 보고한다.

## 5. 시트 구성 (연구자 승인 후 생성)

- 평가자 A, B 가 같은 표본 전체를 판정한다(`rater_A_supp/`, `rater_B_supp/`). 열 구성, 뷰어(CSV 불러오기 포함),
  지침서(`docs/rater_guidelines_v2.md` 그대로)는 본 시트와 같다.
- 조건명, run 이름, 채점 결과, 층은 시트와 뷰어에 넣지 않고 `results/revision/human_eval/supp_label/key/` 에만 둔다.
  issue_id 와 스크린샷 파일명은 무작위 토큰이다.
- 스크린샷은 대표 이슈 run 의 해당 페이지 스크린샷을 그대로 쓴다. E3, E2 는 1280x800, E4-mobile 은 390x844 이다.
  지침 v2 는 '화면에서 보이는가'를 데스크톱 1280x800 기준이라고 적고 있어, E4-mobile 대표 이슈는 이 기준과 다르다.
  시트 생성 전에 연구자가 처리 방식을 정하고, 정한 내용을 계획 이탈 기록에 남긴다.

## 6. 분석

- 이 시트는 채점 결과(의미 라벨, string_match)로 뽑은 표본이므로 disagreement_focus 성격이다.
  **본 평가 시트와 합쳐 전체 정확도를 계산하지 않는다.** 층별로 따로 보고한다.
- 층별 보고(기술 통계만, 검정 없음):
  - 평가자 간 일치: 열별 단순 일치율, Cohen's kappa, PABAK, Gwet AC1. 값이 한 가지뿐인 열은 kappa 계산 불가로 표시.
  - 사람 판정(합의 또는 평가자별)과 의미 라벨, string_match, 키워드 라벨의 일치를 층별 건수로 보고.
- 합의 절차는 본 평가와 같다(불일치는 조정자가 판정).
