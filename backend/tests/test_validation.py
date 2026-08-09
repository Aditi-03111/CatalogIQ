"""
Tests for Phase 5 Validation Engine, Rule Registry, Unit/Range Validators, Completeness, and Quality Scoring.
"""
import uuid
import pytest
from app.models import (
    AttributeStatus,
    Product,
    ProductAttribute,
    ProductStatus,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
    ValidationType,
)
from app.services.completeness import CompletenessCalculator
from app.services.confidence import ProductQualityCalculator
from app.services.range_validator import RangeValidator
from app.services.unit_validator import UnitValidator
from app.services.validation_engine import ValidationEngine
from app.services.validation_rules import get_category_rules


def test_category_rule_resolution():
    """Verify specific category rules vs generic fallback."""
    motor_rules = get_category_rules("industrial_motor")
    assert "voltage" in motor_rules["required"]
    assert "power" in motor_rules["required"]
    assert "speed" in motor_rules["required"]

    unknown_rules = get_category_rules("unknown_category_xyz")
    assert unknown_rules["required"] == []


def test_valid_and_invalid_units():
    """Test deterministic unit validation and incompatible unit detection."""
    validator = UnitValidator()

    # Valid unit normalization
    res_voltage = validator.validate_unit("voltage", "volts")
    assert res_voltage.is_valid
    assert res_voltage.normalized_unit == "V"

    res_speed = validator.validate_unit("speed", "rpm")
    assert res_speed.is_valid
    assert res_speed.normalized_unit == "RPM"

    # Incompatible unit detection
    res_incompatible = validator.validate_unit("power", "230 V")
    assert not res_incompatible.is_valid
    assert res_incompatible.issue_type == "invalid_unit"


def test_negative_numeric_range_validation():
    """Test numeric range bounds (e.g. voltage > 0, power > 0)."""
    validator = RangeValidator()

    # Valid numeric
    assert validator.validate_numeric_value("power", 5.5).is_valid
    assert validator.validate_numeric_value("voltage", 230).is_valid

    # Negative values must fail
    res_neg_volts = validator.validate_numeric_value("voltage", -5.0)
    assert not res_neg_volts.is_valid
    assert res_neg_volts.issue_type == "out_of_range"

    res_neg_power = validator.validate_numeric_value("power", -10.0)
    assert not res_neg_power.is_valid
    assert res_neg_power.issue_type == "out_of_range"


def test_completeness_calculator():
    """Test required/optional field coverage scoring."""
    calc = CompletenessCalculator()

    # Full industrial motor
    present = {"voltage", "power", "speed", "weight", "efficiency", "frequency"}
    evidence = {"voltage", "power", "speed", "weight", "efficiency", "frequency"}
    res = calc.calculate("industrial_motor", present, evidence)

    assert res.required_fields_present == 3
    assert res.required_fields_total == 3
    assert res.completeness_score >= 80.0
    assert res.evidence_coverage == 100.0


def test_missing_required_attribute_validation():
    """Test missing mandatory attribute triggers error issue in engine."""
    engine = ValidationEngine()

    product = Product(
        sku="MX500-230",
        brand="CatalogIQ",
        product_name="MX-500 Motor",
        category="industrial_motor",
        status=ProductStatus.draft,
    )

    # Only provide power and speed — voltage is missing
    attrs = [
        ProductAttribute(
            product_id=product.id,
            attribute_name="power",
            display_name="Power",
            raw_value="5.5 kW",
            unit="kW",
            data_type="numeric",
            confidence=0.95,
            status=AttributeStatus.extracted,
            source_type="deterministic",
        ),
        ProductAttribute(
            product_id=product.id,
            attribute_name="speed",
            display_name="Speed",
            raw_value="1440 RPM",
            unit="RPM",
            data_type="numeric",
            confidence=0.92,
            status=AttributeStatus.extracted,
            source_type="deterministic",
        ),
    ]

    val_res = engine.validate_product(product, attrs)
    assert val_res.has_errors
    missing_issues = [
        i for i in val_res.issues
        if i.validation_type == ValidationType.missing_required_attribute
    ]
    assert len(missing_issues) == 1
    assert missing_issues[0].attribute_name == "voltage"


def test_product_quality_calculator():
    """Test transparent formula calculation for quality score."""
    calc = ProductQualityCalculator()

    breakdown = calc.calculate(
        completeness_score=100.0,
        avg_attribute_confidence=0.90,  # 90%
        evidence_coverage_score=100.0,
        validation_issues=[],
        source_trust_level=1.0,
    )

    # 100*0.25 + 90*0.25 + 100*0.20 + 100*0.15 + 100*0.15 = 25 + 22.5 + 20 + 15 + 15 = 97.5
    assert breakdown.quality_score >= 95.0
    assert breakdown.validation_health == 100.0


