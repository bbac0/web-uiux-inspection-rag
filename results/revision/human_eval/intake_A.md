# 평가자 A 본 평가 접수

작성: `experiments/revision/human_eval_A_followup.py intake` (API 호출 없음). 2026-11-16.
정답 키(key/)와 채점 결과는 읽지 않았다. 입력은 아래 두 파일뿐이다.

- 입력: `results/revision/human_eval/rater_A/eval_sheet_A_filled.csv`
  SHA256 `14dcc061cafd1adb89587142716537367863e028e9e93110c66cdd040c495fcf`
  크기 244908 바이트. 접수 시 읽기 전용 속성 설정(파일 내용은 바꾸지 않음), 커밋하지 않음.
- 대조 시트: `results/revision/human_eval/rater_A/eval_sheet_A.csv`
  SHA256 `08012fb797dc8f09d0b460f47ec1a2fa08c20a41449d4aaa5f272b9a2ff4ab9a`

## 1. 점검

| 점검 | 결과 | 비고 |
|---|---|---|
| 열 구성이 시트와 같음 | 통과 |  |
| 행 수 444 | 통과 |  |
| issue_id 집합이 eval_sheet_A.csv 와 같음 | 통과 |  |
| issue_id 순서가 시트와 같음 | 통과 |  |
| 중복 issue_id 없음 | 통과 |  |
| 스크린샷 경로·설명·제안이 시트와 같음 | 통과 |  |
| rater_category 빈칸 없음 | 통과 |  |
| rater_category 허용 값만 | 통과 |  |
| exists_in_code 빈칸 없음 | 통과 |  |
| exists_in_code 허용 값만 | 통과 |  |
| visible_on_screen 빈칸 없음 | 통과 |  |
| visible_on_screen 허용 값만 | 통과 |  |
| login_link_label_concern 빈칸 없음 | 통과 |  |
| login_link_label_concern 허용 값만 | 통과 |  |

출처: `results/revision/human_eval/rater_A/eval_sheet_A_filled.csv`,
`results/revision/human_eval/rater_A/eval_sheet_A.csv`

## 2. 열별 값 분포 (A 의 답만)

| 열 | 값 | 건수 | 비율 |
|---|---|---|---|
| 6분류 | 명도 대비 부족 | 29 | 0.065 |
| 6분류 | 모바일 레이아웃 깨짐 | 30 | 0.068 |
| 6분류 | 버튼 영역 잘림 | 32 | 0.072 |
| 6분류 | 표준 용어 위반 | 0 | 0.000 |
| 6분류 | 중복 ID | 26 | 0.059 |
| 6분류 | 해당 없음 | 327 | 0.736 |
| 코드에 존재 | 예 | 146 | 0.329 |
| 코드에 존재 | 아니오 | 298 | 0.671 |
| 코드에 존재 | 판단 불가 | 0 | 0.000 |
| 화면에서 보임 | 예 | 46 | 0.104 |
| 화면에서 보임 | 아니오 | 398 | 0.896 |
| 화면에서 보임 | 판단 불가 | 0 | 0.000 |
| 로그인 레이블 지적 | 예 | 1 | 0.002 |
| 로그인 레이블 지적 | 아니오 | 443 | 0.998 |

출처: `results/revision/human_eval/rater_A/eval_sheet_A_filled.csv`

## 3. 코드 존재 × 화면에서 보임 (A 의 답만)

| 코드에 존재 \ 화면에서 보임 | 예 | 아니오 | 판단 불가 |
|---|---|---|---|
| 예 | 45 | 101 | 0 |
| 아니오 | 1 | 297 | 0 |
| 판단 불가 | 0 | 0 | 0 |

출처: `results/revision/human_eval/rater_A/eval_sheet_A_filled.csv`

## 4. 비고

| 항목 | 건수 |
|---|---|
| 비고가 있는 행 | 308 |
| '부재형' 포함 | 293 |
| '기준 비교형' 포함 | 0 |
| 둘 다 포함 | 0 |

출처: `results/revision/human_eval/rater_A/eval_sheet_A_filled.csv` (부분 문자열 일치)

### 비고 빈도 상위 20개 (비고 전체 문자열, 앞뒤 공백 제거, 빈 비고 제외)

| 순위 | 비고 | 건수 |
|---|---|---|
| 1 | 부재형 | 293 |
| 2 | !important 중심 vs 색상 중심 | 11 |
| 3 | 오래된 가이드라인 문제 | 3 |
| 4 | viewport 태그 | 1 |

서로 다른 비고 4종. 동률은 비고 문자열 순.
출처: `results/revision/human_eval/rater_A/eval_sheet_A_filled.csv`
