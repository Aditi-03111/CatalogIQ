import os
import sys
import csv
import argparse
import logging
import uuid
import sqlalchemy as sa
from sqlmodel import Session, select, create_engine

# Setup sys.path to resolve app imports correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import settings
from app.models.unilog import UnilogRecord, UnilogEnriched, UnilogStatus
from app.services.unilog.pipeline import UnilogPipelineService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL)

def import_csv(file_path: str):
    """Parses raw input CSV and inserts missing records to PostgreSQL."""
    if not os.path.exists(file_path):
        logger.error(f"Input file not found at: {file_path}")
        return
        
    logger.info(f"Importing raw dataset from: {file_path}")
    count = 0
    skipped = 0
    
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        with Session(engine) as session:
            for row in reader:
                mpn = row.get("Mfg_Part_Num", "").strip()
                if not mpn:
                    continue
                    
                # Check duplicate
                stmt = select(UnilogRecord).where(UnilogRecord.mfg_part_num == mpn)
                existing = session.exec(stmt).first()
                if existing:
                    skipped += 1
                    continue
                    
                record = UnilogRecord(
                    id=uuid.uuid4(),
                    mfg_part_num=mpn,
                    part_desc=row.get("Part_Desc", ""),
                    e1_brand=row.get("E1_Brand", ""),
                    unilog_brand=row.get("Unilog_Brand", ""),
                    dib_brand=row.get("DIB_Brand", ""),
                    part_manuf=row.get("Part_Manuf", "")
                )
                session.add(record)
                count += 1
                
                # Commit in batches of 100
                if count % 100 == 0:
                    session.commit()
            session.commit()
            
    logger.info(f"Import complete: {count} records added, {skipped} records skipped (already exist).")

def run_enrichment(limit: int):
    """Runs batch AI processing on queued records."""
    logger.info(f"Starting batch AI processing (limit={limit})")
    
    with Session(engine) as session:
        # Find queued or failed records
        stmt = (
            select(UnilogRecord.id)
            .join(UnilogEnriched, UnilogRecord.id == UnilogEnriched.record_id, isouter=True)
            .where(
                (UnilogEnriched.status == None) |
                (UnilogEnriched.status == UnilogStatus.queued) |
                (UnilogEnriched.status == UnilogStatus.failed)
            )
            .limit(limit)
        )
        record_ids = session.exec(stmt).all()
        
        if not record_ids:
            logger.info("No queued records found for processing.")
            return
            
        logger.info(f"Found {len(record_ids)} records to enrich.")
        pipeline = UnilogPipelineService(session)
        
        success = 0
        failed = 0
        
        for idx, rec_id in enumerate(record_ids):
            try:
                enriched = pipeline.process_record(rec_id)
                if enriched.status == UnilogStatus.enriched:
                    success += 1
                    logger.info(f"[{idx+1}/{len(record_ids)}] Successfully enriched {enriched.enriched_data.get('manufacturer_part_number')}")
                else:
                    failed += 1
                    logger.warning(f"[{idx+1}/{len(record_ids)}] Failed to enrich record {rec_id}: {enriched.error_message}")
            except Exception as e:
                failed += 1
                logger.error(f"[{idx+1}/{len(record_ids)}] Fatal error during record process: {e}")
                
        logger.info(f"Batch processing run complete: {success} enriched, {failed} failed.")

