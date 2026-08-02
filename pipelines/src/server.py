"""
Webhook receiver for Instagram comment and mention events.
Verifies Meta's signature on every request before touching the database.
"""

import hashlib
import hmac
import os

from flask import Flask, request

from .db import init_db, insert_raw_comment

META_APP_SECRET = os.environ.get("META_APP_SECRET")
WEBHOOK_VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN")
IG_BUSINESS_ACCOUNT_ID = os.environ.get("IG_BUSINESS_ACCOUNT_ID")

if not all([META_APP_SECRET, WEBHOOK_VERIFY_TOKEN, IG_BUSINESS_ACCOUNT_ID]):
    raise SystemExit(
        "Missing required env vars: META_APP_SECRET, WEBHOOK_VERIFY_TOKEN, "
        "IG_BUSINESS_ACCOUNT_ID. Copy .env.example to .env and fill them in."
    )

app = Flask(__name__)
init_db()


@app.get("/webhook")
def verify_webhook():
    """Handshake Meta performs once when you register the webhook URL."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        return challenge, 200
    return "", 403


def is_valid_signature(raw_body: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False

    assert META_APP_SECRET is not None
    expected = (
        "sha256="
        + hmac.new(
            META_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
    )
    return hmac.compare_digest(signature_header, expected)


@app.post("/webhook")
def receive_webhook():
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not is_valid_signature(request.get_data(), signature):
        return "", 403

    body = request.get_json(silent=True) or {}
    # Respond fast; Meta retries on timeout. Processing is cheap (SQLite
    # insert) so it's fine to do inline here.
    handle_webhook_body(body)
    return "EVENT_RECEIVED", 200


def handle_webhook_body(body: dict):
    if body.get("object") != "instagram":
        return
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            field = change.get("field")
            if field == "comments":
                ingest_comment(change.get("value", {}), "own_media")
            elif field == "mentions":
                ingest_comment(change.get("value", {}), "mention")


def ingest_comment(value: dict, source_type: str):
    if not value or not value.get("text"):
        return
    media = value.get("media", {}) or {}
    result = insert_raw_comment(
        {
            "username": (value.get("from") or {}).get("username"),
            "comment_text": value.get("text"),
            "source_page": media.get("username"),
            "post_url": media.get("permalink"),
            "ig_media_id": media.get("id"),
            "ig_media_owner_id": IG_BUSINESS_ACCOUNT_ID,
            "source_type": source_type,
            "comment_created_at": value.get("timestamp"),
            "raw_payload": value,
        }
    )
    if result["inserted"]:
        print(f"Ingested {source_type} comment (row {result['id']})")
    else:
        print("Skipped duplicate comment")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
