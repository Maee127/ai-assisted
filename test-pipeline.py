"""
Simulates a batch of realistic Instagram comment webhook payloads and
runs them through the full pipeline: raw ingestion -> rules classifier
-> promotion. Used to generate real, inspectable evidence of the
pipeline working end to end.
"""

from pipelines.src.classifier import run_rules_pass
from pipelines.src.db import init_db, insert_raw_comment
from pipelines.src.promote import run_promotion

SAMPLE_COMMENTS = [
    {"username": "beauty_user22", "text": "Is this foundation suitable for oily skin?"},
    {"username": "sara_makeup", "text": "Do you ship to Berlin?"},
    {"username": "clara.b", "text": "How much is the lipstick set?"},
    {"username": "nina_glow", "text": "Where can I buy this in the US?"},
    {"username": "makeupfan99", "text": "😍😍😍 obsessed with this color"},
    {"username": "randomuser1", "text": "following you now!"},
    {"username": "j.wilson", "text": "Is it available in stock right now?"},
    {"username": "priya.k", "text": "gorgeous as always ❤️"},
    {
        "username": "beauty_user22",
        "text": "Is this foundation suitable for oily skin?",
    },  # duplicate on purpose
    {
        "username": "denise_r",
        "text": "Does this work for sensitive skin? kind of unsure about it tbh",
    },
]

IG_MEDIA_OWNER_ID = "17841400000000000"  # placeholder brand account id


def simulate_ingestion():
    for i, c in enumerate(SAMPLE_COMMENTS):
        media_id = "media_0" if i == 8 else f"media_{i}"
        result = insert_raw_comment(
            {
                "username": c["username"],
                "comment_text": c["text"],
                "source_page": "your_cosmetics_brand",
                "post_url": f"https://instagram.com/p/sample{i}",
                "ig_media_id": media_id,
                "ig_media_owner_id": IG_MEDIA_OWNER_ID,
                "source_type": "own_media",
                "comment_created_at": "2026-07-14T10:00:00+0000",
                "raw_payload": c,
            }
        )
        status = (
            "inserted" if result["inserted"] else f"skipped ({result.get('reason')})"
        )
        print(f"  [{status}] @{c['username']}: {c['text'][:50]}")


if __name__ == "__main__":
    print("== Step 1: init schema ==")
    init_db()

    print(
        "\n== Step 2: simulate 10 webhook-ingested comments (1 intentional duplicate) =="
    )
    simulate_ingestion()

    print("\n== Step 3: run rules-based classifier ==")
    stats = run_rules_pass()
    print(f"  {stats}")

    print("\n== Step 4: promote validated comments to validated_leads ==")
    promo_stats = run_promotion()
    print(f"  {promo_stats}")

    print("\nDone. Inspect data/leads.db to see the full pipeline state.")
