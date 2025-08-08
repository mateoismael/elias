import csv
import hashlib
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict

try:
    import resend  # type: ignore
except Exception:
    resend = None  # type: ignore


def load_phrases(csv_path: str) -> List[Dict[str, str]]:
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader if row.get('text')]
    if not rows:
        raise RuntimeError('No se encontraron frases en el CSV.')
    return rows


def current_slot_by_seconds(period_seconds: int) -> int:
    now = datetime.now(timezone.utc)
    return int(now.timestamp()) // max(1, period_seconds)


def build_email_html(phrase_id: str, phrase_text: str) -> str:
    return f"""
    <div style='font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height:1.6'>
      <h2 style='margin:0 0 12px'>[PRUEBA] Frase motivacional</h2>
      <blockquote style='margin:12px 0; padding:12px 16px; border-left:4px solid #4f46e5; background:#f6f6ff'>
        <p style='margin:0; font-size:16px'>{phrase_text}</p>
        <small style='opacity:.7'>ID: {phrase_id}</small>
      </blockquote>
      <p style='font-size:12px; color:#666'>
        Este es un envío de prueba.
      </p>
    </div>
    """.strip()


def send_via_resend(sender: str, to: List[str], subject: str, html: str) -> None:
    api_key = os.getenv('RESEND_API_KEY')
    if not api_key:
        raise RuntimeError('Falta RESEND_API_KEY')
    if resend is None:
        raise RuntimeError('El paquete resend no está instalado.')
    resend.api_key = api_key
    idem = hashlib.sha256((subject + ''.join(to)).encode('utf-8')).hexdigest()
    resend.Emails.send({
        'from': sender,
        'to': to,
        'subject': subject,
        'html': html,
        'headers': {'Idempotency-Key': idem},
    })


def main(argv: List[str]) -> int:
    csv_path = os.getenv('PHRASES_CSV', 'frases_pilot.csv')
    period_seconds = int(os.getenv('PERIOD_SECONDS', '10'))
    sender = os.getenv('SENDER_EMAIL', 'Frases <no-reply@example.com>')
    recipients_csv = os.getenv('TEST_RECIPIENTS', '')

    if not recipients_csv:
        print('[ERROR] TEST_RECIPIENTS vacío.');
        return 2

    recipients = [e.strip() for e in recipients_csv.split(',') if e.strip()]
    if not recipients:
        print('[ERROR] TEST_RECIPIENTS no contiene emails válidos.')
        return 2

    phrases = load_phrases(csv_path)
    slot = current_slot_by_seconds(period_seconds)
    idx = slot % len(phrases)
    phrase = phrases[idx]

    phrase_id = phrase.get('id') or f'IDX{idx}'
    phrase_text = phrase.get('text') or ''

    subject_prefix = os.getenv('SUBJECT_PREFIX', '[TEST] ')
    subject = f"{subject_prefix}Tu frase motivacional ({phrase_id})"
    html = build_email_html(phrase_id, phrase_text)

    try:
        send_via_resend(sender, recipients, subject, html)
        print(f"[OK] Prueba enviada a {len(recipients)} destinatario(s): {phrase_id}")
        return 0
    except Exception as e:
        print('[ERROR] Falló el envío de prueba:', e)
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
