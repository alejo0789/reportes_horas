"""
Simula el flujo COMPLETO del webhook de WhatsApp y muestra los mensajes que se
enviarian, sin enviar nada por Meta.

Postea un mensaje entrante al webhook con ?dry_run=1, de modo que el backend
ejecuta TODA la logica real (deteccion de primer contacto del dia via
is_first_session_of_day, ruteo por rol, recopilatorio de ayer, botones) pero en
vez de responder por la Graph API devuelve los mensajes compuestos, que aqui se
imprimen con los saltos de linea reales.

Ojo: como corre la logica real, el backend REGISTRA el primer contacto en la
tabla whatsapp_user_requests. Por eso la primera corrida del dia muestra el
recopilatorio de ayer + reporte de hoy, y las siguientes (pasada la ventana de
180 s) muestran solo el reporte de hoy. Para volver a ver el primer contacto,
resetea la fila del telefono en uploads/cache.db.

Uso:
    python scratch/render_whatsapp.py 573024226412 hola
    python scratch/render_whatsapp.py 573024226412 "producto / oficina"
"""
import sys
import json
import time
import urllib.request
import urllib.error

WEBHOOK = "http://127.0.0.1:8032/api/whatsapp/webhook?dry_run=1"

phone = sys.argv[1] if len(sys.argv) > 1 else "573024226412"
text = sys.argv[2] if len(sys.argv) > 2 else "hola"

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
                            "phone_number_id": "DRY_RUN",
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

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"HTTPError {e.code}: {e.read().decode('utf-8')}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

if data.get("status") != "dry_run":
    print("Respuesta inesperada (el backend no esta en modo dry_run):")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

messages = data.get("messages", [])
print("#" * 60)
print(f"# phone={phone}  texto={text!r}  -> {len(messages)} mensaje(s)")
print("#" * 60)
print()
for i, m in enumerate(messages, 1):
    print("=" * 60)
    print(f"MENSAJE {i}/{len(messages)}  [{m.get('label', m.get('kind'))}]")
    print("=" * 60)
    print(m.get("text", "(sin texto)"))
    if m.get("kind") == "interactive":
        print("-" * 60)
        print("Botones: " + " | ".join(m.get("buttons", [])))
    print()
