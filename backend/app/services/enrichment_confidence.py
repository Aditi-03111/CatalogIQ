"""
Enrichment Confidence Calculator.

Calculates confidence score for AI-generated commerce content (0.0-0.95 scale).
Ensures AI-generated marketing text is never rated 1.0.
"""
from typing import Optional
from app.services.claim_checker import ClaimCheckResult


class EnrichmentConfidenceCalculator:
    """
    Calculates confidence for AI commerce content based on verified claim support,
    evidence coverage, validation health, and source trust.
    """

    def calculate(
        self,
        claim_result: ClaimCheckResult,
        evidence_coverage: float,  # 0-100
        validation_health: float,  # 0-100
        source_trust: float = 0.9,  # 0.0-1.0
        llm_confidence: float = 0.88,  # 0.0-1.0
    ) -> float:
        """
        Calculates confidence bounded strictly between 0.0 and 0.95.

        Guidelines:
          - Fully supported (no unsupported claims, high evidence) -> 0.85-0.95
          - Mostly supported -> 0.70-0.85
          - Partially supported -> 0.50-0.70
          - Unsupported claims present -> < 0.50
        """
        # If unsupported claims exist, cap confidence under 0.50
        if claim_result.has_unsupported_claims:
            penalty = len(claim_result.unsupported_claims) * 0.10
            return round(max(0.10, 0.48 - penalty), 4)

        # Claim support ratio
        claim_ratio = (
            claim_result.supported_claims_count / max(1, claim_result.total_claims_count)
        )

        evid_ratio = min(1.0, max(0.0, evidence_coverage / 100.0))
        val_ratio = min(1.0, max(0.0, validation_health / 100.0))
        trust_ratio = min(1.0, max(0.0, source_trust))
        llm_ratio = min(1.0, max(0.0, llm_confidence))

        # Weighted score
        score = (
            (claim_ratio * 0.35)
            + (evid_ratio * 0.25)
            + (val_ratio * 0.15)
            + (trust_ratio * 0.15)
            + (llm_ratio * 0.10)
        )

        # Cap strictly at 0.95 (AI text is never 1.0)
        final_conf = min(0.95, max(0.20, score))
        return round(final_conf, 4)
