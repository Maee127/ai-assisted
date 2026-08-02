"""
AI classification pass. Runs ONLY over comments the rules pass marked
'needs_review' -- ambiguous cases where keyword matching wasn't confident
enough. This keeps API costs proportional to actual ambiguity instead of
re-classifying everything with an LLM.

Requires ANTHROPIC_API_KEY in the environment. Uses the Anthropic Python
SDK (`pip install anthropic`).
"""
import json
import os
from datetime import datetime, timezone

import anthropic
from db import get_connection

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You classify Instagram comments under a cosmetics brand's \
posts for purchase intent. Respond ONLY with a JSON object, no other text:
{
  "is_question": true|false,
  "intent_type": "price"|"shipping"|"availability"|"product_suitability"|"purchase_location"|null,
  "product_category": string|null,
  "confidence_score": float between 0.0 and 1.0
}"""


def classify_with_ai(client: anthropic.Anthropic, text: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = response.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def run_ai_pass():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set -- required to run the AI pass.")

    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()

    ambiguous = conn.execute(
        "SELECT * FROM processed_comments WHERE validation_status = 'needs_review'"
    ).fetchall()

    stats = {"reviewed": 0, "validated": 0, "rejected": 0, "errors": 0}

    for row in ambiguous:
        try:
            result = classify_with_ai(client, row["cleaned_text"])
        except Exception as exc:  # noqa: BLE001 -- log and continue the batch
            print(f"AI classification failed for row {row['id']}: {exc}")
            stats["errors"] += 1
            continue

        confidence = float(result.get("confidence_score", 0))
        status = "validated" if confidence >= 0.75 else "rejected"
        stats[status] += 1
        stats["reviewed"] += 1

        conn.execute(
            """
            UPDATE processed_comments
            SET intent_type = ?, product_category = ?, confidence_score = ?,
                classifier_stage = 'ai', validation_status = ?, processed_at = ?
            WHERE id = ?
            """,
            (
                result.get("intent_type"), result.get("product_category"),
                confidence, status, datetime.now(timezone.utc).isoformat(),
                row["id"],
            ),
        )

    conn.commit()
    conn.close()
    return stats


if __name__ == "__main__":
    stats = run_ai_pass()
    print(f"AI pass complete: {stats}")