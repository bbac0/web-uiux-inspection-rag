# E9 테스트베드 (생성·결정적 검증만, API 호출 없음, 2026-11-13)

- 생성: `python experiments/revision/e9_generate.py` (시드 20261116, docs/e9_design.md v5). 다시 생성해도 바이트 단위로 같다(`testbed_e9_manifest.csv`).
- 서버: `python -m http.server 8090 --bind 127.0.0.1 --directory testbed_e9` (루트에 `/login/`, `/signup/` 목적지 페이지).
- 검증: `python experiments/revision/e9_verify.py` → `ground_truth_e9.csv`, `e9_verify_summary.json`
  (Chromium 1280x800, networkidle + 3초, page.content(); 30개 규격 검사, 로그인 링크 1280/768/390 가시성, 클릭 목적지, 주입 위치, 뷰포트 위치).
- 조건 입력: `e9_related_clause_chunks.csv`(6청크), `e9_fixed_long_chunks.csv`(9청크, `fixed_long_selection.json`), 91페이지 모두 같은 청크·같은 순서.
- 본문 재사용 규칙: 기존 10개 템플릿의 `<main>` 을 그대로 쓰고, 그 안의 `<a href="/login">로그인</a>` 만 지웠다(faq_page, terms_page, contact_page).
- 아직 하지 않은 것(연구자 승인 후): `exp-freeze-e9-v1` 태그, 러너의 E9 페이지 메타데이터 지원(현재 러너는 testbed_200 메타데이터만 읽음), 파일럿, 본 실행.
