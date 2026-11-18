# Validation
CPU only. Full figure wrapper regenerated 8 formal + 3 alternative vector figures and 27 tables. Eight formal PDFs and 27 TeX tables match the frozen final manuscript byte for byte. Three-pass PDFLaTeX in isolated build directory creates 33 pages; prior same-input build matches all final PDF pages at 144 DPI and extracted text. TeX requires a full preinstalled dependency/font environment. No GPU/model requests.

All Python source entry points explicitly refuse optimized execution. Tested `python -O scripts/rebuild.py`: exit 1 before data access. Appending one newline to frozen draw JSONL in a separate disposable copy: hash/size guard fails with exit 1 before generation. These checks do not make a maliciously modified validation program trustworthy.

Template source: repository Git blobs acmart.dtx 257befe7a82c5cc461798e2818a0de8688fa175c, acmart.ins d17dc066fd7f86023b4ea0e33aa75aef95b33857. Local bytes match Git objects. Actual docstrip generation yielded cls SHA256 f125da317f9786bebc39dea412bc942405eee18f960f33d83b4ac936ff4438e5, identical to bundled manuscript class. LPPL text retained.

Removed private raw audit ledgers and optional audit_values.py. Recursive text and nested ZIP scan found no selected private absolute path/IP patterns; this is a bounded scan, not a universal privacy guarantee. Historic GitHub links remain intentional provenance and may require access. Final public naming/licensing and companion URL update are release decisions not performed here.

## Public-data minimization update
The three native CSV inputs are now field-allowlisted derivatives (see DATA_MINIMIZATION.json). RTX original request identifiers are replaced by synthetic public row labels. Removed prompt hashes, backend identities, scheduling IDs, host wall clocks, native receipt hashes and reference IDs are not shipped in these tables. The scientific ZIP, member manifest and corresponding frozen checks were updated as a new derivative, not represented as original raw bytes. The sanitized-data full-chain entry point passed: eight figure PDFs and 27 tables byte-identical to final manuscript, three-pass TeX 33 pages. The manuscript itself is unchanged.
