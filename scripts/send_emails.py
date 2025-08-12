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
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="format-detection" content="telephone=no, date=no, address=no, email=no, url=no">
    <title>Pseudosapiens Daily</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style>
        /* Reset styles */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        /* Prevent text scaling */
        body, table, td, p, a, li, blockquote {{ 
            -webkit-text-size-adjust: 100%; 
            -ms-text-size-adjust: 100%; 
        }}
        
        /* Dark mode detection and styles */
        :root {{
            color-scheme: light dark;
        }}
        
        /* Light theme (default) */
        .email-container {{
            background: #ffffff !important;
            border: 1px solid #e1e4e8 !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1) !important;
        }}
        
        .header-content {{
            background: #ffffff !important;
            border-bottom: 1px solid #e1e4e8 !important;
        }}
        
        .brand-title {{
            color: #1a1a1a !important;
        }}
        
        .reflection-subtitle {{
            color: #586069 !important;
        }}
        
        .quote-text {{
            color: #24292e !important;
        }}
        
        .footer-content {{
            background: #f6f8fa !important;
            border-top: 1px solid #e1e4e8 !important;
        }}
        
        .footer-brand {{
            color: #586069 !important;
        }}
        
        .footer-unsubscribe {{
            color: #6a737d !important;
        }}
        
        .separator-line {{
            background: linear-gradient(90deg, transparent 0%, #0366d6 20%, #0366d6 80%, transparent 100%) !important;
        }}
        
        /* Dark theme */
        @media (prefers-color-scheme: dark) {{
            body {{
                background-color: #0d1117 !important;
            }}
            
            .email-container {{
                background: #161b22 !important;
                border: 1px solid #30363d !important;
                box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
            }}
            
            .header-content {{
                background: #161b22 !important;
                border-bottom: 1px solid #30363d !important;
            }}
            
            .brand-title {{
                color: #f0f6fc !important;
            }}
            
            .reflection-subtitle {{
                color: #8b949e !important;
            }}
            
            .quote-text {{
                color: #e6edf3 !important;
            }}
            
            .footer-content {{
                background: #0d1117 !important;
                border-top: 1px solid #30363d !important;
            }}
            
            .footer-brand {{
                color: #8b949e !important;
            }}
            
            .footer-unsubscribe {{
                color: #6e7681 !important;
            }}
            
            .separator-line {{
                background: linear-gradient(90deg, transparent 0%, #58a6ff 20%, #58a6ff 80%, transparent 100%) !important;
            }}
        }}
        
        /* Mobile styles */
        @media only screen and (max-width: 600px) {{
            .email-container {{
                width: 100% !important;
                margin: 16px auto !important;
                max-width: calc(100% - 32px) !important;
            }}
            
            .header-content {{
                padding: 24px 16px 20px !important;
            }}
            
            .main-content {{
                padding: 32px 16px 24px !important;
            }}
            
            .quote-text {{
                font-size: 20px !important;
                line-height: 1.4 !important;
                max-width: 100% !important;
                letter-spacing: -0.2px !important;
            }}
            
            .brand-title {{
                font-size: 16px !important;
            }}
            
            .reflection-subtitle {{
                font-size: 12px !important;
            }}
            
            .footer-content {{
                padding: 20px 16px !important;
            }}
            
            .separator-line {{
                width: 60px !important;
            }}
        }}
        
        @media only screen and (max-width: 480px) {{
            .quote-text {{
                font-size: 18px !important;
            }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif; background-color: #f6f8fa; line-height: 1.6; width: 100%; min-height: 100vh;">
    
    <div class="email-container" style="max-width: 580px; margin: 40px auto; border-radius: 8px; overflow: hidden;">
        
        <!-- Header minimalista adaptativo -->
        <div class="header-content" style="padding: 32px 32px 24px;">
            <div style="text-align: center;">
                <h1 class="brand-title" style="margin: 0; font-size: 18px; font-weight: 600; letter-spacing: -0.2px;">
                    PSEUDOSAPIENS
                </h1>
                <p class="reflection-subtitle" style="margin: 4px 0 0; font-size: 13px; font-weight: 400; letter-spacing: 0.5px; text-transform: uppercase;">
                    #{phrase_id}
                </p>
            </div>
        </div>

        <!-- Contenido principal -->
        <div class="main-content" style="padding: 48px 24px 48px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 200px;">
            
            <!-- Frase elegante -->
            <div style="text-align: center; margin-bottom: 32px; width: 100%; max-width: 460px;">
                <blockquote style="margin: 0; padding: 0; border: none;">
                    <p class="quote-text" style="margin: 0; font-size: 26px; font-weight: 400; line-height: 1.45; font-style: italic; letter-spacing: -0.4px; text-align: center;">
                        "{phrase_text}"
                    </p>
                </blockquote>
            </div>

            <!-- Separador elegante centrado -->
            <div style="width: 80px; height: 1px; opacity: 0.6;" class="separator-line"></div>

        </div>

        <!-- Footer minimalista adaptativo -->
        <div class="footer-content" style="padding: 24px 32px;">
            <div style="text-align: center;">
                <p class="footer-unsubscribe" style="margin: 0; font-size: 11px; line-height: 1.4;">
                    Para cancelar esta suscripción, responde con "UNSUBSCRIBE"
                </p>
            </div>
        </div>

    </div>
    
</body>
</html>""".strip()


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

    subscribers: List[str] = []
    if site_id and token:
        try:
            subscribers = get_subscribers_from_netlify(form_name, site_id, token)
        except Exception as e:
            print(f"[WARN] No se pudieron obtener suscriptores de Netlify: {e}")
    else:
        print("[INFO] NETLIFY_SITE_ID o NETLIFY_ACCESS_TOKEN no configurados; 0 suscriptores.")

    subject = f"#{phrase_id} • Pseudosapiens"
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
