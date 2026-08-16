import os
import csv
import sys

def verify_unilog_compliance():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
    template_path = os.path.join(data_dir, "Unihack_ Expected Output - Delivery Format.csv")
    output_path = os.path.join(data_dir, "enriched_unilog_output.csv")
    
    if not os.path.exists(output_path):
        print("ERROR: Enriched output CSV not found. Please run the pipeline script first.")
        sys.exit(1)
        
    print("--- STARTING UNILOG CATALOG COMPLIANCE RUN ---")
    
    # 1. Header Verification
    with open(template_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        template_headers = next(reader)
        
    with open(output_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        output_headers = next(reader)
        output_rows = list(reader)
        
    if len(template_headers) != len(output_headers):
        print(f"FAIL: Header count mismatch! Expected {len(template_headers)} columns, got {len(output_headers)}.")
        sys.exit(1)
        
    mismatches = []
    for idx, (th, oh) in enumerate(zip(template_headers, output_headers)):
        if th != oh:
            mismatches.append(f"Col {idx}: Expected '{th}', got '{oh}'")
            
    if mismatches:
        print("FAIL: Headers do not align exactly:")
        for m in mismatches[:10]:
            print(f"  {m}")
        sys.exit(1)
    else:
        print("PASS: CSV schema matches all 252 expected headers exactly!")

    # 2. Row Auditing
    total_rows = len(output_rows)
    print(f"Auditing {total_rows} enriched records...")
    
    invoice_desc_col = output_headers.index("INVOICE_DESC")
    mfr_part_col = output_headers.index("Mfg_Part_Num")
    
    invoice_len_violations = 0
    invoice_case_violations = 0
    
    for row_idx, row in enumerate(output_rows):
        mpn = row[mfr_part_col]
        invoice_desc = row[invoice_desc_col]
        
        # Length check (<= 40 chars)
        if len(invoice_desc) > 40:
            invoice_len_violations += 1
            print(f"  [LEN VIOLATION] Row {row_idx+1} ({mpn}): Invoice description is {len(invoice_desc)} chars: '{invoice_desc}'")
            
        # Casing check (must be uppercase)
        if invoice_desc != invoice_desc.upper():
            invoice_case_violations += 1
            print(f"  [CASE VIOLATION] Row {row_idx+1} ({mpn}): Invoice description is not uppercase: '{invoice_desc}'")
            
    print("\n--- COMPLIANCE REPORT SUMMARY ---")
    if invoice_len_violations == 0 and invoice_case_violations == 0:
        print("PASS: Invoice description rules satisfied! All descriptions are uppercase and <= 40 characters.")
    else:
        print(f"FAIL: Found {invoice_len_violations} length violations and {invoice_case_violations} casing violations.")
        sys.exit(1)

if __name__ == "__main__":
    verify_unilog_compliance()
