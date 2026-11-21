# Contributing to RefBound

Documentation fixes, clearer reproduction instructions and focused source changes
are welcome. Open an issue for a build or reconstruction problem, or a pull request
with the change and the checks you performed.

## Make the problem reproducible

Include the RefBound commit, relevant tool versions, the exact command and a small
error-log excerpt. State the expected result and what happened. For a numerical
discrepancy, identify the study and output field so the comparison uses the same
sampling unit and estimator.

## Check the affected workflow

Run these commands from the repository root after installing the dependencies in
the corresponding component README. Choose the workflow your change affects;
documentation-only changes need the file-integrity and link checks.

```sh
python3 verify.py
```

This verifies the files listed in the release manifest. Also check any links and
commands you changed in the rendered documentation.

| Component | Command from the repository root |
| --- | --- |
| [Saved-measurement statistics](reproduce/README.md) | `python3 reproduce/scripts/reproduce.py` |
| [CPU source and state checks](runtime/README.md) | `python3 runtime/scripts/build_cpu.py --out /absolute/path/to/new-cpu-build --jobs 2` |
| [Frozen paper and figures](paper/README.md) | `python3 paper/build.py --output /absolute/path/to/new-paper-build` |

The statistics command writes `reproduce/results/recomputed.json`. CPU and paper
builds require fresh output directories that do not already exist; place them
outside the repository. Run scientific verification without Python's `-O`, `-OO`
or `PYTHONOPTIMIZE` setting. Report the actual command and outcome in the pull
request; a documentation edit does not require rebuilding every component.

## Keep artifact identities accurate

Documentation is part of the distributed artifact. When a changed file appears
in a component manifest, refresh its byte count and SHA-256 there first:

- `paper/DELIVERY_MANIFEST.json`
- `reproduce/MANIFEST.json`
- `runtime/DELIVERY_MANIFEST.json`

Then update `RELEASE_MANIFEST.json` for the changed documents, component manifests
and any new distributed files. Keep unrelated entries unchanged and run
`python3 verify.py` after the updates. Mention the updated manifests in the pull
request.

Preserve frozen measurements, bootstrap draws, source identities and historical
validation records when fixing documentation or build instructions. Do not edit
`runtime/PROVENANCE.json`, `reproduce/SOURCE_MAP.json` or scientific expected
values merely to make a failed check pass. If a proposed research change requires
new inputs or expectations, describe that change and its provenance explicitly.

## Licensing and attribution

Follow the component's existing terms and retain upstream notices. Original
author software uses MIT; author-owned text, figures and released data use
CC BY 4.0. Third-party components retain their own licenses. See [LICENSE.md](LICENSE.md)
for the scope and exceptions. Use [CITATION.cff](CITATION.cff) when citing the work.
