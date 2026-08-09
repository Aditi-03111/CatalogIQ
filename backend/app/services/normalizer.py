"""
AttributeNormalizer — transforms raw extracted values into structured normalized forms.

Normalization pipeline:
  raw_value (str)
       ↓
  parse numeric / boolean / list
       ↓
  unit standardization
       ↓
  normalized_value (JSONB-ready)

Design:
  - Normalization is best-effort. If parsing fails, raw_value is preserved as-is.
  - Normalization success is reported back to ConfidenceCalculator so it can
    add a bonus to the confidence score.
  - No exceptions are raised; failure is communicated via the returned dict.
"""
import logging
import re
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unit standardization lookup table
# ---------------------------------------------------------------------------
# Maps common variant spellings → canonical unit string.
_UNIT_ALIASES: Dict[str, str] = {
    # Voltage
    "volt": "V", "volts": "V", "vac": "V",
    # Power
    "kilowatt": "kW", "kilowatts": "kW", "kw": "kW",
    "watt": "W", "watts": "W", "hp": "HP", "horsepower": "HP",
    # Speed
    "rpm": "RPM", "r/min": "RPM", "rev/min": "RPM",
    # Current
    "ampere": "A", "amperes": "A", "amp": "A", "amps": "A",
    "milliampere": "mA", "milliamperes": "mA", "ma": "mA",
    # Frequency
    "hertz": "Hz", "hz": "Hz",
    # Temperature
    "celsius": "°C", "°c": "°C", "c": "°C",
    "fahrenheit": "°F", "°f": "°F",
    # Pressure
    "bar": "bar", "psi": "PSI", "pa": "Pa", "pascal": "Pa",
    # Mass / Weight
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "gram": "g", "grams": "g",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    # Length / Dimension
    "mm": "mm", "millimeter": "mm", "millimeters": "mm",
    "cm": "cm", "centimeter": "cm", "centimeters": "cm",
    "m": "m", "meter": "m", "meters": "m",
    "in": "in", "inch": "in", "inches": "in",
    # Volume
    "liter": "L", "liters": "L", "l": "L",
    # IP rating (no unit)
    "ip": None,
    # Percentage
    "%": "%", "percent": "%",
    # Dimensionless
    "": None,
}

# Regex to split "230 V", "5.5kW", "1440RPM" into (number, unit)
_NUMERIC_UNIT_RE = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z°%/]+)?\s*$"
)

# Boolean true/false textual variants
_BOOL_TRUE = {"yes", "true", "1", "on", "enabled", "available", "included", "yes/included"}
_BOOL_FALSE = {"no", "false", "0", "off", "disabled", "unavailable", "excluded", "n/a"}


def _standardize_unit(raw_unit: Optional[str]) -> Optional[str]:
    """Normalizes a unit string to its canonical form. Returns None if unknown/empty."""
    if not raw_unit:
        return None
    key = raw_unit.strip().lower()
    if key in _UNIT_ALIASES:
        return _UNIT_ALIASES[key]
    # Return as-is if not in lookup (preserve unknown units)
    return raw_unit.strip()


