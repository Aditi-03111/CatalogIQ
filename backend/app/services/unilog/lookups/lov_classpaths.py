from typing import Tuple

APPROVED_CLASSPATHS = [
    "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
    "Appliances & Consumer Electronics>Laundry Appliances>Dryers",
    "Appliances & Consumer Electronics>Laundry Appliances>Washing Machines",
    "Abrasives>Sanding & Grinding>Sanding Belts",
    "Abrasives>Sanding & Grinding>Sanding Discs",
    "Abrasives>Sanding & Grinding>Cut-Off Wheels",
    "Building Materials>Decking & Railing>Deck Boards",
    "Building Materials>Decking & Railing>Railing Kits",
    "Building Materials>Joint Tapes & Sealants>Expansion Joints",
    "Tools & Hardware>Hand Tools>Kneeling Pads",
    "Building Materials>Drywall & Plastering>Drywall Sheets",
    "Building Materials>Siding & Trim>Siding Panels",
    "Electrical & Lighting>Wiring Accessories>Electrical Tape",
    "Electrical & Lighting>Power Distribution>Box Covers",
]

def fuzzy_classify_classpath(raw_classpath: str) -> Tuple[str, float]:
    """
    Validates predicted classpath against approved taxonomy paths.
    Returns: (VALID_CLASSPATH, MATCH_CONFIDENCE).
    """
    if not raw_classpath:
        return APPROVED_CLASSPATHS[0], 0.0
        
    raw_clean = raw_classpath.strip().lower()
    
    best_match = None
    best_score = 0.0
    
    for path in APPROVED_CLASSPATHS:
        path_clean = path.lower()
        
        # Word overlap score
        raw_words = set(raw_clean.split(">"))
        path_words = set(path_clean.split(">"))
        
        overlap = len(raw_words.intersection(path_words))
        score = overlap / max(len(raw_words), 1)
        
        # Exact match override
        if raw_clean == path_clean:
            score = 1.0
            
        if score > best_score:
            best_score = score
            best_match = path
            
    if best_match and best_score >= 0.4:
        return best_match, round(best_score, 2)
        
    # Default fallback to closest match if low score
    return APPROVED_CLASSPATHS[0], 0.1
