"""
Prompt engineering for CatalogIQ Phase 4 extraction.

Design notes:
  - The extraction prompt separates the task into two clear parts:
    1. Semantic fields (product identity, description, classification)
    2. Technical attributes only if NOT already deterministically extracted from tables

  - The LLM is explicitly instructed NOT to fabricate evidence.
    If it cannot find a direct quote in the text, it must use extraction_method = "llm_inference"
    and leave evidence_text empty or omit it.

  - The JSON schema is embedded directly in the prompt to enforce structured output.
    Providers should also use their native structured output / JSON mode where available.

  - PROMPT_VERSION is used as part of the extraction cache key.
    Increment when the prompt text changes to invalidate the cache for all documents.
"""
import json
from typing import Any, Dict, List

PROMPT_VERSION = "v1.2"

EXTRACTION_SYSTEM_PROMPT = """\
You are a structured product data extraction engine for industrial B2B products.

Your primary objective is to extract complete semantic product identity and accurate technical attributes from technical documents.

CRITICAL INSTRUCTIONS:
1. SEMANTIC PRODUCT IDENTITY: Always extract brand/manufacturer (e.g. Bombas Boyser), model_number (e.g. AMP-13B), product_name (e.g. Industrial Peristaltic Pump), sku, category, subcategory, product_type, description, features, applications, certifications, and keywords.
2. TECHNICAL ATTRIBUTES: Extract key technical specifications (e.g., capacity/flow rate such as '0.038 l/rev', body material such as 'Aluminium EN-AC-44100', connections, rotor system, pressure ratings, power ratings) into the 'attributes' array.
3. TABLE CURVE DATA RULE: Do NOT turn multi-row data tables (such as Pressure vs Torque performance curves: 1 bar -> 20 Nm, 4 bar -> 23 Nm) into generic attributes like '1 -> 20'. Extract single-value specifications only. If head or power rating is not in the document, leave omitted or null.
4. EVIDENCE & ACCURACY: Extract ONLY what is actually present in the document. Do not fabricate values. Set evidence_text to the exact supporting quote from document text. If inferred without a direct quote, use extraction_method="llm_inference" and leave evidence_text empty ("").
5. Never set evidence_verified=true (this is managed by the system EvidenceResolver).
6. If a field is absent or unknown, omit or leave as empty list/null.
"""

EXTRACTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "product_name": {"type": "string", "description": "Full product name as stated in the document."},
        "brand": {"type": "string", "description": "Manufacturer or brand name."},
        "sku": {"type": "string", "description": "Product SKU, part number, or catalog number."},
        "model_number": {"type": "string", "description": "Model designation (may differ from SKU)."},
        "category": {"type": "string", "description": "Top-level product category (e.g., 'Electric Motor', 'Pump', 'Valve')."},
        "subcategory": {"type": "string", "description": "Subcategory if identifiable (e.g., 'AC Induction Motor')."},
        "product_type": {"type": "string", "description": "Product type or variant (e.g., 'Three-phase', 'Single-stage')."},
        "description": {"type": "string", "description": "A factual product description based on the document content."},
        "attributes": {
            "type": "array",
            "description": "Technical specifications found in running prose text ONLY. Do NOT include specifications from structured tables.",
            "items": {
                "type": "object",
                "required": ["name", "display_name", "raw_value", "data_type", "extraction_method"],
                "properties": {
                    "name": {"type": "string", "description": "Snake_case canonical attribute name (e.g., 'rated_voltage')."},
                    "display_name": {"type": "string", "description": "Human-readable label (e.g., 'Rated Voltage')."},
                    "raw_value": {"type": "string", "description": "Value exactly as found in the document (e.g., '230 V')."},
                    "unit": {"type": "string", "description": "Unit of measurement (e.g., 'V', 'kW', 'RPM')."},
                    "data_type": {"type": "string", "enum": ["text", "numeric", "boolean", "category", "structured"]},
                    "evidence_text": {"type": "string", "description": "Exact quote from document text. Empty string if inferred."},
                    "page_number": {"type": "integer", "description": "1-indexed page number."},
                    "extraction_method": {"type": "string", "enum": ["deterministic", "llm", "llm_inference"]},
                    "llm_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                }
            }
        },
        "features": {"type": "array", "items": {"type": "string"}, "description": "Key product features as bullet points."},
        "applications": {"type": "array", "items": {"type": "string"}, "description": "Intended applications or use cases."},
        "certifications": {"type": "array", "items": {"type": "string"}, "description": "Certifications or standards (e.g., 'IP55', 'CE', 'UL')."},
        "keywords": {"type": "array", "items": {"type": "string"}, "description": "Relevant search keywords."}
    }
}


