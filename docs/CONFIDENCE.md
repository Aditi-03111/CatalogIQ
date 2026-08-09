# CatalogIQ — Confidence Scoring

## Overview

CatalogIQ uses a **transparent, multi-factor confidence scoring system** (0–100 scale) for all extracted product attributes. This score is NOT treated as a mathematical probability — it is a heuristic that communicates the relative trustworthiness of an extracted value.

## Scale

| Score | Status | Meaning |
|---|---|---|
| ≥ 85 | `verified` | High-confidence, evidence-backed value |
| 60–84 | `extracted` | Reasonable confidence, may need review for critical fields |
| < 60 | `needs_review` | Low confidence; LLM inference, conflict, or failed normalization |

Thresholds are configurable via `CONFIDENCE_THRESHOLD_HIGH` (0–1 float, default `0.85`) and `CONFIDENCE_THRESHOLD_MEDIUM` (default `0.60`).

## Factors

| Factor | Effect | Rationale |
|---|---|---|
| `extraction_method = deterministic` | Base: **82** | Strong structural signal from table, but not infallible |
| `extraction_method = llm` | Base: **72** | LLM with direct quote in evidence_text |
| `extraction_method = llm_inference` | Base: **52** | LLM inferred with no direct quote |
| `evidence_verified = True` | **+12** | EvidenceResolver found the quote verbatim in IR |
| `evidence_verified = False` (llm method) | **−4** | LLM claimed a quote but it wasn't found |
| `normalization_success = True` | **+4** | Raw value successfully parsed to typed form |
| `llm_confidence ≥ 0.85` | **+6** | LLM self-reported high certainty |
| `llm_confidence < 0.40` | **−10** | LLM self-reported low certainty |
| `source_trust` (0.0–1.0) | **×multiplier** | Scaled trust level of the provenance Source |
| `conflict_count ≥ 1` | **−8 per conflict** (max −20) | Conflicting existing attributes reduce trust |

## Example Calculations

### Deterministic Table Attribute (verified)
```
extraction_method = deterministic   → base = 82
evidence_verified = True            → +12
normalization_success = True        → +4
llm_confidence = 0.88               → +6
source_trust = 0.9                  → ×0.9
conflict_count = 0                  → no penalty

raw = (82 + 12 + 4 + 6) × 0.9 = 104 × 0.9 = 93.6
clamped = 93.6 → status: "verified"
```

### LLM Inference (no evidence)
```
extraction_method = llm_inference   → base = 52
evidence_verified = False           → no bonus
normalization_success = True        → +4
llm_confidence = 0.55               → no bonus/penalty
source_trust = 1.0                  → ×1.0
conflict_count = 0                  → no penalty

raw = (52 + 4) × 1.0 = 56.0 → status: "needs_review"
```

## Conflict Policy

When `ConflictDetector` detects that a newly extracted value differs from an existing attribute value:

1. The **existing attribute** is marked `status = conflicting`.
2. A `ValidationResult` with `type = cross_source_conflict` is created.
3. The **new attribute** is still persisted with a reduced confidence score.
4. **Neither value is silently overwritten.**
5. Human resolution (future Phase 5) resolves which value to accept.

## Storage

Confidence is stored in `ProductAttribute.confidence` as a `0.0–1.0` float (divide score by 100). The original 0–100 breakdown is available in logs.
