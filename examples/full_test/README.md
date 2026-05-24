# PrivCage Full Test Example

This folder contains sample input files for a full local smoke test.

Run from the project root:

```powershell
$env:PRIVCAGE_MASTER_KEY = "NTU1NTU1NTU1NTU1NTU1NTU1NTU1NTU1NTU1NTU1NTU"
.venv-gui\Scripts\python -m privcage preprocess --input examples\full_test\input --output examples\full_test\out --centralize-unprocessed --print-log
```

Expected behavior:

- Public files are written to `examples/full_test/out/input.privacy/`.
- Internal state is written to `examples/full_test/out/.privcage/`.
- `bad/nested/unsupported.bin` is copied to `.privcage/input.privacy/unprocessed/bad/nested/unsupported.bin`.
- Text PDF pages are written as text only.
- Image-only PDF pages are rendered into `figures/pdf_pages/`.

Restore one sample:

```powershell
.venv-gui\Scripts\python -m privcage restore --privacy examples\full_test\out\input.privacy\docs\note.txt.privacy --input examples\full_test\out\input.privacy\docs\note.txt.privacy\document.md --print-log
```

Default restored output:

```text
examples/full_test/out/input.privacy/docs/note.txt.privacy/note.txt_restored.md
```
