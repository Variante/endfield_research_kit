[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$version = "r2117"
$archiveSha256 = "6c4a8a3813864fefed081bbd337dbc0ad93bf88e0b92f5db98d7ab258b22dc6c"
$downloadUrl = "https://github.com/vgmstream/vgmstream/releases/download/$version/vgmstream-win64.zip"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$installRoot = Join-Path $repoRoot "tools\vgmstream"
$executable = Join-Path $installRoot "vgmstream-cli.exe"

if ((Test-Path -LiteralPath $executable) -and (-not $Force)) {
    Write-Host "[setup-vgmstream] Reusing $executable"
    exit 0
}

if ($DryRun) {
    Write-Host "[setup-vgmstream] Would download $downloadUrl"
    Write-Host "[setup-vgmstream] Would verify SHA-256 $archiveSha256"
    Write-Host "[setup-vgmstream] Would install to $installRoot"
    exit 0
}

$workRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("fluffy-dump-vgmstream-" + [Guid]::NewGuid().ToString("N"))
$archivePath = Join-Path $workRoot "vgmstream-win64.zip"
$stageRoot = Join-Path $workRoot "stage"

try {
    New-Item -ItemType Directory -Path $workRoot, $stageRoot -Force | Out-Null
    Write-Host "[setup-vgmstream] Downloading vgmstream $version..."
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath -UseBasicParsing

    $actualSha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $archiveSha256) {
        throw "vgmstream archive SHA-256 mismatch: expected $archiveSha256, got $actualSha256"
    }

    Expand-Archive -LiteralPath $archivePath -DestinationPath $stageRoot -Force
    $stagedExecutable = Get-ChildItem -LiteralPath $stageRoot -Filter "vgmstream-cli.exe" -File -Recurse | Select-Object -First 1
    if ($null -eq $stagedExecutable) {
        throw "Downloaded archive does not contain vgmstream-cli.exe"
    }

    New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
    Copy-Item -Path (Join-Path $stagedExecutable.Directory.FullName "*") -Destination $installRoot -Recurse -Force
    if (-not (Test-Path -LiteralPath $executable)) {
        throw "vgmstream-cli.exe was not installed at $executable"
    }
    Write-Host "[setup-vgmstream] Installed $executable"
}
finally {
    if (Test-Path -LiteralPath $workRoot) {
        Remove-Item -LiteralPath $workRoot -Recurse -Force
    }
}
