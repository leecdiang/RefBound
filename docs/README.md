# Artifact guide

RefBound has three public workflows. Start with the one that matches the question you want to answer.

| Question | Guide | Inputs and output |
| --- | --- | --- |
| How is P4 implemented? | [Runtime source](../runtime/README.md) | Included numerical core and frontend → CPU build, frontend objects and state checks |
| Do the saved measurements produce the reported statistics? | [Statistical reconstruction](../reproduce/README.md) | Released scalar records and fixed draws → `reproduce/results/recomputed.json` |
| How were the figures and bundled paper produced? | [Paper reconstruction](../paper/README.md) | Plotting inputs and frozen sidecars → 8 figures, 27 tables and a 33-page manuscript |

Use the [evidence map](EVIDENCE_MAP.md) to connect manuscript labels to the datasets and reconstructed fields. All commands in the component guides are written from the repository root.

## Manuscript versions

The `paper/` build is bound to the **bundled frozen reference manuscript** and checks a **33-page** result. It preserves that artifact's figures, tables and text. The [arXiv record](https://arxiv.org/abs/2610.03228) is the public paper entry point; a later manuscript revision can use a separate self-contained source package.

Repository documentation and the bundled manuscript can therefore be updated on different schedules. Follow a source package's own build instructions and identify the commit used when reporting a result.

## Reading the provenance records

| Record | What it identifies |
| --- | --- |
| [`runtime/PROVENANCE.json`](../runtime/PROVENANCE.json) | Recovered runtime source, transformation chain and historical source identities |
| [`runtime/VALIDATION.json`](../runtime/VALIDATION.json) | The recorded CPU build, frontend-object and model-free state checks |
| [`reproduce/SOURCE_MAP.json`](../reproduce/SOURCE_MAP.json) | Released statistical derivatives, their hashes and historical input identities |
| [`paper/DATA_MINIMIZATION.json`](../paper/DATA_MINIMIZATION.json) | The inputs selected for the figure and manuscript package |
| [`RELEASE_MANIFEST.json`](../RELEASE_MANIFEST.json) | Distributed file sizes and SHA-256 identities for this repository revision |

Some frozen records retain labels such as `PRIVATE_REVIEW_CANDIDATE_NOT_RELEASED` or `public_release: false`. Those fields describe the candidate-stage snapshot in which the checks were recorded. They are retained as historical evidence; the files linked here are available in this public repository. A documentation change refreshes distribution-file hashes without rewriting the scientific source identities or original validation outcomes.

Historical archive hashes and private commit identifiers are provenance labels. The three public workflows use the inputs distributed here and do not need access to those archives.

## What each kind of check establishes

**File verification** checks the byte counts and SHA-256 hashes of manifest-listed files. Extra local files are outside that check.

**Statistical reconstruction** checks estimates and the specified intervals against frozen references. Earlier-study and M1 interval endpoints retain their recorded scope in the [statistics guide](../reproduce/SCOPE.md).

**CPU build and state checks** exercise source compilation and consumer-state logic. CUDA arithmetic and complete worker execution require the [deployment-specific CUDA checks](../runtime/CUDA_BUILD.md). The public frontend is the P4 application frontend; the later LOCAL diagnostic frontend is a separate artifact.

**Paper reconstruction** regenerates exhibits from their included inputs and compiles the frozen manuscript. It is a saved-artifact workflow, separate from original model execution. Model weights, original prompt text and full captured vocabulary/KV payloads are outside this distribution.

## Citation, maintenance and licenses

- [CITATION.cff](../CITATION.cff): paper citation; also identify the RefBound commit used.
- [Contributing](../CONTRIBUTING.md): focused corrections, reproduction reports and manifest maintenance.
- [Release checks](RELEASE_CHECKLIST.md): the original artifact validation record and steps to repeat for a release.
- [Licensing](../LICENSE.md): MIT author software, CC BY 4.0 author materials and preserved third-party terms.