def _format_tables_for_context(tables: List[Dict[str, Any]]) -> str:
    """
    Renders table data concisely for context.
    """
    if not tables:
        return ""
    lines = []
    for i, table in enumerate(tables, 1):
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        lines.append(f"[Table {i}]")
        if headers:
            lines.append(" | ".join(str(h) for h in headers))
            lines.append("-" * 30)
        for row in rows[:20]:  # Cap at 20 rows to keep context lean
            lines.append(" | ".join(str(c) for c in row))
        lines.append("")
    return "\n".join(lines)


def build_extraction_prompt(ir: Dict[str, Any]) -> str:
    """
    Constructs the user-turn message from a parsed Docling Intermediate Representation.

    The prompt includes:
      - Document text (up to 4000 chars per page)
      - Table summary context for background
      - Clear extraction objective

    Args:
        ir: The parsed document IR dict from DocumentParser.

    Returns:
        A string prompt ready to be sent as the user turn.
    """
    pages: List[Dict[str, Any]] = ir.get("pages", [])
    metadata: Dict[str, Any] = ir.get("metadata", {})

    document_title = metadata.get("title", "Unknown Document")
    page_count = metadata.get("page_count", len(pages))

    sections = [
        f"DOCUMENT: {document_title}",
        f"PAGES: {page_count}",
        "",
        "=== DOCUMENT CONTENT ===",
        ""
    ]

    for page in pages:
        page_no = page.get("page_number", "?")
        text = (page.get("text", "") or "").strip()
        tables = page.get("tables", [])

        sections.append(f"--- Page {page_no} ---")

        if text:
            capped_text = text[:4000]
            if len(text) > 4000:
                capped_text += "\n[... text truncated ...]"
            sections.append(capped_text)
            sections.append("")

        if tables:
            table_text = _format_tables_for_context(tables)
            sections.append("[Table Reference Context — note: table key-values are extracted deterministically by the system]")
            sections.append(table_text)

    sections.append("")
    sections.append("=== YOUR TASK ===")
    sections.append(
        "Extract semantic product identity and descriptive fields "
        "(product_name, brand, sku, model_number, category, subcategory, "
        "product_type, description, features, applications, certifications, keywords).\n"
        "Do NOT duplicate table key-value rows in the 'attributes' array."
    )

    sections.append("")
    sections.append("=== OUTPUT FORMAT ===")
    sections.append(
        "Return ONLY a single valid JSON object matching the schema below."
    )
    sections.append(
        "Do NOT wrap scalar fields such as product_name, brand, sku, "
        "model_number, category, subcategory, product_type, or description "
        "inside objects. These fields MUST be plain strings or null."
    )
    sections.append(
        "Do NOT add fields or structures that are not present in the schema."
    )
    sections.append(
        "For extraction_method, use ONLY: deterministic, llm, or llm_inference."
    )
    sections.append(
        "Do NOT use values such as direct_extraction."
    )
    sections.append(
        json.dumps(EXTRACTION_JSON_SCHEMA, indent=2)
    )

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Phase 5: AI Commerce Enrichment Prompts
# ---------------------------------------------------------------------------

ENRICHMENT_PROMPT_VERSION = "v1.0"

