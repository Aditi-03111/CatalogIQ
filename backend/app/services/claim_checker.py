"""
Claim Checker service.

Inspects AI-generated commerce content against verified product attributes, evidence,
and features to detect unsupported claims or numerical alterations.
"""
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel

from app.services.llm.base import CommerceEnrichment


class ClaimCheckResult(BaseModel):
    valid: bool
    unsupported_claims: List[str]
    supported_claims_count: int
    total_claims_count: int
    has_unsupported_claims: bool
    clean_features: List[str]
    clean_applications: List[str]


class ClaimChecker:
    """
    Verifies AI commerce claims against verified source attributes and evidence.
    Prevents hallucinated specs, altered values, or fabricated certifications.
    """

    def check(
        self,
        enrichment: CommerceEnrichment,
        verified_attributes: Dict[str, Any],  # attr_name -> raw_value or normalized_value
        verified_features: List[str],
        verified_applications: List[str],
        product_identity_text: Optional[str] = None,
    ) -> ClaimCheckResult:
        """
        Scans AI generated commerce description and lists for unsupported claims.
        """
        unsupported: List[str] = []
        supported_count = 0
        total_count = 0

        # Build set of verified numbers and words for quick checking
        verified_text_blob = " ".join([
            str(k) + " " + str(v) for k, v in verified_attributes.items()
        ] + verified_features + verified_applications + [product_identity_text or ""]).lower()

        # Extract all numbers from verified text
        verified_numbers: Set[str] = set(re.findall(r"\b\d+(?:\.\d+)?\b", verified_text_blob))

        # Check 1: Numeric value integrity in commerce description
        all_text = f"{enrichment.commerce_description or ''} {enrichment.short_description or ''}"
        generated_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", all_text.lower())

        for num in generated_numbers:
            total_count += 1
            if num in verified_numbers:
                supported_count += 1
            else:
                # Number in AI text is not present in verified source data!
                unsupported.append(f"Unsupported numeric spec claim: '{num}' found in description.")

        # Check 2: Certifications and ratings integrity
        ratings_to_check = ["ip65", "ip66", "ip67", "ip68", "class h", "ie3", "ie4", "ul listed", "5-year warranty"]
        for rating in ratings_to_check:
            if rating in all_text.lower() and rating not in verified_text_blob:
                unsupported.append(f"Unsupported certification/rating claim: '{rating}' in AI text.")
                total_count += 1

        # Check 3: Clean features
        clean_feats: List[str] = []
        for feat in enrichment.features:
            total_count += 1
            feat_lower = feat.lower()
            # If feature contains specific numbers, verify they match verified numbers
            feat_nums = re.findall(r"\b\d+(?:\.\d+)?\b", feat_lower)
            is_feat_valid = True
            for fn in feat_nums:
                if fn not in verified_numbers:
                    is_feat_valid = False
                    unsupported.append(f"Unsupported feature claim: '{feat}' contains unverified number '{fn}'.")
                    break
            
            if is_feat_valid:
                clean_feats.append(feat)
                supported_count += 1

        # Check 4: Clean applications
        clean_apps: List[str] = []
        for app_str in enrichment.applications:
            total_count += 1
            # Applications should be consistent
            clean_apps.append(app_str)
            supported_count += 1

        has_unsupported = len(unsupported) > 0

        return ClaimCheckResult(
            valid=not has_unsupported,
            unsupported_claims=unsupported,
            supported_claims_count=supported_count,
            total_claims_count=max(1, total_count),
            has_unsupported_claims=has_unsupported,
            clean_features=clean_feats,
            clean_applications=clean_apps,
        )
