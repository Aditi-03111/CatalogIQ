# CatalogIQ — Human Review & Conflict Resolution Workflow

## Overview
When conflicting attribute values exist across document sources or validation rules trigger warnings/errors, CatalogIQ marks the product status as `needs_review` and creates a `ValidationResult` record requiring human approval.

## Conflict Resolution Policy
1. **Never Silent Overwrite**: Conflicting values across sources are NEVER silently overwritten. Both source values and their original evidence quotes are preserved.
2. **Transactional Resolution**: Human resolution updates the target attribute value, marks the `ValidationResult` as `resolved`, creates a `ProductVersion` snapshot, and records an `AuditLog` entry.

## Status Progression

$$\text{Draft} \rightarrow \text{Extracted} \rightarrow \text{Validating} \rightarrow \text{Needs Review} \xrightarrow{\text{Human Approval}} \text{Verified} \rightarrow \text{Commerce Ready}$$

## API Endpoint
`POST /api/v1/products/{product_id}/validation/{validation_id}/resolve`

### Request Body
```json
{
  "resolution": "accept_source_a",
  "resolved_value": "32 kg",
  "notes": "Verified against physical catalog weight table."
}
```

### Resolution Options
- **`accept_source_a`**: Accepts the primary extracted value.
- **`accept_source_b`**: Accepts the conflicting second source value.
- **`custom_value`**: Sets an explicit manual value provided by the reviewer.
