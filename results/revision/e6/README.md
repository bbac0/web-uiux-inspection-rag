# E6 axe-core 스캔 결과 폴더

사전 지정: `results/revision/analysis_plan_addendum_e6.md`. 스크립트: `experiments/revision/e6_axe_scan.py`.

## 실행 방식

- 도구: Playwright Chromium 151.0.7922.34 (Python),
  저장소 루트 `axe.min.js` (axe-core 4.14.0, SHA-256 20c09fe157a8a34a…)
  를 `page.add_script_tag(content=...)` 로 주입 후 `axe.run(document, options)`.
- 서버: `python -m http.server 8080 --bind 127.0.0.1 --directory <저장소 루트>`,
  URL `http://localhost:8080/testbed_200/page_XXX.html`.
- 대기: goto(wait_until='networkidle', timeout=30000) + 3000 ms (기존 파이프라인과 같음). UA 는 프로덕션과 같음.
- 뷰포트: 1280x800, 390x844 각각 새 브라우저 컨텍스트.
- 규칙 활성화: 설정 A 는 옵션 없음(기본).
  설정 B 는 `{rules: {duplicate-id, duplicate-id-active, duplicate-id-aria: {enabled: true}}}`.
  한 번 렌더링한 페이지에서 A, B 를 차례로 실행.
- 저장: 페이지별 violations·incomplete 전체, passes 는 규칙 ID 와 노드 수, inapplicable 은 규칙 ID.

## 파일

- `scan_A_1280.json`, `scan_B_1280.json`, `scan_A_390.json`, `scan_B_390.json`
- `run_log.json` (시작·끝 시각, 설정, 오류)
- `SHA256SUMS` (위 5개 파일)
- 스캔 시각 2026-11-13T14:38:46Z ~ 2026-11-13T15:05:25Z, 오류 0건.

