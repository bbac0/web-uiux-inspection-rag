"""
저장소 공개 전 API 키 점검 (읽기 전용, 키 값은 절대 출력하지 않는다).

검사 범위
  1. 커밋 이력 전체: `git rev-list --all --objects` 의 모든 blob (모든 브랜치·태그에서 닿는 모든 버전)
  2. 작업 트리: git 이 추적하는 파일 + 추적하지 않지만 무시되지 않은 파일 (`git ls-files -co --exclude-standard`)
검사 패턴
  - Google API 키 형식: `AIza[0-9A-Za-z_-]{35}`
  - Anthropic 키 형식: `sk-ant-[0-9A-Za-z_-]{20,}`
  - 실제 값 일치: 환경변수 GEMINI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY 중 **이 프로세스에 설정된 것**의 값 그대로
    (설정되지 않은 변수는 '검사 안 함'으로 보고한다. 값은 메모리에서만 비교하고 출력·저장하지 않는다.)
예외
  - 경로 이름이 `.env` 또는 `.env.*` 인 파일은 내용을 읽지 않는다(연구 규칙: .env 는 읽지 않음). 대신 그런 경로가 이력이나
    작업 트리에 있는지 여부만 보고한다.
출력: 패턴별 일치 건수, 일치한 (커밋에서 처음 나타난 blob 의) 경로와 blob id 앞 10자, 일치 문자열의 길이.
      일치 문자열 자체나 그 일부(접두어 포함)는 출력하지 않는다.

  python tools/scan_secrets.py
"""
import os
import re
import subprocess
import sys
from collections import defaultdict

PATTERNS = {"google_api_key_format (AIza...)": re.compile(rb"AIza[0-9A-Za-z_\-]{35}"),
            "anthropic_key_format (sk-ant-...)": re.compile(rb"sk-ant-[0-9A-Za-z_\-]{20,}")}
ENV_VARS = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"]


def is_env_path(p):
    b = os.path.basename(p)
    return b == ".env" or b.startswith(".env.")


def git(*args, input_=None):
    return subprocess.run(["git", *args], capture_output=True, input=input_, check=True).stdout


def scan_bytes(data, values):
    hits = []
    for name, rx in PATTERNS.items():
        for m in rx.finditer(data):
            hits.append((name, len(m.group(0))))
    for var, val in values.items():
        if val and val.encode() in data:
            hits.append((f"exact value of ${var}", len(val)))
    return hits


def main():
    root = git("rev-parse", "--show-toplevel").decode().strip()
    os.chdir(root)
    values = {v: os.environ.get(v) for v in ENV_VARS}
    checked_vars = {v: ("checked" if values[v] else "not set in this process: exact-value check skipped") for v in ENV_VARS}

    # 1. 이력의 모든 blob
    objs = git("rev-list", "--all", "--objects").decode("utf-8", "replace").splitlines()
    blob_paths = defaultdict(set)
    for line in objs:
        parts = line.split(" ", 1)
        if len(parts) == 2:
            blob_paths[parts[0]].add(parts[1])
    types = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                input_="\n".join(blob_paths).encode()).decode().splitlines()
    blobs = [t.split()[0] for t in types if t.split()[1] == "blob"]
    env_in_history = sorted({p for b in blobs for p in blob_paths[b] if is_env_path(p)})
    hist_hits, n_scanned, bytes_scanned = [], 0, 0
    for i in range(0, len(blobs), 500):
        chunk = [b for b in blobs[i:i + 500] if not all(is_env_path(p) for p in blob_paths[b])]
        if not chunk:
            continue
        out = git("cat-file", "--batch", input_="\n".join(chunk).encode())
        pos = 0
        while pos < len(out):
            nl = out.index(b"\n", pos)
            sha, _typ, size = out[pos:nl].decode().split()
            size = int(size)
            data = out[nl + 1: nl + 1 + size]
            pos = nl + 1 + size + 1
            n_scanned += 1
            bytes_scanned += size
            for name, ln in scan_bytes(data, values):
                hist_hits.append({"where": "history", "blob": sha[:10], "paths": sorted(blob_paths[sha]), "pattern": name, "length": ln})

    # 2. 작업 트리
    files = git("ls-files", "-co", "--exclude-standard", "-z").decode("utf-8", "replace").split("\0")
    env_in_tree = sorted(f for f in files if f and is_env_path(f))
    tree_hits, n_files = [], 0
    for f in files:
        if not f or is_env_path(f) or not os.path.isfile(f):
            continue
        n_files += 1
        with open(f, "rb") as fh:
            data = fh.read()
        for name, ln in scan_bytes(data, values):
            tree_hits.append({"where": "working tree", "paths": [f], "pattern": name, "length": ln})
    env_ignored = subprocess.run(["git", "check-ignore", "-q", ".env"]).returncode == 0

    print("== API 키 점검 결과 (키 값은 출력하지 않음) ==")
    print(f"커밋 수: {len(git('rev-list', '--all').splitlines())}, 검사한 blob: {n_scanned} ({bytes_scanned / 2**20:.1f} MB), "
          f"작업 트리 파일: {n_files}")
    print("실제 값 검사:", ", ".join(f"{k}: {v}" for k, v in checked_vars.items()))
    print(f".env 경로: 이력 {env_in_history or '없음'}, 작업 트리(추적/미무시) {env_in_tree or '없음'}, "
          f".env 가 .gitignore 로 무시됨: {env_ignored}")
    for label, hits in (("이력", hist_hits), ("작업 트리", tree_hits)):
        agg = defaultdict(int)
        for h in hits:
            agg[h["pattern"]] += 1
        print(f"[{label}] 일치 {len(hits)}건" + (": " + ", ".join(f"{k} {v}건" for k, v in agg.items()) if hits else ""))
        for h in hits:
            print(f"   - {h['pattern']} | 길이 {h['length']} | {', '.join(h['paths'][:3])}" + (f" | blob {h['blob']}" if "blob" in h else ""))
    return 1 if (hist_hits or tree_hits or env_in_history or env_in_tree) else 0


if __name__ == "__main__":
    sys.exit(main())
