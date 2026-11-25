# Capstan release build: the app bundle, the GitHub installer and the Microsoft Store package.
#
#   .\packaging\build.ps1              # bundle + installer + MSIX
#   .\packaging\build.ps1 -Skip msix   # leave a step out (bundle, installer, msix)
#
# Needs: .venv with packaging\requirements-lock.txt (see packaging\README.md),
#        Inno Setup 6 (installer), Windows 10/11 SDK (MSIX: makeappx.exe).
# Output: packaging\out\Capstan-<ver>-Setup.exe and Capstan-<ver>.msix
param([string[]]$Skip = @())
$ErrorActionPreference = 'Stop'

# Windows PowerShell 5.1 turns a native tool's stderr log lines into errors: run tools
# with that switched off and judge them by their exit code instead.
function Invoke-Tool([string]$what, [scriptblock]$cmd) {
  $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try { & $cmd 2>&1 | ForEach-Object { "$_" } } finally { $ErrorActionPreference = $prev }
  if ($LASTEXITCODE) { throw "$what failed (exit $LASTEXITCODE)" }
}

$root = Split-Path -Parent $PSScriptRoot
$pkg  = $PSScriptRoot
$work = Join-Path $pkg 'build'
$dist = Join-Path $pkg 'dist'
$out  = Join-Path $pkg 'out'
New-Item -ItemType Directory -Force $work, $out | Out-Null

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw ".venv not found. See packaging\README.md." }

# One version for everything: VERSION in app\api.py.
$m = Select-String -Path (Join-Path $root 'app\api.py') -Pattern '^VERSION = "([0-9]+\.[0-9]+\.[0-9]+)"'
if (-not $m) { throw 'VERSION = "x.y.z" not found in app\api.py' }
$ver = $m.Matches[0].Groups[1].Value
$v = $ver.Split('.')
Write-Host "Capstan $ver" -ForegroundColor White

# ── 1. App bundle (PyInstaller) ─────────────────────────────────────────────
if ($Skip -notcontains 'bundle') {
  $vi = @"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($($v[0]), $($v[1]), $($v[2]), 0), prodvers=($($v[0]), $($v[1]), $($v[2]), 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'VULLKI'),
      StringStruct('FileDescription', 'Capstan'),
      StringStruct('FileVersion', '$ver'),
      StringStruct('InternalName', 'Capstan'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 VULLKI. MIT License.'),
      StringStruct('OriginalFilename', 'Capstan.exe'),
      StringStruct('ProductName', 'Capstan'),
      StringStruct('ProductVersion', '$ver')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@
  [IO.File]::WriteAllText((Join-Path $work 'version_info.txt'), $vi, (New-Object Text.UTF8Encoding $false))
  Invoke-Tool 'PyInstaller' { & $py -m PyInstaller --noconfirm --clean --log-level WARN --distpath $dist --workpath (Join-Path $work 'pyi') (Join-Path $pkg 'capstan.spec') }
  $bad = Get-ChildItem -Recurse (Join-Path $dist 'Capstan') -Filter 'Satoshi-*'
  if ($bad) { throw "Satoshi must not be bundled: $($bad.FullName -join ', ')" }
}
$app = Join-Path $dist 'Capstan'
if (-not (Test-Path (Join-Path $app 'Capstan.exe'))) { throw "No bundle at $app" }

# ── 2. Installer for GitHub (Inno Setup) ────────────────────────────────────
if ($Skip -notcontains 'installer') {
  $iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $iscc) { throw 'Inno Setup 6 not found (winget install JRSoftware.InnoSetup)' }
  Invoke-Tool 'Inno Setup' { & $iscc /Qp "/DAppVersion=$ver" "/DSourceDir=$app" "/DOutDir=$out" (Join-Path $pkg 'installer\capstan.iss') }
}

# ── 3. Microsoft Store package (MSIX) ───────────────────────────────────────
if ($Skip -notcontains 'msix') {
  $idFile = Join-Path $pkg 'msix\identity.json'
  if (-not (Test-Path $idFile)) { $idFile = Join-Path $pkg 'msix\identity.example.json' }
  $id = Get-Content -Raw -Encoding UTF8 $idFile | ConvertFrom-Json
  if ($idFile -like '*example*') { Write-Warning 'Using placeholder Store identity (msix\identity.example.json): fine for testing, not for the Store.' }

  $sdk = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
         Sort-Object FullName -Descending | Select-Object -First 1
  if (-not $sdk) { throw 'makeappx.exe not found: install the Windows 10/11 SDK' }

  $layout = Join-Path $work 'msix-layout'
  if (Test-Path $layout) { Remove-Item -Recurse -Force $layout }
  Copy-Item -Recurse $app $layout
  Copy-Item -Recurse (Join-Path $pkg 'msix\Assets') (Join-Path $layout 'Assets')
  $manifest = (Get-Content -Raw -Encoding UTF8 (Join-Path $pkg 'msix\AppxManifest.xml')).
    Replace('{{NAME}}', $id.name).Replace('{{PUBLISHER}}', $id.publisher).
    Replace('{{PUBLISHER_DISPLAY}}', $id.publisher_display).Replace('{{DISPLAY_NAME}}', $id.display_name).
    Replace('{{VERSION}}', "$ver.0")
  [IO.File]::WriteAllText((Join-Path $layout 'AppxManifest.xml'), $manifest, (New-Object Text.UTF8Encoding $false))

  # resources.pri maps "Assets\StoreLogo.png" to its scale/targetsize variants.
  $makepri = Join-Path $sdk.DirectoryName 'makepri.exe'
  $pricfg = Join-Path $work 'priconfig.xml'
  Invoke-Tool 'makepri createconfig' { & $makepri createconfig /cf $pricfg /dq en-US /pv 10.0.0 /o } | Out-Null
  # One .msix loads only resources.pri: drop the default <packaging> block, or makepri splits
  # the 125% and 150% logos into resources.scale-*.pri files that never get read.
  $cfg = [IO.File]::ReadAllText($pricfg) -replace '(?s)\s*<packaging>.*?</packaging>', ''
  [IO.File]::WriteAllText($pricfg, $cfg, (New-Object Text.UTF8Encoding $false))
  Invoke-Tool 'makepri new' { & $makepri new /pr $layout /cf $pricfg /mn (Join-Path $layout 'AppxManifest.xml') /of (Join-Path $layout 'resources.pri') /o } | Out-Null

  $msix = Join-Path $out "Capstan-$ver.msix"
  Invoke-Tool 'makeappx' { & $sdk.FullName pack /o /h SHA256 /d $layout /p $msix } | Select-Object -Last 2
}

Get-ChildItem $out | Select-Object Name, @{n='MB'; e={[math]::Round($_.Length / 1MB, 1)}} | Format-Table -AutoSize
