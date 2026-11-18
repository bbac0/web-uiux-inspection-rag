"""
공개용 스테이징 스냅샷 (API 호출 없음). 원본 파일·커밋·태그는 건드리지 않고 스테이징 폴더에만 쓴다.

1. `git -c core.autocrlf=false archive HEAD` 를 스테이징에 푼다(.git 제외, 추적 파일만, 커밋된 바이트 그대로).
2. 제외 규칙에 걸리는 경로를 풀지 않는다: .env·.env.*, *.pem·*.key·*.p12, 이름에 credential 이 든 파일,
   __pycache__·*.pyc, 캐시 폴더(.cache, .pytest_cache, chroma_db, node_modules), RAG 근거 PDF
   (data/gov_guide.pdf, data/gov_check.pdf; 해시와 재생성 방법은 data/README_SOURCES.md).
3. 이미 알려진 aternos 문자열: 스테이징의 results/revision/human_eval/intake_all.md 에서만 [REDACTED] 로 바꾼다.
4. 평가자 CSV(추적하지 않는 *_filled*.csv)의 공개용 복사본을 같은 경로에 넣는다(내용은 원본 그대로).
   원본·복사본 SHA-256 을 PUBLIC_RATER_DATA.md 에 적는다. 작업용 복사본(intake_hit52/)은 넣지 않는다.
5. 추적하지 않는 의미 채점 결과 results/revision/semantic_scores/ 를 그대로 복사한다.
6. 스테이징 README.md 끝에 경로 치환·해시 안내 절을 더한다.
7. 스테이징 안의 scripts/redact_home_paths.py 로 홈 경로를 <HOME> 으로 바꾸고 SHA256SUMS.original·public 을 만든다.

  python tools/build_public_staging.py [--out repo_public_staging] [--meta <요약 JSON 경로>]   # 이미 있으면 거부
"""
import argparse
import glob
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCL = re.compile(r"(^|/)(\.env(\..*)?|.*\.(pem|key|p12)|[^/]*credential[^/]*)$|(^|/)(__pycache__|\.cache|\.pytest_cache|"
                  r"chroma_db|node_modules)(/|$)|\.pyc$|^data/gov_(guide|check)\.pdf$", re.I)
INTAKE = "results/revision/human_eval/intake_all.md"
SEM = "results/revision/semantic_scores"
README_NOTE = r"""
## 공개본의 경로 치환과 해시

동결 매니페스트와 SHA256SUMS의 해시는 원본(경로 치환 전) 기준이며, 치환은 scripts/redact_home_paths.py로 재현된다.

- 공개본에서는 Windows 사용자 홈 경로(드라이브:\Users\<이름> 와 슬래시 표기)를 `<HOME>` 으로 바꾸었다.
- 바뀐 파일의 치환 전 해시는 `SHA256SUMS.original`, 치환 후 해시는 `SHA256SUMS.public` 에 있다(형식 `<해시>  <경로>`).
- 원본 저장소 내용에 `python scripts/redact_home_paths.py --root <폴더>` 를 실행하면 같은 공개본이 나온다.
- RAG 근거 PDF 두 개는 공개본에 넣지 않았다. 해시와 인덱스 재생성 방법은 `data/README_SOURCES.md` 에 있다.
- 평가자 CSV 공개용 복사본과 원본 해시는 `PUBLIC_RATER_DATA.md` 에 있다.
"""


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "repo_public_staging"))
    ap.add_argument("--meta")
    a = ap.parse_args(argv)
    ST = os.path.abspath(a.out)
    if os.path.exists(ST):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {ST}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
    meta_path = a.meta or os.path.join(ROOT, "results/revision/reports", f"public_staging_meta_{head[:12]}.json")
    if os.path.exists(meta_path):
        raise SystemExit(f"이미 있음(덮어쓰지 않음): {meta_path}")
    tar = subprocess.run(["git", "-c", "core.autocrlf=false", "archive", "--format=tar", "HEAD"],
                         capture_output=True, cwd=ROOT, check=True).stdout
    excluded = []
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        members = []
        for m in t.getmembers():
            if EXCL.search(m.name):
                excluded.append(m.name)
            else:
                members.append(m)
        t.extractall(ST, members=members)
    red = 0
    p = os.path.join(ST, INTAKE)
    if os.path.exists(p):
        s = open(p, "rb").read()
        new, red = re.subn(rb"[^\s|`'\"]*aternos[^\s|`'\"]*", b"[REDACTED]", s, flags=re.I)
        if red:
            open(p, "wb").write(new)
    raters = sorted(f.replace(os.sep, "/") for f in glob.glob(os.path.join(ROOT, "results/revision/human_eval/**/*filled*.csv"),
                                                              recursive=True) if "intake_hit52" not in f)
    rows = []
    for f in raters:
        rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
        dst = os.path.join(ST, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(f, dst)
        rows.append((rel, sha(f), sha(dst)))
    L = ["# 평가자 CSV 공개용 복사본", "",
         f"스냅샷: 커밋 `{head}` 의 추적 파일 + 아래 평가자 CSV 공개용 복사본. 작성: `tools/build_public_staging.py`.",
         "원본은 연구 저장소에서 추적하지 않는 읽기 전용 파일이다. 복사본 내용은 원본과 같다(비고는 개인 문자열 점검",
         "`tools/scan_personal.py` 결과 해당 없음, 고친 값 없음). 아래 표로 원본과 같은지 확인할 수 있다.", "",
         "| 경로 | 원본 SHA-256 | 복사본 SHA-256 |", "|---|---|---|"]
    L += [f"| `{r}` | `{x}` | `{y}` |" for r, x, y in rows]
    L += ["", "작업용 복사본(`results/revision/human_eval/e9_eval/intake_hit52/`)은 원본과 같아 넣지 않았다.", ""]
    open(os.path.join(ST, "PUBLIC_RATER_DATA.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L))
    sem_added = 0
    for d, _, fs in os.walk(os.path.join(ROOT, SEM)):
        for f in fs:
            src = os.path.join(d, f)
            rel = os.path.relpath(src, ROOT).replace(os.sep, "/")
            dst = os.path.join(ST, rel)
            if not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
                sem_added += 1
    rp = os.path.join(ST, "README.md")
    b = open(rp, "rb").read()
    nl = "\r\n" if b"\r\n" in b else "\n"
    if not b.endswith(nl.encode()):
        b += nl.encode()
    open(rp, "wb").write(b + README_NOTE.replace("\n", nl).encode("utf-8"))
    r = subprocess.run([sys.executable, "-B", os.path.join(ST, "scripts", "redact_home_paths.py"), "--root", ST],
                       capture_output=True, text=True, check=True)
    m = re.search(r"files changed (\d+), replacements (\d+)", r.stdout)
    n, size = 0, 0
    for d, _, fs in os.walk(ST):
        for f in fs:
            n += 1
            size += os.path.getsize(os.path.join(d, f))
    meta = {"head": head, "archive": "git -c core.autocrlf=false archive HEAD", "files": n, "bytes": size,
            "excluded_from_archive": excluded, "aternos_redactions": red, "semantic_scores_added": sem_added,
            "home_redaction": {"files": int(m.group(1)), "replacements": int(m.group(2))},
            "rater_copies": [{"path": x, "sha256_original": y, "sha256_copy": z} for x, y, z in rows]}
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{ST}: {n} files, {size} bytes; excluded {len(excluded)}; aternos {red}; rater copies {len(rows)}; "
          f"semantic_scores added {sem_added}; home redaction {m.group(1)} files / {m.group(2)} places; meta {meta_path}")


if __name__ == "__main__":
    sys.exit(main())
