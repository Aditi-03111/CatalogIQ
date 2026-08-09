# CatalogIQ — Evidence Architecture

## Separation of Concepts

| Entity | Represents | Example |
|---|---|---|
| `Document` | Physical uploaded file | `motor_datasheet.pdf` (SHA-256 identified) |
| `Source` | Provenance record for a document | Source type: `document`, trust_level: 0.9 |
| `AttributeEvidence` | Specific supporting evidence for one attribute | Page 2, "Voltage \| 230 V", method: `deterministic` |

## Traceability Chain

```
Product
  └── ProductAttribute (e.g., rated_voltage = 230 V)
        └── AttributeEvidence
              ├── source_id  → Source (provenance)
              │                  └── document_id → Document (physical file)
              ├── document_id → Document (direct FK for quick queries)
              ├── page_number → 2
              ├── evidence_text → "Voltage | 230 V"
              └── extraction_method → "deterministic"
```

## Extraction Methods

| Method | Meaning | `evidence_verified` |
|---|---|---|
| `deterministic` | Extracted from a structured Docling table. High certainty of correct attribution. | Set by EvidenceResolver (raw_value in corpus) |
| `llm` | LLM extracted with a direct document quote. `evidence_text` contains the verbatim quote. | Set by EvidenceResolver (quote found in IR) |
| `llm_inference` | LLM inferred this value. No direct quote available. Lower confidence, may be flagged. | Always `False` |

## EvidenceResolver Rules

The `EvidenceResolver` runs **after** LLM output and **before** confidence scoring.

1. **`deterministic`**: Verifies `raw_value` appears anywhere in the IR corpus. If not found (e.g., normalized differently), sets `evidence_verified=False` with a warning log.
2. **`llm`**: Verifies `evidence_text` exists in the IR corpus. Uses substring + word-overlap matching. If NOT found → **downgrades** `extraction_method` to `llm_inference` and sets `evidence_verified=False`.
3. **`llm_inference`**: Always `evidence_verified=False` by definition. No verification attempted.

**The pipeline sets `evidence_verified`. The LLM never sets it.** LLM output always has `evidence_verified=False`; only the EvidenceResolver can set it to `True`.

## Source Trust Levels

| Source Type | Default Trust | Rationale |
|---|---|---|
| `document` (manufacturer datasheet) | 0.9 | Primary source, generally reliable |
| `catalog` | 0.8 | Curated but may have errors |
| `manual` | 0.9 | High authority |
| `ai_inference` | 0.7 | AI-derived, needs verification |
| `human` | 1.0 | Human-verified — highest trust |
| `manufacturer_website` | 0.85 | Authoritative but mutable |

## API

- `GET /api/v1/products/{product_id}/evidence` — all evidence for all attributes of a product.
- `GET /api/v1/products/{product_id}/attributes` — all attributes with their confidence scores.
