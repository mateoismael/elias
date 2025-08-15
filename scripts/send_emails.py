import csv
import hashlib
import os
import sys
import requests
from datetime import datetime, timezone
from typing import List, Dict
import time

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


# Optional import: if resend is not installed, allow dry-run
try:
    import resend  # type: ignore
except Exception:  # pragma: no cover
    resend = None  # type: ignore


NETLIFY_API = "https://api.netlify.com/api/v1"


def load_phrases(csv_path: str) -> List[Dict[str, str]]:
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        phrases = [row for row in reader if row.get('text')]
    if not phrases:
        raise RuntimeError("No se encontraron frases en el CSV.")
    return phrases


def current_hour_slot() -> int:
    """Return the current UTC hour slot (epoch hours)."""
    now = datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    return epoch // 3600


def is_sending_hours() -> bool:
    """Check if current UTC time corresponds to Peru sending hours (5:00 AM - 11:59 PM PET)."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    # Peru time = UTC-5, so 5 AM PET = 10 AM UTC, 11:59 PM PET = 4:59 AM UTC (next day)
    return hour >= 10 or hour <= 4


def get_forms(site_id: str, token: str) -> List[Dict]:
    r = requests.get(
        f"{NETLIFY_API}/sites/{site_id}/forms",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_submissions(form_id: str, token: str) -> List[Dict]:
    r = requests.get(
        f"{NETLIFY_API}/forms/{form_id}/submissions",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_subscribers_from_netlify(form_name: str, site_id: str, token: str) -> List[Dict[str, str]]:
    """Get subscribers with their preferences from Netlify Forms."""
    forms = get_forms(site_id, token)
    form = next((f for f in forms if f.get('name') == form_name), None)
    if not form:
        return []
    subs = get_submissions(form.get('id'), token)
    
    # Track latest preference for each email
    email_prefs = {}
    for s in subs:
        data = s.get('data') or {}
        email = data.get('email') or data.get('Email') or data.get('correo')
        frequency = data.get('frequency', '1')  # default to every hour
        
        if email:
            email = str(email).strip()
            # Keep the latest submission for each email
            submission_time = s.get('created_at', '')
            if email not in email_prefs or submission_time > email_prefs[email]['time']:
                email_prefs[email] = {
                    'frequency': int(frequency),
                    'time': submission_time
                }
    
    # Return list of email + frequency pairs
    return [{'email': email, 'frequency': prefs['frequency']} 
            for email, prefs in email_prefs.items()]


def build_email_html(phrase_id: str, phrase_text: str) -> str:
    """
    Email ultra personal - como un mensaje de texto de un amigo.
    Sin footers corporativos ni elementos que parezcan newsletter.
    """
    
    # HTML mínimo que parece mensaje personal
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:20px;font-family:system-ui,sans-serif;line-height:1.5;color:#333">

<p style="margin:0 0 20px;font-size:16px">
Hola! Espero que tengas un buen día.
</p>

<p style="margin:20px 0;font-size:16px;color:#555">
Quería compartir esto contigo:
</p>

<p style="margin:20px 0;font-size:17px;font-style:italic;color:#444;padding:15px;background:#f8f9fa;border-left:3px solid #ddd">
{phrase_text}
</p>

<p style="margin:20px 0 5px;font-size:14px;color:#666">
Un saludo,<br>
Pseudosapiens
</p>

<p style="margin:30px 0 0;font-size:12px;color:#999">
<a href="mailto:reflexiones@pseudosapiens.com?subject=No más emails" style="color:#999">No recibir más</a>
</p>

<!-- Timestamp invisible para evitar agrupación en Gmail -->
<div style="display:none;font-size:1px;color:transparent">{int(time.time())}</div>

</body>
</html>"""
    return html


def build_email_text(phrase_text: str) -> str:
    """
    Texto plano ultra personal - como un mensaje de WhatsApp.
    """
    return f"""Hola! Espero que tengas un buen día.

Quería compartir esto contigo:

{phrase_text}

Un saludo,
Pseudosapiens

---
Si no quieres recibir más emails, solo responde "NO MÁS"

[{int(time.time())}]
"""


def send_via_resend(sender: str, to: List[str], subject: str, html: str, text: str = "") -> None:
    """
    Envia correos con Resend cumpliendo el límite de 2 req/seg y reintenta si hay 429.
    - Envia 1 correo por destinatario para preservar privacidad.
    - Usa Idempotency-Key por destinatario para evitar duplicados en reintentos.
    - Respeta header Retry-After cuando Resend devuelve 429 (Too Many Requests).
    Puedes ajustar el ritmo y reintentos con:
      RESEND_THROTTLE_SECONDS (float, por defecto 0.6s) y RESEND_MAX_RETRIES (int, por defecto 8).
    """
    api_key = os.getenv('RESEND_API_KEY')
    if not api_key:
        raise RuntimeError('Falta RESEND_API_KEY')
    if resend is None:  # pragma: no cover
        raise RuntimeError('El paquete resend no está instalado.')
    resend.api_key = api_key

    # Config de throttling y reintentos
    try:
        throttle_seconds = float(os.getenv('RESEND_THROTTLE_SECONDS', '0.6'))
    except Exception:
        throttle_seconds = 0.6
    try:
        max_retries = int(os.getenv('RESEND_MAX_RETRIES', '8'))
    except Exception:
        max_retries = 8

    slot = str(current_hour_slot())

    for recipient in to:
        # Idempotency por destinatario
        idem = hashlib.sha256((subject + "|" + slot + "|" + recipient).encode('utf-8')).hexdigest()

        attempts = 0
        while True:
            try:
                email_data = {
                    "from": sender,
                    "to": [recipient],  # Envío individual
                    "subject": subject,
                    "html": html,
                    "reply_to": "reflexiones@pseudosapiens.com",
                    "headers": {
                        "Idempotency-Key": idem,
                        "Message-ID": f"<{idem}@pseudosapiens.com>"
                    }
                }
                
                # Add text version if provided
                if text:
                    email_data["text"] = text
                
                resend.Emails.send(email_data)
                # Asegura <= 2 req/seg (0.5s); usamos 0.6s como colchón
                time.sleep(throttle_seconds)
                break
            except Exception as e:
                # Si es un 429, respetar Retry-After y reintentar
                status = None
                retry_after_s = None
                resp = getattr(e, "response", None)
                if resp is not None:
                    status = getattr(resp, "status_code", None)
                    headers = getattr(resp, "headers", {}) or {}
                    ra = headers.get("Retry-After") or headers.get("retry-after")
                    if ra:
                        try:
                            retry_after_s = int(ra)
                        except Exception:
                            retry_after_s = None

                if status == 429:
                    attempts += 1
                    if attempts > max_retries:
                        raise
                    time.sleep(retry_after_s if retry_after_s is not None else 1.5)
                    continue  # volver a intentar
                # Otros errores: propagar
                raise


