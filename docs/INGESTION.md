# Document Ingestion Flow & Security

This document outlines the ingestion, validation, and deduplication logic implemented in CatalogIQ.

---

## 1. Upload & Ingestion Timeline

The HTTP handler for uploads acts as a lightweight dispatcher:

```
Client                  FastAPI Server                   Postgres DB
  │                           │                               │
  ├─► POST /upload ───────────┤                               │
  │   (multipart PDF file)    │                               │
  │                           ├─► Calculate SHA-256           │
  │                           ├─► Check duplicate ───────────►│
  │                           ├─► Upload original to S3/Store │
  │                           ├─► Insert Document & Job ─────►│
  │                           │   (commit transaction)        │
  │                           ├─► Dispatch Celery task        │
  │                           │                               │
  ├─◄ Return 201 Response ────┤                               │
  │   (job_id, queued status) │                               │
```

---

## 2. File Validation Controls

CatalogIQ performs three levels of validation before storing files:
1. **Size check**: Rejects empty files or files exceeding `MAX_UPLOAD_SIZE_MB` (configured via env).
2. **Extension check**: Restricts uploads strictly to `.pdf` extensions.
3. **Magic Bytes Validation**: Reads the first 4 bytes of the binary stream to verify it matches the standard `%PDF` file signature, preventing MIME-spoofing attacks.

---

## 3. Concurrency Safety & Deduplication

### Database-Level Unique Constraint
To prevent race conditions where two threads/users upload the same document simultaneously, the system relies on a uniqueness constraint on `Document.file_hash`. If a conflict occurs, the transaction rolls back, catches `IntegrityError`, cleans up storage uploads, and returns the existing database record.

### Idempotency States
Upon upload, the system calculates `SHA256(file_bytes)` and performs deduplication:
- **Completed Document**: If `Document.status == "processed"`, the upload returns the cached representation immediately without starting a worker task (`cached: true`, `status: "already_processed"`).
- **Active Job**: If `Document.status` is `uploaded` or `parsing`, it returns the active `ProcessingJob` ID (`cached: true`, `status: "processing"`).
- **Failed Job**: If the previous attempt failed, the upload reset status to `uploaded` and schedules a new clean attempt.
