param([string]$Configuration = "Release")
$ErrorActionPreference = "Stop"
$toolRoot = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $toolRoot "..\..")).Path
$buildRoot = Join-Path $toolRoot "build"
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
$sourceRoot = (Resolve-Path (Join-Path $projectRoot "..\scratch\character_recovery\vfx_shader_variants\shader_export\Shader\HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader.bytecode")).Path
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
python (Join-Path $toolRoot "generate_embedded_header.py") --vertex (Join-Path $sourceRoot "0138_endfield_dxbc_0.dxbc") --pixel (Join-Path $sourceRoot "0139_endfield_dxbc_1.dxbc") --output (Join-Path $buildRoot "EmbeddedM23Dxbc.generated.h")
$visualStudio = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vsDevCmd = Join-Path $visualStudio "Common7\Tools\VsDevCmd.bat"
$dll = Join-Path $buildRoot "OriginalM23DxbcExactPlugin.dll"
$obj = Join-Path $buildRoot "OriginalM23DxbcExactPlugin.obj"
$source = Join-Path $toolRoot "OriginalM23DxbcExactPlugin.cpp"
$importLibrary = Join-Path $buildRoot "OriginalM23DxbcExactPlugin.lib"
$exports = Join-Path $buildRoot "OriginalM23DxbcExactPlugin.exp"
$cmd = "cl.exe /nologo /std:c++17 /O2 /EHsc /LD /I`"$buildRoot`" /Fo`"$obj`" `"$source`" /link /NOLOGO /Brepro /OUT:`"$dll`" /IMPLIB:`"$importLibrary`""
cmd.exe /d /c "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 && $cmd"
if ($LASTEXITCODE -ne 0) { throw "M23 plugin compilation failed." }
$validatorObj = Join-Path $buildRoot "ValidateEmbeddedM23Dxbc.obj"
$validator = Join-Path $buildRoot "ValidateEmbeddedM23Dxbc.exe"
$report = Join-Path $buildRoot "m23_dxbc_validation.json"
$vcmd = "cl.exe /nologo /std:c++17 /O2 /EHsc /I`"$buildRoot`" /Fo`"$validatorObj`" `"$(Join-Path $toolRoot 'ValidateEmbeddedM23Dxbc.cpp')`" /link /NOLOGO /Brepro /OUT:`"$validator`" `"$importLibrary`" d3d11.lib"
cmd.exe /d /c "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 && $vcmd"
if ($LASTEXITCODE -ne 0) { throw "M23 validator compilation failed." }
& $validator $report
if ($LASTEXITCODE -ne 0) { throw "WARP rejected the M23 exact-DXBC creation contract." }
Remove-Item -Force -ErrorAction SilentlyContinue $obj,$validatorObj
Write-Output "native_creation_fixture=$dll"
Write-Output "native_validation_report=$report"