def test_low_confidence_creates_review():
    """Test low confidence attribute flags warning issue."""
    engine = ValidationEngine()

    product = Product(
        sku="MX500-230",
        brand="CatalogIQ",
        product_name="MX-500 Motor",
        category="industrial_motor",
    )

    attrs = [
        ProductAttribute(
            product_id=product.id,
            attribute_name="voltage",
            display_name="Voltage",
            raw_value="230 V",
            confidence=0.45,  # Low confidence
            status=AttributeStatus.needs_review,
            source_type="llm_inference",
        ),
    ]

    val_res = engine.validate_product(product, attrs)
    low_conf_issues = [
        i for i in val_res.issues
        if i.validation_type == ValidationType.low_confidence
    ]
    assert len(low_conf_issues) == 1


def test_text_attributes_not_sent_to_numeric_range_validation():
    """Verify text attributes with non-null normalized_value do NOT trigger range validation errors."""
    engine = ValidationEngine()
    product = Product(
        sku="TEST-SKU",
        brand="CatalogIQ Motors",
        product_name="Test Motor",
        category="generic",
    )
    attrs = [
        ProductAttribute(
            product_id=product.id,
            attribute_name="brand",
            display_name="Brand",
            raw_value="CatalogIQ Motors",
            normalized_value="CatalogIQ Motors",
            data_type="text",
            confidence=0.90,
            status=AttributeStatus.verified,
            source_type="deterministic",
        ),
        ProductAttribute(
            product_id=product.id,
            attribute_name="cooling_method",
            display_name="Cooling Method",
            raw_value="TEFC - Totally Enclosed Fan Cooled",
            normalized_value="TEFC - Totally Enclosed Fan Cooled",
            data_type="text",
            confidence=0.90,
            status=AttributeStatus.verified,
            source_type="deterministic",
        ),
    ]

    val_res = engine.validate_product(product, attrs)
    invalid_num_issues = [
        i for i in val_res.issues
        if i.validation_type == ValidationType.invalid_numeric_value
    ]
    assert len(invalid_num_issues) == 0
    assert val_res.quality_breakdown.validation_health == 100.0


def test_rated_attributes_satisfy_required_fields():
    """Verify rated_voltage, rated_power, and rated_speed satisfy required voltage, power, and speed."""
    engine = ValidationEngine()
    product = Product(
        sku="TEST-MOTOR",
        brand="CatalogIQ",
        product_name="Industrial Motor",
        category="industrial_motor",
    )
    attrs = [
        ProductAttribute(
            product_id=product.id,
            attribute_name="rated_voltage",
            display_name="Rated Voltage",
            raw_value="230 V",
            normalized_value=230,
            unit="V",
            data_type="numeric",
            confidence=0.90,
            status=AttributeStatus.verified,
            source_type="deterministic",
        ),
        ProductAttribute(
            product_id=product.id,
            attribute_name="rated_power",
            display_name="Rated Power",
            raw_value="5.5 kW",
            normalized_value=5.5,
            unit="kW",
            data_type="numeric",
            confidence=0.90,
            status=AttributeStatus.verified,
            source_type="deterministic",
        ),
        ProductAttribute(
            product_id=product.id,
            attribute_name="rated_speed",
            display_name="Rated Speed",
            raw_value="1440 RPM",
            normalized_value=1440,
            unit="RPM",
            data_type="numeric",
            confidence=0.90,
            status=AttributeStatus.verified,
            source_type="deterministic",
        ),
    ]

    val_res = engine.validate_product(product, attrs)
    missing_issues = [
        i for i in val_res.issues
        if i.validation_type == ValidationType.missing_required_attribute
    ]
    assert len(missing_issues) == 0
    assert val_res.completeness.required_fields_present == 3
    assert val_res.completeness.required_fields_total == 3


def test_mojibake_repair_functions():
    """Verify repair_mojibake corrects double-decoded UTF-8 sequences and leaves normal/malformed strings safe."""
    from app.services.normalizer import repair_mojibake, AttributeNormalizer

    # 1. Mojibake correction
    mojibake_str = "-10\u00c2\u00b0C to 40\u00c2\u00b0C"
    assert repair_mojibake(mojibake_str) == "-10°C to 40°C"

    # 2. Normal Unicode text remains unchanged
    normal_str = "10°C"
    assert repair_mojibake(normal_str) == "10°C"

    # 3. International names remain unchanged
    assert repair_mojibake("Müller") == "Müller"
    assert repair_mojibake("São Paulo") == "São Paulo"

    # 4. Normal plain text remains unchanged
    plain_str = "230 V"
    assert repair_mojibake(plain_str) == "230 V"

    # 5. AttributeNormalizer integration
    normalizer = AttributeNormalizer()
    res = normalizer.normalize(mojibake_str, "text")
    assert res.normalized_value == "-10°C to 40°C"


