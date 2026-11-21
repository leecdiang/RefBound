# Paper and figure reconstruction

Rebuild the **bundled frozen reference manuscript**: **33 pages, 8 formal figures and 27 native TeX tables**. The builder regenerates the graphics from included inputs, checks them against the bundled exhibits, and compiles the manuscript in a fresh output directory.

[Repository home](../README.md) · [Artifact guide](../docs/README.md) · [Evidence map](../docs/EVIDENCE_MAP.md) · [arXiv record](https://arxiv.org/abs/2610.03228)

## Build from the repository root

Install the Python plotting dependencies and `pypdf` in your environment:

```sh
python -m pip install -r paper/figures/requirements.txt pypdf
```

A full **TeX Live** installation with **pdfLaTeX**, **acmart**, **Libertine**, **zi4** and **newtxmath** is also required. Tested font packages are Libertine 2024-04-23, zi4 1.12 and newtxmath 1.754. If your TeX packages live outside standard distribution trees, configure their TeX/font search paths first.

```sh
python3 paper/build.py --output /absolute/path/to/new-paper-build
```

Choose a directory that does not exist and is outside the repository. Run without Python optimization (`-O`, `-OO` or `PYTHONOPTIMIZE`).

## Outputs

| Path inside the new output directory | Content |
| --- | --- |
| `paper/main.pdf` | The 33-page bundled manuscript |
| `figures/figures/` | Regenerated formal figure PDFs |
| `figures/tables/` | Regenerated native TeX tables |
| `figures.log`, `tex-pass-*.log` | Figure-generation and TeX logs |
| `BUILD_REPORT.json` | Page count, PDF hash and reconstruction scope |

The builder verifies `DELIVERY_MANIFEST.json`, regenerates the eight figures and 27 tables, checks each against the bundled exhibit bytes, and compiles three TeX passes. It requires 33 pages and resolved citations and references. The recorded release check also compared all rendered pages with the frozen author manuscript at 144 DPI; that rendering check is distinct from PDF byte identity.

## Version and evidence scope

This is the manuscript snapshot distributed with the original RefBound artifact. The [arXiv record](https://arxiv.org/abs/2610.03228) is the public paper entry point; later manuscript revisions have their own source packages. A documentation update here preserves this builder's 33-page target and all scientific inputs.

Figure generation uses included frozen statistics and sidecars. The [statistical companion](../reproduce/README.md) reconstructs its specified estimates from scalar measurements; the [evidence map](../docs/EVIDENCE_MAP.md) distinguishes that route from the plotting inputs. Historical archive links in the bundled manuscript identify provenance; all required build inputs are included here. Model execution and original raw-ledger analysis are outside this workflow.

## Licenses

Author text, figures and data use CC BY 4.0; original Python packaging and plotting code use MIT. Third-party terms remain with their components: acmart is LPPL 1.3 or later (sources in `third_party/acmart`), `ACM-Reference-Format.bst` declares public domain, and DejaVu notices are in `figures/typography/LICENSE_DEJAVU`. See [LICENSE.md](../LICENSE.md) for the repository-wide scope.
