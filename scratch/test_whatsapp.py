import sys
import json
from backend.main import _process_whatsapp_message

phone = "573108723207" # example promoter or admin
text = "hola"
if len(sys.argv) > 1:
    phone = sys.argv[1]
if len(sys.argv) > 2:
    text = sys.argv[2]

body = {
    "entry": [{
        "changes": [{
            "value": {
                "metadata": {
                    "phone_number_id": "12345"
                },
                "messages": [{
                    "from": phone,
                    "type": "text",
                    "text": {"body": text}
                }]
            }
        }]
    }]
}

result = _process_whatsapp_message(body, dry_run=True)
print(json.dumps(result, indent=2, ensure_ascii=False))
