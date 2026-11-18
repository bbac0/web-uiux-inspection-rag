# 평가자 간 일치 (시범)

작성: `experiments/revision/human_eval_pilot_compare.py` (API 호출 없음, 검정 없음).
입력 A: `results/revision/human_eval/pilot_rater/eval_sheet_pilot_filled_A.csv`
입력 B: `results/revision/human_eval/pilot_rater/eval_sheet_pilot_filled_B.csv`
정답 키·채점 결과 미사용. 병합 방식 `same`.
비교 이슈 20건 (A 에만 0, B 에만 0).

## 1. 열별 일치율과 Cohen's kappa

| 열 | 비교 건 | 빈 칸(제외) | 일치 | 일치율 | kappa |
|---|---|---|---|---|---|
| 6분류 (rater_category) | 20 | 0 | 20 | 1.000 | 1.000 |
| 코드에 존재 (exists_in_code) | 20 | 0 | 20 | 1.000 | 1.000 |
| 화면에서 보임 (visible_on_screen) | 20 | 0 | 15 | 0.750 | 0.219 |
| 로그인 레이블 지적 (login_link_label_concern) | 20 | 0 | 20 | 1.000 | - |

출처: 위 입력 A, B CSV

## 2. 6분류 혼동 행렬 (행 = A, 열 = B)

| A \ B | 명도 대비 부족 | 모바일 레이아웃 깨짐 | 버튼 영역 잘림 | 표준 용어 위반 | 중복 ID | 해당 없음 |
|---|---|---|---|---|---|---|
| 명도 대비 부족 | 1 | 0 | 0 | 0 | 0 | 0 |
| 모바일 레이아웃 깨짐 | 0 | 1 | 0 | 0 | 0 | 0 |
| 버튼 영역 잘림 | 0 | 0 | 1 | 0 | 0 | 0 |
| 표준 용어 위반 | 0 | 0 | 0 | 0 | 0 | 0 |
| 중복 ID | 0 | 0 | 0 | 0 | 0 | 0 |
| 해당 없음 | 0 | 0 | 0 | 0 | 0 | 17 |

출처: 위 입력 A, B CSV

## 3. 불일치 이슈 (5건)

| issue_id | 열 | A | B | A 비고 | B 비고 |
|---|---|---|---|---|---|
| I1aa0822eb8 | visible_on_screen | 예 | 아니오 | 부재형 | 브라우저 부재형 |
| I3aed7f3794 | visible_on_screen | 예 | 아니오 | 부재형 | 배너 부재형 |
| I5a804c43f0 | visible_on_screen | 예 | 아니오 | 부재형 | 부재형 |
| I659719567d | visible_on_screen | 예 | 아니오 | 부재형 | 브라우저 부재형 |
| I6e62f70f04 | visible_on_screen | 예 | 아니오 | 부재형 | 브라우저 부재형 |

출처: 위 입력 A, B CSV

## 4. 메모 (수기 추가)

- 첫 비교(`pilot_agreement.md`) 이후 A 가 I010a049fdb 의 로그인 레이블 지적을 '예'에서 '아니오'로 고쳤다
  (입력 실수 정정). 같은 파일 이름으로 덮어써서 첫 보고서에 적힌 A 해시는 이전 파일의 것이다.
- 입력 SHA256: A `febefb84c5f870fc311701aa26b3498195cd23f8aeccd441dd382479a7725059`,
  B `808c73898a10501814a7e881fe814a80661f1a07483de3c7fbe02b56135fba14` (변경 없음).
- 로그인 레이블 열은 두 평가자 모두 20건 '아니오'라 kappa 를 계산할 수 없다('-').
  시트 전체에 로그인 레이블 문구를 지적한 이슈가 없다는 점검은 `login_label_scan.md` 참고.
- 남은 불일치 5건은 모두 화면에서 보임 열의 부재형 이슈다(첫 보고서 4절과 같음).
