# Paper and figure reconstruction
Frozen author-manuscript reconstruction. No GPU/model execution.

1. Install dependencies listed in figures/requirements.txt, pypdf, and a full TeX Live setup with acmart font dependencies.
2. Run `python3 build.py --output /path/to/new-output` (Python optimization disabled).
3. Review the generated 33-page paper/main.pdf and BUILD_REPORT.json in that separate output directory.

Eight formal figure PDFs and 27 tables were rebuilt byte-for-byte against the final paper. Figure generation uses frozen statistics; it does not rerun all original experiments or the optional raw-ledger audit. Private raw ledgers and that audit script are deliberately omitted. The manuscript retains its frozen historical companion URL pending an authorized revision; this software release does not revise the submitted arXiv record.

Author-owned text/figures/data use CC BY 4.0; original Python packaging/plotting code uses MIT. See ../LICENSE.md; third-party components retain their own terms. acmart is LPPL 1.3 or later; its exact source is in third_party/acmart. ACM-Reference-Format.bst declares public domain. DejaVu font rights are retained under figures/typography/LICENSE_DEJAVU. Do not label the whole distribution MIT.

Tested TeX/font components: PDFLaTeX with a full TeX Live installation, Libertine 2024-04-23, zi4 1.12, and newtxmath 1.754. If your packages are installed outside TeX Live's standard trees, configure the corresponding TeX/font search paths before running. A clean environment without these dependencies is not expected to build successfully.
