"""
공개 전 개인 문자열 점검 (읽기 전용, 자동 수정 없음, API 호출 없음).

검사 범위: `git ls-files -co --exclude-standard` (추적 파일 + 무시되지 않은 미추적 파일: 평가자 CSV, intake 복사본 포함)
          또는 --root 로 준 폴더 아래 모든 파일. 이진 파일(앞 8KB 에 NUL)과 `.env`/`.env.*` 경로는 읽지 않는다.
분류: aternos, 이메일, 전화번호, 사용자 홈 경로, 키·토큰 형태, 신원 문자열(이름·별명).
신원 문자열은 코드에 적지 않고 실행할 때 읽는다: git config user.name, user.email(과 그 @ 앞부분),
  홈 폴더 이름, 환경변수 PERSONAL_NAMES(쉼표로 구분; 평가자 이름·별명을 연구자가 넣는다).
출력:
  --out      가린 목록 CSV(일치 문자열과 맥락 속 개인 문자열을 ⟨분류⟩ 로 바꿈). 저장소에 둘 수 있다.
  --raw-out  가리지 않은 목록 CSV. 저장소 밖(예: 임시 폴더)에만 쓴다. 저장소 안 경로면 거부한다.
맥락: 일치 부분 앞뒤 20자.

  python tools/scan_personal.py --out results/revision/reports/public_prep_findings.csv --raw-out <저장소 밖 경로>
"""
import argparse
import csv
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def identity():
    ids = set()
    name, email = git("config", "user.name"), git("config", "user.email")
    for x in (name, email, email.split("@")[0] if email else "", os.path.basename(os.path.expanduser("~"))):
        if x and len(x) >= 3:
            ids.add(x)
    for x in os.environ.get("PERSONAL_NAMES", "").split(","):
        if x.strip():
            ids.add(x.strip())
    return sorted(ids, key=len, reverse=True)


def patterns(ids):
    P = [("aternos", re.compile(r"aternos", re.I)),
         ("키·토큰", re.compile(r"AIza[0-9A-Za-z_\-]{35}|sk-ant-[0-9A-Za-z_\-]{20,}|\bsk-[A-Za-z0-9]{20,}|"
                              r"\bgh[pousr]_[A-Za-z0-9]{36,}|\bxox[baprs]-[A-Za-z0-9-]{10,}|"
                              r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                              r"\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-+/]{20,}",
                              re.I)),
         ("이메일", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
         ("전화번호", re.compile(r"(?<![\d-])(?:\+82[-. ]?)?0(?:1[016789]|2|[3-6][1-5])[-. )]\d{3,4}[-. ]\d{4}(?![\d-])")),
         ("홈 경로", re.compile(r"\b[A-Za-z]:(?:\\\\|\\|/)+Users(?:\\\\|\\|/)+[^\\/\s\"'<>|,;:]+|"
                              r"(?<![\w:])/(?:mnt/)?c/Users/[^/\s\"']+|(?<![\w])/home/[^/\s\"']+", re.I))]
    if ids:
        P.append(("신원 문자열", re.compile("|".join(
            (r"(?<![0-9A-Za-z])" + re.escape(x) + r"(?![0-9A-Za-z])") if x.isascii() else re.escape(x) for x in ids),
            re.I)))
    return P


def files(root):
    if root:
        for d, _, fs in os.walk(root):
            for f in fs:
                yield os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, "/")
    else:
        yield from (f for f in git("ls-files", "-co", "--exclude-standard").splitlines() if f)


def mask(text, P):
    for cat, pat in P:
        text = pat.sub(f"⟨{cat}⟩", text)
    return text


def scan(paths, P):
    out = []
    for rel in paths:
        b = os.path.basename(rel)
        if b == ".env" or b.startswith(".env."):
            continue
        p = os.path.join(ROOT, rel)
        try:
            with open(p, "rb") as f:
                if b"\0" in f.read(8192):
                    continue
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            seen = []
            for cat, pat in P:
                for m in pat.finditer(line):
                    if any(s <= m.start() < e for s, e in seen):
                        continue
                    seen.append(m.span())
                    ctx = line[max(0, m.start() - 20):m.end() + 20]
                    out.append({"file": rel, "line": ln, "category": cat, "match": m.group(0), "context": ctx})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw-out", required=True)
    a = ap.parse_args(argv)
    raw = os.path.abspath(a.raw_out)
    if raw.startswith(ROOT + os.sep):
        raise SystemExit("--raw-out 는 저장소 밖이어야 한다")
    P = patterns(identity())
    res = scan(files(a.root), P)
    cols = ["file", "line", "category", "match", "context"]
    with open(raw, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(res)
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in res:
            w.writerow({**r, "file": mask(r["file"], P), "match": f"⟨{r['category']}⟩ (길이 {len(r['match'])})",
                        "context": mask(r["context"], P)})
    from collections import Counter
    print(f"{len(res)} hits; " + ", ".join(f"{k} {v}" for k, v in Counter(r["category"] for r in res).most_common()))


if __name__ == "__main__":
    sys.exit(main())
