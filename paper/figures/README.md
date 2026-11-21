# Editable scientific figures

Regenerate **eight formal figures**, **three editable alternatives** and **27 native TeX tables**. Figure outputs include both PDF and SVG.

[Paper guide](../README.md) · [Artifact guide](../../docs/README.md) · [Evidence map](../../docs/EVIDENCE_MAP.md)

## Rebuild

The [paper builder](../README.md#build-from-the-repository-root) copies the figure workspace to a new output directory, regenerates the exhibits and compiles the bundled manuscript.

To work on the figures alone, install `paper/figures/requirements.txt`, copy this directory to a new workspace outside the repository, then run its entry point. From the repository root:

```sh
python -m pip install -r paper/figures/requirements.txt
cp -R paper/figures /absolute/path/to/new-figure-workspace
python3 /absolute/path/to/new-figure-workspace/scripts/rebuild.py
```

Use a destination that does not already exist. The script resolves paths from its own location and writes to the copied workspace. Run without `-O`, `-OO` or `PYTHONOPTIMIZE`.

## Inputs and checks

The pipeline checks frozen input hashes, saved values, pairing and visual encodings before producing the exhibits. [REBUILD_REPORT.json](proof/REBUILD_REPORT.json) records the original regeneration stages, environment and output identities. It reconstructs saved evidence on the CPU; original GPU/model execution is a separate workflow.

The three native CSV derivatives retain selected statistical fields and the original numerical values and row order. RTX per-row labels are assigned public IDs. [DATA_MINIMIZATION.json](../DATA_MINIMIZATION.json) documents the field selection; original prompt hashes, backend identities, host timestamps and source receipts remain outside this package.

## Licenses and manuscript links

Author text, figures and data use CC BY 4.0; original scripts use MIT, subject to the third-party terms in [LICENSE.md](../../LICENSE.md). DejaVu notices are retained in `typography/LICENSE_DEJAVU`.

The bundled manuscript preserves its historical links, some of which identify private source archives. All inputs required by this public figure entry point are included here.
