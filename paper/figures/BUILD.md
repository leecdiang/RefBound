# Rebuilding
From the package root use `python3 build.py --output /path/to/new-output` for package integrity checks, isolated figure/table regeneration, three-pass PDFLaTeX and output checks. The output path must be new and outside the package tree. Temporary font caches live inside that output directory. The original package is not modified.

Requirements: Python dependencies listed here in requirements.txt, pypdf, PDFLaTeX and complete TeX/font dependencies described in ../paper/BUILD.txt. Install them before running; this build does not install software or access a network. Environment variables for an existing TeX installation may be needed on nonstandard setups. No absolute author machine path is embedded in the build entry point.

For a figure-only editing copy: `python3 scripts/rebuild.py`. That command writes generated outputs within its own copied figure directory. It verifies the derived data ZIP/manifest and prescribed bootstrap draws, executes the five generators, regenerates caption metadata and performs bounded encoding checks. Optional historical raw audit and preview builders are not part of this candidate.

Optimized Python is rejected. Do not use -O/-OO or PYTHONOPTIMIZE. An intentionally modified frozen draw file was verified to fail before drawing. All eight final PDFs and 27 TeX tables matched the final author manuscript byte for byte after data minimization.