class NormalizationResult:
    """Container for the output of a single normalization operation."""
    __slots__ = ("normalized_value", "unit", "data_type", "success", "error")

    def __init__(
        self,
        normalized_value: Any,
        unit: Optional[str],
        data_type: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        self.normalized_value = normalized_value
        self.unit = unit
        self.data_type = data_type
        self.success = success
        self.error = error


def repair_mojibake(text: str) -> str:
    """
    Safely repairs common UTF-8 mojibake such as:
        "Â°" -> "°"
        "Ã©" -> "é"
    Returns the original text if no mojibake markers are detected
    or if repair fails.
    """
    if not text or not isinstance(text, str):
        return text

    mojibake_markers = ("Â", "Ã")

    if not any(marker in text for marker in mojibake_markers):
        return text

    try:
        repaired = text.encode("latin-1").decode("utf-8")
        return repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


class AttributeNormalizer:
    """
    Normalizes raw string attribute values into structured, typed representations.

    Methods:
        normalize(raw_value, data_type, unit) → NormalizationResult

    The returned NormalizationResult.normalized_value is JSONB-serializable.
    """

    def normalize(
        self,
        raw_value: str,
        data_type: str,
        unit: Optional[str] = None,
    ) -> NormalizationResult:
        """
        Normalize a raw attribute value.

        Args:
            raw_value:  The raw string value (e.g., "230 V", "yes", "IP55").
            data_type:  One of: text | numeric | boolean | category | structured.
            unit:       Optional unit hint from the LLM (may be overridden by parse).

        Returns:
            NormalizationResult with structured normalized_value.
        """
        raw = repair_mojibake((raw_value or "").strip())

        if data_type == "boolean":
            return self._normalize_boolean(raw)
        elif data_type == "numeric":
            return self._normalize_numeric(raw, unit)
        elif data_type == "structured":
            return self._normalize_structured(raw, unit)
        else:
            # text / category — light cleanup only
            return NormalizationResult(
                normalized_value=raw,
                unit=_standardize_unit(unit),
                data_type=data_type,
                success=True,
            )

    def _normalize_numeric(self, raw: str, hint_unit: Optional[str]) -> NormalizationResult:
        """
        Parse a numeric value and extract/standardize its unit.

        Examples:
            "230 V"   → {value: 230.0, unit: "V"}
            "5.5kW"   → {value: 5.5, unit: "kW"}
            "1440RPM" → {value: 1440.0, unit: "RPM"}
            "32 kg"   → {value: 32.0, unit: "kg"}
        """
        match = _NUMERIC_UNIT_RE.match(raw)
        if match:
            num_str, raw_unit = match.group(1), match.group(2)
            # Normalize decimal separator (European "," → ".")
            num_str = num_str.replace(",", ".")
            try:
                num_value = float(num_str)
                # Integer display if whole number
                if num_value == int(num_value):
                    num_value = int(num_value)

                resolved_unit = _standardize_unit(raw_unit or hint_unit)
                return NormalizationResult(
                    normalized_value=num_value,
                    unit=resolved_unit,
                    data_type="numeric",
                    success=True,
                )
            except ValueError:
                pass

        # Fallback: store as text if numeric parse fails
        return NormalizationResult(
            normalized_value=raw,
            unit=_standardize_unit(hint_unit),
            data_type="text",
            success=False,
            error=f"Could not parse '{raw}' as numeric",
        )

    def _normalize_boolean(self, raw: str) -> NormalizationResult:
        """Normalize yes/no, true/false, 1/0 variants to Python bool."""
        lower = raw.lower().strip()
        if lower in _BOOL_TRUE:
            return NormalizationResult(
                normalized_value=True, unit=None, data_type="boolean", success=True
            )
        if lower in _BOOL_FALSE:
            return NormalizationResult(
                normalized_value=False, unit=None, data_type="boolean", success=True
            )
        # Ambiguous — return text with flag
        return NormalizationResult(
            normalized_value=raw,
            unit=None,
            data_type="text",
            success=False,
            error=f"Could not parse '{raw}' as boolean",
        )

    def _normalize_structured(self, raw: str, hint_unit: Optional[str]) -> NormalizationResult:
        """
        Attempt to parse comma-separated or semicolon-separated lists.
        Falls back to string if not clearly a list.
        """
        for sep in [";", ","]:
            if sep in raw:
                parts = [p.strip() for p in raw.split(sep) if p.strip()]
                if len(parts) > 1:
                    return NormalizationResult(
                        normalized_value=parts,
                        unit=_standardize_unit(hint_unit),
                        data_type="structured",
                        success=True,
                    )
        return NormalizationResult(
            normalized_value=raw,
            unit=_standardize_unit(hint_unit),
            data_type="structured",
            success=True,
        )
