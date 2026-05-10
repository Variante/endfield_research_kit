[CmdletBinding()]
param(
    [ValidateSet("CLI", "GUI", "Patcher", "AllManaged")]
    [string]$Target = "CLI",
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [switch]$NoRestore,
    [switch]$UseSystemDotnet,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$animeRoot = Join-Path $repoRoot "tools\AnimeStudio"
$localDotnetExe = Join-Path $animeRoot ".dotnet\dotnet.exe"
$dotnetCliHome = Join-Path $animeRoot ".dotnet-cli"

function Write-Step {
    param([string]$Message)
    Write-Host "[rebuild-animestudio] $Message"
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

function Invoke-External {
    param([string[]]$Command)

    if ($DryRun) {
        Write-Step ("Would run: " + (Format-Command $Command))
        return
    }

    $exe = $Command[0]
    $args = @()
    if ($Command.Count -gt 1) {
        $args = $Command[1..($Command.Count - 1)]
    }

    & $exe @args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $(Format-Command $Command)"
    }
}

function Get-DotnetExe {
    if ((-not $UseSystemDotnet) -and (Test-Path $localDotnetExe)) {
        return $localDotnetExe
    }

    $systemDotnet = Get-Command "dotnet.exe" -ErrorAction SilentlyContinue
    if ($null -ne $systemDotnet) {
        return $systemDotnet.Source
    }

    throw "dotnet.exe was not found. Run .\scripts\animestudio\setup_dotnet9.bat first."
}

$cliTarget = [pscustomobject]@{
    Name = "CLI"
    Project = Join-Path $animeRoot "AnimeStudio.CLI\AnimeStudio.CLI.csproj"
    Framework = "net9.0-windows"
    Output = Join-Path $animeRoot "AnimeStudio.CLI\bin\$Configuration\net9.0-windows\AnimeStudio.CLI.exe"
}

$guiTarget = [pscustomobject]@{
    Name = "GUI"
    Project = Join-Path $animeRoot "AnimeStudio.GUI\AnimeStudio.GUI.csproj"
    Framework = "net9.0-windows"
    Output = Join-Path $animeRoot "AnimeStudio.GUI\bin\$Configuration\net9.0-windows\AnimeStudio.GUI.exe"
}

$patcherTarget = [pscustomobject]@{
    Name = "Patcher"
    Project = Join-Path $animeRoot "AnimeStudio.Patcher\AnimeStudio.Patcher.csproj"
    Framework = "net9.0"
    Output = Join-Path $animeRoot "AnimeStudio.Patcher\bin\$Configuration\net9.0\AnimeStudio.Patcher.exe"
}

$selectedTargets = switch ($Target) {
    "CLI" { @($cliTarget) }
    "GUI" { @($guiTarget) }
    "Patcher" { @($patcherTarget) }
    "AllManaged" { @($cliTarget, $guiTarget, $patcherTarget) }
}

$dotnetExe = Get-DotnetExe

if (-not $DryRun) {
    New-Item -ItemType Directory -Path $dotnetCliHome -Force | Out-Null
}

$env:DOTNET_CLI_HOME = $dotnetCliHome
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = "1"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$env:DOTNET_NOLOGO = "1"

if (-not $UseSystemDotnet -and ($dotnetExe -eq $localDotnetExe)) {
    $env:DOTNET_ROOT = Split-Path $dotnetExe -Parent
    $env:DOTNET_MULTILEVEL_LOOKUP = "0"
}

if (-not $DryRun) {
    $sdkVersion = (& $dotnetExe --version).Trim()
    if ($sdkVersion -notmatch '^9\.') {
        if ($UseSystemDotnet) {
            Write-Warning "Using non-.NET 9 SDK $sdkVersion because -UseSystemDotnet was specified."
        }
        else {
            throw "Found SDK $sdkVersion at $dotnetExe. Run .\scripts\animestudio\setup_dotnet9.bat, or rerun with -UseSystemDotnet to override."
        }
    }

    Write-Step "Using dotnet SDK $sdkVersion from $dotnetExe"
}
else {
    Write-Step "Dry run mode is enabled."
}

foreach ($buildTarget in $selectedTargets) {
    Write-Step "Preparing $($buildTarget.Name) build"

    if (-not $NoRestore) {
        Invoke-External @(
            $dotnetExe,
            "restore",
            $buildTarget.Project,
            "-p:RestoreIgnoreFailedSources=true",
            "-p:NuGetAudit=false"
        )
    }

    $buildCommand = @(
        $dotnetExe,
        "build",
        $buildTarget.Project,
        "-c", $Configuration,
        "-f", $buildTarget.Framework
    )

    if ($NoRestore) {
        $buildCommand += "--no-restore"
    }

    Invoke-External $buildCommand
    Write-Step "$($buildTarget.Name) output: $($buildTarget.Output)"
}
