# analysis_plan 부록: E6b axe-core 추가 스캔 (WCAG 2.2 규칙 켬)

작성 2026-11-19. **스캔 실행 전에** 커밋한다. 연구자 지시(2026-11-19)에 따른 사후 추가 스캔이며 E6 결과와 부록
`analysis_plan_addendum_e6.md` 는 고치지 않는다. API 호출 없음(로컬 브라우저 스캔).

## 설정

- axe-core: 저장소 루트 `axe.min.js` (4.14.0, E6 와 같은 파일). 실행 중 `axe.version` 이 4.14.0 이 아니면 멈춘다.
- 설정 C = E6 설정 B(duplicate-id, duplicate-id-active, duplicate-id-aria 켬) + `axe.getRules(["wcag22a", "wcag22aa"])` 로
  얻은 모든 규칙을 `enabled: true` 로 켬(target-size 포함). 켠 규칙 목록은 run_log.json 에 기록한다.
- 뷰포트: ① 1280x800, ② 390x844(모바일, E6·E4 와 같음). 렌더링·대기·UA·대상(testbed_200 200페이지)은 E6 와 같다.
- 출력(새 폴더, 덮어쓰지 않음): `results/revision/e6b/scan_C_{1280,390}.json`, `run_log.json`, `SHA256SUMS`.

## 집계

- 유형별 대응 규칙은 E6 부록 (c) 표 그대로 쓴다(대비 color-contrast, 중복 ID duplicate-id 계열, 버튼 target-size,
  모바일·용어 없음). 표 형식도 E6 보고서 2절과 같다(라벨 nominal 과 같은 뷰포트의 effective).
- 기술 집계만 하고 검정은 하지 않는다.
