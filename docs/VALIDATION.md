# CatalogIQ — Validation Architecture

## Overview
CatalogIQ Phase 5 introduces a multi-stage validation engine (`ValidationEngine`) that enforces data integrity, category constraints, physical unit correctness, and numeric range bounds on extracted product data.

## Pipeline Integration
Validation runs as Stage 3 of the 4-stage processing pipeline:
$$\text{ParsingStage} \rightarrow \text{ExtractionStage} \rightarrow \text{ValidationStage} \rightarrow \text{EnrichmentStage}$$

```
Extracted Product Attributes
        ↓
ValidationStage
        ↓
+-----------------------+
|  ValidationEngine     |
|  - Category Rules     |
|  - Unit Validator     |
|  - Range Validator    |
|  - Low Confidence     |
|  - Conflict Integration|
+-----------------------+
        ↓
Persist ValidationResult Records
        ↓
Calculate Product Quality Score (0–100)
        ↓
Update Product.status (verified vs needs_review)
```

## Key Components

### 1. Category Rule Registry (`validation_rules.py`)
Provides category-specific mandatory and optional attribute rules:
- **`industrial_motor`**: Required fields (`voltage`, `power`, `speed`), optional (`weight`, `efficiency`, `frequency`, `phase`).
- **Generic Fallback**: Evaluates present attributes without failing on unlisted categories.

### 2. Unit Validator (`unit_validator.py`)
- Standardizes unit strings (e.g., `"rpm"` → `"RPM"`, `"kilowatts"` → `"kW"`).
- Detects physical unit incompatibilities (e.g., `Power = "230 V"` → flags `invalid_unit`).

### 3. Range Validator (`range_validator.py`)
- Enforces physical numeric bounds (e.g., `voltage > 0`, `power > 0`, `speed >= 0`, `weight > 0`).
- Prevents negative specifications while avoiding artificial upper limit caps.

### 4. Validation Issues (`ValidationIssue`)
Structured issues with severity (`info`, `warning`, `error`, `critical`) and validation types:
- `missing_required_attribute`
- `invalid_unit`
- `invalid_numeric_value`
- `out_of_range`
- `cross_attribute_conflict`
- `low_confidence`
- `unsupported_claim`
