param(
    [string]$Configuration = "Release",
    [switch]$ToolOnly
)

$ErrorActionPreference = "Stop"

$toolRoot = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $toolRoot "..\..")).Path
$buildRoot = Join-Path $toolRoot "build"
$pluginOutputRoot = if ($ToolOnly) {
    $buildRoot
} else {
    Join-Path $projectRoot "Assets\EndfieldGraphShaderLab\Plugins\x86_64"
}
$outputDll = Join-Path $pluginOutputRoot "OriginalDxbcSwapPlugin.dll"
$outputImportLibrary = Join-Path $buildRoot "OriginalDxbcSwapPlugin.lib"
$outputExports = Join-Path $buildRoot "OriginalDxbcSwapPlugin.exp"
$pluginObject = Join-Path $buildRoot "OriginalDxbcSwapPlugin.obj"
$validatorObject = Join-Path $buildRoot "ValidateEmbeddedDxbc.obj"
$validatorExe = Join-Path $buildRoot "ValidateEmbeddedDxbc.exe"
$registryValidatorObject = Join-Path $buildRoot "VerifyM27SubstitutionRegistry.obj"
$registryValidatorExe = Join-Path $buildRoot "VerifyM27SubstitutionRegistry.exe"
$generatedHeader = Join-Path $buildRoot "EmbeddedDxbc.generated.h"
$vertex = Join-Path $toolRoot "bytecode\selected_deferred_resolver_vs.dxbc"
$pixel = Join-Path $toolRoot "bytecode\selected_deferred_resolver_ps.dxbc"
$m27Vertex = Join-Path $toolRoot "bytecode\endminf_m27_hgbuffer_vs.dxbc"
$m27Pixel = Join-Path $toolRoot "bytecode\endminf_m27_hgbuffer_ps.dxbc"
$m14Vertex = Join-Path $toolRoot "bytecode\endminf_m14_vfxbasev2_vs.dxbc"
$m14Pixel = Join-Path $toolRoot "bytecode\endminf_m14_vfxbasev2_ps.dxbc"
$m13Vertex = Join-Path $toolRoot "bytecode\endminf_m13_vfxbasev2_vs.dxbc"
$m13Pixel = Join-Path $toolRoot "bytecode\endminf_m13_vfxbasev2_ps.dxbc"
$uberVertex = Join-Path $toolRoot "bytecode\endminf_uber_post_vs.dxbc"
$uberPixel = Join-Path $toolRoot "bytecode\endminf_uber_post_ps.dxbc"
$pluginApi = "D:\Program Files\2022.3.62f3\Editor\Data\PluginAPI"
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"

if ($Configuration -ne "Release") {
    throw "Only the deterministic Release configuration is supported."
}
if (-not (Test-Path -LiteralPath $pluginApi)) {
    throw "Unity 2022.3.62f3 PluginAPI was not found: $pluginApi"
}
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw "Visual Studio locator was not found: $vswhere"
}

New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
New-Item -ItemType Directory -Path $pluginOutputRoot -Force | Out-Null
python (Join-Path $toolRoot "generate_embedded_header.py") `
    --deferred-vertex $vertex `
    --deferred-pixel $pixel `
    --m27-vertex $m27Vertex `
    --m27-pixel $m27Pixel `
    --m14-vertex $m14Vertex `
    --m14-pixel $m14Pixel `
    --m13-vertex $m13Vertex `
    --m13-pixel $m13Pixel `
    --uber-vertex $uberVertex `
    --uber-pixel $uberPixel `
    --output $generatedHeader
if ($LASTEXITCODE -ne 0) {
    throw "Exact DXBC header generation failed with exit code $LASTEXITCODE."
}

$visualStudio = & $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath
if (-not $visualStudio) {
    throw "Visual Studio C++ Build Tools were not found."
}

$vsDevCmd = Join-Path $visualStudio "Common7\Tools\VsDevCmd.bat"
$source = Join-Path $toolRoot "OriginalDxbcSwapPlugin.cpp"
$validatorSource = Join-Path $toolRoot "ValidateEmbeddedDxbc.cpp"
$compileCommand = @(
    "cl.exe /nologo /std:c++17 /O2 /EHsc /Brepro /LD",
    "/I`"$pluginApi`" /I`"$buildRoot`"",
    "/Fo`"$pluginObject`"",
    "`"$source`"",
    "/link /NOLOGO /Brepro /OUT:`"$outputDll`" /IMPLIB:`"$outputImportLibrary`" bcrypt.lib d3dcompiler.lib dxguid.lib"
) -join " "
$compile = "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 && $compileCommand"
cmd.exe /d /c $compile
if ($LASTEXITCODE -ne 0) {
    throw "Native plugin compilation failed with exit code $LASTEXITCODE."
}

$validatorCompileCommand = @(
    "cl.exe /nologo /std:c++17 /O2 /EHsc /Brepro",
    "/I`"$buildRoot`" /Fo`"$validatorObject`" `"$validatorSource`"",
    "/link /NOLOGO /Brepro /OUT:`"$validatorExe`" d3d11.lib"
) -join " "
$validatorCompile =
    "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 && $validatorCompileCommand"
cmd.exe /d /c $validatorCompile
if ($LASTEXITCODE -ne 0) {
    throw "DXBC validator compilation failed with exit code $LASTEXITCODE."
}

& $validatorExe
if ($LASTEXITCODE -ne 0) {
    throw "D3D11 rejected an embedded selected shader (exit $LASTEXITCODE)."
}

$registryValidatorSource = Join-Path $toolRoot "VerifyM27SubstitutionRegistry.cpp"
$registryValidatorCompileCommand = @(
    "cl.exe /nologo /std:c++17 /O2 /EHsc /Brepro",
    "/I`"$buildRoot`" /I`"$toolRoot`"",
    "/Fo`"$registryValidatorObject`" `"$registryValidatorSource`"",
    "/link /NOLOGO /Brepro /OUT:`"$registryValidatorExe`" d3d11.lib bcrypt.lib"
) -join " "
$registryValidatorCompile =
    "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 && $registryValidatorCompileCommand"
cmd.exe /d /c $registryValidatorCompile
if ($LASTEXITCODE -ne 0) {
    throw "M27 registry validator compilation failed with exit code $LASTEXITCODE."
}

& $registryValidatorExe
if ($LASTEXITCODE -ne 0) {
    throw "M27 substitution registry validation failed with exit $LASTEXITCODE."
}

foreach ($intermediate in @(
    $outputImportLibrary,
    $outputExports,
    $pluginObject,
    $validatorObject,
    $registryValidatorObject
)) {
    [System.IO.File]::Delete($intermediate)
}

$dllHash = (Get-FileHash -LiteralPath $outputDll -Algorithm SHA256).Hash.ToLowerInvariant()
$validatorHash =
    (Get-FileHash -LiteralPath $validatorExe -Algorithm SHA256).Hash.ToLowerInvariant()
$registryValidatorHash =
    (Get-FileHash -LiteralPath $registryValidatorExe -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "plugin=$outputDll"
Write-Output "plugin_sha256=$dllHash"
Write-Output "validator=$validatorExe"
Write-Output "validator_sha256=$validatorHash"
Write-Output "m27_registry_validator=$registryValidatorExe"
Write-Output "m27_registry_validator_sha256=$registryValidatorHash"
