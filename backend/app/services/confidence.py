"""
ConfidenceCalculator — multi-factor confidence scoring for extracted attributes.

Scale: 0–100 (integer-like float for transparency).

Design principles (per Phase 4 corrections):
  - Deterministic extraction is a STRONG signal, not guaranteed certainty.
    A table with two rows "Voltage | 230V" still starts at 88, not 100.
  - All attributes pass through this calculator regardless of extraction method.
  - The score is a transparent weighted combination of multiple signals.
  - The score is NOT treated as mathematical certainty.

Factors considered:
  1. extraction_method    — base score starting point
  2. evidence_verified    — large bonus when evidence found verbatim in IR
  3. normalization_success — small bonus for successful type parsing
  4. llm_confidence       — LLM's self-reported certainty (moderate weight)
  5. source_trust         — trust level of the provenance Source record
  6. conflict_penalty     — applied externally by ConflictDetector before persistence

Status mapping (per settings):
  score >= CONFIDENCE_THRESHOLD_HIGH  → "verified"
  score >= CONFIDENCE_THRESHOLD_MEDIUM → "extracted"
  score <  CONFIDENCE_THRESHOLD_MEDIUM → "needs_review"
"""
import logging
from typing import Optional

from app.core.config import settings
from app.models import AttributeStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base scores by extraction method (0–100 scale)
# NOTE: The maximum achievable score (all bonuses, source_trust=1.0, no conflicts)
# for deterministic must remain < 100 to uphold the principle that no extraction
# is treated as infallible. With base=76: 76+12+4+6=98 × 1.0 = 98.0.
# ---------------------------------------------------------------------------
_BASE_SCORES = {
    "deterministic": 76,   # Strong structural signal but not infallible
    "llm": 68,             # LLM with direct evidence quote
    "llm_inference": 48,   # LLM inferred, no direct quote — lower confidence
}

# Additive bonuses
_EVIDENCE_VERIFIED_BONUS = 12   # Evidence quote found verbatim in IR
_NORMALIZATION_SUCCESS_BONUS = 4  # Raw value parsed to correct type
_HIGH_LLM_CONFIDENCE_BONUS = 6  # LLM self-reported confidence > 0.85
_LOW_LLM_CONFIDENCE_PENALTY = 10  # LLM self-reported confidence < 0.4

# Source trust multiplier range
_SOURCE_TRUST_MIN = 0.80
_SOURCE_TRUST_MAX = 1.00


class ConfidenceScore:
    """Container for a computed confidence score with breakdown for transparency."""
    __slots__ = ("score", "base", "bonuses", "penalties", "status")

    def __init__(self, score: float, base: int, bonuses: list, penalties: list) -> None:
        self.score = round(min(100.0, max(0.0, score)), 1)
        self.base = base
        self.bonuses = bonuses
        self.penalties = penalties
        # Derive status from score
        high = settings.CONFIDENCE_THRESHOLD_HIGH * 100  # convert 0.85 → 85
        medium = settings.CONFIDENCE_THRESHOLD_MEDIUM * 100  # convert 0.60 → 60
        if self.score >= high:
            self.status = AttributeStatus.verified
        elif self.score >= medium:
            self.status = AttributeStatus.extracted
        else:
            self.status = AttributeStatus.needs_review

    def to_pipeline_float(self) -> float:
        """Returns a 0.0–1.0 float for storage in ProductAttribute.confidence column."""
        return round(self.score / 100.0, 4)

    def __repr__(self) -> str:
        return (
            f"ConfidenceScore(score={self.score}, status={self.status.value}, "
            f"base={self.base}, bonuses={self.bonuses}, penalties={self.penalties})"
        )


