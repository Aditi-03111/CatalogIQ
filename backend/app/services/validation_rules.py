"""
Category validation rules registry.

Provides category-specific requirements (required fields, optional fields, expected units)
and generic fallback rules when no specific category match exists.
"""
from typing import Any, Dict, List, Optional


CATEGORY_RULES: Dict[str, Dict[str, Any]] = {
    "industrial_motor": {
        "display_name": "Industrial Motor",
        "required": [
            "voltage",
            "power",
            "speed",
        ],
        "optional": [
            "weight",
            "efficiency",
            "frequency",
            "phase",
            "current",
            "frame_size",
            "insulation_class",
            "ip_rating",
        ],
        "expected_units": {
            "voltage": ["V", "kV"],
            "power": ["W", "kW", "MW", "HP"],
            "speed": ["RPM"],
            "weight": ["g", "kg", "t", "lbs"],
            "frequency": ["Hz"],
            "current": ["A"],
        },
    },
    "motor": {
        "display_name": "Motor",
        "required": [
            "voltage",
            "power",
            "speed",
        ],
        "optional": [
            "weight",
            "efficiency",
            "frequency",
            "phase",
        ],
        "expected_units": {
            "voltage": ["V", "kV"],
            "power": ["W", "kW", "HP"],
            "speed": ["RPM"],
            "weight": ["kg"],
        },
    },
    "pump": {
        "display_name": "Industrial Pump",
        "required": [
            "flow_rate",
            "head",
            "power",
        ],
        "optional": [
            "speed",
            "pressure",
            "weight",
            "material",
        ],
        "expected_units": {
            "flow_rate": ["m³/h", "L/min", "GPM"],
            "head": ["m", "ft"],
            "power": ["kW", "W", "HP"],
            "pressure": ["bar", "PSI", "kPa"],
        },
    },
    "transformer": {
        "display_name": "Transformer",
        "required": [
            "primary_voltage",
            "secondary_voltage",
            "power_rating",
        ],
        "optional": [
            "frequency",
            "weight",
            "cooling_type",
        ],
        "expected_units": {
            "primary_voltage": ["V", "kV"],
            "secondary_voltage": ["V", "kV"],
            "power_rating": ["kVA", "MVA", "VA"],
            "frequency": ["Hz"],
        },
    },
}

GENERIC_FALLBACK_RULES: Dict[str, Any] = {
    "display_name": "Generic Product",
    "required": [],  # Generic products have no hardcoded mandatory attributes
    "optional": [
        "weight",
        "voltage",
        "power",
        "dimensions",
    ],
    "expected_units": {},
}


def normalize_category_key(category: Optional[str]) -> str:
    """Normalizes category string to standard dictionary key format."""
    if not category:
        return ""
    cat = category.strip().lower()
    cat = cat.replace(" ", "_").replace("-", "_").replace("&", "and")
    return cat


def get_category_rules(category: Optional[str]) -> Dict[str, Any]:
    """
    Returns validation rules for a specific product category.
    Falls back to GENERIC_FALLBACK_RULES if the category is unknown or None.
    """
    if not category:
        return GENERIC_FALLBACK_RULES.copy()

    key = normalize_category_key(category)
    
    # Direct match
    if key in CATEGORY_RULES:
        return CATEGORY_RULES[key].copy()

    # Substring match (e.g. "electric_industrial_motors" -> "industrial_motor")
    for known_key, rules in CATEGORY_RULES.items():
        if known_key in key or key in known_key:
            return rules.copy()

    return GENERIC_FALLBACK_RULES.copy()


# Explicit canonical alias mapping for category required/optional attributes
ATTRIBUTE_ALIASES: Dict[str, set] = {
    "voltage": {"voltage", "rated_voltage", "operating_voltage", "supply_voltage", "primary_voltage", "secondary_voltage"},
    "power": {"power", "rated_power", "power_rating", "motor_power", "output_power"},
    "speed": {"speed", "rated_speed", "operating_speed", "rotation_speed", "no_load_speed"},
    "frequency": {"frequency", "rated_frequency", "line_frequency", "operating_frequency"},
    "current": {"current", "rated_current", "full_load_current", "operating_current"},
    "phase": {"phase", "number_of_phases", "phase_count"},
    "weight": {"weight", "gross_weight", "net_weight"},
    "efficiency": {"efficiency", "motor_efficiency", "energy_efficiency"},
    "ip_rating": {"ip_rating", "protection_rating", "enclosure_rating", "ip_class"},
}


def is_attribute_present(target_field: str, present_attributes: set) -> bool:
    """
    Checks if target_field (or one of its explicit canonical aliases) is present in present_attributes.
    """
    req_key = target_field.lower().strip().replace(" ", "_")
    present_lower = {a.lower().strip().replace(" ", "_") for a in present_attributes}

    if req_key in present_lower:
        return True

    aliases = ATTRIBUTE_ALIASES.get(req_key, set())
    for alias in aliases:
        if alias in present_lower:
            return True

    return False

