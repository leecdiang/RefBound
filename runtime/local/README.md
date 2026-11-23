# A5000 LOCAL diagnostic frontend

This component packages the later two-history LOCAL frontend, its CUDA build recipe, a trace check, and a reader for saved numerical captures. [Claim map and evidence boundaries](../../docs/A5000_LOCAL.md).

## Run the public checks

From the repository root:

~~~sh
python3 -B runtime/local/check.py --quick
bash runtime/local/test_cpu.sh local-cpu-out
bash runtime/local/build_cuda.sh local-cuda-out
~~~

Use fresh output directories. The quick path requires Python 3.9+ and the small JSON files under `evidence/`. The CPU script also requires GCC 11. The CUDA script builds and links the real Linux x86-64/sm86 worker with CMake, Ninja, GCC 11.4.0, and CUDA Toolkit 12.5.40. The checked A5000 deployment used driver 595.84. Install system OpenSSL 3 and provide the CUDA runtime libraries required by the build. This configuration also detected NCCL 2.22.3. `CUDA_ROOT` and `GCC_BIN_DIR` can locate the pinned toolchain. The build hides GPUs and exercises both immutable lowerings, the P4-off control, and native state serialization fixtures without models. Configure, compilation, link command, map, dependency and symbol logs stay in the output directory.

## Frozen input and operation

The target is Qwen3-32B Q4_K_M with Q8_1 activations. The separately resident draft is Qwen3-0.6B Q8_0. The diagnostic uses frozen proposals, so draft forward rows are zero. Model file sizes and SHA-256 values are in [CASE.json](evidence/CASE.json). The execution uses the GGUF tokenizers and checks exact target/draft vocabulary entries and EOG classification. Use the pinned single-GPU Linux profile, C1024, F16 KV, C4 on and P4 off, with FlashAttention and CUDA graphs disabled.

Both histories derive from CodeContests/train/161. The noncrossing history begins at cycle 0 with 137 tokens. The fixed crossing begins at cycle 37 with 253 tokens. Each transaction verifies one pending token and three saved proposals. The input identity includes both the first and successor proposals. Each arm trims to its own accepted prefix, takes its own pending token and consumes its own retained KV on the successor.

| History | Ordered physical extents, primary / successor | R | SIMPLE | LOCAL |
| --- | --- | --- | --- | --- |
| Noncrossing | `[256,256,256,256]` / `[256,256,256,256]` | 4 × q1 / 4 × q1 | q4 / q4 | q4 / q4 |
| Crossing | `[256,256,256,512]` / `[256,512,512,512]` | 4 × q1 / 4 × q1 | 3+1 / 1+3 | q4 / q4 |

The candidate's ordered extent-vector guard rejects GGML graph reuse across the crossing even though both calls have maximum extent 512. The noncrossing successor reuses one GGML graph per candidate. These are GGML graph reuse observations under the CUDA-graphs-off policy. For the recorded crossing calls LOCAL used 449 native4 dispatches per call. SIMPLE used the same 449 native4 dispatches plus 385 q1 projection dispatches per call. The table describes logical physical forward widths and the counters describe backend dispatches. Kernel-launch counts are a separate measurement.

## Saved numerical qualification

[TWO_HISTORIES.json](evidence/TWO_HISTORIES.json) gives six historical receipts' work and control summaries. [CROSSING_OBJECTS.json](evidence/CROSSING_OBJECTS.json) identifies the later three-arm A5000 qualification. It records all 27 complete F32 vectors (151,936 values each), 15 native F16 KV states, and the 82 full-byte comparisons. The comparisons comprise 18 candidate/reference F32, 10 candidate/reference active KV, 42 same-arm historical objects, and 12 retained prefixes. The five checkpoint roles are incoming, primary uncommitted, primary committed, successor uncommitted, and successor committed. [STATE_PROFILE.json](evidence/STATE_PROFILE.json) pins the native layout, with 64 layers and 1,024 elements each for K and V per active position.

The public quick check validates the trace and published comparison records. To independently recalculate from authorized saved captures, provide a directory with `R/`, `SIMPLE/`, and `LOCAL/`, each pointing to its original request directory. Each must contain `RECEIPT.json`, `prefix-frontier.f32`, the `owned/` vectors and `states/` payloads. Python 3.10 and NumPy 2.3.5 were used for the A5000 readback. NumPy accelerates the reader if installed.

~~~sh
python3 -B runtime/local/check.py --captures "$CAPTURE_DIR"
~~~

The reader checks the complete input identity, finite values, active positions, full candidate/reference bytes, same-arm retained-prefix bytes, and each arm's pending/owned-score chain. Historical canonical bytes are identified by their published hashes in this mode. The resulting hash matches leave the earlier same-arm byte comparisons traceable to their original record. A saved raw serializer hash is also reported, separately from canonical byte equality.

## Native command interface for authorized replay

A fixed-case GPU replay requires the lawful original input/proposal bundle, both licensed GGUF files, and the independent q1 R built with its frozen numerical source. The R and original candidate ELF SHA-256 values are in [CASE.json](evidence/CASE.json). The build above produces a separately bound candidate ELF using the released CUDA backend. The release build has passed the model-free checks; this build has not been used for a new GPU qualification. It does not provide the independent q1 oracle. The saved-capture check uses the actual R capture.

With approved device access and prepared private config and command files, invoke one worker process per arm. The config keys are `gpu_uuid`, `target_model`, `target_sha256`, `draft_model`, `draft_sha256`, `source_freeze_sha256`, `prefill_pack4_enabled=false`, and `local_diagnostic=false`, together with the process's `local_lowering`. Set the candidate's `target_C_dispatch_profile` to `a5000_C_native4_small_width_v1`. Verify the GGUF hashes outside the worker. Set `LOWERING` to `SIMPLE` for R or SIMPLE and `LOCAL` for LOCAL. Use the independent R executable for the R command.

~~~sh
CUDA_VISIBLE_DEVICES="$RESEARCH_GPU_UUID" GGML_CUDA_DISABLE_GRAPHS=1 \
  HS_PREFILL_PACK4=0 HS_LOCAL_LOWERING="$LOWERING" OMP_NUM_THREADS=2 \
  HS_TPDS_TRACE=1 HS_RTX164_TRACE=1 \
  "$WORKER" "$CONFIG_JSON" "$NEW_OUTPUT_DIR" < "$ONE_REQUEST_JSONL"
~~~

The input is one private controller-admitted JSON record and optionally a finish record. The request envelope binds `actual_request_id`, `attempt`, the controller's `budget_reserved`, `source_freeze_sha256`, and `request`. Use `request.experiment=a5000_local_boundary_v1`, `stage=qualification`, `arm=R_TO` for R or `TO_C` for the candidate, `prompt_tokens=137`, the configured `lowering`, and the complete frozen `case_input`. The canonical JSON SHA-256 values and history hashes are in `TWO_HISTORIES.json`. An input hash is an identity check and does not supply the input tokens. The private controller must enforce device authorization and budget before invoking the worker. Keep the output directories private because receipts contain token IDs, paths and payloads.

## License and scope

Original frontend, readers, and scripts use the project's MIT license. Existing backend and dependencies retain their notices. The case index, author measurements and redacted derivatives use CC BY 4.0. See the [repository license](../../LICENSE.md), [runtime license scope](../LICENSE_SCOPE.md), and [third-party notices](../THIRD_PARTY.md). Separately acquired model weights and benchmark material retain their own terms.
