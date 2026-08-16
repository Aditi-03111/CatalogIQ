import re
from typing import Tuple, Dict, List

# Seeding canonical manufacturer details: (CANONICAL_NAME, APPROVED_BRAND, CANONICAL_CODE)
CANONICAL_MANUFACTURERS = [
    ("Freud Inc", "Diablo®", "2435"),
    ("3M Company", "3M™", "JAMIN"),
    ("Jam Industrial Supply LLC", "3M™", "JAMIN"),
    ("Mirka Abrasives Inc", "Mirka®", "MIRKA"),
    ("Milwaukee Accessory", "Milwaukee®", "MILW"),
    ("Emseal Joint Systems Ltd", "Emseal™", "EMSEAL"),
    ("Appliance Dealers Cooperative", "Frigidaire®", "APPDE"),
    ("V & V Appliance Parts Inc", "Whirlpool®", "VVAP"),
    ("Wera Tools NA Inc", "Wera®", "WERA"),
    ("U S Lumber", "Trex®", "USLUM"),
    ("Boise Cascade Building Materials", "Trex®", "BOISE"),
    ("Parksite", "TimberTech®", "PARKSITE"),
    ("Velux America LLC", "Velux®", "VELUX"),
    ("Provia LLC", "Provia®", "PROVIA"),
    ("James Hardie Building Products", "James Hardie®", "HARDIE"),
    ("Huber Engineered Woods", "Huber®", "HUBER"),
    ("Leviton Manufacturing Co Inc", "Leviton®", "LEVITON"),
    ("General Electric Company", "GE®", "GE"),
    ("LG Electronics Inc", "LG®", "LG"),
    ("Speed Queen Company", "Speed Queen®", "SQ"),
]

def calculate_similarity_ratio(s1: str, s2: str) -> float:
    """Helper to calculate standard Jaccard token overlap similarity between two strings."""
    tokens1 = set(re.findall(r"\w+", s1.lower()))
    tokens2 = set(re.findall(r"\w+", s2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    return len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))

def fuzzy_normalize_manufacturer(raw_manuf: str) -> Tuple[str, str, str, float]:
    """
    Fuzzy-matches a messy manufacturer string against the approved canonical list.
    Returns: (CANONICAL_NAME, BRAND_NAME, CODE, CONFIDENCE_SCORE).
    """
    placeholders = {
        "", "-", "--", "-- unbranded --", "-- no unilog brand --",
        "-- no dib brand --", "-- no e1 brand --", "unbranded", "no brand",
        "none", "n/a", "null", "undefined"
    }
    if not raw_manuf or raw_manuf.strip().lower() in placeholders:
        return "Unknown Manufacturer", "Unbranded", "UNKNOWN", 0.0
        
    clean_raw = re.sub(r"\s*\(\w+\)\s*$", "", raw_manuf).strip()
    
    best_match = None
    best_score = 0.0
    
    for canon_mfr, brand, code in CANONICAL_MANUFACTURERS:
        # Calculate overlap similarity
        score = calculate_similarity_ratio(clean_raw, canon_mfr)
        
        # Check direct substring as bonus
        if clean_raw.lower() in canon_mfr.lower() or canon_mfr.lower() in clean_raw.lower():
            score = max(score, 0.8)
            
        if score > best_score:
            best_score = score
            best_match = (canon_mfr, brand, code)
            
    if best_match and best_score >= 0.3:
        return best_match[0], best_match[1], best_match[2], round(best_score, 2)
        
    # Fallback if no fuzzy overlap resolved
    return clean_raw, clean_raw, "UNKNOWN", 0.1
