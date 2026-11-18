# exp-freeze-e9-v4: exp-freeze-e9-v3 대비 해시 변경

작성 2026-11-13. 목록 도구 `experiments/revision/freeze_manifest_e9.py`(v3 동결, 수정 없음)로 다시 작성.
항목 136개 → 136개. 추가 0, 삭제 0, 변경 1 (예상 범위: analysis_plan_e9.md 만).

| 파일 | v3 sha256 (앞 16자) | v4 sha256 (앞 16자) | 변경 내용 |
|---|---|---|---|
| `e9/analysis_plan_e9.md` | 2787312c0257fa11 | ba99651796ded536 | 사전 수정 (a)(b)(c), 한계 1줄 |

v3 목록의 나머지 135개(생성기, 테스트베드 파일, 조건 입력, 러너, 정규식 규칙, 판정 프롬프트, 설계 문서 등)는 그대로다.
목록 밖 변경: `results/revision/README.md` 계획 이탈 기록 1행.

출처:
- `results/revision/e9/freeze_manifest_e9.csv` (v4)
- `git show exp-freeze-e9-v3:results/revision/e9/freeze_manifest_e9.csv`
