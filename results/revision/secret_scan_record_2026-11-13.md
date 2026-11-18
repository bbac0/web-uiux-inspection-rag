# 확정 기록: 저장소 API 키 패턴 점검 (2026-11-13)

- 실행: `python tools/scan_secrets.py` (Claude Code 세션, 키 값은 출력하지 않음), 점검 시점 HEAD `db8fe98d18bf34f5547bd8ccea91360f99b0ccff`, 종료 코드 0
- 이 세션에는 GEMINI_API_KEY 만 있어 실제 값 대조는 그 키만 했다. ANTHROPIC_API_KEY·GOOGLE_API_KEY 실제 값 대조는 연구자가 연구자 창에서 직접 실행한다.

```
== API 키 점검 결과 (키 값은 출력하지 않음) ==
커밋 수: 37, 검사한 blob: 747 (69.7 MB), 작업 트리 파일: 861
실제 값 검사: GEMINI_API_KEY: checked, GOOGLE_API_KEY: not set in this process: exact-value check skipped, ANTHROPIC_API_KEY: not set in this process: exact-value check skipped
.env 경로: 이력 없음, 작업 트리(추적/미무시) 없음, .env 가 .gitignore 로 무시됨: True
[이력] 일치 0건
[작업 트리] 일치 0건
```
