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
    """
    Genera HTML para email con soporte adaptativo para temas claro/oscuro.
    Compatible con Gmail, Outlook, Apple Mail y otros clientes principales.
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
    <title>Pseudosapiens #{phrase_id}</title>
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
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }}
        
        /* Light theme (default) */
        .wrapper {{ background-color: #f6f8fa !important; }}
        .container {{ background-color: #ffffff !important; }}
        .header-bg {{ background-color: #ffffff !important; border-bottom: 1px solid #e1e4e8 !important; }}
        .content-bg {{ background-color: #ffffff !important; }}
        .footer-bg {{ background-color: #f6f8fa !important; border-top: 1px solid #e1e4e8 !important; }}
        .brand-text {{ color: #1a1a1a !important; }}
        .subtitle-text {{ color: #586069 !important; }}
        .quote-text {{ color: #24292e !important; }}
        .footer-text {{ color: #6a737d !important; }}
        .separator-line {{ background: linear-gradient(90deg, transparent 0%, #0366d6 50%, transparent 100%) !important; }}
        
        /* Dark theme support */
        @media (prefers-color-scheme: dark) {{
            /* Meta color-scheme */
            :root {{ color-scheme: dark !important; }}
            
            /* Background colors */
            .wrapper {{ background-color: #0d1117 !important; }}
            .container {{ background-color: #0d1117 !important; }}
            .header-bg {{ background-color: #0d1117 !important; border-bottom: 1px solid #30363d !important; }}
            .content-bg {{ background-color: #161b22 !important; }}
            .footer-bg {{ background-color: #0d1117 !important; border-top: 1px solid #30363d !important; }}
            
            /* Text colors */
            .brand-text {{ color: #f0f6fc !important; }}
            .subtitle-text {{ color: #8b949e !important; }}
            .quote-text {{ color: #e6edf3 !important; }}
            .footer-text {{ color: #6e7681 !important; }}
            
            /* Accent colors */
            .separator-line {{ background: linear-gradient(90deg, transparent 0%, #58a6ff 50%, transparent 100%) !important; }}
            
            /* Table backgrounds for Outlook dark mode */
            table {{ background-color: transparent !important; }}
        }}
        
        /* Mobile responsive */
        @media only screen and (max-width: 600px) {{
            .container {{ width: 100% !important; max-width: 100% !important; }}
            .content-padding {{ padding: 30px 20px !important; }}
            .quote-text {{ font-size: 20px !important; line-height: 1.5 !important; }}
            .header-padding {{ padding: 25px 15px !important; }}
            .footer-padding {{ padding: 20px 15px !important; }}
        }}
        
        @media only screen and (max-width: 480px) {{
            .quote-text {{ font-size: 18px !important; }}
            .brand-text {{ font-size: 16px !important; }}
            .subtitle-text {{ font-size: 12px !important; }}
        }}
        
        /* Outlook-specific dark mode */
        [data-ogsc] .wrapper {{ background-color: #0d1117 !important; }}
        [data-ogsc] .container {{ background-color: #0d1117 !important; }}
        [data-ogsc] .content-bg {{ background-color: #161b22 !important; }}
        [data-ogsc] .brand-text {{ color: #f0f6fc !important; }}
        [data-ogsc] .quote-text {{ color: #e6edf3 !important; }}
    </style>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #24292e; background-color: #f6f8fa;">

    <!-- Hidden preheader text -->
    <div style="display: none; font-size: 1px; color: #f6f8fa; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
        {phrase_text[:90]}...
    </div>

    <!-- Wrapper Table -->
    <table class="wrapper" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f6f8fa;">
        <tr>
            <td align="center" style="padding: 20px 10px;">
                
                <!-- Container Table -->
                <table class="container" border="0" cellpadding="0" cellspacing="0" width="600" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);">
                    
                    <!-- Header -->
                    <tr>
                        <td class="header-bg header-padding" align="center" style="padding: 32px 20px 28px; background-color: #ffffff; border-bottom: 1px solid #e1e4e8;">
                            <table border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center">
                                        <h1 class="brand-text" style="margin: 0; color: #1a1a1a; font-size: 18px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase;">
                                            PSEUDOSAPIENS
                                        </h1>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-top: 6px;">
                                        <p class="subtitle-text" style="margin: 0; color: #586069; font-size: 13px; font-weight: 500; letter-spacing: 1px; text-transform: uppercase;">
                                            #{phrase_id}
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td class="content-bg content-padding" align="center" style="padding: 45px 30px; background-color: #ffffff;">
                            
                            <!-- Quote Container -->
                            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 480px;">
                                <tr>
                                    <td align="center">
                                        <!-- Left Quote Mark -->
                                        <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td align="left" width="30" valign="top" style="padding-right: 10px;">
                                                    <span class="subtitle-text" style="color: #586069; font-size: 36px; line-height: 1; font-family: Georgia, serif; opacity: 0.3;">"</span>
                                                </td>
                                                <td align="center">
                                                    <p class="quote-text" style="margin: 0; color: #24292e; font-size: 22px; line-height: 1.55; font-style: italic; font-weight: 300; font-family: Georgia, 'Times New Roman', serif;">
                                                        {phrase_text}
                                                    </p>
                                                </td>
                                                <td align="right" width="30" valign="bottom" style="padding-left: 10px;">
                                                    <span class="subtitle-text" style="color: #586069; font-size: 36px; line-height: 1; font-family: Georgia, serif; opacity: 0.3;">"</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                        </td>
                    </tr>
                    
                    <!-- Separator -->
                    <tr>
                        <td class="content-bg" align="center" style="padding: 0 30px 35px 30px; background-color: #ffffff;">
                            <table border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td width="80" height="2" class="separator-line" style="background: linear-gradient(90deg, transparent 0%, #0366d6 50%, transparent 100%); font-size: 0; line-height: 0;">
                                        &nbsp;
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td class="footer-bg footer-padding" align="center" style="padding: 24px 20px; background-color: #f6f8fa; border-top: 1px solid #e1e4e8;">
                            <table border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center">
                                        <p class="footer-text" style="margin: 0; color: #6a737d; font-size: 12px; line-height: 1.5;">
                                            Para cancelar esta suscripción, responde con<br>
                                            <strong style="color: #586069;">UNSUBSCRIBE</strong>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                </table>
                <!-- End Container -->
                
            </td>
        </tr>
    </table>
    <!-- End Wrapper -->
    
    <!-- Dark mode meta tag for Apple Mail -->
    <div style="display: none; white-space: nowrap; font: 15px courier; line-height: 0;">
        &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; 
        &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; 
        &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
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
