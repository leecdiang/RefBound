# Release checks

Use this guide when preparing a repository update. The [contribution guide](../CONTRIBUTING.md) describes how to keep distribution hashes current while preserving scientific source identities.

## Recorded artifact validation

The original release preparation completed data minimization, third-party license review, file-identity checks, adverse-case preservation, independent statistical checks, CPU core/frontend-object compilation, and figure/manuscript reconstruction.

| Component | Preserved record |
| --- | --- |
| Statistics, including corrupted-input and optimized-Python rejection | [`reproduce/validation/`](../reproduce/validation/) |
| CPU core, real frontend objects and state tests | [`runtime/VALIDATION.json`](../runtime/VALIDATION.json) |
| Figure regeneration and frozen exhibit identities | [`paper/figures/proof/REBUILD_REPORT.json`](../paper/figures/proof/REBUILD_REPORT.json) |
| Source provenance and distributed file identities | [`runtime/PROVENANCE.json`](../runtime/PROVENANCE.json), [`reproduce/SOURCE_MAP.json`](../reproduce/SOURCE_MAP.json), [`RELEASE_MANIFEST.json`](../RELEASE_MANIFEST.json) |

These records describe the checks performed for that artifact snapshot. Keep their original outcomes and historical status labels intact.

## Prepare an update

1. **State the scope.** Identify the affected documents or workflow. A change to instructions or presentation should preserve frozen data, source identities and expected scientific values.
2. **Check the reader's path.** Review the rendered README, relative links, commands, output locations, citation metadata and license scope. Keep the bundled 33-page manuscript distinct from later paper source packages.
3. **Run the affected workflow.** Use the commands in the [statistics](../reproduce/README.md), [runtime](../runtime/README.md) or [paper](../paper/README.md) guide. Record the command, environment and observed outcome. Documentation edits need integrity and link checks; they do not require a new model run.
4. **Refresh distribution manifests.** Update changed document entries in component manifests first, then their entries and any new files in `RELEASE_MANIFEST.json`. Leave scientific provenance and unrelated entries unchanged.
5. **Verify the proposed checkout.** Run `python3 verify.py` from the repository root. Review the diff and confirm that generated local outputs are excluded.
6. **Describe the result.** Include the actual checks in the pull request or release notes and link any new manuscript package separately.

## Deployment work

A new GPU deployment follows the [CUDA build and qualification guide](../runtime/CUDA_BUILD.md): compile the true CUDA backend, link the complete worker and qualify numerical behavior on the target toolchain and device. A general-purpose model/input interface and portable deployment configuration are separate development work. The public artifact preserves the study frontend and its guards.

Repository publication and arXiv replacement are separate actions. Model weights, original prompts and full numerical-state captures are outside this distribution.
