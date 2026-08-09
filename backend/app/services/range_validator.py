"""
Deterministic numeric and range validator.

Validates numeric attribute values against physical bounds (e.g. voltage > 0, power > 0,
speed >= 0, weight > 0) without enforcing arbitrary upper caps.
"""
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel


class RangeValidationResult(BaseModel):
    is_valid: bool
    issue_type: Optional[str] = None  # invalid_numeric_value | out_of_range
    message: Optional[str] = None


class RangeValidator:
    """
    Validates numeric values and range bounds safely.
    """

    def validate_numeric_value(
        self,
        attribute_name: str,
        value: Any,
        category_rules: Optional[Dict[str, Any]] = None,
    ) -> RangeValidationResult:
        """
        Validates a normalized or raw numeric attribute value.
        Checks for non-numeric types, negative values, or zero bounds where inappropriate.
        """
        if value is None:
            return RangeValidationResult(is_valid=True)

        # Parse numeric value
        num_val: Optional[float] = None
        if isinstance(value, (int, float)):
            num_val = float(value)
        elif isinstance(value, str):
            try:
                # Handle basic numeric strings
                clean_str = value.strip().replace(",", "")
                num_val = float(clean_str)
            except ValueError:
                # String value could not be parsed as a float
                return RangeValidationResult(
                    is_valid=False,
                    issue_type="invalid_numeric_value",
                    message=f"Attribute '{attribute_name}' value '{value}' cannot be parsed as a valid numeric number.",
                )

        if num_val is None:
            return RangeValidationResult(is_valid=True)

        name_lower = attribute_name.lower().replace(" ", "_")

        # Specific physical rules
        if "voltage" in name_lower or "volt" in name_lower:
            if num_val <= 0:
                return RangeValidationResult(
                    is_valid=False,
                    issue_type="out_of_range",
                    message=f"Voltage must be strictly positive (> 0), got {num_val}.",
                )

        elif "power" in name_lower:
            if num_val <= 0:
                return RangeValidationResult(
                    is_valid=False,
                    issue_type="out_of_range",
                    message=f"Power must be strictly positive (> 0), got {num_val}.",
                )

        elif "speed" in name_lower or "rpm" in name_lower:
            if num_val < 0:
                return RangeValidationResult(
                    is_valid=False,
                    issue_type="out_of_range",
                    message=f"Speed must be non-negative (>= 0), got {num_val}.",
                )

        elif "weight" in name_lower or "mass" in name_lower:
            if num_val <= 0:
                return RangeValidationResult(
                    is_valid=False,
                    issue_type="out_of_range",
                    message=f"Weight must be strictly positive (> 0), got {num_val}.",
                )

        elif "freq" in name_lower:
            if num_val <= 0:
                return RangeValidationResult(
                    is_valid=False,
                    issue_type="out_of_range",
                    message=f"Frequency must be strictly positive (> 0), got {num_val}.",
                )

        elif "efficiency" in name_lower:
            if num_val < 0 or num_val > 100:
                return RangeValidationResult(
                    is_valid=False,
                    issue_type="out_of_range",
                    message=f"Efficiency percentage must be between 0% and 100%, got {num_val}.",
                )

        # General rule for any numeric spec: negative values are usually invalid
        elif num_val < 0:
            return RangeValidationResult(
                is_valid=False,
                issue_type="out_of_range",
                message=f"Attribute '{attribute_name}' value {num_val} is negative, which is unexpected.",
            )

        return RangeValidationResult(is_valid=True)
