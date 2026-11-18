"""
공개본의 Windows 사용자 홈 경로를 <HOME> 으로 바꾼다 (결정적, API 호출 없음).

규칙(대소문자 무시):
  <드라이브>:\\Users\\<이름>, <드라이브>:\\\\Users\\\\<이름>(JSON 이스케이프), <드라이브>:/Users/<이름>
  /c/Users/<이름>, /mnt/c/Users/<이름>
  → '<HOME>' (드라이브부터 사용자 이름까지를 바꾸고, 그 뒤 경로는 그대로 둔다).
  <이름> = 경로 구분자, 공백, 따옴표, <>|,;:*? 가 아닌 글자들.
대상: --root 아래 모든 파일 중 텍스트 파일(앞 8KB 에 NUL 이 없는 파일). 파일은 바이트 그대로 읽고 쓰므로
      줄바꿈·인코딩은 바뀌지 않는다. 경로를 정렬해 처리하므로 같은 입력이면 같은 출력이 나온다.
기록(--root 에, 이미 있으면 거부):
  SHA256SUMS.original  바뀐 파일의 치환 전 SHA-256 (형식: '<해시>  <경로>')
  SHA256SUMS.public    바뀐 파일의 치환 후 SHA-256
동결 매니페스트와 run 폴더의 SHA256SUMS 는 원본(치환 전) 기준이다. 원본을 가진 사람은 이 스크립트로 같은 공개본을 만든다.

  python scripts/redact_home_paths.py --root .
"""
import argparse
import hashlib
import os
import re
import sys

SEP = r"(?:\\\\|\\|/)+"
NAME = r"[^\\/\s\"'<>|,;:*?]+"
PAT = re.compile(rb"(?<![A-Za-z])[A-Za-z]:" + SEP.encode() + rb"[Uu][Ss][Ee][Rr][Ss]" + SEP.encode() + NAME.encode()
                 + rb"|(?<![\w])(?:/mnt)?/[cC]/[Uu][Ss][Ee][Rr][Ss]/" + NAME.encode())
OUT = ("SHA256SUMS.original", "SHA256SUMS.public")


def is_text(data):
    return b"\0" not in data[:8192]


def redact(data):
    return PAT.subn(b"<HOME>", data)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    for o in OUT:
        if os.path.exists(os.path.join(root, o)):
            raise SystemExit(f"이미 있음(덮어쓰지 않음): {o}")
    paths = sorted(os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
                   for d, _, fs in os.walk(root) for f in fs)
    orig, pub, total = [], [], 0
    for rel in paths:
        if rel in OUT or rel == "scripts/redact_home_paths.py":
            continue
        p = os.path.join(root, rel)
        data = open(p, "rb").read()
        if not is_text(data):
            continue
        new, n = redact(data)
        if n:
            orig.append(f"{hashlib.sha256(data).hexdigest()}  {rel}")
            pub.append(f"{hashlib.sha256(new).hexdigest()}  {rel}")
            open(p, "wb").write(new)
            total += n
    for name, lines in zip(OUT, (orig, pub)):
        open(os.path.join(root, name), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print(f"files changed {len(orig)}, replacements {total}")


if __name__ == "__main__":
    sys.exit(main())
