import csv
import hashlib
import os
import sys
import requests
from datetime import datetime, timezone
from typing import List, Dict
import time


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
    Versión ultra minimalista para evitar el problema de 'texto citado' en Gmail.
    Mantiene el diseño pero con mínimo código.
    """
    
    # Detectar hora para tema (6 AM - 6 PM = claro, resto = oscuro)
    from datetime import datetime
    hour = datetime.now().hour
    is_dark = hour >= 18 or hour < 6
    
    # Colores según tema
    if is_dark:
        bg = "#0d1117"
        card = "#161b22"
        text = "#e6edf3"
        muted = "#8b949e"
        border = "#30363d"
    else:
        bg = "#f6f8fa"
        card = "#ffffff"
        text = "#24292e"
        muted = "#586069"
        border = "#e1e4e8"
    
    # HTML ultra minimalista - sin CSS innecesario
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>P</title>
</head>
<body style="margin:0;padding:20px;background:{bg};font-family:-apple-system,system-ui,sans-serif">
<table align="center" width="100%" style="max-width:600px">
<tr><td style="background:{card};border-radius:8px;border:1px solid {border}">
<div style="padding:30px 20px;text-align:center;border-bottom:1px solid {border}">
<h1 style="margin:0;color:{text};font-size:18px;letter-spacing:2px">PSEUDOSAPIENS</h1>
<p style="margin:5px 0 0;color:{muted};font-size:13px">#{phrase_id}</p>
</div>
<div style="padding:40px 30px;text-align:center">
<p style="color:{text};font-size:22px;line-height:1.5;font-style:italic;margin:0">"{phrase_text}"</p>
</div>
<div style="padding:20px;text-align:center;border-top:1px solid {border}">
<p style="margin:0;color:{muted};font-size:11px">
<a href="https://pseudosapiens.com/preferences" style="color:{muted};text-decoration:none">Gestionar preferencias</a> | 
<a href="mailto:noreply@pseudosapiens.com?subject=UNSUBSCRIBE" style="color:{muted};text-decoration:none">Desuscribirse</a>
</p>
</div>
</td></tr>
</table>
</body>
</html>"""
    return html + f"\n<!-- build:{int(time.time())} -->"


def send_via_resend(sender: str, to: List[str], subject: str, html: str) -> None:
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
                resend.Emails.send({
                    "from": sender,
                    "to": [recipient],  # Envío individual
                    "subject": subject,
                    "html": html,
                    "headers": {"Idempotency-Key": idem}
                })
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
    if site_id and token:
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

    subject = f"Frase #{phrase_id} • Pseudosapiens"
    html = build_email_html(phrase_id, phrase_text)

    if dry_run:
        print("[DRY-RUN] HourSlot:", slot, "Index:", idx)
        print(f"[DRY-RUN] Frase: {phrase_id} -> {phrase_text[:80]}{'...' if len(phrase_text)>80 else ''}")
        print(f"[DRY-RUN] Total suscriptores: {len(all_subscribers)}")
        print(f"[DRY-RUN] Filtrados para esta hora: {len(recipients)}")
        for sub in all_subscribers[:5]:  # Show first 5 for debugging
            will_receive = "✓" if slot % sub['frequency'] == 0 else "✗"
            print(f"[DRY-RUN] {sub['email']} (cada {sub['frequency']}h) {will_receive}")
        return 0

    if not recipients:
        print(f"[INFO] No hay destinatarios para esta hora (slot {slot}). {len(all_subscribers)} suscriptores totales.")
        return 0

    try:
        send_via_resend(sender, recipients, subject, html)
        print(f"[OK] Enviados {len(recipients)} correos de {len(all_subscribers)} suscriptores: {phrase_id}")
        return 0
    except Exception as e:
        print("[ERROR] Falló el envío:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
