# Asynchronous Processing Queue & Worker Pipeline

This document details the Celery-based worker queue, processing-stage abstractions, and execution fault-tolerance in CatalogIQ.

---

## 1. Queue Architecture

CatalogIQ splits the worker architecture into isolated stages:

```
 FastAPI App        Redis Broker        Celery Worker        Docling Parser
     │                   │                   │                      │
     ├─► Delay Task ────►│                   │                      │
     │                   ├─► Pulls Task ────►│                      │
     │                   │                   ├─► Executes Stage ───►│
     │                   │                   ├─► Writes JSON/Logs   │
     │                   │                   ├─► Updates DB Status  │
```

---

## 2. Processing-Stage Abstraction

Tasks are structured around a modular pipeline stage interface (`PipelineStage`):
- **ParsingStage**: Orchestrates fetching original files, running parsers, hashing parsed structures, and writing output.
- **Resumability**: Future stages (Extraction, Validation, Enrichment) can be chained sequentially without modifications to worker tasks or scheduler setups.

---

## 3. Idempotency & Fault-Tolerance

### Task Idempotency
Each worker task verifies the current database state of the `Document` before executing. If another worker thread has already completed the stage or is currently processing it, the task returns immediately without repeating layout parsing.

### Retry Rules
The Celery task classifies failures:
- **Transient Failures**: Connectivity timeouts (e.g. S3 timeout) raise `TransientProcessingError`, updating attempt logs and calling:
  `self.retry(exc=e, countdown=10)`
  (capped at 3 maximum attempts).
- **Non-Retryable Failures**: Format violations, empty files, or parser engine exceptions raise `NonRetryableProcessingError`, immediately setting step and job statuses to `failed` and committing the error trace to logs.

---

## 4. Reprocessing History Preservation
When a reprocessing request is triggered (`POST /reprocess`), the system resets the Document status to `uploaded` and schedules a new `ProcessingJob` / `ProcessingStep` pair. This appends to the log history instead of overwriting previous attempts, ensuring complete audit traceability.
