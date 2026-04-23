import requests
import json
import sys

# Agent Zero runs on 50001
AGENT_ZERO_URL = "http://localhost:50001/api/avender/chatwoot"

def send_mock_webhook(message_text, sender_id="+593999999999"):
    payload = {
        "event": "message_created",
        "content": message_text,
        "sender": {
            "identifier": sender_id,
            "name": "Cliente Prueba"
        }
    }
    
    print(f"🚀 Sending Mock Webhook: '{message_text}'")
    try:
        response = requests.post(
            AGENT_ZERO_URL, 
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ Response Status: {response.status_code}")
        print(f"📥 Response Body: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Make sure Agent Zero is running on port 50001.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        msg = sys.argv[1]
    else:
        print("Usage: python test_webhook.py 'your message here'")
        print("Example 1: python test_webhook.py 'Tienes hamburguesas dobles?'")
        print("Example 2: python test_webhook.py 'OWNER MODE'")
        sys.exit(1)
        
    send_mock_webhook(msg)
