# CatalogIQ — AI Commerce Enrichment Architecture

## Overview
CatalogIQ Phase 5 transforms validated, evidence-backed product specifications into B2B commerce content (descriptions, bullet points, SEO metadata) without hallucinating or fabricating technical specifications.

## Safety Principles
1. **Evidence-Constrained Generation**: The LLM receives ONLY verified product attributes, evidence quotes, and features.
2. **Forbidden Fabrication**: The LLM is strictly prohibited from inventing specifications, certifications (e.g. IP65, CE), performance ratings, or warranty years.
3. **Number & Unit Preservation**: Numerical values (e.g. `230 V`, `5.5 kW`, `1440 RPM`) must be preserved exactly as given.

## Architecture

```
Validated Product & Attributes
        ↓
Build ProductContext
        ↓
Check Enrichment Cache (CacheService)
        ↓
BaseLLMProvider.enrich(product_context)
  ├── MockProvider (tests)
  ├── OllamaProvider (local dev: qwen3:8b)
  └── GeminiProvider (prod: gemini-3.6-flash)
        ↓
ClaimChecker Validation
        ↓
EnrichmentConfidenceCalculator (0.00 – 0.95)
        ↓
Persist EnrichmentResult & Update Product Fields
```

## Key Components

### 1. `CommerceEnrichment` Schema (`base.py`)
Pydantic model containing:
- `commerce_description` (2-3 paragraph factual B2B overview)
- `short_description` (1-2 sentence summary)
- `features` (bullet point features)
- `applications` (industrial use cases)
- `keywords` (catalog search tags)
- `seo_title` & `seo_description` (catalog SEO tags)

### 2. Claim Checker (`claim_checker.py`)
Scans generated text against verified product attributes:
- Detects altered or fabricated numbers.
- Detects unsupported certification or rating claims.
- Flags `unsupported_claim` and sets enrichment status to `needs_review` if violations occur.

### 3. Enrichment Confidence (`enrichment_confidence.py`)
- Returns confidence between `0.00` and `0.95`.
- AI commerce text is NEVER rated 1.0.
- Unsupported claims reduce confidence below `0.50`.
