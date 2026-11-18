# 재판정 시트 정보 누출 점검

작성: `experiments/revision/human_eval_A_followup.py leak` (API 호출 없음). 2026-11-16.
방법: 본 시트 점검(`leak_audit.md`)과 같은 검색어·위치에, 이전 답 흔적('_filled', '이전 답', '본 평가 답'),
입력 칸이 비었는지, 스크린샷 파일명이 본 시트와 겹치는지를 더했다. `retest_howto.md` 본문도 검사했다.
원 검색 결과: `results/revision/human_eval/leak_audit_retest.json`.

검사한 파일 39개 (rater_A_retest/ 와 retest_howto.md). 제외: 이슈 설명·제안 본문.

## 1. 검색 결과

| 폴더 | 위치 | 분류 | 일치 | 건수 | 판단 |
|---|---|---|---|---|---|
| rater_A_retest | 뷰어 코드·마크업 | 결함 유형(한글) | 대비 | 2 | 예상됨: 6분류 선택지 문구(모든 행에 같음) |
| rater_A_retest | 뷰어 코드·마크업 | 결함 유형(한글) | 모바일 | 2 | 예상됨: 6분류 선택지 문구(모든 행에 같음) |
| rater_A_retest | 뷰어 코드·마크업 | 결함 유형(한글) | 용어 | 2 | 예상됨: 6분류 선택지 문구(모든 행에 같음) |
| rater_A_retest | 뷰어 코드·마크업 | 결함 유형(한글) | 중복 ID | 2 | 예상됨: 6분류 선택지 문구(모든 행에 같음) |
| rater_A_retest | 뷰어 코드·마크업 | 이전 답 | _filled | 1 | 예상됨: 6분류 선택지 문구(모든 행에 같음) |
| rater_A_retest | 뷰어 코드·마크업 CSS | 조건명 | fixed | 1 | 예상됨: CSS position:fixed (조건명 아님) |
| rater_A_retest | 지침서 본문 | 결함 유형(한글) | 대비 | 5 | 예상됨: 지침서 v2 의 6분류 정의와 예시 |
| rater_A_retest | 지침서 본문 | 결함 유형(한글) | 모바일 | 1 | 예상됨: 지침서 v2 의 6분류 정의와 예시 |
| rater_A_retest | 지침서 본문 | 결함 유형(한글) | 버튼 잘림 | 1 | 예상됨: 지침서 v2 의 6분류 정의와 예시 |
| rater_A_retest | 지침서 본문 | 결함 유형(한글) | 용어 | 5 | 예상됨: 지침서 v2 의 6분류 정의와 예시 |
| rater_A_retest | 지침서 본문 | 결함 유형(한글) | 중복 ID | 4 | 예상됨: 지침서 v2 의 6분류 정의와 예시 |
| rater_A_retest | 파일명·경로 | 라벨 열 이름 | guideline | 1 | 예상됨: 지침서 파일명 rater_guidelines.md |
| retest_howto.md | 안내문 본문 안내 문구 | 이전 답 | _filled | 1 | 예상됨: 내보낼 파일 이름·찾아보지 말라는 안내 |
| retest_howto.md | 안내문 본문 안내 문구 | 이전 답 | 이전 답 | 1 | 예상됨: 내보낼 파일 이름·찾아보지 말라는 안내 |
| retest_howto.md | 안내문 본문 지침서 파일명 | 라벨 열 이름 | guideline | 1 | 예상됨: 지침서 파일명 언급 |

출처: `results/revision/human_eval/leak_audit_retest.json`

## 2. 추가 점검

| 점검 | 결과 |
|---|---|
| 시트 입력 칸(5개 열 × 40행) 중 값이 있는 칸 | 0 |
| 본 시트와 이름이 같은 스크린샷 파일 | 0 |

출처: 위와 같음

**누출로 판단한 항목: 0건.**

## 3. 알아둘 점

- issue_id 는 본 시트와 같다(비교 스크립트가 issue_id 로 맞추기 때문). 평가자가 자기 본 평가 CSV 를 열어
  issue_id 로 찾으면 이전 답을 볼 수 있다. retest_howto.md 에서 찾아보지 말라고 안내했다.
- 스크린샷 그림 내용은 본 시트와 같은 파일이다(이름만 새 토큰).
