"""
Completeness calculator.

Calculates required field coverage, optional field coverage, evidence coverage,
and missing field count to produce a transparent 0-100 completeness score.
"""
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel
from app.services.validation_rules import get_category_rules, is_attribute_present


class CompletenessResult(BaseModel):
    required_fields_present: int
    required_fields_total: int
    optional_fields_present: int
    optional_fields_total: int
    evidence_coverage: float  # 0-100 scale
    missing_fields: List[str]
    completeness_score: float  # 0-100 scale


class CompletenessCalculator:
    """
    Calculates product completeness based on category rules and attribute evidence.
    """

    def calculate(
        self,
        category: Optional[str],
        present_attributes: Set[str],
        evidence_supported_attributes: Set[str],
    ) -> CompletenessResult:
        """
        Calculate transparent completeness score (0-100).

        Weighting:
          - Required fields: 70% of completeness score
          - Optional fields: 30% of completeness score
          - (If category has no required fields, present attributes count for 100%)
        """
        rules = get_category_rules(category)
        required_list: List[str] = rules.get("required", [])
        optional_list: List[str] = rules.get("optional", [])

        # Lowercase set of present attribute names for matching
        present_lower = {a.lower().strip().replace(" ", "_") for a in present_attributes}
        evidence_lower = {a.lower().strip().replace(" ", "_") for a in evidence_supported_attributes}

        # 1. Required fields
        req_total = len(required_list)
        req_present = 0
        missing: List[str] = []

        for req_field in required_list:
            if is_attribute_present(req_field, present_attributes):
                req_present += 1
            else:
                missing.append(req_field)

        req_ratio = (req_present / req_total) if req_total > 0 else 1.0

        # 2. Optional fields
        opt_total = len(optional_list)
        opt_present = 0
        for opt_field in optional_list:
            if is_attribute_present(opt_field, present_attributes):
                opt_present += 1

        opt_ratio = (opt_present / opt_total) if opt_total > 0 else (1.0 if opt_present > 0 else 0.5)

        # 3. Completeness score
        if req_total > 0:
            score = (req_ratio * 70.0) + (opt_ratio * 30.0)
        else:
            # Generic category without required fields
            total_present = len(present_lower)
            if total_present >= 5:
                score = 100.0
            elif total_present > 0:
                score = min(100.0, 50.0 + (total_present * 10.0))
            else:
                score = 0.0

        score = round(min(100.0, max(0.0, score)), 1)

        # 4. Evidence coverage (percentage of present attributes backed by verified evidence)
        total_present = len(present_lower)
        if total_present > 0:
            supported_count = sum(1 for a in present_lower if a in evidence_lower)
            evidence_cov = round((supported_count / total_present) * 100.0, 1)
        else:
            evidence_cov = 0.0

        return CompletenessResult(
            required_fields_present=req_present,
            required_fields_total=req_total,
            optional_fields_present=opt_present,
            optional_fields_total=opt_total,
            evidence_coverage=evidence_cov,
            missing_fields=missing,
            completeness_score=score,
        )
