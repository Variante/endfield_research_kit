param(
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

$toolRoot = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $toolRoot "..\..")).Path
$buildRoot = Join-Path $toolRoot "build"
$pluginOutputRoot = Join-Path $projectRoot "Assets\EndfieldGraphShaderLab\Plugins\x86_64"
$outputDll = Join-Path $pluginOutputRoot "OriginalDxbcSwapPlugin.dll"
$outputImportLibrary = Join-Path $buildRoot "OriginalDxbcSwapPlugin.lib"
$outputExports = Join-Path $buildRoot "OriginalDxbcSwapPlugin.exp"
$pluginObject = Join-Path $buildRoot "OriginalDxbcSwapPlugin.obj"
$validatorObject = Join-Path $buildRoot "ValidateEmbeddedDxbc.obj"
$validatorExe = Join-Path $buildRoot "ValidateEmbeddedDxbc.exe"
$generatedHeader = Join-Path $buildRoot "EmbeddedDxbc.generated.h"
$vertex = Join-Path $toolRoot "bytecode\selected_deferred_resolver_vs.dxbc"
$pixel = Join-Path $toolRoot "bytecode\selected_deferred_resolver_ps.dxbc"
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
    --vertex $vertex `
    --pixel $pixel `
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
    "/link /NOLOGO /Brepro /OUT:`"$outputDll`" /IMPLIB:`"$outputImportLibrary`""
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

foreach ($intermediate in @(
    $outputImportLibrary,
    $outputExports,
    $pluginObject,
    $validatorObject
)) {
    [System.IO.File]::Delete($intermediate)
}

$dllHash = (Get-FileHash -LiteralPath $outputDll -Algorithm SHA256).Hash.ToLowerInvariant()
$validatorHash =
    (Get-FileHash -LiteralPath $validatorExe -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "plugin=$outputDll"
Write-Output "plugin_sha256=$dllHash"
Write-Output "validator=$validatorExe"
Write-Output "validator_sha256=$validatorHash"
