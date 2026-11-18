<#
공개본 시크릿·개인 문자열 점검 (읽기 전용). 키 값과 이름은 출력하지 않고, 일치한 파일과 줄 번호만 출력한다.

검사 내용 (이 스크립트가 있는 폴더의 상위 폴더 = 공개본 루트 아래 모든 파일)
  1. 실제 키 값: 환경변수 GEMINI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY 중 설정된 것의 값 그대로
  2. 키 형식: AIza...(Google), sk-ant-...(Anthropic)
  3. 개인 문자열: 환경변수 PERSONAL_NAMES 에 쉼표로 넣은 이름·별명 (대소문자 무시)

사용 방법 (PowerShell 창에서, 공개본 루트 폴더에서)
  $env:PERSONAL_NAMES = "이름1,별명1,이름2"     # 평가자 이름·별명 등을 쉼표로 구분
  # 키는 이미 환경변수에 있으면 그대로 둔다. 없으면 이 창에서만 설정한다(파일에 적지 않는다).
  powershell -ExecutionPolicy Bypass -File .\scripts\scan_secrets_public.ps1
  Remove-Item Env:PERSONAL_NAMES                 # 끝나면 지운다

출력 예: '키 값 일치 [GEMINI_API_KEY]: results\...\calls.jsonl:12'. 값이나 이름 자체는 출력하지 않는다.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$files = Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.FullName -ne $PSCommandPath }
$hits = 0

function Report($label, $found) {
    foreach ($m in $found) {
        $rel = $m.Path.Substring($root.Length).TrimStart('\')
        Write-Output ("{0}: {1}:{2}" -f $label, $rel, $m.LineNumber)
        $script:hits++
    }
}

foreach ($name in @('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'ANTHROPIC_API_KEY')) {
    $v = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrEmpty($v)) { Write-Output ("키 값 검사 안 함 [{0}]: 환경변수 없음" -f $name); continue }
    Report ("키 값 일치 [{0}]" -f $name) ($files | Select-String -SimpleMatch -Pattern $v)
}

Report '키 형식 일치 [AIza]' ($files | Select-String -CaseSensitive -Pattern 'AIza[0-9A-Za-z_\-]{35}')
Report '키 형식 일치 [sk-ant]' ($files | Select-String -CaseSensitive -Pattern 'sk-ant-[0-9A-Za-z_\-]{20,}')

$names = @()
if ($env:PERSONAL_NAMES) { $names = $env:PERSONAL_NAMES.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ } }
if ($names.Count -eq 0) { Write-Output '개인 문자열 검사 안 함: PERSONAL_NAMES 없음' }
$i = 0
foreach ($n in $names) {
    $i++
    Report ("개인 문자열 일치 [이름 {0}번]" -f $i) ($files | Select-String -SimpleMatch -Pattern $n)
}

Write-Output ("끝: 파일 {0}개 검사, 일치 {1}건" -f $files.Count, $hits)
