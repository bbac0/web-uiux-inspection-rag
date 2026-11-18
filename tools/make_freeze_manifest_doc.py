"""동결 태그 표 docs/freeze_manifest.md 생성 (읽기 전용 git 조회, API 호출 없음). 태그와 커밋은 고치지 않는다."""
import hashlib
import subprocess

MAN = {"exp-freeze-v": "results/revision/freeze_manifest.csv",
       "exp-freeze-v6-semretry": "results/revision/freeze_manifest_v6.csv",
       "exp-freeze-e9-v": "results/revision/e9/freeze_manifest_e9.csv"}
ORDER = [f"exp-freeze-v{i}" for i in range(1, 6)] + ["exp-freeze-v6-semretry"] + [f"exp-freeze-e9-v{i}" for i in range(1, 5)]


def git(*a, text=True):
    return subprocess.run(["git", *a], capture_output=True, text=text, check=True).stdout


def manifest_for(tag):
    if tag == "exp-freeze-v6-semretry":
        return MAN[tag]
    return MAN["exp-freeze-e9-v"] if tag.startswith("exp-freeze-e9-v") else MAN["exp-freeze-v"]


L = ["# 동결 태그와 SHA256 매니페스트", "",
     "작성: `python tools/make_freeze_manifest_doc.py` (git 조회만, 태그·커밋은 고치지 않음).",
     "매니페스트 = 그 태그 시점에 동결된 파일의 SHA-256 목록(CSV). 'blob SHA-256' 은 태그 시점 매니페스트 파일 자체의 해시.", "",
     "매니페스트 경로: M1 = `results/revision/freeze_manifest.csv`,",
     "M2 = `results/revision/freeze_manifest_v6.csv`,",
     "M3 = `results/revision/e9/freeze_manifest_e9.csv`. 종류: 주석 = 주석 태그, 가벼움 = 가벼운 태그. 날짜는 KST(+09:00).", "",
     "| 태그 | 종류 | 커밋 | 커밋 날짜 | 매니페스트 | 행 | blob SHA-256 (앞 12자) |",
     "|---|---|---|---|---|---|---|"]
CODE = {MAN["exp-freeze-v"]: "M1", MAN["exp-freeze-v6-semretry"]: "M2", MAN["exp-freeze-e9-v"]: "M3"}
for t in ORDER:
    c = git("rev-list", "-n1", t).strip()
    kind = "주석" if git("cat-file", "-t", t).strip() == "tag" else "가벼움"
    d = git("log", "-1", "--format=%cI", t).strip()[:16].replace("T", " ")
    m = manifest_for(t)
    blob = subprocess.run(["git", "show", f"{t}:{m}"], capture_output=True, check=True).stdout
    rows = blob.decode("utf-8-sig").count("\n") - 1
    L.append(f"| `{t}` | {kind} | `{c[:12]}` | {d} | {CODE[m]} | {rows} | `{hashlib.sha256(blob).hexdigest()[:12]}` |")
L += ["", "출처: `git tag`, `git rev-list -n1 <태그>`, `git show <태그>:<매니페스트>`", "",
      "- v1~v5 는 같은 경로 `freeze_manifest.csv` 를 태그마다 갱신했다(태그 시점 내용이 다르다).",
      "- 커밋 해시 전체는 `git rev-list -n1 <태그>` 로 확인한다.", ""]
open("docs/freeze_manifest.md", "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("docs/freeze_manifest.md", len(ORDER))
