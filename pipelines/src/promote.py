"""
Promotion job. Copies rows from processed_comments where
validation_status = 'validated' into validated_leads, joining back to
raw_comments for the fields the outreach/review layer actually needs.

Idempotent: uses INSERT OR IGNORE keyed on raw_comment_id, so re-running
this job (e.g. on a schedule) never creates duplicate leads.
"""

from datetime import UTC, datetime

from .db import get_connection, retention_expiry


def run_promotion():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.raw_comment_id, p.cleaned_text, p.intent_type,
               p.product_category, p.confidence_score,
               r.username, r.comment_text, r.source_page, r.post_url
        FROM processed_comments p
        JOIN raw_comments r ON r.id = p.raw_comment_id
        WHERE p.validation_status = 'validated'
        """
    ).fetchall()

    promoted = 0
    for row in rows:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO validated_leads (
                raw_comment_id, username, original_comment, cleaned_question,
                intent_type, product_category, lead_score, source_page,
                post_url, validated_at, retention_expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["raw_comment_id"],
                row["username"],
                row["comment_text"],
                row["cleaned_text"],
                row["intent_type"],
                row["product_category"],
                row["confidence_score"],
                row["source_page"],
                row["post_url"],
                datetime.now(UTC).isoformat(),
                retention_expiry(),
            ),
        )
        if cur.rowcount:
            promoted += 1

    conn.commit()
    conn.close()
    return {"promoted": promoted, "candidates": len(rows)}


if __name__ == "__main__":
    stats = run_promotion()
    print(f"Promotion complete: {stats}")
