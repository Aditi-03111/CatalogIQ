"""
Validation Engine for CatalogIQ.

Orchestrates category validation, type validation, unit validation,
numeric range validation, completeness calculation, conflict integration,
and product quality scoring.
"""
import uuid
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.models import (
    AttributeStatus,
    Product,
    ProductAttribute,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
    ValidationType,
)
from app.services.completeness import CompletenessCalculator, CompletenessResult
from app.services.confidence import ProductQualityCalculator, ProductQualityBreakdown
from app.services.range_validator import RangeValidator
from app.services.unit_validator import UnitValidator
from app.services.validation_rules import get_category_rules, is_attribute_present


class ValidationIssue(BaseModel):
    validation_type: ValidationType
    severity: ValidationSeverity
    attribute_name: Optional[str] = None
    message: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    source_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    attribute_id: Optional[uuid.UUID] = None

    def to_db_model(self, product_id: uuid.UUID) -> ValidationResult:
        """Converts ValidationIssue to persistent ValidationResult SQLModel entity."""
        return ValidationResult(
            product_id=product_id,
            attribute_id=self.attribute_id,
            validation_type=self.validation_type,
            severity=self.severity,
            status=ValidationStatus.open,
            message=self.message,
            expected_value=self.expected_value,
            actual_value=self.actual_value,
        )


class ValidationEngineResult(BaseModel):
    issues: List[ValidationIssue]
    completeness: CompletenessResult
    quality_breakdown: ProductQualityBreakdown
    has_critical_issues: bool
    has_errors: bool


class ValidationEngine:
    """
    Core rule validation engine.
    Applies category rules, unit checks, range bounds, and quality scoring.
    """

    def __init__(self) -> None:
        self.unit_validator = UnitValidator()
        self.range_validator = RangeValidator()
        self.completeness_calculator = CompletenessCalculator()
        self.quality_calculator = ProductQualityCalculator()

    def validate_product(
        self,
        product: Product,
        attributes: List[ProductAttribute],
        evidence_supported_attribute_names: Optional[Set[str]] = None,
        source_trust_level: float = 0.9,
    ) -> ValidationEngineResult:
        """
        Runs comprehensive deterministic & category validation on a Product and its attributes.
        """
        issues: List[ValidationIssue] = []
        present_names: Set[str] = set()
        evidence_names: Set[str] = evidence_supported_attribute_names or set()

        attr_by_name: Dict[str, List[ProductAttribute]] = {}
        total_confidence = 0.0

        for attr in attributes:
            present_names.add(attr.attribute_name)
            name_key = attr.attribute_name.lower().strip()
            attr_by_name.setdefault(name_key, []).append(attr)
            total_confidence += attr.confidence

        avg_confidence = (total_confidence / len(attributes)) if attributes else 0.8

        # 1. Category validation (Missing required attributes)
        cat_rules = get_category_rules(product.category)
        required_fields: List[str] = cat_rules.get("required", [])

        for req in required_fields:
            if not is_attribute_present(req, present_names):
                issues.append(
                    ValidationIssue(
                        validation_type=ValidationType.missing_required_attribute,
                        severity=ValidationSeverity.error,
                        attribute_name=req,
                        message=f"Required attribute '{req}' is missing for category '{product.category}'.",
                        expected_value=f"Present attribute '{req}'",
                        actual_value="Missing",
                    )
                )

        # 2. Per-attribute validation (Unit, Range, Low Confidence, Conflicts)
        for attr in attributes:
            # a. Unit validation
            unit_res = self.unit_validator.validate_unit(
                attribute_name=attr.attribute_name,
                unit=attr.unit,
                raw_value=attr.raw_value,
            )
            if not unit_res.is_valid:
                issues.append(
                    ValidationIssue(
                        validation_type=ValidationType.invalid_unit,
                        severity=ValidationSeverity.error,
                        attribute_name=attr.attribute_name,
                        attribute_id=attr.id,
                        message=unit_res.message or f"Invalid unit '{attr.unit}' for '{attr.attribute_name}'.",
                        expected_value="Compatible unit",
                        actual_value=attr.unit or attr.raw_value,
                    )
                )

            # b. Range / Numeric validation
            is_numeric = (
                attr.data_type == "numeric"
                or getattr(attr.data_type, "value", None) == "numeric"
            )
            if is_numeric:
                val_to_check = attr.normalized_value if attr.normalized_value is not None else attr.raw_value
                range_res = self.range_validator.validate_numeric_value(
                    attribute_name=attr.attribute_name,
                    value=val_to_check,
                    category_rules=cat_rules,
                )
                if not range_res.is_valid:
                    issues.append(
                        ValidationIssue(
                            validation_type=ValidationType(range_res.issue_type or "out_of_range"),
                            severity=ValidationSeverity.error,
                            attribute_name=attr.attribute_name,
                            attribute_id=attr.id,
                            message=range_res.message or f"Numeric value out of range for '{attr.attribute_name}'.",
                            expected_value="Valid positive numeric value",
                            actual_value=str(val_to_check),
                        )
                    )

            # c. Low confidence check
            if attr.confidence < 0.60:
                issues.append(
                    ValidationIssue(
                        validation_type=ValidationType.low_confidence,
                        severity=ValidationSeverity.warning,
                        attribute_name=attr.attribute_name,
                        attribute_id=attr.id,
                        message=f"Attribute '{attr.attribute_name}' has low extraction confidence ({round(attr.confidence * 100)}%).",
                        expected_value="Confidence >= 60%",
                        actual_value=f"{round(attr.confidence * 100)}%",
                    )
                )

            # d. Conflicting status check
            if attr.status == AttributeStatus.conflicting:
                issues.append(
                    ValidationIssue(
                        validation_type=ValidationType.cross_attribute_conflict,
                        severity=ValidationSeverity.warning,
                        attribute_name=attr.attribute_name,
                        attribute_id=attr.id,
                        message=f"Attribute '{attr.attribute_name}' has conflicting source values that require human resolution.",
                        expected_value="Single verified value",
                        actual_value=attr.raw_value,
                    )
                )

        # 3. Completeness score
        completeness_res = self.completeness_calculator.calculate(
            category=product.category,
            present_attributes=present_names,
            evidence_supported_attributes=evidence_names,
        )

        # 4. Product Quality Score calculation
        quality_breakdown = self.quality_calculator.calculate(
            completeness_score=completeness_res.completeness_score,
            avg_attribute_confidence=avg_confidence,
            evidence_coverage_score=completeness_res.evidence_coverage,
            validation_issues=issues,
            source_trust_level=source_trust_level,
        )

        has_crit = any(i.severity == ValidationSeverity.critical for i in issues)
        has_err = any(i.severity == ValidationSeverity.error for i in issues)

        return ValidationEngineResult(
            issues=issues,
            completeness=completeness_res,
            quality_breakdown=quality_breakdown,
            has_critical_issues=has_crit,
            has_errors=has_err,
        )
