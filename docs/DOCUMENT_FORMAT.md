# Parsed Intermediate Document Representation

All parsed documents in CatalogIQ are structured into a standardized, deterministic JSON schema before storage. This schema preserves page boundaries, tabular matrices, and layout elements required for evidence-backed AI extraction.

---

## 1. Schema Specifications

The intermediate file format is stored in object storage at `documents/parsed/{document_id}.json`.

```json
{
  "document_id": "uuid",
  "parser": {
    "name": "docling",
    "version": "1.5.0"
  },
  "content_hash": "deterministic_sha256_hash",
  "pages": [
    {
      "page_number": 1,
      "text": "Extracted layout text contents\n...",
      "tables": [
        {
          "headers": ["Specification", "Value"],
          "rows": [
            ["Voltage", "230 V"],
            ["Power", "5.5 kW"]
          ]
        }
      ],
      "images": [
        {
          "image_id": "uuid",
          "page_number": 1,
          "label": "wiring_diagram"
        }
      ]
    }
  ],
  "metadata": {
    "page_count": 1,
    "title": "Document Title Reference"
  }
}
```

---

## 2. Structural Elements

### 1. Page-Level Layout
Each item in the `pages` array maps to a physical PDF page. Layout boundaries are preserved so that subsequent LLM extractions can supply page numbers when referencing facts.

### 2. Structured Tables
Tables are maintained in structured cells (matrices of rows and headers) rather than being flattened into plain text strings. This retains the semantic context of cell mappings.

### 3. Image References
Extracted figures are stored through `StorageService` (`documents/assets/{document_id}/page-{num}-image-{idx}.png`) and listed as page element logs with unique IDs.

### 4. Content Hash (`content_hash`)
After generating the structured dict representation, the parser serializes the payload deterministically (sorting keys, removing non-significant whitespace). The SHA-256 hash of this string is stored as `content_hash`, allowing CatalogIQ to detect if different PDFs share identical semantic layout specs.
