"""
Search document representation and Qdrant payload builder.
Constructs canonical, fact-bounded textual representations and payloads strictly from verified product data.
"""
import json
from typing import Any, Dict, List, Optional

from app.models import EnrichmentResult, Product, ProductAttribute


def build_search_document(
    product: Product,
    attributes: List[ProductAttribute],
    enrichment: Optional[EnrichmentResult] = None,
) -> str:
    """
    Builds a canonical, structured text representation of a product for vector embedding.

    FACT-BOUNDED SAFETY RULE:
      Only includes information already stored in PostgreSQL product, attribute, and
      enrichment records. Missing specifications are omitted and NEVER invented.

    Args:
        product: Authoritative Product SQLModel record.
        attributes: List of associated ProductAttribute records.
        enrichment: Optional EnrichmentResult record.

    Returns:
        Structured multiline text canonical representation.
    """
    sections: List[str] = []

    # 1. Product Identity
    identity_lines = [f"{product.product_name}"]
    if product.brand:
        identity_lines.append(f"Manufacturer: {product.brand}")
    if product.sku:
        identity_lines.append(f"SKU: {product.sku}")
    if product.model:
        identity_lines.append(f"Model: {product.model}")
    if product.category:
        cat_str = product.category
        if product.subcategory:
            cat_str += f" > {product.subcategory}"
        identity_lines.append(f"Category: {cat_str}")
    if product.product_type:
        identity_lines.append(f"Type: {product.product_type}")

    sections.append("\n".join(identity_lines))

    # 2. Base Description
    if product.description:
        sections.append(f"Description:\n{product.description.strip()}")

    # 3. Technical Specifications
    if attributes:
        spec_lines = ["Specifications:"]
        for attr in sorted(attributes, key=lambda a: a.display_name or a.attribute_name):
            val = attr.raw_value.strip()
            unit_str = f" {attr.unit.strip()}" if attr.unit and attr.unit.strip() else ""
            spec_lines.append(f"- {attr.display_name}: {val}{unit_str}")
        sections.append("\n".join(spec_lines))

    # 4. Commerce Description & Enrichment Content
    gen_data = {}
    if enrichment and enrichment.generated_value:
        try:
            gen_data = json.loads(enrichment.generated_value) if isinstance(enrichment.generated_value, str) else enrichment.generated_value
            if not isinstance(gen_data, dict):
                gen_data = {}
        except Exception:
            gen_data = {}

    comm_desc = gen_data.get("commerce_description") or product.commerce_description
    if comm_desc:
        sections.append(f"Commerce Description:\n{comm_desc.strip()}")

    short_desc = gen_data.get("short_description")
    if short_desc:
        sections.append(f"Short Description:\n{short_desc.strip()}")

    # 5. Features & Bullet Points
    features = gen_data.get("features") or product.features or []
    if features:
        feat_lines = ["Key Features:"]
        for f in features:
            if isinstance(f, str) and f.strip():
                feat_lines.append(f"- {f.strip()}")
        if len(feat_lines) > 1:
            sections.append("\n".join(feat_lines))

    # 6. Target Applications
    apps = gen_data.get("applications") or product.applications or []
    if apps:
        app_lines = ["Applications:"]
        for a in apps:
            if isinstance(a, str) and a.strip():
                app_lines.append(f"- {a.strip()}")
        if len(app_lines) > 1:
            sections.append("\n".join(app_lines))

    # 7. Certifications
    certs = product.certifications or []
    if certs:
        cert_lines = ["Certifications:"]
        for c in certs:
            if isinstance(c, str) and c.strip():
                cert_lines.append(f"- {c.strip()}")
        if len(cert_lines) > 1:
            sections.append("\n".join(cert_lines))

    # 8. Search Keywords
    keywords = gen_data.get("keywords") or product.keywords or []
    if keywords:
        kw_str = ", ".join([k.strip() for k in keywords if isinstance(k, str) and k.strip()])
        if kw_str:
            sections.append(f"Keywords: {kw_str}")

    return "\n\n".join(sections)


def build_qdrant_payload(
    product: Product,
    attributes: List[ProductAttribute],
) -> Dict[str, Any]:
    """
    Builds lightweight metadata payload dictionary to attach to the Qdrant vector point.

    Contains product identity, category, manufacturer, quality score, and normalized specifications
    for vector payload filtering without duplicating huge text fields.
    """
    attr_payload = {}
    for attr in attributes:
        attr_payload[attr.attribute_name] = {
            "display_name": attr.display_name,
            "raw_value": attr.raw_value,
            "normalized_value": attr.normalized_value,
            "unit": attr.unit,
            "confidence": attr.confidence,
        }

    return {
        "product_id": str(product.id),
        "sku": product.sku,
        "product_name": product.product_name,
        "model": product.model,
        "category": product.category,
        "subcategory": product.subcategory,
        "manufacturer": product.brand,
        "brand": product.brand,
        "status": product.status.value if hasattr(product.status, "value") else str(product.status),
        "quality_score": float(product.quality_score),
        "attributes": attr_payload,
    }
