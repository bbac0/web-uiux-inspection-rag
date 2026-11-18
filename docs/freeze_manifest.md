# 동결 태그와 SHA256 매니페스트

작성: `python tools/make_freeze_manifest_doc.py` (git 조회만, 태그·커밋은 고치지 않음).
매니페스트 = 그 태그 시점에 동결된 파일의 SHA-256 목록(CSV). 'blob SHA-256' 은 태그 시점 매니페스트 파일 자체의 해시.

매니페스트 경로: M1 = `results/revision/freeze_manifest.csv`,
M2 = `results/revision/freeze_manifest_v6.csv`,
M3 = `results/revision/e9/freeze_manifest_e9.csv`. 종류: 주석 = 주석 태그, 가벼움 = 가벼운 태그. 날짜는 KST(+09:00).

| 태그 | 종류 | 커밋 | 커밋 날짜 | 매니페스트 | 행 | blob SHA-256 (앞 12자) |
|---|---|---|---|---|---|---|
| `exp-freeze-v1` | 주석 | `a8d2997b316a` | 2026-11-11 15:24 | M1 | 230 | `7c96e809c9ad` |
| `exp-freeze-v2` | 주석 | `e567d23a845e` | 2026-11-11 15:35 | M1 | 230 | `6af834800587` |
| `exp-freeze-v3` | 주석 | `c077d42316bf` | 2026-11-12 09:26 | M1 | 232 | `7c6bbd632281` |
| `exp-freeze-v4` | 주석 | `d65dfbd3cbf0` | 2026-11-12 09:46 | M1 | 234 | `e822dfaa88f8` |
| `exp-freeze-v5` | 주석 | `e81a67bea2dd` | 2026-11-13 00:00 | M1 | 261 | `9258a7c788c3` |
| `exp-freeze-v6-semretry` | 가벼움 | `1e59f17c7ad3` | 2026-11-13 21:50 | M2 | 298 | `b8e63b816bf7` |
| `exp-freeze-e9-v1` | 주석 | `2598e526a572` | 2026-11-13 00:50 | M3 | 114 | `c4c9ad1e4c4c` |
| `exp-freeze-e9-v2` | 주석 | `8c1d0d84f958` | 2026-11-13 01:04 | M3 | 130 | `9ebc4efd369c` |
| `exp-freeze-e9-v3` | 주석 | `50c5efbbe731` | 2026-11-13 11:45 | M3 | 136 | `7534f6ff1724` |
| `exp-freeze-e9-v4` | 가벼움 | `bd0940f0145f` | 2026-11-13 21:56 | M3 | 136 | `4d30fdcbbfc9` |

출처: `git tag`, `git rev-list -n1 <태그>`, `git show <태그>:<매니페스트>`

- v1~v5 는 같은 경로 `freeze_manifest.csv` 를 태그마다 갱신했다(태그 시점 내용이 다르다).
- 커밋 해시 전체는 `git rev-list -n1 <태그>` 로 확인한다.
