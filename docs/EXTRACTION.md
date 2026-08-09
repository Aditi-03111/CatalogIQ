# CatalogIQ — AI Extraction Pipeline

## Overview

Phase 4 transforms a Docling Intermediate Representation (IR) into fully persisted, evidence-backed product intelligence.

## Pipeline Flow

```
Docling IR (parsed JSON from storage)
        │
        ├─────────────────────────────────────────┐
        │                                         │
        ▼                                         ▼
  Structured Tables                      Unstructured Text
  (IR pages[].tables)                    (IR pages[].text)
        │                                         │
        ▼                                         ▼
  TableExtractor                         LLM Provider
  (deterministic)                        (Ollama/Gemini/Mock)
  extraction_method="deterministic"      extraction_method="llm" or
  confidence base: 82                    "llm_inference"
        │                                         │
        └──────────────┬──────────────────────────┘
                       │
                       ▼
               Merged Candidate Data
               (deterministic attrs take precedence over LLM duplicates)
                       │
                       ▼
              EvidenceResolver
              (verifies evidence_text against IR corpus)
              (downgrades llm → llm_inference if unverified)
                       │
                       ▼
           AttributeNormalizer
           ("230 V" → {value: 230, unit: "V"})
                       │
                       ▼
          ConfidenceCalculator
          (0–100 score, multi-factor, transparent breakdown)
                       │
                       ▼
           ConflictDetector
           (checks existing attributes, marks conflicts,
            creates ValidationResult, NEVER overwrites)
                       │
                       ▼
            ProductService
            (upsert Product by SKU + brand)
                       │
                       ▼
         AttributeRepository
         (persist ProductAttribute + AttributeEvidence)
                       │
                       ▼
           CacheService
           (register extraction cache entry)
           key = SHA256(content_hash + schema_version + model + prompt_version)
                       │
                       ▼
              PostgreSQL ✓
```

## Extraction Cache Key

```
SHA256(
    content_hash              +  # SHA256 of normalized IR content
    extraction_schema_version +  # e.g., "v1"
    model_name                +  # e.g., "gemini-3.6-flash"
    prompt_version               # e.g., "v1.0"
)
```

Cache invalidation triggers:
- Document content changes (`content_hash` changes)
- LLM model upgrade (`model_name` changes)
- Prompt template revision (`prompt_version` incremented)
- Schema version bump (`extraction_schema_version` incremented)

## Deterministic vs LLM Split

| What | Method | Rationale |
|---|---|---|
| Table row values (Voltage \| 230 V) | `deterministic` | Structure is unambiguous |
| Product name, brand, SKU | `llm` | Requires reading document context |
| Category, description | `llm` | Semantic interpretation |
| Features, applications | `llm` | List comprehension from prose |
| Non-obvious inferences | `llm_inference` | No direct quote available |

## Idempotency

- Same document + same model + same prompt version → cache hit → skip re-extraction.
- Same SKU + brand → product update (not duplicate).
- Conflicting attribute values → both preserved, `ValidationResult` created, no overwrite.

## New API Endpoints (Phase 4)

| Endpoint | Description |
|---|---|
| `GET /api/v1/documents/{id}/extracted` | Extraction summary (product_id, attributes_count, model used) |
| `GET /api/v1/products/{id}/evidence` | All AttributeEvidence for a product's attributes |
| `GET /api/v1/products/{id}/attributes` | All ProductAttributes with confidence scores |
| `GET /api/v1/products/{id}/validation` | All ValidationResult records (including conflicts) |