def export_delivery_csv(template_path: str, output_path: str):
    """
    Reads the expected output format headers, maps enriched records from the database,
    and exports a fully compliant CSV file.
    """
    if not os.path.exists(template_path):
        logger.error(f"Expected format template not found at: {template_path}")
        return
        
    logger.info(f"Exporting delivery CSV using headers from: {template_path}")
    
    # Read headers from template
    with open(template_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader)
        
    with Session(engine) as session:
        # Fetch all enriched records
        stmt = (
            select(UnilogRecord, UnilogEnriched)
            .join(UnilogEnriched, UnilogRecord.id == UnilogEnriched.record_id)
            .where(UnilogEnriched.status == UnilogStatus.enriched)
        )
        results = session.exec(stmt).all()
        
        logger.info(f"Found {len(results)} enriched records to export.")
        
        export_rows = []
        for record, enriched in results:
            data = enriched.enriched_data
            
            # Map Pydantic properties to the CSV columns
            row_dict = {}
            row_dict["MFR URL"] = data.get("mfr_url", "")
            row_dict["PART_NUMBER"] = data.get("sku", "")
            row_dict["Dept"] = data.get("dept", "")
            row_dict["Class"] = data.get("clss", "")
            row_dict["Fine"] = data.get("fine", "")
            row_dict["SKU - MY_PART_NUMBER"] = data.get("sku", "")
            row_dict["Mfg_Part_Num"] = record.mfg_part_num
            row_dict["Part_Desc"] = record.part_desc
            row_dict["E1_Brand"] = record.e1_brand
            row_dict["Unilog_Brand"] = record.unilog_brand
            row_dict["DIB_Brand"] = record.dib_brand
            row_dict["Part_Manuf"] = record.part_manuf
            row_dict["MANUFACTURER_NAME"] = data.get("manufacturer_name", "")
            row_dict["BRAND_NAME"] = data.get("brand_name", "")
            row_dict["TRADE_NAME"] = data.get("trade_name", "")
            row_dict["MANUFACTURER_PART_NUMBER"] = data.get("manufacturer_part_number", "")
            row_dict["ALTERNATE_PART_NUMBER"] = data.get("alternate_part_number", "")
            row_dict["Classpath"] = data.get("classpath", "")
            row_dict["MOBILE_DESC"] = data.get("mobile_desc", "")
            row_dict["INVOICE_DESC"] = data.get("invoice_desc", "")
            row_dict["SHORT_DESC"] = data.get("short_desc", "")
            row_dict["LONG_DESC1"] = data.get("long_desc", "")
            row_dict["RETAIL_DESC"] = data.get("retail_desc", "")
            row_dict["MARKETING_DESCRIPTION"] = data.get("marketing_description", "")
            row_dict["With"] = data.get("with_attr", "")
            row_dict["Standard/Approvals"] = data.get("standards", "")
            row_dict["Prop 65"] = data.get("prop_65", "")
            row_dict["Application"] = data.get("application", "")
            row_dict["Includes"] = data.get("includes", "")
            row_dict["Product Name"] = data.get("product_name", "")
            row_dict["UPC"] = data.get("upc", "")
            row_dict["EAN"] = data.get("ean", "")
            row_dict["GTIN"] = data.get("gtin", "")
            row_dict["UNSPSC"] = data.get("unspsc", "")
            row_dict["Warranty"] = data.get("warranty", "")
            row_dict["List Price"] = data.get("list_price", "")
            row_dict["Selling Qty"] = data.get("selling_qty", "")
            row_dict["Selling UOM"] = data.get("selling_uom", "")
            row_dict["Standard Packaging Information"] = data.get("packaging_info", "")
            row_dict["LENGTH"] = data.get("length", "")
            row_dict["LENGTH_UOM"] = data.get("length_uom", "")
            row_dict["HEIGHT"] = data.get("height", "")
            row_dict["HEIGHT_UOM"] = data.get("height_uom", "")
            row_dict["WIDTH"] = data.get("width", "")
            row_dict["WIDTH_UOM"] = data.get("width_uom", "")
            row_dict["WEIGHT"] = data.get("weight", "")
            row_dict["WEIGHT_UOM"] = data.get("weight_uom", "")
            row_dict["VOLUME"] = data.get("volume", "")
            row_dict["VOLUME_UOM"] = data.get("volume_uom", "")
            row_dict["Product Image"] = data.get("product_image", "")
            row_dict["SDS"] = data.get("sds", "")
            row_dict["SDS_1"] = data.get("sds_1", "")
            row_dict["Warranty Information"] = data.get("warranty_info", "")
            row_dict["Catalog"] = data.get("catalog", "")
            row_dict["Specification Sheet"] = data.get("spec_sheet", "")
            row_dict["Country Of Origin"] = data.get("country_of_origin", "")
            row_dict["Discontinued"] = data.get("discontinued", "")
            row_dict["Actual Image (Yes/No)"] = data.get("actual_image", "")

            # Map Ref URLs
            ref_urls = [data.get("ref_url_1", ""), data.get("ref_url_2", ""), data.get("ref_url_3", ""), data.get("ref_url_4", ""), data.get("ref_url_5", "")]
            for idx, url in enumerate(ref_urls):
                row_dict[f"Ref URL {idx+1}"] = url

            # Map features (max 20)
            feats = data.get("features", [])
            for idx in range(20):
                feat_val = feats[idx] if idx < len(feats) else ""
                row_dict[f"ITEM_FEATURES_{idx+1}"] = feat_val

            # Map alternate images (max 4)
            alt_imgs = data.get("alternate_images", [])
            for idx in range(4):
                alt_val = alt_imgs[idx] if idx < len(alt_imgs) else ""
                row_dict[f"Alternate Image {idx+1}"] = alt_val

            # Map manuals
            manuals = data.get("manuals", [])
            row_dict["Instruction/Installation Manual"] = manuals[0] if len(manuals) > 0 else ""
            row_dict["Service Manual"] = manuals[1] if len(manuals) > 1 else ""
            row_dict["Owners/User Manual"] = manuals[2] if len(manuals) > 2 else ""
            row_dict["Line Drawing"] = manuals[3] if len(manuals) > 3 else ""

            # Map Attributes (max 50)
            attrs = data.get("attributes", [])
            for idx in range(50):
                if idx < len(attrs):
                    attr_item = attrs[idx]
                    row_dict[f"ATTRIBUTE_LABEL {idx+1}"] = attr_item.get("label", "")
                    row_dict[f"ATTRIBUTE_VALUE {idx+1}"] = attr_item.get("value", "")
                    row_dict[f"ATTRIBUTE_UOM {idx+1}"] = attr_item.get("uom", "")
                else:
                    row_dict[f"ATTRIBUTE_LABEL {idx+1}"] = ""
                    row_dict[f"ATTRIBUTE_VALUE {idx+1}"] = ""
                    row_dict[f"ATTRIBUTE_UOM {idx+1}"] = ""

            # Construct row ordered matching template headers
            row_values = [row_dict.get(h, "") for h in headers]
            export_rows.append(row_values)
            
        # Write export file
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(export_rows)
            
    logger.info(f"Export complete: output saved at: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UniHack Catalog Ingestion & Enrichment pipeline CLI tool")
    parser.add_argument("--import-raw", type=str, help="Import raw catalog records from a CSV input dataset")
    parser.add_argument("--process", action="store_true", help="Start AI batch processing on imported database records")
    parser.add_argument("--limit", type=int, default=5, help="Number of records to enrich in this batch run")
    parser.add_argument("--export", action="store_true", help="Compile and export fully enriched records to a delivery CSV")
    
    args = parser.parse_args()
    
    # Path mappings
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
    raw_input_path = os.path.join(data_dir, "Unihack_ Sample Dataset - Input.csv")
    template_path = os.path.join(data_dir, "Unihack_ Expected Output - Delivery Format.csv")
    output_path = os.path.join(data_dir, "enriched_unilog_output.csv")
    
    if args.import_raw:
        import_csv(args.import_raw)
    elif args.process:
        # Make sure records exist in DB. If not, auto-import from default path
        with Session(engine) as session:
            count = session.exec(select(sa.func.count(UnilogRecord.id))).one()
            if count == 0:
                logger.info("Database table is empty. Auto-importing default dataset.")
                import_csv(raw_input_path)
        run_enrichment(args.limit)
    elif args.export:
        export_delivery_csv(template_path, output_path)
    else:
        parser.print_help()