def main(argv: List[str]) -> int:
    dry_run = "--dry-run" in argv
    test_mode = "--test" in argv or os.getenv('TEST_MODE', 'false').lower() == 'true'

    # Check if we're in sending hours (5:00 AM - 11:59 PM Peru time)
    if not dry_run and not is_sending_hours():
        print("[INFO] Fuera del horario de envío (5:00 AM - 11:59 PM hora de Perú). No se envían frases.")
        return 0

    # Config
    csv_path = os.getenv('PHRASES_CSV', 'frases_pilot.csv')
    form_name = os.getenv('NETLIFY_FORM_NAME', 'subscribe')
    site_id = os.getenv('NETLIFY_SITE_ID', '')
    token = os.getenv('NETLIFY_ACCESS_TOKEN', '')
    sender = os.getenv('SENDER_EMAIL', 'Frases <no-reply@example.com>')

    phrases = load_phrases(csv_path)
    # Choose a pseudo-random phrase per hour (deterministic within the hour)
    slot = current_hour_slot()
    seed_bytes = hashlib.sha256(f"{slot}:{len(phrases)}".encode('utf-8')).digest()
    seed_int = int.from_bytes(seed_bytes[:8], 'big')
    idx = seed_int % len(phrases)
    phrase = phrases[idx]
    phrase_id = phrase.get('id') or f"IDX{idx}"
    phrase_text = phrase.get('text') or ''

    all_subscribers: List[Dict[str, str]] = []
    
    # Test mode: use only test emails
    if test_mode:
        test_emails = os.getenv('TEST_EMAILS', '').split(',')
        test_emails = [email.strip() for email in test_emails if email.strip()]
        if test_emails:
            all_subscribers = [{'email': email, 'frequency': 1} for email in test_emails]
            print(f"[TEST] Usando {len(test_emails)} emails de prueba: {test_emails}")
        else:
            print("[TEST] No se encontraron TEST_EMAILS. Agrega TEST_EMAILS=tu-email@gmail.com en .env")
            return 0
    elif site_id and token:
        try:
            all_subscribers = get_subscribers_from_netlify(form_name, site_id, token)
        except Exception as e:
            print(f"[WARN] No se pudieron obtener suscriptores de Netlify: {e}")
    else:
        print("[INFO] NETLIFY_SITE_ID o NETLIFY_ACCESS_TOKEN no configurados; 0 suscriptores.")

    # Filter subscribers based on their frequency preference
    recipients = []
    for subscriber in all_subscribers:
        email = subscriber['email']
        frequency = subscriber['frequency']
        
        # Send if current hour slot is divisible by user's frequency
        if slot % frequency == 0:
            recipients.append(email)

    # Ultra personal subjects that don't sound like newsletters
    subjects = [
        "Hola",
        "Buenos días",
        "Espero estés bien", 
        "Algo que me hizo pensar",
        "Quería compartir esto contigo"
    ]
    # Choose subject based on phrase_id for consistency but avoid promotional look
    subject_index = hash(phrase_id) % len(subjects)
    subject = subjects[subject_index]
    html = build_email_html(phrase_id, phrase_text)
    text = build_email_text(phrase_text)

    if dry_run:
        print("[DRY-RUN] HourSlot:", slot, "Index:", idx)
        print(f"[DRY-RUN] Frase: {phrase_id} -> {phrase_text[:80]}{'...' if len(phrase_text)>80 else ''}")
        print(f"[DRY-RUN] Total suscriptores: {len(all_subscribers)}")
        print(f"[DRY-RUN] Filtrados para esta hora: {len(recipients)}")
        for sub in all_subscribers[:5]:  # Show first 5 for debugging
            will_receive = "SI" if slot % sub['frequency'] == 0 else "NO"
            print(f"[DRY-RUN] {sub['email']} (cada {sub['frequency']}h) {will_receive}")
        return 0

    if not recipients:
        print(f"[INFO] No hay destinatarios para esta hora (slot {slot}). {len(all_subscribers)} suscriptores totales.")
        return 0

    try:
        send_via_resend(sender, recipients, subject, html, text)
        print(f"[OK] Enviados {len(recipients)} correos de {len(all_subscribers)} suscriptores con asunto: {subject}")
        return 0
    except Exception as e:
        print("[ERROR] Falló el envío:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