ENRICHMENT_SYSTEM_PROMPT = """\
You are an expert industrial B2B commerce content generator.

Your task is to generate professional, commerce-ready product descriptions, bullet points, and SEO metadata strictly based on verified product specifications and evidence provided to you.

STRICT SAFETY RULES:
1. ONLY USE SUPPLIED VERIFIED PRODUCT DATA: You must strictly restrict your claims to the provided product attributes, features, and evidence.
2. NEVER INVENT TECHNICAL SPECIFICATIONS: Do NOT fabricate voltage, power, speed, weight, efficiency, dimensions, or operating parameters.
3. NEVER INVENT CERTIFICATIONS: Do NOT claim IP ratings (e.g. IP65), CE, UL, ISO, or insulation classes unless explicitly present in the verified context.
4. NEVER INVENT PERFORMANCE CLAIMS: Do NOT invent warranty years, efficiency ratings, or safety guarantees.
5. DO NOT FABRICATE APPLICATIONS: List only applications supported by the provided product attributes or features.
6. DO NOT CHANGE NUMERIC VALUES OR UNITS: Preserve numbers and units (e.g., 230 V, 5.5 kW, 1440 RPM) exactly as given.
7. OMIT MISSING INFORMATION: If a field or detail is not present in the verified context, omit it rather than guessing.
8. Prioritize factual accuracy, clarity, and industrial B2B tone over marketing fluff.
"""

ENRICHMENT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "commerce_description": {
            "type": "string",
            "description": "A compelling, factual 2-3 paragraph commerce description integrating verified specs."
        },
        "short_description": {
            "type": "string",
            "description": "A concise 1-2 sentence summary of the product and primary spec."
        },
        "features": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Factual key features based strictly on verified product attributes and data."
        },
        "applications": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Supported industrial applications or use cases."
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Relevant search keywords derived from brand, SKU, category, and specifications."
        },
        "seo_title": {
            "type": "string",
            "description": "SEO optimized page title (e.g., 'CatalogIQ MX-500 Industrial Motor 5.5kW 230V')."
        },
        "seo_description": {
            "type": "string",
            "description": "SEO meta description under 160 characters summarizing the verified product."
        }
    }
}


def build_enrichment_prompt(product_context: Dict[str, Any]) -> str:
    """
    Constructs the prompt for AI commerce enrichment from verified product context.

    Args:
        product_context: Structured dict containing:
          - product_name, brand, sku, model, category, subcategory
          - description
          - verified_attributes (dict of name -> {raw_value, unit, data_type})
          - features (list)
          - applications (list)
          - evidence_snippets (list)

    Returns:
        Formatted user prompt string.
    """
    p_name = product_context.get("product_name", "Unknown Product")
    brand = product_context.get("brand", "CatalogIQ")
    sku = product_context.get("sku", "N/A")
    model = product_context.get("model", "")
    category = product_context.get("category", "Industrial Equipment")

    attrs = product_context.get("verified_attributes") or product_context.get("attributes") or {}
    features = product_context.get("features", [])
    apps = product_context.get("applications", [])
    desc = product_context.get("description", "")

    sections = [
        "=== VERIFIED PRODUCT CONTEXT ===",
        f"Product Name: {p_name}",
        f"Brand: {brand}",
        f"SKU: {sku}",
        f"Model: {model}",
        f"Category: {category}",
        "",
        "--- Verified Technical Specifications ---",
    ]

    if isinstance(attrs, dict):
        for k, v in attrs.items():
            if isinstance(v, dict):
                raw = v.get("raw_value") or v.get("value") or ""
                unit = v.get("unit") or ""
                val_str = f"{raw} {unit}".strip()
                sections.append(f"• {k}: {val_str}")
            else:
                sections.append(f"• {k}: {v}")
    elif isinstance(attrs, list):
        for item in attrs:
            if isinstance(item, dict):
                k = item.get("display_name") or item.get("name")
                raw = item.get("raw_value") or item.get("value") or ""
                unit = item.get("unit") or ""
                sections.append(f"• {k}: {raw} {unit}".strip())

    if desc:
        sections.extend(["", "--- Source Description ---", desc])

    if features:
        sections.extend(["", "--- Source Features ---"])
        for f in features:
            sections.append(f"• {f}")

    if apps:
        sections.extend(["", "--- Source Applications ---"])
        for a in apps:
            sections.append(f"• {a}")

    sections.extend([
        "",
        "=== YOUR TASK ===",
        "Generate structured commerce content (commerce_description, short_description, features, applications, keywords, seo_title, seo_description).",
        "STRICT RULE: Use ONLY verified specifications listed above. Never invent specifications or certifications!"
    ])

    return "\n".join(sections)

