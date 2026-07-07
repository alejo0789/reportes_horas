"""
Simula un mensaje ENTRANTE de WhatsApp (webhook de Meta) contra el backend
LOCAL y dispara el envío REAL del reporte al celular indicado.

A diferencia de render_whatsapp.py (que solo llama a /api/whatsapp/query y
muestra el texto en consola), este script postea un payload de webhook a
/api/whatsapp/webhook. El backend local (tu rama actual, con cambios sin
commitear) procesa el mensaje y responde por la Graph API de Meta, así el
WhatsApp llega a tu celular real. Ideal para probar cambios antes de desplegar.

Requisitos:
  - Backend local corriendo (uvicorn) en 127.0.0.1:8032
  - WHATSAPP_TOKEN válido en .env
  - PHONE_NUMBER_ID: el "Phone number ID" del bot en Meta for Developers
    (WhatsApp > API Setup). Se pasa por argumento o variable de entorno.

Uso:
    python scratch/send_whatsapp.py <telefono> [texto] [phone_number_id]

Ejemplos:
    # Reporte general (texto "hola" -> report_type products)
    python scratch/send_whatsapp.py 573024226412 hola 123456789012345

    # Producto / Oficina
    python scratch/send_whatsapp.py 573024226412 "producto / oficina" 123456789012345

    # Usando variable de entorno para no repetir el ID
    set PHONE_NUMBER_ID=123456789012345
    python scratch/send_whatsapp.py 573024226412 hola
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error

WEBHOOK = "http://127.0.0.1:8032/api/whatsapp/webhook"

phone = sys.argv[1] if len(sys.argv) > 1 else "573024226412"
text = sys.argv[2] if len(sys.argv) > 2 else "hola"
phone_number_id = (
    sys.argv[3] if len(sys.argv) > 3 else os.getenv("PHONE_NUMBER_ID", "")
)

if not phone_number_id:
    print("ERROR: falta phone_number_id (arg 3 o variable PHONE_NUMBER_ID).")
    print("Lo obtienes en Meta for Developers > WhatsApp > API Setup > 'Phone number ID'.")
    sys.exit(1)

# Payload con la misma estructura que envía Meta a nuestro webhook.
payload = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "SIMULATED_WABA_ID",
            "changes": [
                {
                    "field": "messages",
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": phone,
                            "phone_number_id": phone_number_id,
                        },
                        "messages": [
                            {
                                "from": phone,
                                "id": f"wamid.SIM{int(time.time())}",
                                "timestamp": str(int(time.time())),
                                "type": "text",
                                "text": {"body": text},
                            }
                        ],
                    },
                }
            ],
        }
    ],
}

req = urllib.request.Request(
    WEBHOOK,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

print("=" * 50)
print(f"-> to={phone}  text={text!r}  phone_number_id={phone_number_id}")
print("=" * 50)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        print(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"HTTPError {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
