# Windows RTX native C4 capture

This component reproduces the capture worker and checks for one paired C1/C4 qualification on the **GeForce RTX 5070 Ti Laptop GPU**. It uses the native Windows `sm_120a` backend, Llama-3.1-8B-Instruct Q8_0 as the target, and Llama-3.2-1B-Instruct Q8_0 as the draft. Both arms use C1024 with active F16 KV, FlashAttention off, CUDA graphs and fusion off, and PDL off. C1 and C4 differ only in `HS_SD_TARGET_PACK4=0/1`. `HS_PREFILL_PACK4=0` in both arms. Blackwell P4 is outside this component's support scope.

The input is CodeContests/test/124 with 757 input IDs. Supply the exact locally held JSON array of IDs. The worker validates the SHA256 of the compact UTF-8 JSON representation against [the frozen input identity](records/expected.json). The input file, text and IDs stay local. Model sizes and hashes are in the same record.

## Quick checks

From `runtime/rtx`, use Python 3.11 or newer. These checks require the standard library and the small shipped files.

```powershell
python -B verify.py --quick
python -B -m unittest discover -s tests
```

## Build the worker and CUPTI collector

Use PowerShell 7 and a configured x64 Visual Studio 2022 C++/Windows SDK environment. The observed capture used MSVC 19.44.35229, CUDA Toolkit 12.9 with NVCC 12.9.86, NVIDIA driver 621.24 and CUPTI 12.9.79 (Activity API version 28). The build uses CMake 3.31.8, Ninja and Git. Provide `nvcc` and `cuobjdump` from the CUDA toolchain and put `<CUDA>/bin` on the runtime `PATH` for the link and CPU checks. Install the [official CUDA toolkit](https://docs.nvidia.com/cuda/archive/12.9.0/cuda-installation-guide-microsoft-windows/index.html) and [CUPTI 12.9.79 component](https://developer.download.nvidia.com/compute/cuda/redist/cuda_cupti/windows-x86_64/cuda_cupti-windows-x86_64-12.9.79-archive.zip) under their own terms. Check the CUPTI zip against the size and SHA256 in [expected.json](records/expected.json) before unpacking it.

Download the pinned upstream archive from [PROFILE.json](PROFILE.json). The materializer checks the archive and patch SHA256, the exact four patched files and the original native worker source. Choose fresh directories for the following commands.

```powershell
python materialize_source.py --upstream-archive <llama-tar.gz> --out <source>
./build.ps1 -InputDirectory <source> -OutputDirectory <native> -CMake <cmake.exe> -Ninja <ninja.exe> -Nvcc <nvcc.exe>
python verify_build.py --build <native>/build --dumpbin <dumpbin.exe> --cuobjdump <cuobjdump.exe> --out <native-check>
python capture/instrument.py --base-source <source>/worker --out <instrumented>
./capture/build_capture.ps1 -InstrumentedSource <instrumented> -BackendSource <source>/source -AcceptedBuild <native>/build -CuptiRoot <CUPTI> -CudaRoot <CUDA> -Output <capture-build>
```

The native verifier checks the worker link, five backend DLLs, CUDA images and required symbols, 20 CPU fixture cases and a synthetic active F16 state. The capture build also runs the linked CUPTI version/timestamp probe and the worker's 20 CPU fixtures. The instrumenter adds request and host submission scopes, separates KV export from file writes, and persists already-serialized checkpoint bytes. It retains the native backend link. The archived EXE and DLL identities and the generated source hashes are listed in [expected.json](records/expected.json). A rebuilt EXE and DLL can have new build identities.

## Capture and verify a local pair

Supply the fixed input and two identified local GGUFs. Reserve the GPU and output volume exclusively, use the same lock path for coordinating local qualification work, and start with at least 26 GiB free at the output location. The launcher checks the pinned device and driver, GPU recovery state, quiet GPU utilization, visible compute processes and available VRAM before each worker. It runs two serial requests with one arm per worker, a 220-second limit per worker, an 18 GiB storage limit and an 8 GiB free-space floor. While a worker is active, it checks GPU health and temperatures up to 84 °C, records whether it saw the worker in the compute process list, and saves the resource summary locally. Save every run under a fresh ID. Device or capture errors stop the pair and preserve the outputs.

```powershell
python capture/run_pair.py --capture-bin <capture-build>/bin --cuda-bin <CUDA>/bin --input <local-input.json> --target <target.gguf> --draft <draft.gguf> --out <fresh-run-id> --lock <shared-local-lock> --exclusive-window
python capture/trace_independent.py --run <fresh-run-id> --out <fresh-sql-receipt.json>
python capture/verify_capture.py --run <fresh-run-id> --sd-u <local-SD_U-request> --r-trace <local-R_TRACE-request> --target-reference-kv <local-R_TO-target.kv> --draft-reference-kv <local-SD_U-draft.kv>
```

The last command uses NumPy for complete F16 and F32 finite-value checks. It takes local independent reference objects. The `SD_U` and `R_TRACE` request directories hold `native.json`, `vectors.jsonl` and `vectors.f32`. The pinned reference hashes bind the row indices, vector streams and independent transaction sequence. The caller supplies the separately stored terminal target and draft files for direct byte comparison. The uninstrumented worker exposes `SD_U` through its `BC` interface and `R_TO` and `R_TRACE` through the scalar `R` interface. A local `R_TRACE` request points `replay_request` at the `SD_U` request's `native.json`. Reference preparation is separate from the two capture requests.

The primary trace reader binds GPU activity to successful driver/runtime API records by CUDA correlation ID, then checks Windows worker/thread, scope ancestry and host API interval. The separate SQLite reader recomputes the exact request-kernel link multiset. Both support the original decoded export layout. The capture directory includes full numerical payloads, input IDs, raw activity buffers and local process detail. Keep it private. [NVIDIA CUPTI correlation documentation](https://docs.nvidia.com/cupti/12.9/main/main.html)

## Frozen expected result

| Per request | C1 | C4 |
| --- | ---: | ---: |
| All associated request kernels | 246,252 | 246,252 |
| Target verification kernels | 49,828 | 49,828 |
| Target verification Q8_0 MMVQ q1 | 8,550 | 0 |
| Target verification Q8_0 MMVQ q4 | 0 | 8,325 |
| Target verification Q8_0 MMVQ q2 | 0 | 225 |
| Dropped and unassociated request records | 0 | 0 |
| Intermediate active F16 KV objects | 75 | 75 |
| Own-successor links | 37 | 37 |

The public checkpoint rows give generation, role, geometry, size and hashes. The archived acceptance covered all F16 values, 5,065,667,352 intermediate bytes per arm, two terminal objects per arm and one inactive draft marker. It compared the paired payloads byte for byte and checked the terminal state against the independent references. Each arm also matched 174 complete F32 target vectors to the independent q1 trace and 339 complete target/draft F32 vectors to `SD_U`. [Expected counts and identities](records/expected.json) · [Checkpoint receipt](records/kv-checkpoints.json)

The clean release build also passed on the GeForce RTX 5070 Ti Laptop GPU. This replay used two qualification requests and 454 native forwards. An independent SQL review matched every request-kernel link, the new per-checkpoint hashes matched all 78 published entries, and the paired payloads, independent F32 and terminal references, and own-successor checks passed. The replay receipt records the actual rebuilt EXE and CUDA DLL identities. [Release-build device replay](records/device-replay.json)

See the [claim map and access inventory](../../docs/RTX_CAPTURE.md) and [third-party notices](THIRD_PARTY.md).
