# 표준 용어 위반 주입: 정확한 문자열 쌍

- 주입 규칙: `experiments/generate_200_testbed.py` 의 `DEF_OPS_01` = `html.replace("로그인", "접속하기")` (모든 출현 치환).
- 아래 표는 각 템플릿 원문에서 '로그인'이 들어 있는 요소를 찾아, 치환 전후 문자열을 그대로 적은 것이다 (요소 단위).
- `href="/login"` 의 영문 `login` 은 바뀌지 않는다.

| 템플릿 | 용어 위반 페이지 수 | 위치 | 원래 문자열 | 주입 후 문자열 |
|---|---:|---|---|---|
| `portal_main` | 4 | `<a>` | `<a href="/login">로그인</a>` | `<a href="/login">접속하기</a>` |
| `board_list` | 6 | `<a>` | `<a href="/login">로그인</a>` | `<a href="/login">접속하기</a>` |
| `login_page` | 6 | `<title>` | `<title>로그인 - 대한민국 정부</title>` | `<title>접속하기 - 대한민국 정부</title>` |
| `login_page` | 6 | `<h2>` | `<h2>로그인</h2>` | `<h2>접속하기</h2>` |
| `login_page` | 6 | `<button>` | `<button class="login-btn">로그인</button>` | `<button class="login-btn">접속하기</button>` |
| `detail_page` | 4 | `<a>` | `<a href="/login">로그인</a>` | `<a href="/login">접속하기</a>` |
| `dashboard` | 4 | `<a>` | `<a href="/login">로그인</a>` | `<a href="/login">접속하기</a>` |
| `search_result` | 1 | `<a>` | `<a href="/login">로그인</a>` | `<a href="/login">접속하기</a>` |
| `faq_page` | 5 | `<a>` | `<a href="/login">로그인</a>` | `<a href="/login">접속하기</a>` |
| `form_page` | 3 | - | ('로그인' 없음, 주입되지 않음) | - |
| `terms_page` | 6 | `<a>` | `<a href="/login">로그인</a>` | `<a href="/login">접속하기</a>` |
| `contact_page` | 6 | `<a>` | `<a href="/login">로그인</a>` | `<a href="/login">접속하기</a>` |

치환되는 단어 쌍은 모든 템플릿에서 하나다: **`로그인` → `접속하기`**. login_page 만 세 곳(`<title>`, `<h2>`, `<button>`)이 바뀌고, 나머지 템플릿은 `<a href="/login">` 링크 텍스트 한 곳이 바뀐다. form_page 에는 '로그인'이 없어 용어 위반 3페이지(page_028, page_038, page_168)는 주입되지 않았다.
