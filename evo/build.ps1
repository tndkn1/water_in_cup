# Builds dist/WaterCupEVO-<version>.zip containing a standalone WaterCupEVO.exe.
# Usage: pwsh ./evo/build.ps1   (needs Python; installs PyInstaller if missing)
$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$src = Join-Path $PSScriptRoot 'water_cup_evo.py'
$version = (Select-String -Path $src -Pattern "^VERSION = '(.+)'").Matches[0].Groups[1].Value

$dist = Join-Path $root 'dist'
$work = Join-Path $dist 'evo-build'
$stage = Join-Path $dist 'evo-stage'
$zip = Join-Path $dist "WaterCupEVO-$version.zip"

python -m pip install --quiet --disable-pip-version-check pyinstaller
if ($LASTEXITCODE) { throw 'pip install pyinstaller failed' }

foreach ($d in $work, $stage) { if (Test-Path $d) { Remove-Item $d -Recurse -Force } }
python -m PyInstaller --noconfirm --onefile --windowed --name WaterCupEVO `
  --distpath $stage --workpath $work --specpath $work $src
if ($LASTEXITCODE) { throw 'PyInstaller failed' }
Copy-Item (Join-Path $root 'LICENSE') $stage

if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip
Remove-Item $work, $stage -Recurse -Force

Write-Host "Built $zip"
