import logging
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import settings
from app.models.unilog import UnilogRecord, UnilogEnriched, UnilogStatus
from app.services.unilog.normalizers import clean_brand_manufacturer, format_value_with_uom, clean_uom
from app.services.unilog.prompts import (
    UNILOG_SYSTEM_PROMPT,
    UNILOG_FEW_SHOT_EXAMPLES,
    build_unilog_prompt
)

logger = logging.getLogger(__name__)

class UnilogAttributeItem(BaseModel):
    label: str = ""
    value: str = ""
    uom: str = ""

class UnilogEnrichedSchema(BaseModel):
    mfr_url: str = ""
    dept: str = ""
    clss: str = ""
    fine: str = ""
    sku: str = ""
    manufacturer_name: str = ""
    brand_name: str = ""
    trade_name: str = ""
    manufacturer_part_number: str = ""
    alternate_part_number: str = ""
    classpath: str = ""
    mobile_desc: str = ""
    invoice_desc: str = ""
    short_desc: str = ""
    long_desc: str = ""
    retail_desc: str = ""
    marketing_description: str = ""
    features: List[str] = []
    with_attr: str = ""
    standards: str = ""
    prop_65: str = ""
    application: str = ""
    includes: str = ""
    product_name: str = ""
    attributes: List[UnilogAttributeItem] = []
    upc: str = ""
    ean: str = ""
    gtin: str = ""
    unspsc: str = ""
    warranty: str = ""
    list_price: str = ""
    selling_qty: str = "1"
    selling_uom: str = "EA"
    packaging_info: str = ""
    length: str = ""
    length_uom: str = ""
    height: str = ""
    height_uom: str = ""
    width: str = ""
    width_uom: str = ""
    weight: str = ""
    weight_uom: str = ""
    volume: str = ""
    volume_uom: str = ""
    product_image: str = ""
    alternate_images: List[str] = []
    sds: str = ""
    sds_1: str = ""
    warranty_info: str = ""
    catalog: str = ""
    spec_sheet: str = ""
    manuals: List[str] = []
    country_of_origin: str = ""
    discontinued: str = "No"
    actual_image: str = "Yes"

