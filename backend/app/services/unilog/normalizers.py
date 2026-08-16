import re
from typing import Optional, Tuple

# Approved UOM mapping dictionary for standardizing spelling and casing
UOM_MAPPINGS = {
    "inches": "in",
    "inch": "in",
    "in.": "in",
    "in": "in",
    "feet": "ft",
    "foot": "ft",
    "ft.": "ft",
    "ft": "ft",
    "volts": "V",
    "volt": "V",
    "v": "V",
    "amps": "A",
    "amp": "A",
    "a": "A",
    "decibels": "dBA",
    "decibel": "dBA",
    "dba": "dBA",
    "db": "dBA",
    "hertz": "Hz",
    "hz": "Hz",
    "rpm": "RPM",
    "cfm": "CFM",
    "psi": "PSI",
    "degree": "°",
    "degrees": "°",
    "deg": "°",
    "celsius": "°C",
    "c": "°C",
    "f": "°F",
    "fahrenheit": "°F",
    "pc": "pc",
    "pcs": "pc",
    "pack": "pk",
    "pk": "pk",
    "box": "box",
    "disc": "disc",
    "discs": "disc",
}

# Trade fraction mapping based on 63 exact fraction points from Decimal_Fraction.xlsx
FRACTIONS = [
    (0.015625, "1/64"), (0.03125, "1/32"), (0.046875, "3/64"), (0.0625, "1/16"),
    (0.078125, "5/64"), (0.09375, "3/32"), (0.109375, "7/64"), (0.125, "1/8"),
    (0.140625, "9/64"), (0.15625, "5/32"), (0.171875, "11/64"), (0.1875, "3/16"),
    (0.203125, "13/64"), (0.21875, "7/32"), (0.234375, "15/64"), (0.25, "1/4"),
    (0.265625, "17/64"), (0.28125, "9/32"), (0.296875, "19/64"), (0.3125, "5/16"),
    (0.328125, "21/64"), (0.34375, "11/32"), (0.359375, "23/64"), (0.375, "3/8"),
    (0.390625, "25/64"), (0.40625, "13/32"), (0.421875, "27/64"), (0.4375, "7/16"),
    (0.453125, "29/64"), (0.46875, "15/32"), (0.484375, "31/64"), (0.5, "1/2"),
    (0.515625, "33/64"), (0.53125, "17/32"), (0.546875, "35/64"), (0.5625, "9/16"),
    (0.578125, "37/64"), (0.59375, "19/32"), (0.609375, "39/64"), (0.625, "5/8"),
    (0.640625, "41/64"), (0.65625, "21/32"), (0.671875, "43/64"), (0.6875, "11/16"),
    (0.703125, "45/64"), (0.71875, "23/32"), (0.734375, "47/64"), (0.75, "3/4"),
    (0.765625, "49/64"), (0.78125, "25/32"), (0.796875, "51/64"), (0.8125, "13/16"),
    (0.828125, "53/64"), (0.84375, "27/32"), (0.859375, "55/64"), (0.875, "7/8"),
    (0.890625, "57/64"), (0.90625, "29/32"), (0.921875, "59/64"), (0.9375, "15/16"),
    (0.953125, "61/64"), (0.96875, "31/32"), (0.984375, "63/64")
]

def decimal_to_fraction(val: float) -> str:
    """
    Converts a decimal size float (e.g. 50.25) to its closest fractional representation (e.g. 50-1/4).
    Uses a tolerance boundary of 0.0078 (half of 1/64) to decide if it maps to a trade fraction.
    """
    if val is None:
        return ""
    
    whole = int(val)
    frac = val - whole
    
    if frac < 0.0078:
        return str(whole)
    if frac > 0.9921:
        return str(whole + 1)
        
    # Find closest fraction
    closest_fraction = ""
    min_diff = 1.0
    for decimal_val, frac_str in FRACTIONS:
        diff = abs(frac - decimal_val)
        if diff < min_diff:
            min_diff = diff
            closest_fraction = frac_str
            
    if whole == 0:
        return closest_fraction
    return f"{whole}-{closest_fraction}"

def clean_uom(val: str, uom: Optional[str]) -> Tuple[str, str]:
    """
    Normalizes value and UOM mappings, adding appropriate space paddings
    and returning a tuple of standardized (value, UOM).
    Example: ("24", "in") or ("50-1/4", "in").
    """
    if not val:
        return "", ""
        
    val_str = str(val).strip()
    uom_str = str(uom).strip() if uom else ""
    
    # Standardize UOM spelling and casing
    norm_uom = UOM_MAPPINGS.get(uom_str.lower(), uom_str)
    
    # Extract embedded trailing unit from val_str if present (e.g., "24 in", "120V", "1 1/2 in")
    unit_pattern = r"^(.+?)\s*([a-zA-Z°%]+)$"
    match = re.match(unit_pattern, val_str)
    if match:
        possible_val, possible_uom = match.group(1).strip(), match.group(2).strip()
        possible_uom_lower = possible_uom.lower()
        if possible_uom_lower in UOM_MAPPINGS:
            val_str = possible_val
            if not norm_uom or norm_uom.lower() == possible_uom_lower:
                norm_uom = UOM_MAPPINGS[possible_uom_lower]
        
    # Try parsing decimal values for size normalizations
    try:
        # Match pattern like "24.25"
        if re.match(r"^\d+\.\d+$", val_str):
            float_val = float(val_str)
            if norm_uom in ("in", "ft", "°C", "°F", "°"):
                val_str = decimal_to_fraction(float_val)
    except ValueError:
        pass
        
    return val_str, norm_uom

def format_value_with_uom(val: str, uom: Optional[str]) -> str:
    """
    Combines normalized value and UOM with a standard single space padding.
    Example: "24 in" (UOM standard), or "120 V", or "41 dBA".
    """
    val_clean, uom_clean = clean_uom(val, uom)
    if not val_clean:
        return ""
    if not uom_clean:
        return val_clean
        
    # Enforce space except for degrees symbol
    if uom_clean == "°":
        return f"{val_clean}{uom_clean}"
    return f"{val_clean} {uom_clean}"

def clean_brand_manufacturer(manuf_str: str) -> Tuple[str, str, str, float]:
    """
    Normalizes manufacturer string utilizing approved lookup indexing and fuzzy string similarities.
    Returns tuple of (MANUFACTURER_NAME, BRAND_NAME, MFR_CODE, SIM_CONFIDENCE).
    """
    from app.services.unilog.lookups.manufacturers import fuzzy_normalize_manufacturer
    return fuzzy_normalize_manufacturer(manuf_str)
