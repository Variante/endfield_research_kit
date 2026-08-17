param(
    [string]$PlayerPath = "$PSScriptRoot\Builds\LiZhiyanM23ParticleRendererCapture\EndfieldLiZhiyanM23ParticleRendererCapture.exe",
    [string]$DxCapPath = "$env:WINDIR\System32\DXCap.exe",
    [string]$OutputRoot = "$PSScriptRoot\scratch\reverse_engineering\lizhiyan_m23_source_dxcap",
    [string]$FrameSpec = "4.25s",
    [ValidateRange(1, 30)][int]$SetupFrames = 2,
    [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"
$player = [IO.Path]::GetFullPath($PlayerPath)
$dxcap = [IO.Path]::GetFullPath($DxCapPath)
$output = [IO.Path]::GetFullPath($OutputRoot)
$parser = Join-Path $PSScriptRoot "tools\original_m23_dxbc_exact\dxcap_xml_evidence.py"
$validator = Join-Path $PSScriptRoot "tools\validate_m23_source_dxcap_capture.py"

foreach ($required in @($player, $dxcap, $parser, $validator)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "preflight_failed.missing_file: $required"
    }
}
if ($FrameSpec -notmatch '^\d+(\.\d+)?s$') {
    throw "preflight_failed.frame_spec: expected a time such as 3.5s, actual=$FrameSpec"
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$run = Join-Path $output $stamp
$vsglog = Join-Path $run "source.vsglog"
$xml = Join-Path $run "source.xml"
$runtime = Join-Path $run "runtime.json"
$evidence = Join-Path $run "evidence.json"
$validation = Join-Path $run "validation.json"

Write-Host "player=$player"
Write-Host "dxcap=$dxcap"
Write-Host "frame=$FrameSpec"
Write-Host "run=$run"
Write-Host "boundary=diagnostic VFXBaseV2SampleStack source baseline; retail 0138/4212 is not expected"
if ($PreflightOnly) { exit 0 }

New-Item -ItemType Directory -Path $run | Out-Null
$captureArgs = @(
    "-file", $vsglog, "-frame", $FrameSpec, "-terminateonsave", "-c", $player,
    "-force-d3d11",
    "-endfield-m23-particle-renderer-capture",
    "-endfield-m23-particle-renderer-mode=positive",
    "-endfield-m23-particle-renderer-frames=$SetupFrames",
    "-endfield-m23-particle-renderer-foreground-window",
    "-endfield-m23-particle-renderer-output=$runtime"
)
$captureProcess = Start-Process -FilePath $dxcap -ArgumentList $captureArgs -PassThru -Wait
if ($captureProcess.ExitCode -ne 0) { throw "capture_failed: exit=$($captureProcess.ExitCode)" }
if (-not (Test-Path -LiteralPath $vsglog -PathType Leaf)) { throw "capture_missing_vsglog: $vsglog" }

& $dxcap "-p" $vsglog "-toXML" $xml
if ($LASTEXITCODE -ne 0) { throw "xml_export_failed: exit=$LASTEXITCODE" }
if (-not (Test-Path -LiteralPath $runtime -PathType Leaf)) { throw "runtime_report_missing: $runtime" }
& python $parser $xml -o $evidence
if ($LASTEXITCODE -ne 0) { throw "evidence_parse_failed: exit=$LASTEXITCODE" }
& python $validator $runtime $evidence -o $validation
if ($LASTEXITCODE -ne 0) {
    Get-Content -LiteralPath $validation
    throw "source_baseline_validation_failed: $validation"
}
Write-Host "source_baseline_pass: $validation"
