# E9 평가 시트 정보 누출 점검

작성: `experiments/revision/e9_human_sheets.py leak` (API 호출 없음). 2026-11-18.
검사 대상: `rater_A_e9/`, `rater_A_e9_retest/` 의 모든 파일과 `e9_howto.md`.
검색어: 조건·run 이름, 페이지 ID·경로, 결함 유형 표기, 정규식·층 표기, 실제 주입 문구·값. 원 결과: `leak_audit_e9.json`.
이슈 문장(점검 도구 출력)과 페이지 HTML 원문은 평가 대상 그 자체라 일치해도 누출로 보지 않고 건수만 적는다.

검사한 파일 141개.

## 1. 검색 결과 (묶음별 건수)

| 폴더 | 위치 | 분류 | 판단 | 건수 |
|---|---|---|---|---|
| e9_howto.md | 안내문 본문 | 결함 유형 표기 | 연구자가 지정한 파일·폴더 이름(e9) | 6 |
| rater_A_e9 | CSV 본문(이슈 문장) | 주입 문구 | 평가 대상(이슈 문장) | 23 |
| rater_A_e9 | 뷰어 본문(이슈 문장) | 주입 문구 | 평가 대상(이슈 문장) | 23 |
| rater_A_e9 | 뷰어 코드·마크업 | 조건·run | CSS position:fixed | 1 |
| rater_A_e9 | 파일명 | 결함 유형 표기 | 연구자가 지정한 파일·폴더 이름(e9) | 1 |
| rater_A_e9 | 포함된 페이지 HTML | 주입 문구 | 평가 대상(페이지 원문) | 67 |
| rater_A_e9_retest | CSV 본문(이슈 문장) | 주입 문구 | 평가 대상(이슈 문장) | 5 |
| rater_A_e9_retest | 뷰어 본문(이슈 문장) | 주입 문구 | 평가 대상(이슈 문장) | 5 |
| rater_A_e9_retest | 뷰어 코드·마크업 | 조건·run | CSS position:fixed | 1 |
| rater_A_e9_retest | 파일명 | 결함 유형 표기 | 연구자가 지정한 파일·폴더 이름(e9) | 1 |
| rater_A_e9_retest | 포함된 페이지 HTML | 주입 문구 | 평가 대상(페이지 원문) | 11 |

출처: `results/revision/human_eval/e9_eval/leak_audit_e9.json`

## 2. 추가 점검

| 점검 | 결과 |
|---|---|
| 시트 입력 칸 중 값이 있는 칸 | 0 |
| 본 시트와 재평가 시트의 같은 스크린샷 파일명 | 0 |

출처: 위와 같음

**누출로 판단한 항목: 0건.**
