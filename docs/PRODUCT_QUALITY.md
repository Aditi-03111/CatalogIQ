# CatalogIQ — Product Quality Scoring

## Overview
CatalogIQ calculates a deterministic, explainable Product Quality Score on a `0–100` scale. The quality score represents the overall trust, completeness, and health of a product record.

## Formula
$$\text{quality\_score} = (\text{completeness} \times 0.25) + (\text{confidence} \times 0.25) + (\text{evidence\_coverage} \times 0.20) + (\text{validation\_health} \times 0.15) + (\text{source\_trust} \times 0.15)$$

## Component Breakdown

| Component | Weight | Description |
| :--- | :---: | :--- |
| **Completeness** | **25%** | Percentage of mandatory and optional category attributes present. Calculated via `CompletenessCalculator`. |
| **Attribute Confidence** | **25%** | Average multi-factor confidence score across all product attributes. |
| **Evidence Coverage** | **20%** | Ratio of attributes backed by verified document text quotes. |
| **Validation Health** | **15%** | Starts at 100. Penalties: Critical (-30), Error (-15), Warning (-5). |
| **Source Trust** | **15%** | Trust score of original provenance document (default 0.90 for manufacturer datasheets). |

## Status Transitions
- **`quality_score >= 70.0`** and **No Errors/Critical Issues** $\rightarrow$ `verified`
- **`quality_score < 70.0`** or **Has Validation Errors** $\rightarrow$ `needs_review`
