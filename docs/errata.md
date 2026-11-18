# 정오표 (errata)

작성일: 2026-11-18. 기존 보고서, 커밋, 태그는 고치지 않고 이 문서에만 바로잡는 내용을 적는다.

1. **`results/revision/reports/e7_final_report.md` 119행**
   - 원문: "`paper_numbers.py` 와 논문 숫자표는 이번에 갱신하지 않았다."
   - 바로잡음: 숫자표는 커밋 e3a9a5f 에서 E7 최종 결과로 갱신되었다(`reports/paper_numbers.md` 4절).
2. **`results/revision/reports/e6_axe_report.md` 5절**
   - 상태: LLM 의미 채점 열은 재채점 전 값(원 pass1, 잘림 = 음성)뿐이다.
   - 바로잡음: 재채점(retry800) 병합 값은 E6 보고서에 없고 `reports/paper_numbers.md` 5절에만 있다.
     바뀐 칸은 A1-1 표준 용어 TP/FP 3/3 → 5/7 하나다.

출처: 위 보고서들, `results/revision/reports/paper_numbers.md`

## 2번 항목의 출처

- `paper_numbers.md` 5절 '의(재)' 열의 출처는 재채점 결과 파일
  `results/revision/semantic_scores/{E1-R1,E2-A1-1}-sem-p1-retry/grades.jsonl` 이다.
  재채점 전체 요약은 `results/revision/reports/semantic_retry_report.md` 에 있다.
- `results/revision/semantic_scores/` 의 채점 결과 폴더는 연구 규칙에 따라 커밋하지 않았다(시험 호출 `probe-E1-R1` 만 추적).
  따라서 저장소만으로는 이 열과 의미 채점 열을 다시 계산할 수 없고, 공개할 때 이 폴더를 함께 낼지 따로 정해야 한다.
