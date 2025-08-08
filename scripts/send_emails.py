import csv
import hashlib
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict

import requests

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


def get_subscribers_from_netlify(form_name: str, site_id: str, token: str) -> List[str]:
    forms = get_forms(site_id, token)
    form = next((f for f in forms if f.get('name') == form_name), None)
    if not form:
        return []
    subs = get_submissions(form.get('id'), token)
    emails = []
    for s in subs:
        data = s.get('data') or {}
        email = data.get('email') or data.get('Email') or data.get('correo')
        if email:
            emails.append(str(email).strip())
    # unique preserving order
    seen = set()
    uniq = []
    for e in emails:
        if e and e not in seen:
            seen.add(e)
            uniq.append(e)
    return uniq


def build_email_html(phrase_id: str, phrase_text: str) -> str:
    return f"""
    <div style='font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height:1.6'>
      <h2 style='margin:0 0 12px'>Frase motivacional</h2>
      <blockquote style='margin:12px 0; padding:12px 16px; border-left:4px solid #4f46e5; background:#f6f6ff'>
        <p style='margin:0; font-size:16px'>{phrase_text}</p>
        <small style='opacity:.7'>ID: {phrase_id}</small>
      </blockquote>
      <p style='font-size:12px; color:#666'>
        Recibes este correo porque te suscribiste en nuestro formulario.
        Para dejar de recibir, responde a este correo con "UNSUBSCRIBE".
      </p>
    </div>
    """.strip()


def send_via_resend(sender: str, to: List[str], subject: str, html: str) -> None:
    api_key = os.getenv('RESEND_API_KEY')
    if not api_key:
        raise RuntimeError('Falta RESEND_API_KEY')
    if resend is None:  # pragma: no cover
        raise RuntimeError('El paquete resend no está instalado.')
    resend.api_key = api_key
    # Use an idempotency key to reduce duplicates within the same hour
    slot = str(current_hour_slot())
    idem = hashlib.sha256((subject + "|" + slot).encode('utf-8')).hexdigest()
    # Some SDKs support idempotency_key in headers or params; the Python SDK accepts it in send options via headers.
    # If not supported, Resend ignores it.
    resend.Emails.send({
        "from": sender,
        "to": to,
        "subject": subject,
        "html": html,
        "headers": {"Idempotency-Key": idem}
    })


def main(argv: List[str]) -> int:
    dry_run = "--dry-run" in argv

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

    subscribers: List[str] = []
    if site_id and token:
        try:
            subscribers = get_subscribers_from_netlify(form_name, site_id, token)
        except Exception as e:
            print(f"[WARN] No se pudieron obtener suscriptores de Netlify: {e}")
    else:
        print("[INFO] NETLIFY_SITE_ID o NETLIFY_ACCESS_TOKEN no configurados; 0 suscriptores.")

    subject = f"Tu frase motivacional ({phrase_id})"
    html = build_email_html(phrase_id, phrase_text)

    if dry_run:
        print("[DRY-RUN] HourSlot:", slot, "Index:", idx)
        print(f"[DRY-RUN] Frase: {phrase_id} -> {phrase_text[:80]}{'...' if len(phrase_text)>80 else ''}")
        print("[DRY-RUN] Suscriptores:", subscribers)
        return 0

    if not subscribers:
        print("[INFO] No hay suscriptores. Nada que enviar.")
        return 0

    try:
        send_via_resend(sender, subscribers, subject, html)
        print(f"[OK] Enviados {len(subscribers)} correos: {phrase_id}")
        return 0
    except Exception as e:
        print("[ERROR] Falló el envío:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
