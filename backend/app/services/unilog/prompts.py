UNILOG_SYSTEM_PROMPT = """You are an expert AI industrial data engineer specializing in product information management (PIM) for industrial commerce. Your task is to ingest messy, abbreviated catalog rows and enrich them into complete, standardized, search-ready product intelligence.

You must follow these strict rules when formulating the output:

1. CORE IDENTITY & BRANDS:
- MANUFACTURER_NAME: Clean name of the manufacturer. Remove trailing database codes like (2435).
- BRAND_NAME: Approved brand name (with ® or ™ if standard). If the product has no brand, fallback to MANUFACTURER_NAME.
- MANUFACTURER_PART_NUMBER: Extracted MPN (e.g. PDSH4816AF, WDTS7024RZ).
- CLASSPATH: Hierarchical path following structural patterns (e.g. "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers" or "Abrasives>Sanding & Grinding>Sanding Belts").

2. DESCRIPTIONS FORMULAS:
- INVOICE_DESC: UPPERCASE, maximum 40 characters. Abbreviate terms (e.g. "SST" for Stainless Steel, "BLTLN" for Built-in, "CPLG" for Coupling, "BRS" for Brass).
  Example: "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN"
- MOBILE_DESC: 60-80 characters long. Format: "[MANUFACTURER] [BRAND], [Item Type], [Series], [MPN], [Key Feature]"
  Example: "Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF"
- SHORT_DESC (Product Title): [BRAND] [Series] [MPN] [Item Type] with [Features].
  Example: "FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost™, Leg Mounting, 5-Wash Cycle, Stainless Steel"
- LONG_DESC: Detailed listing of all technical features, voltages, sizes, materials, and additional features.

3. COMPREHENSIVE TECHNICAL ATTRIBUTES & SPECS:
- Extract ALL applicable technical specifications into the `attributes` array of objects: `{"label": "Standardized Label", "value": "Clean Value", "uom": "Approved UOM"}`.
- Standard attribute labels include: Series, Model, Voltage Rating, Amperage Rating, Mounting Type, Size, Depth With Door Open, Minimum Height, Maximum Height, Sound Level, Material, Color, Number of Wash Cycles, Grit, Flow Rate, Operating Pressure, Connection Type, Thread Size, Additional Information.
- UOM spacing rule: Separate value and unit with a space, e.g. "24 in" (value="24", uom="in"), "120 V" (value="120", uom="V").
- Fraction rule: Convert decimal inch sizes to trade fractions (0.5 -> "1/2", 0.25 -> "1/4", 0.375 -> "3/8", 50.25 -> "50-1/4").
  Example: Size = "33-7/16 in H x 23-7/8 in W x 22-5/8 in D", Depth With Door Open = "50-3/16 in".

4. IMAGES & PDF ACCESSORIES:
- PRODUCT_IMAGE: Predict catalog image filename (e.g., "[BRAND]_[MPN].jpg").
- SPEC_SHEET: Predict spec sheet PDF filename (e.g., "[BRAND]_[MPN]_Specification_Sheet.pdf").
"""

