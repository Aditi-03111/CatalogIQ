import os
import io
import json
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_product_pdf(enriched_data: Dict[str, Any], record_info: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Generates a professional, publication-grade PDF specification sheet
    for an enriched catalog record. Returns raw PDF byte content.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom color palette
    NAVY = colors.HexColor("#1F4E79")
    DARK_BG = colors.HexColor("#1A1D24")
    TEXT_COLOR = colors.HexColor("#2C3E50")
    MUTED_TEXT = colors.HexColor("#5A6B7C")
    ACCENT_EMERALD = colors.HexColor("#059669")
    BORDER_COLOR = colors.HexColor("#E2E8F0")
    LIGHT_BG = colors.HexColor("#F8FAFC")

    # Typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=NAVY,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=MUTED_TEXT,
        textTransform='uppercase'
    )

    section_header = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=6
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=TEXT_COLOR
    )

    body_text = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=TEXT_COLOR
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    elements = []

    # 1. Header Banner
    brand_name = enriched_data.get("brand_name") or enriched_data.get("manufacturer_name") or "CatalogIQ Item"
    mpn = enriched_data.get("manufacturer_part_number") or record_info.get("mfg_part_num", "") if record_info else ""
    
    header_data = [
        [
            Paragraph(f"<b>CatalogIQ Product Intelligence Report</b>", title_style),
            Paragraph(f"<b>REF: {mpn}</b><br/>DATE: 2026-08-16", ParagraphStyle('RightHead', parent=subtitle_style, alignment=TA_RIGHT))
        ]
    ]
    header_table = Table(header_data, colWidths=[380, 160])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=12, spaceBefore=4))

    # 2. Product Identity Grid
    manuf = enriched_data.get("manufacturer_name") or (record_info.get("part_manuf", "") if record_info else "")
    classpath = enriched_data.get("classpath", "Industrial Products")
    product_title = enriched_data.get("short_desc") or record_info.get("part_desc", "") if record_info else ""
    invoice_desc = enriched_data.get("invoice_desc", "")
    mobile_desc = enriched_data.get("mobile_desc", "")

    identity_data = [
        [Paragraph("<b>Manufacturer:</b>", body_bold), Paragraph(manuf, body_text), Paragraph("<b>Brand:</b>", body_bold), Paragraph(brand_name, body_text)],
        [Paragraph("<b>Mfg Part Num:</b>", body_bold), Paragraph(mpn, body_text), Paragraph("<b>Category Path:</b>", body_bold), Paragraph(classpath, body_text)],
        [Paragraph("<b>Invoice Desc (≤40):</b>", body_bold), Paragraph(f"<code>{invoice_desc}</code>", body_text), Paragraph("<b>Mobile Desc (60-80):</b>", body_bold), Paragraph(mobile_desc, body_text)],
    ]

    id_table = Table(identity_data, colWidths=[95, 175, 95, 175])
    id_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(id_table)
    elements.append(Spacer(1, 10))

    # 3. Product Descriptions
    elements.append(Paragraph("Product Descriptions & Master Content", section_header))
    
    desc_data = [
        [Paragraph("<b>Product Title / Short Description</b>", body_bold)],
        [Paragraph(product_title, body_text)],
        [Paragraph("<b>Long Technical Description</b>", body_bold)],
        [Paragraph(enriched_data.get("long_desc", "N/A"), body_text)]
    ]
    desc_table = Table(desc_data, colWidths=[540])
    desc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#EFF6FF")),
        ('BACKGROUND', (0, 2), (0, 2), colors.HexColor("#EFF6FF")),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(desc_table)
    elements.append(Spacer(1, 12))

    # 4. Product Technical Specifications Table
    attributes = enriched_data.get("attributes", [])
    elements.append(Paragraph(f"Technical Specifications ({len(attributes)})", section_header))

    spec_rows = [
        [Paragraph("<b>Specification</b>", table_header), Paragraph("<b>Value</b>", table_header), Paragraph("<b>Unit</b>", table_header), Paragraph("<b>Status</b>", table_header)]
    ]

    for attr in attributes[:30]:
        label = attr.get("label") or attr.get("display_name") or attr.get("name") or "Attribute"
        val = str(attr.get("value", ""))
        uom = str(attr.get("uom", "") or "")
        status_txt = "VERIFIED" if attr.get("status") == "verified" else "ENRICHED"
        
        spec_rows.append([
            Paragraph(label, body_bold),
            Paragraph(val, body_text),
            Paragraph(uom, body_text),
            Paragraph(f"<font color='#059669'><b>{status_txt}</b></font>", body_text)
        ])

    if len(spec_rows) == 1:
        spec_rows.append([Paragraph("No extracted specifications", body_text), Paragraph("-", body_text), Paragraph("-", body_text), Paragraph("-", body_text)])

    spec_table = Table(spec_rows, colWidths=[180, 200, 70, 90])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG])
    ]))
    elements.append(spec_table)
    elements.append(Spacer(1, 12))

    # 5. Features & Certifications
    features = enriched_data.get("features", [])
    standards = enriched_data.get("standards", "")
    
    if features or standards:
        elements.append(Paragraph("Key Features & Standards", section_header))
        feat_bullets = "<br/>".join([f"• {f}" for f in features]) if features else "N/A"
        feat_data = [
            [Paragraph("<b>Key Product Features:</b>", body_bold), Paragraph("<b>Standards / Approvals:</b>", body_bold)],
            [Paragraph(feat_bullets, body_text), Paragraph(standards or "N/A", body_text)]
        ]
        feat_table = Table(feat_data, colWidths=[300, 240])
        feat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(feat_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
