# Paper PDFs

Place 1-3 real academic paper PDFs that you are authorized to use in this directory.

Run:

```bash
.venv/bin/python -m rag.cli ingest
.venv/bin/python -m rag.cli ask "Your question about the imported papers"
```

This first version does not perform OCR. Image-only or otherwise non-extractable pages
are reported and skipped.