class ConfidenceCalculator:
    """
    Computes a transparent, multi-factor confidence score for a single attribute.

    Usage:
        calc = ConfidenceCalculator()
        score = calc.calculate(
            extraction_method="deterministic",
            evidence_verified=True,
            normalization_success=True,
            llm_confidence=0.92,
            source_trust=1.0,
        )
        attribute.confidence = score.to_pipeline_float()
        attribute.status = score.status
    """

    def calculate(
        self,
        extraction_method: str,
        evidence_verified: bool,
        normalization_success: bool,
        llm_confidence: float,
        source_trust: float = 1.0,
        conflict_count: int = 0,
    ) -> ConfidenceScore:
        """
        Calculate a 0–100 confidence score for a single extracted attribute.

        Args:
            extraction_method:    "deterministic" | "llm" | "llm_inference"
            evidence_verified:    True if evidence_text found verbatim in IR by EvidenceResolver.
            normalization_success: True if the normalizer successfully parsed the raw value.
            llm_confidence:       LLM self-reported confidence (0.0–1.0). 0.8 default for deterministic.
            source_trust:         Source.trust_level (0.0–1.0) — from the provenance Source record.
            conflict_count:       Number of existing attributes with the same name that conflict.

        Returns:
            ConfidenceScore with .score (0–100), .status, and breakdown.
        """
        bonuses = []
        penalties = []

        # 1. Base score from extraction method
        base = _BASE_SCORES.get(extraction_method, 60)

        # 2. Evidence verification bonus
        if evidence_verified:
            bonuses.append(("evidence_verified", _EVIDENCE_VERIFIED_BONUS))
        else:
            # Small nudge down if llm claimed to quote but not verified
            if extraction_method == "llm":
                penalties.append(("evidence_unverified_llm", 4))

        # 3. Normalization success bonus
        if normalization_success:
            bonuses.append(("normalization_success", _NORMALIZATION_SUCCESS_BONUS))

        # 4. LLM confidence signal (weighted)
        if llm_confidence >= 0.85:
            bonuses.append(("high_llm_confidence", _HIGH_LLM_CONFIDENCE_BONUS))
        elif llm_confidence < 0.40:
            penalties.append(("low_llm_confidence", _LOW_LLM_CONFIDENCE_PENALTY))

        # 5. Source trust multiplier (scales the running total, not additive)
        #    Clamp to [MIN, MAX] to avoid zeroing scores
        trust = max(_SOURCE_TRUST_MIN, min(_SOURCE_TRUST_MAX, source_trust))

        # 6. Conflict penalty — each conflicting existing attribute deducts points
        if conflict_count > 0:
            conflict_penalty = min(20, conflict_count * 8)
            penalties.append(("conflict", conflict_penalty))

        # Compute total
        total_bonus = sum(v for _, v in bonuses)
        total_penalty = sum(v for _, v in penalties)
        raw_score = (base + total_bonus - total_penalty) * trust

        return ConfidenceScore(
            score=raw_score,
            base=base,
            bonuses=bonuses,
            penalties=penalties,
        )

    def determine_status(self, score_float: float) -> AttributeStatus:
        """
        Determine AttributeStatus from a 0.0–1.0 confidence float.
        Converts to 0–100 scale then applies thresholds.

        Args:
            score_float: Confidence float as stored in ProductAttribute.confidence.

        Returns:
            AttributeStatus enum value.
        """
        score = score_float * 100
        high = settings.CONFIDENCE_THRESHOLD_HIGH * 100
        medium = settings.CONFIDENCE_THRESHOLD_MEDIUM * 100
        if score >= high:
            return AttributeStatus.verified
        if score >= medium:
            return AttributeStatus.extracted
        return AttributeStatus.needs_review


# ---------------------------------------------------------------------------
# Phase 5: Product Quality Calculator
# ---------------------------------------------------------------------------

from pydantic import BaseModel
from typing import List, Dict, Any


class ProductQualityBreakdown(BaseModel):
    quality_score: float                # Overall 0-100 score
    completeness: float                 # 0-100 (25% weight)
    confidence: float                   # 0-100 (25% weight)
    evidence_coverage: float            # 0-100 (20% weight)
    validation_health: float            # 0-100 (15% weight)
    source_trust: float                 # 0-100 (15% weight)
    critical_issues_count: int = 0
    error_issues_count: int = 0
    warning_issues_count: int = 0


class ProductQualityCalculator:
    """
    Calculates overall product quality score (0-100) using a transparent weighted formula:
      - completeness:        25%
      - confidence:          25%
      - evidence coverage:   20%
      - validation health:   15%
      - source trust:        15%
    """

    def calculate(
        self,
        completeness_score: float,
        avg_attribute_confidence: float,  # 0.0-1.0 or 0-100
        evidence_coverage_score: float,   # 0-100
        validation_issues: List[Any],
        source_trust_level: float = 0.9,  # 0.0-1.0
    ) -> ProductQualityBreakdown:
        """
        Calculates quality score and returns transparent component breakdown.
        """
        # Normalize inputs to 0-100
        comp = min(100.0, max(0.0, float(completeness_score)))
        
        conf = avg_attribute_confidence
        if conf <= 1.0:
            conf = conf * 100.0
        conf = min(100.0, max(0.0, float(conf)))

        evid = min(100.0, max(0.0, float(evidence_coverage_score)))

        trust = source_trust_level
        if trust <= 1.0:
            trust = trust * 100.0
        trust = min(100.0, max(0.0, float(trust)))

        # Calculate validation health starting at 100
        val_health = 100.0
        crit_count = 0
        err_count = 0
        warn_count = 0

        for issue in validation_issues:
            # issue can be ValidationIssue dataclass or ValidationResult DB model or dict
            severity = getattr(issue, "severity", None)
            if isinstance(issue, dict):
                severity = issue.get("severity", severity)
            
            sev_str = str(severity.value if hasattr(severity, "value") else severity).lower()

            if sev_str == "critical":
                val_health -= 30.0
                crit_count += 1
            elif sev_str == "error":
                val_health -= 15.0
                err_count += 1
            elif sev_str == "warning":
                val_health -= 5.0
                warn_count += 1

        val_health = min(100.0, max(0.0, val_health))

        # Weighted calculation
        total_score = (
            (comp * 0.25)
            + (conf * 0.25)
            + (evid * 0.20)
            + (val_health * 0.15)
            + (trust * 0.15)
        )

        final_score = round(min(100.0, max(0.0, total_score)), 1)

        return ProductQualityBreakdown(
            quality_score=final_score,
            completeness=round(comp, 1),
            confidence=round(conf, 1),
            evidence_coverage=round(evid, 1),
            validation_health=round(val_health, 1),
            source_trust=round(trust, 1),
            critical_issues_count=crit_count,
            error_issues_count=err_count,
            warning_issues_count=warn_count,
        )

