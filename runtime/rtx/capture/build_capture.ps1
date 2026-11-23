param(
    [Parameter(Mandatory)][string]$InstrumentedSource,
    [Parameter(Mandatory)][string]$BackendSource,
    [Parameter(Mandatory)][string]$AcceptedBuild,
    [Parameter(Mandatory)][string]$CuptiRoot,
    [Parameter(Mandatory)][string]$CudaRoot,
    [Parameter(Mandatory)][string]$Output
)
$ErrorActionPreference = 'Stop'
$scope = (Resolve-Path $InstrumentedSource).Path
$backend = (Resolve-Path $BackendSource).Path
$base = (Resolve-Path $AcceptedBuild).Path
$cupti = (Resolve-Path $CuptiRoot).Path
$cuda = (Resolve-Path $CudaRoot).Path
$out = [IO.Path]::GetFullPath($Output)
if (Test-Path -LiteralPath $out) { throw 'Use an empty capture build directory.' }
$bin = Join-Path $out bin
New-Item -ItemType Directory -Path $bin | Out-Null
foreach($name in @('llama.dll','ggml.dll','ggml-base.dll','ggml-cpu.dll','ggml-cuda.dll')) {
    Copy-Item -LiteralPath "$base/bin/$name" -Destination $bin
}
Copy-Item -LiteralPath "$cupti/lib/cupti64_2025.2.1.dll" -Destination $bin
$cl = (Get-Command cl.exe).Source
$compileArgs = @('/nologo','/TP','/EHsc','/O2','/Ob2','/DNDEBUG','/std:c++17','/MD','/utf-8',
    '/DGGML_BACKEND_SHARED','/DGGML_SHARED','/DGGML_USE_CPU','/DGGML_USE_CUDA','/DLLAMA_SHARED',
    "/I$backend/vendor","/I$backend/include","/I$backend/ggml/include","/I$cupti/include","/I$cuda/include",
    "$scope/worker.cpp","/Fo$out/worker.obj","/Fe$bin/rtx-c4-worker.exe",'/link',
    "$base/llama-build/src/llama.lib","$base/llama-build/ggml/src/ggml.lib",
    "$base/llama-build/ggml/src/ggml-base.lib","$cupti/lib/cupti.lib",'bcrypt.lib')
& $cl @compileArgs *> "$out/compile-link.log"
if ($LASTEXITCODE -ne 0) { throw 'Capture compilation or link failed.' }
$previousPath = $env:PATH
$previousDevices = $env:CUDA_VISIBLE_DEVICES
try {
    $env:PATH = "$bin;$cuda/bin;$env:PATH"
    $env:CUDA_VISIBLE_DEVICES = '-1'
    & (Join-Path $bin 'rtx-c4-worker.exe') --cupti-probe *> "$out/cupti-probe.log"
    if ($LASTEXITCODE -ne 0) { throw 'CUPTI ABI probe failed.' }
    & (Join-Path $bin 'rtx-c4-worker.exe') --fixtures *> "$out/control-fixture.log"
    if ($LASTEXITCODE -ne 0) { throw 'Model-free control fixture failed.' }
}
finally {
    $env:PATH = $previousPath
    $env:CUDA_VISIBLE_DEVICES = $previousDevices
}
