# Run from a configured Windows x64 CMake/Ninja build.
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$BuildDir,
    [string]$CMake = 'cmake',
    [ValidateRange(1, 2)]
    [int]$Jobs = 2,
    [switch]$Smoke
)

$ErrorActionPreference = 'Stop'
$build = (Resolve-Path -LiteralPath $BuildDir).Path
$cache = Join-Path $build 'CMakeCache.txt'
if (-not (Test-Path -LiteralPath $cache -PathType Leaf)) {
    throw 'Configure the Veyra Windows x64 build with CMake before running this script.'
}

& $CMake --build $build --target veyra_qml_ui --parallel $Jobs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$player = Join-Path $build 'veyra_qml_ui.exe'
$profileName = if ($Smoke) { 'veyra-smoke-profile' } else { 'veyra-dev-profile' }
$profile = Join-Path $build $profileName
$playerArgs = @('--data-dir', ('"{0}"' -f $profile))
if ($Smoke) { $playerArgs += @('--page', 'home', '--exit-after', '4000') }
$process = Start-Process -FilePath $player -WorkingDirectory $build -ArgumentList $playerArgs -Wait -PassThru
exit $process.ExitCode