UNILOG_FEW_SHOT_EXAMPLES = """
---
FEW-SHOT TRAINING EXAMPLE 1:

[INPUT ROW]
Mfg_Part_Num: PDSH4816AF
Part_Desc: PDSH4816AF Dishwasher SS - Display Only
E1_Brand: -- Unbranded --
Unilog_Brand: -- No Unilog Brand --
DIB_Brand: -- No DIB Brand --
Part_Manuf: Appliance Dealers Cooperative (APPDE)

[OUTPUT ENRICHMENT]
{
  "mfr_url": "https://www.frigidaire.com/en/p/owner-center/product-support/PDSH4816AF",
  "dept": "Appliances",
  "clss": "Large Appliances",
  "fine": "Dishwashers",
  "sku": "1515863",
  "manufacturer_name": "Rheem Manufacturing",
  "brand_name": "FRIGIDAIRE®",
  "trade_name": "",
  "manufacturer_part_number": "PDSH4816AF",
  "alternate_part_number": "",
  "classpath": "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
  "mobile_desc": "Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF",
  "invoice_desc": "DISHWASHER LEG 5 SST 120V 15A 50-1/4IN",
  "short_desc": "FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost™, Leg Mounting, 5-Wash Cycle, Stainless Steel",
  "long_desc": "FRIGIDAIRE® Dishwasher With CleanBoost™, Professional Series, 5 Wash Cycles, 120 V, 15 A, Leg Mounting, 24 in W x 24-1/4 in D, 50-1/4 in Depth With Door Open, 8-1/2 in Upper Rack, 11-1/4 in Lower Rack Minimum Height, 10-3/8 in Upper Rack, 13-1/4 in Lower Rack Maximum Height, 47 dBA Sound Level, Stainless Steel, Additional Information: 240 kW-hr Annual Energy, 1 to 12 hr Delay Start Hours",
  "retail_desc": "Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel",
  "marketing_description": "",
  "features": [
    "CleanBoost™ technology for deep cleaning",
    "Leg mounting system",
    "5-Wash cycle select options",
    "Stainless steel finish"
  ],
  "with_attr": "CleanBoost™",
  "standards": "ASSE 1006|CEE Tier 2 Qualified|cUL Listed|ENERGY STAR Certified|NSF Certified|UL Listed",
  "prop_65": "",
  "application": "",
  "includes": "",
  "product_name": "Dishwasher",
  "attributes": [
    {"label": "Series", "value": "Professional Series", "uom": ""},
    {"label": "Number of Wash Cycles", "value": "5", "uom": ""},
    {"label": "Voltage Rating", "value": "120", "uom": "V"},
    {"label": "Amperage Rating", "value": "15", "uom": "A"},
    {"label": "Mounting Type", "value": "Leg", "uom": ""},
    {"label": "Size", "value": "24 in W x 24-1/4 in D", "uom": ""},
    {"label": "Depth With Door Open", "value": "50-1/4", "uom": "in"},
    {"label": "Minimum Height", "value": "8-1/2 in Upper Rack, 11-1/4 in Lower Rack", "uom": ""},
    {"label": "Maximum Height", "value": "10-3/8 in Upper Rack, 13-1/4 in Lower Rack", "uom": ""},
    {"label": "Sound Level", "value": "47", "uom": "dBA"},
    {"label": "Material", "value": "Stainless Steel", "uom": ""}
  ],
  "upc": "",
  "ean": "",
  "gtin": "",
  "unspsc": "",
  "warranty": "1 Year Manufacturer, 1 Year Labor and Parts",
  "list_price": "",
  "selling_qty": "1",
  "selling_uom": "EA",
  "packaging_info": "",
  "length": "24",
  "length_uom": "in",
  "height": "35",
  "height_uom": "in",
  "width": "24",
  "width_uom": "in",
  "weight": "85",
  "weight_uom": "lb",
  "volume": "",
  "volume_uom": "",
  "product_image": "FRIGIDAIRE_PDSH4816AF.jpg",
  "alternate_images": [
    "FRIGIDAIRE_PDSH4816AF_1.jpg",
    "FRIGIDAIRE_PDSH4816AF_2.jpg",
    "FRIGIDAIRE_PDSH4816AF_3.jpg"
  ],
  "sds": "",
  "sds_1": "",
  "warranty_info": "",
  "catalog": "",
  "spec_sheet": "FRIGIDAIRE_PDSH4816AF_Specification_Sheet.pdf",
  "manuals": [],
  "country_of_origin": "",
  "discontinued": "No",
  "actual_image": "Yes"
}

---
FEW-SHOT TRAINING EXAMPLE 2:

[INPUT ROW]
Mfg_Part_Num: WDTS7024RZ
Part_Desc: WDTS7024RZ Dishwasher SS - Display Only
E1_Brand: -- Unbranded --
Unilog_Brand: -- No Unilog Brand --
DIB_Brand: -- No DIB Brand --
Part_Manuf: Appliance Dealers Cooperative (APPDE)

[OUTPUT ENRICHMENT]
{
  "mfr_url": "https://www.whirlpool.com/kitchen/dishwasher/built-in/p.WDTS7024RZ.html",
  "dept": "Appliances",
  "clss": "Large Appliances",
  "fine": "Dishwashers",
  "sku": "1515867",
  "manufacturer_name": "Whirlpool Corporation",
  "brand_name": "Whirlpool®",
  "trade_name": "",
  "manufacturer_part_number": "WDTS7024RZ",
  "alternate_part_number": "",
  "classpath": "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
  "mobile_desc": "Whirlpool, Dishwasher, Eco Series, WDTS7024RZ, Built-in Mounting",
  "invoice_desc": "DISHWASHER BLTLN SST SST 120V 10A 41DBA",
  "short_desc": "Whirlpool® Eco Series WDTS7024RZ Dishwasher, Built-in Mounting, Stainless Steel, Stainless Steel",
  "long_desc": "Whirlpool® Dishwasher, Eco Series, 120 V, 10 A, Built-in Mounting, 33-7/16 in H x 23-7/8 in W x 22-5/8 in D, 50-3/16 in Depth With Door Open, 33-7/16 in Minimum Height, 41 dBA Sound Level, Stainless Steel, Stainless Steel, Additional Information: Folding Tines, Leak Detection System, Moisture Repellent Silverware Basket, Normal Cycle, Quick Wash Cycle, Sani Rinse Option, Sensor Cycle, Triple Wash Spray",
  "retail_desc": "Eco Series Dishwasher, Built-in Mounting, Stainless Steel, Stainless Steel",
  "marketing_description": "Load more and run less with our quietest and largest capacity dishwasher. A 3rd Rack provides dedicated space for mugs and bowls, while an adjustable 2nd Rack helps fit all the dishes and pans your family piles up.",
  "features": [
    "3rd rack with extra wash action",
    "Adjustable 2nd Rack",
    "41 dBA Sound Level",
    "Moisture Repellent Silverware Basket",
    "Sensor cycle"
  ],
  "with_attr": "Washing 3rd Rack, Water Repellent Silverware Basket",
  "standards": "",
  "prop_65": "",
  "application": "",
  "includes": "",
  "product_name": "Dishwasher",
  "attributes": [
    {"label": "Series", "value": "Eco Series", "uom": ""},
    {"label": "Voltage Rating", "value": "120", "uom": "V"},
    {"label": "Amperage Rating", "value": "10", "uom": "A"},
    {"label": "Mounting Type", "value": "Built-in", "uom": ""},
    {"label": "Size", "value": "33-7/16 in H x 23-7/8 in W x 22-5/8 in D", "uom": ""},
    {"label": "Depth With Door Open", "value": "50-3/16", "uom": "in"},
    {"label": "Minimum Height", "value": "33-7/16", "uom": "in"},
    {"label": "Sound Level", "value": "41", "uom": "dBA"},
    {"label": "Material", "value": "Stainless Steel", "uom": ""},
    {"label": "Color", "value": "Stainless Steel", "uom": ""}
  ],
  "upc": "",
  "ean": "",
  "gtin": "",
  "unspsc": "",
  "warranty": "",
  "list_price": "",
  "selling_qty": "1",
  "selling_uom": "EA",
  "packaging_info": "",
  "length": "23-7/8",
  "length_uom": "in",
  "height": "33-7/16",
  "height_uom": "in",
  "width": "22-5/8",
  "width_uom": "in",
  "weight": "78",
  "weight_uom": "lb",
  "volume": "",
  "volume_uom": "",
  "product_image": "Whirlpool_WDTS7024RZ.jpg",
  "alternate_images": [],
  "sds": "",
  "sds_1": "",
  "warranty_info": "",
  "catalog": "",
  "spec_sheet": "Whirlpool_WDTS7024RZ_Specification_Sheet.pdf",
  "manuals": [
    "Whirlpool_WDTS7024RZ_Owners_Manual.pdf",
    "Whirlpool_WDTS7024RZ_Installation_Instructions.pdf"
  ],
  "country_of_origin": "",
  "discontinued": "No",
  "actual_image": "Yes"
}
---
"""

def build_unilog_prompt(mfg_part_num: str, part_desc: str, brand_name: str, manufacturer_name: str) -> str:
    return f"""Please enrich the following industrial product row:
Mfg_Part_Num: {mfg_part_num}
Part_Desc: {part_desc}
Brand: {brand_name}
Manufacturer: {manufacturer_name}

Instructions for attribute extraction:
- Thoroughly extract ALL product attributes and specifications (e.g. Series, Model, Voltage, Amperage, Mounting Type, Dimensions, Depth, Height, Material, Color, Sound Level, Wash Cycles, Grit, Flow Rate, Pressure, Certifications, Additional Info).
- Format each attribute object cleanly: {{"label": "Attribute Name", "value": "Clean Value", "uom": "Unit"}}.
- Ensure unit and value are strictly separated into 'value' and 'uom' fields (e.g. value="120", uom="V"; value="24 in W x 24-1/4 in D", uom="").

Output a valid JSON object matching the requested schema.
"""
