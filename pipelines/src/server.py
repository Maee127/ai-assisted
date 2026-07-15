import os
import hashlib
import hmac
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import META_APP_SECRET, WEBHOOK_VERIFY_TOKEN, IG_BUSINESS_ACCOUNT_ID, PORT
from database import Database

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize database
db = Database(os.getenv("DB_PATH", "./data/leads.db"))

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        'service': 'Instagram Lead Collector Webhook',
        'status': 'running',
        'endpoints': {
            '/health': 'GET - Health check',
            '/webhook': 'GET - Webhook verification, POST - Webhook events'
        }
    })

def is_valid_signature(request) -> bool:
    """Verify webhook signature"""
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature or not request.data:
        return False
    
    expected = "sha256=" + hmac.new(
        META_APP_SECRET.encode(),
        request.data,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

def ingest_comment(value: dict, source_type: str):
    """Process incoming comment"""
    if not value or not value.get('text'):
        return
    
    result = db.insert_raw_comment({
        'username': value.get('from', {}).get('username'),
        'comment_text': value.get('text', ''),
        'source_page': value.get('media', {}).get('username'),
        'post_url': value.get('media', {}).get('permalink'),
        'ig_media_id': value.get('media', {}).get('id'),
        'ig_media_owner_id': IG_BUSINESS_ACCOUNT_ID,
        'source_type': source_type,
        'comment_created_at': value.get('timestamp'),
        'raw_payload': value,
    })
    
    if result['inserted']:
        logger.info(f"Ingested {source_type} comment (row {result['id']}) from @{value.get('from', {}).get('username')}")
    else:
        logger.info(f"Skipped duplicate comment from @{value.get('from', {}).get('username')}")

def handle_webhook_body(body: dict):
    """Parse webhook payload"""
    if body.get('object') != 'instagram':
        return
    
    for entry in body.get('entry', []):
        for change in entry.get('changes', []):
            field = change.get('field')
            value = change.get('value', {})
            
            if field == 'comments':
                ingest_comment(value, 'own_media')
            elif field == 'mentions':
                ingest_comment(value, 'mention')

@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """Webhook verification handshake"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return challenge, 200
    
    return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def webhook_receive():
    """Receive webhook events"""
    if not is_valid_signature(request):
        logger.warning("Rejected webhook: invalid signature")
        return 'Forbidden', 403
    
    try:
        handle_webhook_body(request.json)
    except Exception as e:
        logger.error(f"Error processing webhook payload: {e}", exc_info=True)
    
    return 'EVENT_RECEIVED', 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    logger.info(f"Webhook receiver listening on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)