param(
    [Parameter(Mandatory)][string]$InputDirectory,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [Parameter(Mandatory)][string]$CMake,
    [Parameter(Mandatory)][string]$Ninja,
    [Parameter(Mandatory)][string]$Nvcc,
    [ValidateRange(1, 8)][int]$Jobs = 4
)
$ErrorActionPreference = 'Stop'
$inputRoot = (Resolve-Path -LiteralPath $InputDirectory).Path.Replace('\', '/')
$out = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $out) { throw 'A fresh build output directory is required.' }
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) { throw 'Use a configured x64 MSVC/SDK environment.' }
$cmakeBin = (Resolve-Path -LiteralPath $CMake).Path
$ninjaBin = (Resolve-Path -LiteralPath $Ninja).Path
$nvccBin = (Resolve-Path -LiteralPath $Nvcc).Path
$arch = & $nvccBin --list-gpu-code
if ($LASTEXITCODE -ne 0 -or $arch -cnotcontains 'sm_120') { throw 'nvcc does not advertise Blackwell SM120.' }
[void](New-Item -ItemType Directory -Path $out)
$configure = @('-S', $PSScriptRoot, '-B', (Join-Path $out 'build'), '-G', 'Ninja',
    "-DCMAKE_MAKE_PROGRAM=$ninjaBin", "-DCMAKE_CUDA_COMPILER=$nvccBin",
    '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
    "-DNATIVE_SOURCE=$inputRoot/source", "-DNATIVE_WORKER=$inputRoot/worker")
& $cmakeBin @configure *> (Join-Path $out 'configure.log')
if ($LASTEXITCODE -ne 0) { throw "CMake configure failed with code $LASTEXITCODE. See configure.log." }
& $cmakeBin --build (Join-Path $out 'build') --parallel $Jobs --target rtx-c4-worker *> (Join-Path $out 'build.log')
if ($LASTEXITCODE -ne 0) { throw "Worker build failed with code $LASTEXITCODE. See build.log." }
