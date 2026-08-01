"""
Rules-based classification pass. Runs over raw_comments with
processing_status = 'pending', writes results to processed_comments.

Comments the rules classify with high confidence are marked 'validated'
directly. Ambiguous ones are marked 'needs_review' so the AI pass
(ai_classifier.py) only spends API calls on the comments that need it.
"""
import re
from datetime import datetime, timezone

from db import get_connection

# Keyword patterns per intent type. Deliberately simple and inspectable --
# this is the layer a non-ML reviewer can audit line by line.
INTENT_PATTERNS = {
    "price": [r"\bhow much\b", r"\bprice\b", r"\bcost\b", r"\bkosten\b"],
    "shipping": [r"\bship(ping)?\b", r"\bdeliver(y|s)?\b", r"\bversand\b"],
    "availability": [r"\bin stock\b", r"\bavailable\b", r"\bsold out\b"],
    "product_suitability": [
        r"\bsuitable for\b", r"\bgood for\b", r"\bwork(s)? for\b",
        r"\bsensitive skin\b", r"\boily skin\b", r"\bdry skin\b",
    ],
    "purchase_location": [r"\bwhere (can|do) i buy\b", r"\bwhere to buy\b", r"\bwhich store\b"],
}

QUESTION_MARKERS = ("?", "how", "where", "do you", "is this", "can i", "does this")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def looks_like_question(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in QUESTION_MARKERS)


def classify_intent(text: str):
    """Returns (intent_type, matched_patterns_count) or (None, 0)."""
    lowered = text.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        matches = sum(1 for p in patterns if re.search(p, lowered))
        if matches > 0:
            return intent, matches
    return None, 0


def score_confidence(is_question: bool, intent_type: str, match_count: int) -> float:
    if not is_question or not intent_type:
        return 0.0
    # Simple, auditable scoring: base score for an intent match, bonus
    # per additional matched pattern, capped at 0.95 (rules alone never
    # claim full certainty -- that's reserved for reviewed/validated data).
    base = 0.6
    bonus = min(0.15 * (match_count - 1), 0.3)
    return round(min(base + bonus, 0.95), 2)


def run_rules_pass():
    conn = get_connection()
    pending = conn.execute(
        "SELECT * FROM raw_comments WHERE processing_status = 'pending'"
    ).fetchall()

    results = {"processed": 0, "validated": 0, "needs_review": 0, "rejected": 0}

    for row in pending:
        text = clean_text(row["comment_text"])
        is_q = looks_like_question(text)
        intent, match_count = classify_intent(text)
        confidence = score_confidence(is_q, intent, match_count)

        if not is_q or not intent:
            validation_status = "rejected"
            results["rejected"] += 1
        elif confidence >= 0.75:
            validation_status = "validated"
            results["validated"] += 1
        else:
            validation_status = "needs_review"
            results["needs_review"] += 1

        conn.execute(
            """
            INSERT INTO processed_comments (
                raw_comment_id, cleaned_text, detected_language, is_question,
                is_relevant, intent_type, product_category, confidence_score,
                classifier_stage, validation_status, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"], text, "en", int(is_q), int(bool(intent)),
                intent, None, confidence, "rules", validation_status,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.execute(
            "UPDATE raw_comments SET processing_status = 'processed' WHERE id = ?",
            (row["id"],),
        )
        results["processed"] += 1

    conn.commit()
    conn.close()
    return results


if __name__ == "__main__":
    stats = run_rules_pass()
    print(f"Rules pass complete: {stats}")