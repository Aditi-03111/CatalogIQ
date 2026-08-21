#!/usr/bin/env python3
"""
Field-Level Accuracy Scoring Script for CatalogIQ / UniHack Ground-Truth Evaluation.

Compares pipeline output (data/ground_truth_eval_output.csv) against ground-truth
answer key (data/Unihack_ Expected Output - Delivery Format.csv) field-by-field
for exact and case-insensitive accuracy across all 252 delivery format columns.

Outputs:
  - Concise accuracy & worst-performing field summary to stdout.
  - Detailed CSV diff report to data/accuracy_report.csv.
"""

import os
import sys
import csv
import json
import argparse
from typing import Dict, List, Any, Tuple


def normalize_val(val: Any) -> str:
    if val is None:
        return ""
    val_str = str(val).strip()
    if val_str in ("-- No Unilog Brand --", "-- No DIB Brand --", "-- Unbranded --", "N/A", "n/a", "null", "None"):
        # Normalize placeholder strings if needed, or keep raw string
        pass
    return val_str


def score_accuracy(
    actual_csv_path: str,
    expected_csv_path: str,
    output_diff_csv_path: str
) -> Dict[str, Any]:
    if not os.path.exists(actual_csv_path):
        raise FileNotFoundError(f"Actual pipeline output CSV not found at: {actual_csv_path}")
    if not os.path.exists(expected_csv_path):
        raise FileNotFoundError(f"Expected ground truth CSV not found at: {expected_csv_path}")

    # 1. Load Expected (Ground Truth) Rows
    with open(expected_csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        expected_rows = {row.get("Mfg_Part_Num", "").strip(): row for row in reader if row.get("Mfg_Part_Num")}

    # 2. Load Actual (Pipeline Output) Rows
    with open(actual_csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        actual_rows = {row.get("Mfg_Part_Num", "").strip(): row for row in reader if row.get("Mfg_Part_Num")}

    matched_mpns = sorted(list(set(expected_rows.keys()) & set(actual_rows.keys())))
    if not matched_mpns:
        raise ValueError(
            f"No matching Mfg_Part_Num records found between expected ({list(expected_rows.keys())}) "
            f"and actual ({list(actual_rows.keys())})."
        )

    # 3. Field-by-Field Evaluation
    diff_records = []
    field_stats: Dict[str, Dict[str, int]] = {
        col: {
            "exact_match": 0,
            "ci_match": 0,
            "blank_match": 0,
            "mismatch": 0,
            "missing": 0,
            "extra": 0,
            "total_evaluated": 0,
        }
        for col in headers
    }

    total_fields_evaluated = 0
    total_exact_matches = 0
    total_ci_matches = 0
    total_populated_expected = 0
    total_populated_matches = 0

    for mpn in matched_mpns:
        exp_row = expected_rows[mpn]
        act_row = actual_rows[mpn]

        for col in headers:
            exp_val = normalize_val(exp_row.get(col, ""))
            act_val = normalize_val(act_row.get(col, ""))

            stats = field_stats[col]
            stats["total_evaluated"] += 1
            total_fields_evaluated += 1

            if not exp_val and not act_val:
                status = "BLANK_MATCH"
                is_match = True
                stats["blank_match"] += 1
            elif exp_val and not act_val:
                status = "MISSING"
                is_match = False
                stats["missing"] += 1
                total_populated_expected += 1
            elif not exp_val and act_val:
                status = "EXTRA"
                is_match = False
                stats["extra"] += 1
            elif exp_val == act_val:
                status = "EXACT_MATCH"
                is_match = True
                stats["exact_match"] += 1
                stats["ci_match"] += 1
                total_exact_matches += 1
                total_ci_matches += 1
                total_populated_expected += 1
                total_populated_matches += 1
            elif exp_val.lower() == act_val.lower():
                status = "CASE_INSENSITIVE_MATCH"
                is_match = True
                stats["ci_match"] += 1
                total_ci_matches += 1
                total_populated_expected += 1
                total_populated_matches += 1
            else:
                status = "VALUE_MISMATCH"
                is_match = False
                stats["mismatch"] += 1
                total_populated_expected += 1

            diff_records.append({
                "Mfg_Part_Num": mpn,
                "Column_Name": col,
                "Expected_Value": exp_val,
                "Actual_Value": act_val,
                "Match_Status": status,
                "Is_Match": is_match,
            })

    # 4. Write Detailed Accuracy Diff CSV
    os.makedirs(os.path.dirname(output_diff_csv_path) or ".", exist_ok=True)
    with open(output_diff_csv_path, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["Mfg_Part_Num", "Column_Name", "Expected_Value", "Actual_Value", "Match_Status", "Is_Match"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(diff_records)

    # 5. Compute Accuracy Metrics
    total_blank_matches = sum(st["blank_match"] for st in field_stats.values())
    total_correct_fields = total_ci_matches + total_blank_matches
    overall_format_acc = (total_correct_fields / total_fields_evaluated) * 100.0 if total_fields_evaluated else 0.0
    overall_exact_acc = ((total_exact_matches + total_blank_matches) / total_fields_evaluated) * 100.0 if total_fields_evaluated else 0.0
    populated_acc = (total_populated_matches / total_populated_expected) * 100.0 if total_populated_expected else 0.0

    # Sort fields by mismatch rate (worst performing first)
    worst_fields = []
    for col, st in field_stats.items():
        eval_count = st["total_evaluated"]
        exact = st["exact_match"]
        ci = st["ci_match"]
        blank = st["blank_match"]
        mismatch = st["mismatch"] + st["missing"] + st["extra"]
        accuracy = ((ci + blank) / eval_count) * 100.0 if eval_count else 0.0
        worst_fields.append({
            "column": col,
            "accuracy_pct": round(accuracy, 1),
            "exact_matches": exact,
            "ci_matches": ci,
            "mismatches": st["mismatch"],
            "missing": st["missing"],
            "extra": st["extra"],
        })

    worst_fields.sort(key=lambda x: (x["accuracy_pct"], x["mismatches"] + x["missing"]), reverse=False)

    return {
        "matched_records": matched_mpns,
        "total_evaluated_fields": total_fields_evaluated,
        "overall_exact_accuracy_pct": round(overall_exact_acc, 2),
        "overall_case_insensitive_accuracy_pct": round(overall_format_acc, 2),
        "populated_fields_accuracy_pct": round(populated_acc, 2),
        "worst_performing_fields": worst_fields[:15],
        "best_performing_fields": [f for f in worst_fields if f["accuracy_pct"] == 100.0][:15],
        "diff_csv_path": output_diff_csv_path,
    }


def print_summary_report(metrics: Dict[str, Any]):
    print("=" * 80)
    print("      CATALOGIQ / UNILOG FIELD-LEVEL ACCURACY EVALUATION REPORT      ")
    print("=" * 80)
    print(f"Matched MPNs Evaluated : {', '.join(metrics['matched_records'])}")
    print(f"Total Fields Scored    : {metrics['total_evaluated_fields']} ({len(metrics['matched_records'])} rows x 252 cols)")
    print(f"Overall Exact Accuracy : {metrics['overall_exact_accuracy_pct']}%")
    print(f"Overall Case-Insens Acc: {metrics['overall_case_insensitive_accuracy_pct']}%")
    print(f"Populated Ground-Truth Acc: {metrics['populated_fields_accuracy_pct']}%")
    print("-" * 80)
    print("WORST-PERFORMING / DIVERGING FIELDS (Needs Prompt/Normalizer Tuning):")
    print(f"{'Column Name':<32} | {'Accuracy %':<10} | {'Mismatches':<10} | {'Missing':<8} | {'Extra':<6}")
    print("-" * 80)
    for wf in metrics["worst_performing_fields"]:
        if wf["accuracy_pct"] < 100.0 or wf["mismatches"] > 0 or wf["missing"] > 0:
            print(f"{wf['column']:<32} | {wf['accuracy_pct']:>8.1f}% | {wf['mismatches']:>10} | {wf['missing']:>8} | {wf['extra']:>6}")
    print("-" * 80)
    print(f"Detailed diff report written to: {metrics['diff_csv_path']}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score field-level accuracy against ground-truth CSV")
    parser.add_argument(
        "--actual",
        type=str,
        default="data/ground_truth_eval_output.csv",
        help="Path to pipeline actual output CSV",
    )
    parser.add_argument(
        "--expected",
        type=str,
        default="data/Unihack_ Expected Output - Delivery Format.csv",
        help="Path to ground-truth expected CSV",
    )
    parser.add_argument(
        "--output-diff",
        type=str,
        default="data/accuracy_report.csv",
        help="Path to write detailed CSV diff report",
    )

    args = parser.parse_args()

    # Resolve paths relative to repo root if executed from backend/
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    actual_path = os.path.join(base_dir, args.actual) if not os.path.isabs(args.actual) else args.actual
    expected_path = os.path.join(base_dir, args.expected) if not os.path.isabs(args.expected) else args.expected
    diff_path = os.path.join(base_dir, args.output_diff) if not os.path.isabs(args.output_diff) else args.output_diff

    try:
        metrics = score_accuracy(actual_path, expected_path, diff_path)
        print_summary_report(metrics)
    except Exception as e:
        print(f"Error during accuracy evaluation: {e}", file=sys.stderr)
        sys.exit(1)
