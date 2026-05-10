[CmdletBinding()]
param(
    [string]$Channel = "9.0",
    [string]$InstallDir,
    [switch]$Force,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$animeRoot = Join-Path $repoRoot "tools\AnimeStudio"

if (-not $InstallDir) {
    $InstallDir = Join-Path $animeRoot ".dotnet"
}

$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$dotnetExe = Join-Path $InstallDir "dotnet.exe"
$bootstrapScript = Join-Path ([System.IO.Path]::GetTempPath()) "animestudio-dotnet-install.ps1"
$downloadUrl = "https://dot.net/v1/dotnet-install.ps1"
$dotnetCliHome = Join-Path $animeRoot ".dotnet-cli"

function Write-Step {
    param([string]$Message)
    Write-Host "[setup-dotnet9] $Message"
}

function Format-Command {
    param([string[]]$Command)

    return ($Command | ForEach-Object {
        if ($_ -match "\s") {
            '"' + $_ + '"'
        }
        else {
            $_
        }
    }) -join " "
}

if ((-not $Force) -and (Test-Path $dotnetExe)) {
    $installedSdks = & $dotnetExe --list-sdks 2>$null
    if (($LASTEXITCODE -eq 0) -and ($installedSdks | Select-String -Pattern '^\s*9\.')) {
        Write-Step "Found an existing .NET 9 SDK in $InstallDir"
        & $dotnetExe --version
        exit 0
    }
}

$installCommand = @(
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $bootstrapScript,
    "-Channel", $Channel,
    "-Quality", "GA",
    "-InstallDir", $InstallDir,
    "-NoPath"
)

if ($DryRun) {
    Write-Step "Would download $downloadUrl to $bootstrapScript"
    Write-Step ("Would run: " + (Format-Command $installCommand))
    exit 0
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $dotnetCliHome -Force | Out-Null

$env:DOTNET_CLI_HOME = $dotnetCliHome
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = "1"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$env:DOTNET_NOLOGO = "1"

Write-Step "Downloading dotnet-install.ps1"
Invoke-WebRequest -Uri $downloadUrl -OutFile $bootstrapScript

Write-Step "Installing .NET SDK channel $Channel into $InstallDir"
& $installCommand[0] $installCommand[1..($installCommand.Length - 1)]
if ($LASTEXITCODE -ne 0) {
    throw "dotnet-install.ps1 failed with exit code $LASTEXITCODE"
}

Write-Step "Installed SDKs:"
& $dotnetExe --list-sdks

Write-Step "Local .NET 9 setup is ready."
Write-Step "Next step: .\scripts\animestudio\rebuild.bat -Target CLI"
