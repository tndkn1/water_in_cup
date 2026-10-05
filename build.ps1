# Builds dist/WaterCup-<version>.zip, ready to drag and drop into Content Manager.
# Usage: pwsh ./build.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = $PSScriptRoot
$manifest = Join-Path $root 'apps/lua/WaterCup/manifest.ini'
$version = (Select-String -Path $manifest -Pattern '^VERSION\s*=\s*(\S+)').Matches[0].Groups[1].Value

$dist = Join-Path $root 'dist'
$stage = Join-Path $dist 'stage'
$zip = Join-Path $dist "WaterCup-$version.zip"

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
Copy-Item (Join-Path $root 'apps') $stage -Recurse
Copy-Item (Join-Path $root 'LICENSE') (Join-Path $stage 'apps/lua/WaterCup')

if (Test-Path $zip) { Remove-Item $zip -Force }
[System.IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip)
Remove-Item $stage -Recurse -Force

Write-Host "Built $zip"
