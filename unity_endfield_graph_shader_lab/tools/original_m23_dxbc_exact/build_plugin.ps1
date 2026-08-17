param([string]$Configuration = "Release")
$ErrorActionPreference = "Stop"
$toolRoot = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $toolRoot "..\..")).Path
$buildRoot = Join-Path $toolRoot "build"
$pluginOutputRoot = Join-Path $projectRoot "Assets\EndfieldGraphShaderLab\Plugins\x86_64"
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$sourceRoot = (Resolve-Path (Join-Path $projectRoot "..\scratch\character_recovery\vfx_shader_variants\shader_export\Shader\HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode")).Path
$materialPath = (Resolve-Path (Join-Path $projectRoot "..\scratch\animestudio\lizhiyan_peak_particles\dependency_json\Material\M_fxui__lizhiyan_overview_23_pFA062F1311E9B888.json")).Path
$contractPath = (Resolve-Path (Join-Path $projectRoot "Assets\EndfieldGraphShaderLab\Generated\OriginalData\Effects\lizhiyan_overview_peak_particle_effects.json")).Path
$expectedMaterialSha256 = "81B920BE11D13B3662A97851C97C8A41EF98333478578EACD2A164D4BEFE98FA"
$expectedContractSha256 = "41402BE441AD98C7823D021FB86C1FC3E48ECD6515A58D46EEDFD0BE6EEA7EEB"
if ((Get-FileHash $materialPath -Algorithm SHA256).Hash -ne $expectedMaterialSha256) { throw "M23 material hash mismatch: $materialPath" }
if ((Get-FileHash $contractPath -Algorithm SHA256).Hash -ne $expectedContractSha256) { throw "M23 generated contract hash mismatch: $contractPath" }
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
python (Join-Path $toolRoot "generate_embedded_header.py") --vertex (Join-Path $sourceRoot "0138_endfield_dxbc_0.dxbc") --pixel (Join-Path $sourceRoot "0139_endfield_dxbc_1.dxbc") --output (Join-Path $buildRoot "EmbeddedM23Dxbc.generated.h")
python (Join-Path $toolRoot "generate_diagnostic_vs_header.py") --source (Join-Path $toolRoot "diagnostic_vs.hlsl") --output (Join-Path $buildRoot "DiagnosticM23Vs.generated.h")
python (Join-Path $toolRoot "generate_diagnostic_vs_header.py") --source (Join-Path $toolRoot "diagnostic_vs_textures.hlsl") --prefix g_EndfieldM23DiagnosticVsTexture --output (Join-Path $buildRoot "DiagnosticM23TextureVs.generated.h")
$visualStudio = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vsDevCmd = Join-Path $visualStudio "Common7\Tools\VsDevCmd.bat"
$dll = Join-Path $buildRoot "OriginalM23DxbcExactPlugin.dll"
$obj = Join-Path $buildRoot "OriginalM23DxbcExactPlugin.obj"
$source = Join-Path $toolRoot "OriginalM23DxbcExactPlugin.cpp"
$bridgeSource = Join-Path $toolRoot "OriginalM23DxbcUnityBridge.cpp"
$importLibrary = Join-Path $buildRoot "OriginalM23DxbcExactPlugin.lib"
$exports = Join-Path $buildRoot "OriginalM23DxbcExactPlugin.exp"
$bridgeObj = Join-Path $buildRoot "OriginalM23DxbcUnityBridge.obj"
$compileSource = "cl.exe /nologo /std:c++17 /O2 /EHsc /c /I`"$buildRoot`" /Fo`"$obj`" `"$source`""
$compileBridge = "cl.exe /nologo /std:c++17 /O2 /EHsc /c /I`"$buildRoot`" /I`"D:\Program Files\2022.3.62f3\Editor\Data\PluginAPI`" /Fo`"$bridgeObj`" `"$bridgeSource`""
$link = "link.exe /DLL /NOLOGO /Brepro `"$obj`" `"$bridgeObj`" /OUT:`"$dll`" /IMPLIB:`"$importLibrary`" d3d11.lib d3dcompiler.lib bcrypt.lib windowscodecs.lib ole32.lib"
cmd.exe /d /c "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 && $compileSource && $compileBridge && $link"
if ($LASTEXITCODE -ne 0) { throw "M23 plugin compilation failed." }
New-Item -ItemType Directory -Force -Path $pluginOutputRoot | Out-Null
$pluginDll = Join-Path $pluginOutputRoot "OriginalM23DxbcExactPlugin.dll"
Copy-Item -LiteralPath $dll -Destination $pluginDll -Force
$builtHash = (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant()
$copiedHash = (Get-FileHash -LiteralPath $pluginDll -Algorithm SHA256).Hash.ToLowerInvariant()
if ($builtHash -ne $copiedHash) { throw "M23 Unity plugin copy hash mismatch." }
$exportListing = cmd.exe /d /c "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 && dumpbin /exports `"$dll`""
if ($LASTEXITCODE -ne 0) { throw "M23 Unity plugin export inspection failed." }
foreach ($requiredExport in @(
    "UnityPluginLoad",
    "UnityShaderCompilerExtEvent",
    "EndfieldOriginalM23DxbcBridgeSetArmed",
    "EndfieldOriginalM23DxbcBridgeGetRenderEventFunc",
    "EndfieldOriginalM23DxbcBridgeGetCleanupCount",
    "EndfieldOriginalM23DxbcBridgeGetNativeDrawIssued",
    "EndfieldOriginalM23DxbcBridgeCopyNativeReadback"
)) {
    if (-not ($exportListing -match [regex]::Escape($requiredExport))) {
        throw "M23 Unity plugin export missing: $requiredExport"
    }
}
$validatorObj = Join-Path $buildRoot "ValidateEmbeddedM23Dxbc.obj"
$validator = Join-Path $buildRoot "ValidateEmbeddedM23Dxbc.exe"
$report = Join-Path $buildRoot "m23_dxbc_validation.json"
$vcmd = "cl.exe /nologo /std:c++17 /O2 /EHsc /I`"$buildRoot`" /Fo`"$validatorObj`" `"$(Join-Path $toolRoot 'ValidateEmbeddedM23Dxbc.cpp')`" /link /NOLOGO /Brepro /OUT:`"$validator`" `"$importLibrary`" d3d11.lib ole32.lib"
cmd.exe /d /c "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 && $vcmd"
if ($LASTEXITCODE -ne 0) { throw "M23 validator compilation failed." }
& $validator $report
if ($LASTEXITCODE -ne 0) { throw "WARP rejected the M23 exact-DXBC creation contract." }
$diagnosticReport = Join-Path $buildRoot "m23_diagnostic_vs_validation.json"
& $validator $diagnosticReport --diagnostic-vs
if ($LASTEXITCODE -ne 0) { throw "WARP rejected the M23 diagnostic-VS exact-PS contract." }
$namedLowReport = Join-Path $buildRoot "m23_diagnostic_vs_named_low_validation.json"
& $validator $namedLowReport --named-low
if ($LASTEXITCODE -ne 0) { throw "WARP rejected the M23 named-low exact-PS contract." }
$highProbeReport = Join-Path $buildRoot "m23_high_probe_validation.json"
& $validator $highProbeReport --high-probe "b4[33].x"
if ($LASTEXITCODE -ne 0) { throw "WARP rejected the M23 high-slot probe contract." }
$highBaselineReport = Join-Path $buildRoot "m23_high_baseline_validation.json"
& $validator $highBaselineReport --high-baseline 0
if ($LASTEXITCODE -ne 0) { throw "WARP rejected the M23 high-slot baseline contract." }
$highNeutralReport = Join-Path $buildRoot "m23_high_neutral_validation.json"
& $validator $highNeutralReport --high-neutral
if ($LASTEXITCODE -ne 0) { throw "WARP rejected the M23 high-slot neutral-domain contract." }
$overrideReports = @()
foreach ($mask in 1,2,3) {
    $overrideReport = Join-Path $buildRoot "m23_high_neutral_override_$mask.json"
    & $validator $overrideReport --high-neutral-override $mask
    if ($LASTEXITCODE -ne 0) { throw "WARP rejected M23 high-neutral override $mask." }
    $overrideReports += $overrideReport
}
$exactTextureReports = @()
Push-Location $toolRoot
try {
    foreach ($textureMode in @("named-low","high-neutral","high-neutral-rgb")) {
        $textureReport = Join-Path $buildRoot "m23_exact_textures_$($textureMode.Replace('-','_')).json"
        & $validator $textureReport "--exact-textures-$textureMode"
        if ($LASTEXITCODE -ne 0) { throw "WARP rejected M23 exact-texture $textureMode mode." }
        $exactTextureReports += $textureReport
    }
} finally {
    Pop-Location
}
$reports = @($report,$diagnosticReport,$namedLowReport,$highProbeReport,$highBaselineReport,$highNeutralReport) + $overrideReports + $exactTextureReports
foreach ($nativeReport in $reports) {
    python (Join-Path $toolRoot "validate_diagnostic.py") --report $nativeReport
    if ($LASTEXITCODE -ne 0) { throw "M23 report validation failed: $nativeReport" }
}
Remove-Item -Force -ErrorAction SilentlyContinue $obj,$bridgeObj,$validatorObj
Write-Output "native_creation_fixture=$dll"
Write-Output "unity_plugin_output=$pluginDll"
Write-Output "unity_plugin_sha256=$copiedHash"
Write-Output "native_validation_report=$report"
Write-Output "native_diagnostic_validation_report=$diagnosticReport"
Write-Output "native_named_low_validation_report=$namedLowReport"
Write-Output "native_high_probe_validation_report=$highProbeReport"
Write-Output "native_high_baseline_validation_report=$highBaselineReport"
Write-Output "native_high_neutral_validation_report=$highNeutralReport"
Write-Output "native_exact_texture_validation_reports=$($exactTextureReports -join ',')"
