"""
Deterministic unit validator and normalizer.

Validates attribute units against physical concepts, normalizes representations
(e.g., 'kilowatts' -> 'kW', 'rpm' -> 'RPM'), and detects incompatible units
(e.g., Power = '230 V').
"""
import re
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel


class UnitValidationResult(BaseModel):
    is_valid: bool
    normalized_unit: Optional[str] = None
    issue_type: Optional[str] = None  # e.g., "invalid_unit", "missing_unit"
    message: Optional[str] = None


# Canonical unit maps (synonym -> canonical)
UNIT_SYNONYMS: Dict[str, str] = {
    # Power
    "w": "W",
    "watt": "W",
    "watts": "W",
    "kw": "kW",
    "kilowatt": "kW",
    "kilowatts": "kW",
    "mw": "MW",
    "megawatt": "MW",
    "megawatts": "MW",
    "hp": "HP",
    "horsepower": "HP",

    # Voltage
    "v": "V",
    "volt": "V",
    "volts": "V",
    "kv": "kV",
    "kilovolt": "kV",
    "kilovolts": "kV",
    "mv": "mV",
    "millivolt": "mV",

    # Speed
    "rpm": "RPM",
    "r.p.m.": "RPM",
    "revolutions/min": "RPM",
    "rev/min": "RPM",
    "1/min": "RPM",

    # Weight
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "t": "t",
    "ton": "t",
    "tonne": "t",
    "tonnes": "t",
    "lb": "lbs",
    "lbs": "lbs",
    "pound": "lbs",
    "pounds": "lbs",

    # Frequency
    "hz": "Hz",
    "hertz": "Hz",
    "khz": "kHz",
    "kilohertz": "kHz",
    "mhz": "MHz",

    # Current
    "a": "A",
    "amp": "A",
    "amps": "A",
    "ampere": "A",
    "amperes": "A",
    "ma": "mA",
    "milliamp": "mA",
    "ka": "kA",

    # Temperature
    "°c": "°C",
    "c": "°C",
    "celsius": "°C",
    "°f": "°F",
    "f": "°F",
    "fahrenheit": "°F",
    "k": "K",
    "kelvin": "K",

    # Pressure
    "bar": "bar",
    "psi": "PSI",
    "kpa": "kPa",
    "mpa": "MPa",

    # Flow rate
    "m3/h": "m³/h",
    "m³/h": "m³/h",
    "l/min": "L/min",
    "gpm": "GPM",

    # Length / Dimensions / Head
    "m": "m",
    "meter": "m",
    "meters": "m",
    "mm": "mm",
    "millimeter": "mm",
    "millimeters": "mm",
    "cm": "cm",
    "centimeter": "cm",
    "in": "in",
    "inch": "in",
    "inches": "in",
    "ft": "ft",
    "feet": "ft",
}


# Allowed unit families per attribute concept
CONCEPT_ALLOWED_UNITS: Dict[str, Set[str]] = {
    "voltage": {"V", "kV", "mV"},
    "power": {"W", "kW", "MW", "HP"},
    "power_rating": {"VA", "kVA", "MVA", "W", "kW", "MW", "HP"},
    "speed": {"RPM"},
    "weight": {"g", "kg", "t", "lbs"},
    "frequency": {"Hz", "kHz", "MHz"},
    "current": {"A", "mA", "kA"},
    "temperature": {"°C", "°F", "K"},
    "pressure": {"bar", "PSI", "kPa", "MPa"},
    "flow_rate": {"m³/h", "L/min", "GPM"},
    "head": {"m", "ft"},
    "length": {"m", "mm", "cm", "in", "ft"},
    "height": {"m", "mm", "cm", "in", "ft"},
    "width": {"m", "mm", "cm", "in", "ft"},
    "depth": {"m", "mm", "cm", "in", "ft"},
}


class UnitValidator:
    """
    Validates and normalizes attribute units deterministically.
    """

    def normalize_unit(self, unit: Optional[str]) -> Optional[str]:
        """
        Normalizes a unit string to standard canonical representation.
        Example: 'kilowatts' -> 'kW', 'rpm' -> 'RPM'.
        """
        if not unit:
            return None
        cleaned = unit.strip()
        cleaned_lower = cleaned.lower()
        return UNIT_SYNONYMS.get(cleaned_lower, cleaned)

    def extract_unit_from_raw(self, raw_value: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Tries to extract unit and numeric string from raw value if unit was embedded.
        Returns (numeric_part, extracted_unit).
        """
        if not raw_value:
            return None, None
        
        m = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z°%/³]+)$", raw_value.strip())
        if m:
            num_str = m.group(1)
            unit_str = m.group(2)
            return num_str, self.normalize_unit(unit_str)
        return None, None

    def validate_unit(
        self,
        attribute_name: str,
        unit: Optional[str],
        raw_value: Optional[str] = None,
    ) -> UnitValidationResult:
        """
        Validates attribute unit against canonical rules.
        Detects invalid or incompatible units (e.g. Power = '230 V').
        """
        normalized_name = attribute_name.strip().lower().replace(" ", "_")
        
        # Extract unit from raw_value if unit parameter is missing
        actual_unit = unit
        if not actual_unit and raw_value:
            _, extracted = self.extract_unit_from_raw(raw_value)
            if extracted:
                actual_unit = extracted

        if not actual_unit:
            # Check if this attribute concept strictly expects a unit
            concept_key = self._match_concept(normalized_name)
            if concept_key and concept_key in CONCEPT_ALLOWED_UNITS:
                return UnitValidationResult(
                    is_valid=True,
                    normalized_unit=None,
                    issue_type="missing_unit",
                    message=f"Attribute '{attribute_name}' usually expects a unit but none was provided.",
                )
            return UnitValidationResult(is_valid=True, normalized_unit=None)

        canonical_unit = self.normalize_unit(actual_unit)

        # Check concept compatibility if concept is recognized
        concept_key = self._match_concept(normalized_name)
        if concept_key and concept_key in CONCEPT_ALLOWED_UNITS:
            allowed = CONCEPT_ALLOWED_UNITS[concept_key]
            if canonical_unit not in allowed:
                return UnitValidationResult(
                    is_valid=False,
                    normalized_unit=canonical_unit,
                    issue_type="invalid_unit",
                    message=f"Incompatible unit '{actual_unit}' for attribute '{attribute_name}'. Expected one of {sorted(list(allowed))}.",
                )

        return UnitValidationResult(
            is_valid=True,
            normalized_unit=canonical_unit,
        )

    def _match_concept(self, attribute_name: str) -> Optional[str]:
        """Maps an attribute name to a known physical concept."""
        name = attribute_name.lower().replace(" ", "_")
        
        for concept in CONCEPT_ALLOWED_UNITS.keys():
            if concept in name or name in concept:
                return concept
        
        # Specific mappings
        if "voltage" in name or "volt" in name:
            return "voltage"
        if "power" in name or "kw" in name or "watt" in name:
            return "power"
        if "speed" in name or "rpm" in name:
            return "speed"
        if "weight" in name or "mass" in name:
            return "weight"
        if "freq" in name:
            return "frequency"
        if "current" in name or "amp" in name:
            return "current"

        return None