class UnilogPipelineService:
    def __init__(self, session: Session):
        self.session = session
        
        # Initialize Google GenAI Client
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in configuration environment.")
            
        from google import genai
        from google.genai import types
        self._genai = genai
        self._types = types
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL

    def process_record(self, record_id: uuid.UUID) -> UnilogEnriched:
        """
        Ingests a single raw record, normalizes headers, sends to Gemini for structured AI mapping,
        and saves result to DB.
        """
        record = self.session.get(UnilogRecord, record_id)
        if not record:
            raise ValueError(f"UnilogRecord with ID {record_id} not found")

        # Idempotency / Cache check
        stmt = select(UnilogEnriched).where(UnilogEnriched.record_id == record.id)
        enriched = self.session.exec(stmt).first()
        
        if not enriched:
            enriched = UnilogEnriched(
                id=uuid.uuid4(),
                record_id=record.id,
                status=UnilogStatus.queued
            )
            self.session.add(enriched)
            self.session.commit()
            self.session.refresh(enriched)

        if enriched.status == UnilogStatus.enriched:
            logger.info(f"Record {record.mfg_part_num} already processed. Skipping.")
            return enriched

        enriched.status = UnilogStatus.processing
        enriched.updated_at = datetime.now(timezone.utc)
        self.session.add(enriched)
        self.session.commit()

        # Phase 1: Local normalization
        norm_manuf, norm_brand, mfr_code, mfr_conf = clean_brand_manufacturer(record.part_manuf)
        if not norm_brand or norm_brand == "Unbranded":
            norm_brand = record.unilog_brand if record.unilog_brand != "-- No Unilog Brand --" else norm_manuf

        # Phase 2: Call structured Gemini Model with few-shot training context
        try:
            user_prompt = build_unilog_prompt(
                mfg_part_num=record.mfg_part_num,
                part_desc=record.part_desc,
                brand_name=norm_brand,
                manufacturer_name=norm_manuf
            )
            
            full_system_context = f"{UNILOG_SYSTEM_PROMPT}\n{UNILOG_FEW_SHOT_EXAMPLES}"
            
            logger.info(f"Generating enriched specs for MPN: {record.mfg_part_num} using model: {self._model}")
            
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=self._types.GenerateContentConfig(
                    system_instruction=full_system_context,
                    response_mime_type="application/json",
                    response_schema=UnilogEnrichedSchema,
                    temperature=0.1,
                    max_output_tokens=4096,
                )
            )
            
            raw_text = response.text
            parsed_data = json.loads(raw_text)
            
            # Post-processing: Enforce normalized UOM spacing & fraction rules on attributes
            formatted_attrs = []
            for attr in parsed_data.get("attributes", []):
                val = attr.get("value", "")
                uom = attr.get("uom", "")
                if val:
                    val_clean, uom_clean = clean_uom(val, uom)
                    attr["value"] = val_clean
                    attr["uom"] = uom_clean
                formatted_attrs.append(attr)
                
            parsed_data["attributes"] = formatted_attrs
            
            # Fuzzy classify predicted category against approved LOV list
            from app.services.unilog.lookups.lov_classpaths import fuzzy_classify_classpath
            predicted_classpath = parsed_data.get("classpath", "")
            valid_classpath, cp_conf = fuzzy_classify_classpath(predicted_classpath)
            parsed_data["classpath"] = valid_classpath

            # Calculate completeness quality score
            total_keys = len(parsed_data)
            non_empty_keys = sum(1 for v in parsed_data.values() if v not in ("", None, [], {}))
            quality_score = float((non_empty_keys / total_keys) * 100.0)

            # Post-process Invoice Desc (<=40 chars, UPPERCASE)
            invoice_desc = parsed_data.get("invoice_desc", "").upper().strip()
            if len(invoice_desc) > 40:
                invoice_desc = invoice_desc[:40].strip()
            parsed_data["invoice_desc"] = invoice_desc

            # Post-process Mobile Desc (60-80 chars target)
            mobile_desc = parsed_data.get("mobile_desc", "").strip()

            # Audit validation rules
            validation_flags = []
            needs_review = False
            
            if len(invoice_desc) > 40:
                validation_flags.append(f"Invoice description length ({len(invoice_desc)} chars) exceeds 40 characters limit.")
                needs_review = True
            if mobile_desc and (len(mobile_desc) < 45 or len(mobile_desc) > 90):
                validation_flags.append(f"Mobile description length ({len(mobile_desc)} chars) is outside optimal 60-80 chars guideline.")
                needs_review = True
            if not parsed_data.get("brand_name"):
                validation_flags.append("Canonical brand name is empty.")
                needs_review = True
            if cp_conf < 0.4:
                validation_flags.append(f"Category classpath matches standard LOVs with low confidence ({cp_conf}).")
                needs_review = True
            if quality_score < 75.0:
                validation_flags.append(f"Completeness quality score ({round(quality_score, 1)}%) is below human review threshold.")
                needs_review = True

            # Build explainability trace for demo transparency
            explainability_trace = {
                "manufacturer_name": f"Matched '{record.part_manuf}' to approved list with similarity ratio {mfr_conf}. Code: {mfr_code}.",
                "brand_name": f"Resolved brand '{parsed_data.get('brand_name')}' from manufacturer mapping metadata.",
                "classpath": f"Classified category path to '{valid_classpath}' with classpath overlap score {cp_conf}.",
                "invoice_desc": f"Generated uppercase value '{invoice_desc}' conforming to the 40 character content threshold.",
                "mobile_desc": f"Generated description '{mobile_desc}' ({len(mobile_desc)} chars, target 60-80).",
                "attributes": f"Extracted {len(formatted_attrs)} attributes, normalizing UOM casing/spacing (e.g. 'in', 'V', 'A').",
                "quality": f"Assigned completeness ratio of {round(quality_score, 1)}% based on {non_empty_keys}/{total_keys} fields resolved."
            }

            # Update DB record
            enriched.enriched_data = parsed_data
            enriched.quality_score = round(quality_score, 2)
            enriched.needs_review = needs_review
            enriched.validation_flags = validation_flags
            enriched.explainability_trace = explainability_trace
            enriched.status = UnilogStatus.enriched
            enriched.error_message = None
            enriched.updated_at = datetime.now(timezone.utc)

            # Automatic CatalogIQ database synchronization
            try:
                from app.models import Product, ProductStatus, ProductAttribute, AttributeEvidence, AttributeDataType, AttributeStatus
                
                # Check for existing product by brand and sku
                stmt = select(Product).where(Product.brand == norm_brand, Product.sku == record.mfg_part_num)
                product = self.session.exec(stmt).first()
                
                if not product:
                    product = Product(
                        id=uuid.uuid4(),
                        sku=record.mfg_part_num,
                        brand=norm_brand,
                        product_name=parsed_data.get("invoice_desc", record.mfg_part_num).title(),
                        model=record.mfg_part_num,
                        category=valid_classpath.split(">")[0] if ">" in valid_classpath else valid_classpath,
                        subcategory=valid_classpath.split(">")[-1] if ">" in valid_classpath else None,
                        description=record.part_desc,
                        commerce_description=parsed_data.get("mobile_desc", ""),
                        status=ProductStatus.needs_review if needs_review else ProductStatus.verified,
                        quality_score=round(quality_score, 2),
                        attributes={attr["label"]: attr["value"] for attr in parsed_data.get("attributes", [])},
                        features=[],
                        applications=[],
                        certifications=[],
                        keywords=[]
                    )
                    self.session.add(product)
                    self.session.flush() # populate ID
                else:
                    product.product_name = parsed_data.get("invoice_desc", record.mfg_part_num).title()
                    product.category = valid_classpath.split(">")[0] if ">" in valid_classpath else valid_classpath
                    product.subcategory = valid_classpath.split(">")[-1] if ">" in valid_classpath else None
                    product.description = record.part_desc
                    product.commerce_description = parsed_data.get("mobile_desc", "")
                    product.status = ProductStatus.needs_review if needs_review else ProductStatus.verified
                    product.quality_score = round(quality_score, 2)
                    product.attributes = {attr["label"]: attr["value"] for attr in parsed_data.get("attributes", [])}
                    product.updated_at = datetime.now(timezone.utc)
                    self.session.add(product)
                    self.session.flush()

                # Sync attributes
                for attr in parsed_data.get("attributes", []):
                    attr_name = attr["label"]
                    display_name = attr_name.replace("_", " ").title()
                    val_str = str(attr["value"])
                    unit_str = attr.get("uom", None)
                    
                    attr_stmt = select(ProductAttribute).where(
                        ProductAttribute.product_id == product.id,
                        ProductAttribute.attribute_name == attr_name
                    )
                    prod_attr = self.session.exec(attr_stmt).first()
                    
                    data_type = AttributeDataType.numeric if any(char.isdigit() for char in val_str) else AttributeDataType.text
                    attr_status = AttributeStatus.needs_review if needs_review else AttributeStatus.verified
                    
                    if not prod_attr:
                        prod_attr = ProductAttribute(
                            id=uuid.uuid4(),
                            product_id=product.id,
                            attribute_name=attr_name,
                            display_name=display_name,
                            raw_value=val_str,
                            normalized_value=attr["value"],
                            unit=unit_str,
                            data_type=data_type,
                            confidence=0.9,
                            status=attr_status,
                            source_type="enrichment"
                        )
                        self.session.add(prod_attr)
                        self.session.flush()
                        
                        evidence = AttributeEvidence(
                            id=uuid.uuid4(),
                            attribute_id=prod_attr.id,
                            evidence_text=f"Extracted from supplier description: '{record.part_desc}'",
                            extraction_method="enrichment"
                        )
                        self.session.add(evidence)
                    else:
                        prod_attr.raw_value = val_str
                        prod_attr.normalized_value = attr["value"]
                        prod_attr.unit = unit_str
                        prod_attr.data_type = data_type
                        prod_attr.status = attr_status
                        prod_attr.updated_at = datetime.now(timezone.utc)
                        self.session.add(prod_attr)
                        
            except Exception as sync_err:
                logger.error(f"CatalogIQ sync failed for MPN {record.mfg_part_num}: {sync_err}")
            
        except Exception as e:
            logger.error(f"Enrichment pipeline failed for MPN {record.mfg_part_num}: {e}")
            enriched.status = UnilogStatus.failed
            enriched.error_message = str(e)[:500]
            enriched.updated_at = datetime.now(timezone.utc)
            
        self.session.add(enriched)
        self.session.commit()
        self.session.refresh(enriched)
        return enriched
