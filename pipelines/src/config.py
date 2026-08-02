import os

from dotenv import load_dotenv

load_dotenv()

# Database
DB_PATH = os.getenv("DB_PATH", "./data/leads.db")

# Webhook
META_APP_SECRET = os.getenv("META_APP_SECRET")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
IG_BUSINESS_ACCOUNT_ID = os.getenv("IG_BUSINESS_ACCOUNT_ID")
PORT = int(os.getenv("PORT", "3000"))

# Validate required env vars
if not all([META_APP_SECRET, WEBHOOK_VERIFY_TOKEN, IG_BUSINESS_ACCOUNT_ID]):
    raise ValueError(
        "Missing required env vars. Set META_APP_SECRET, WEBHOOK_VERIFY_TOKEN, "
        "and IG_BUSINESS_ACCOUNT_ID in .env file"
    )