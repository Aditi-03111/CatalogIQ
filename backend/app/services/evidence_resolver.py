"""
EvidenceResolver — verifies LLM-claimed evidence against the actual Docling IR.

Responsibility:
  - Prevent fabricated evidence from propagating into the database.
  - Set evidence_verified = True ONLY when the evidence_text is found verbatim
    (or near-verbatim) in the actual IR page text or table cells.
  - Downgrade extraction_method from "llm" → "llm_inference" when evidence
    cannot be verified, ensuring ConfidenceCalculator applies the correct
    base score.

Design:
  - Verification uses substring matching with normalization (case-insensitive,
    whitespace-collapsed). This handles minor formatting differences.
  - For "deterministic" attributes: evidence is considered verified if the
    raw_value appears anywhere in the IR (tables included), since the table
    parser itself found it there.
  - For "llm_inference" attributes: evidence_verified is always False
    (by definition — no evidence exists).
  - Verification does NOT modify the evidence_text. We only set evidence_verified.

This resolver runs AFTER the LLM produces ExtractionResult and BEFORE
ConfidenceCalculator and the persistence step.
"""
import logging
import re
from typing import Any, Dict, List

from app.services.llm.base import ExtractionResult, RawAttributeItem

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Collapse whitespace and lowercase for fuzzy matching."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _build_ir_corpus(ir: Dict[str, Any]) -> str:
    """
    Flattens the entire IR into a single searchable text string.
    Includes: all page text, all table headers, all table cell values.
    """
    parts: List[str] = []
    for page in ir.get("pages", []):
        text = page.get("text", "") or ""
        parts.append(text)
        for table in page.get("tables", []):
            for header in table.get("headers", []):
                parts.append(str(header))
            for row in table.get("rows", []):
                for cell in row:
                    parts.append(str(cell))
    return _normalize_text(" ".join(parts))


class EvidenceResolver:
    """
    Verifies LLM-claimed evidence against the Docling IR and adjusts
    extraction_method and evidence_verified fields on each RawAttributeItem.

    The pipeline calls this after ExtractionResult is received from the provider
    and before the ConfidenceCalculator runs.
    """

    def resolve(
        self,
        result: ExtractionResult,
        ir: Dict[str, Any],
    ) -> ExtractionResult:
        """
        Verify all attributes in the ExtractionResult against the IR corpus.

        Modifies each RawAttributeItem in-place:
          - Sets evidence_verified = True if evidence_text found in IR.
          - Downgrades extraction_method from "llm" → "llm_inference" if
            evidence_text is empty or not found in IR.

        Args:
            result: The ExtractionResult from the LLM provider.
            ir:     The Docling Intermediate Representation dict.

        Returns:
            The same ExtractionResult with updated attribute evidence flags.
        """
        corpus = _build_ir_corpus(ir)
        resolved_count = 0
        downgraded_count = 0

        for attr in result.attributes:
            attr = self._resolve_attribute(attr, corpus)
            if attr.evidence_verified:
                resolved_count += 1
            elif attr.extraction_method == "llm_inference":
                downgraded_count += 1

        logger.info(
            f"EvidenceResolver: {resolved_count} verified, "
            f"{downgraded_count} downgraded to llm_inference "
            f"out of {len(result.attributes)} total attributes"
        )
        return result

    def _resolve_attribute(
        self, attr: RawAttributeItem, corpus: str
    ) -> RawAttributeItem:
        """
        Verify a single attribute's evidence against the IR corpus.
        """
        # llm_inference by definition has no evidence — never verified
        if attr.extraction_method == "llm_inference":
            attr.evidence_verified = False
            return attr

        # deterministic: the parser itself extracted this from the IR —
        # verify that at least the raw_value appears in the corpus
        if attr.extraction_method == "deterministic":
            raw_norm = _normalize_text(attr.raw_value)
            if raw_norm and raw_norm in corpus:
                attr.evidence_verified = True
            else:
                # Value not found — unusual but possible (e.g., normalized differently)
                logger.warning(
                    f"Deterministic attribute '{attr.name}' raw_value '{attr.raw_value}' "
                    f"not found verbatim in IR corpus. Setting evidence_verified=False."
                )
                attr.evidence_verified = False
            return attr

        # llm: verify that the claimed evidence_text quote exists in the IR
        if attr.extraction_method == "llm":
            evidence = (attr.evidence_text or "").strip()

            if not evidence:
                # LLM did not provide a quote — downgrade to inference
                logger.debug(
                    f"LLM attribute '{attr.name}': evidence_text is empty, "
                    f"downgrading to llm_inference"
                )
                attr.extraction_method = "llm_inference"
                attr.evidence_verified = False
                return attr

            evidence_norm = _normalize_text(evidence)
            # Require at least a 3-word overlap or the full normalized quote
            if evidence_norm in corpus:
                attr.evidence_verified = True
            else:
                # Try partial match: all meaningful words present in corpus.
                # Strip pipe separators used in table evidence ('Key | Value' format)
                # and split into individual tokens for word-level overlap check.
                import re as _re
                evidence_tokens = [t for t in _re.split(r'[|\s]+', evidence_norm) if len(t) >= 2]
                if len(evidence_tokens) >= 2 and all(t in corpus for t in evidence_tokens):
                    attr.evidence_verified = True
                    logger.debug(
                        f"LLM attribute '{attr.name}': partial token match for evidence "
                        f"'{attr.evidence_text[:60]}'"
                    )
                else:
                    logger.warning(
                        f"LLM attribute '{attr.name}': evidence text not found in IR corpus. "
                        f"Downgrading from 'llm' \u2192 'llm_inference'. "
                        f"Evidence: '{attr.evidence_text[:60]}'"
                    )
                    attr.extraction_method = "llm_inference"
                    attr.evidence_verified = False

        return attr
