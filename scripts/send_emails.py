import csv
import hashlib
import os
import sys
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Literal
from dataclasses import dataclass, field
from enum import IntEnum
import time
import secrets
import hmac
import logging
import structlog
from pathlib import Path

# Import Supabase database module
try:
    from database import get_db
except ImportError:
    get_db = None
    print("[WARN] Database module not found. Supabase integration disabled.")

try:
    from pydantic import BaseModel, EmailStr, field_validator, Field
except ImportError:
    print("[WARN] Pydantic not installed. Install with: pip install pydantic[email]")
    BaseModel = object
    EmailStr = str
    field_validator = lambda x: lambda y: y
    Field = lambda **kwargs: None

# Configure structured logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("dotenv not installed - environment variables from shell only")


# Optional import: if resend is not installed, allow dry-run
try:
    import resend  # type: ignore
except ImportError as e:
    logger.warning("Resend not installed - dry-run only", error=str(e))
    resend = None  # type: ignore


NETLIFY_API = "https://api.netlify.com/api/v1"


# =============================================================================
# CONFIGURATION MODELS (Dataclasses & Pydantic)
# =============================================================================

class FrequencyEnum(IntEnum):
    """Valid email frequencies - NEW 2025 MODEL (Plan ID = Emails por día)."""
    HOURLY = 1  # Plan 13 - Power User (13/día, manual/VIP)
    EVERY_6_HOURS = 6  # Plan 4 - Premium (4/día)
    THREE_DAILY = 8  # Plan 3 - Premium (3/día)
    TWICE_DAILY = 12  # Plan 2 - Premium (2/día)
    DAILY = 24  # Plan 1 - Premium (1/día)
    FREE_WEEKLY_3 = 56  # Plan 0 - Gratuito (3/semana L-M-V)
    
    # Deprecated values (mantener para compatibilidad)
    EVERY_3_HOURS = 3  # Legacy
    FLOW_STATE = 4  # Legacy


@dataclass(frozen=True)
class EmailConfig:
    """Email service configuration."""
    api_key: str
    sender_email: str
    throttle_seconds: float = 0.6
    max_retries: int = 8
    
    @classmethod
    def from_env(cls) -> 'EmailConfig':
        """Create configuration from environment variables."""
        api_key = os.getenv('RESEND_API_KEY')
        if not api_key:
            raise ValueError("RESEND_API_KEY environment variable is required")
            
        sender = os.getenv('SENDER_EMAIL', 'Frases <no-reply@example.com>')
        throttle = float(os.getenv('RESEND_THROTTLE_SECONDS', '0.6'))
        retries = int(os.getenv('RESEND_MAX_RETRIES', '8'))
        
        return cls(
            api_key=api_key,
            sender_email=sender,
            throttle_seconds=throttle,
            max_retries=retries
        )


@dataclass(frozen=True)
class NetlifyConfig:
    """Netlify Forms configuration."""
    site_id: str
    access_token: str
    form_name: str = 'subscribe'
    
    @classmethod
    def from_env(cls) -> 'NetlifyConfig':
        """Create configuration from environment variables."""
        site_id = os.getenv('NETLIFY_SITE_ID', '')
        token = os.getenv('NETLIFY_ACCESS_TOKEN', '')
        form_name = os.getenv('NETLIFY_FORM_NAME', 'subscribe')
        
        return cls(
            site_id=site_id,
            access_token=token,
            form_name=form_name
        )


class Subscriber(BaseModel):
    """Validated subscriber model."""
    email: EmailStr
    frequency: FrequencyEnum = Field(default=FrequencyEnum.HOURLY, description="Email frequency in hours")
    
    @field_validator('frequency', mode='before')
    @classmethod
    def validate_frequency(cls, v):
        """Convert and validate frequency values."""
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                raise ValueError(f"Invalid frequency: {v}")
        
        if v not in [1, 6, 8, 12, 24, 56]:  # NEW 2025 MODEL values
            raise ValueError(f"Frequency must be 1, 6, 8, 12, 24, or 56 (new model), got: {v}")
        
        return FrequencyEnum(v)


class Phrase(BaseModel):
    """Validated phrase model."""
    id: str
    text: str = Field(min_length=1, description="Phrase content")
    author: str = Field(description="Author of the phrase")
    
    @field_validator('text')
    @classmethod
    def validate_text_not_empty(cls, v):
        """Ensure phrase text is not just whitespace."""
        if not v.strip():
            raise ValueError("Phrase text cannot be empty or just whitespace")
        return v.strip()
    
    @field_validator('author')
    @classmethod
    def validate_author_not_empty(cls, v):
        """Ensure author is not empty."""
        if not v or not v.strip():
            raise ValueError("Author cannot be empty or just whitespace")
        return v.strip()


class EmailContent(BaseModel):
    """Email content with context."""
    recipient: Subscriber
    phrase: Phrase
    subject: str
    html: str
    text: str
    unique_timestamp: int


# =============================================================================
# CORE BUSINESS LOGIC
# =============================================================================

def generate_unsubscribe_token(email: str) -> str:
    """
    Genera un token seguro para desuscripción.
    Combina email + timestamp + secret para crear un token único y verificable.
    """
    # Usar una clave secreta del entorno o generar una por defecto
    secret_key = os.getenv('UNSUBSCRIBE_SECRET', 'pseudosapiens-default-secret-2025')
    
    # Timestamp actual (válido por 30 días)
    timestamp = str(int(time.time()))
    
    # Datos a firmar
    message = f"{email}:{timestamp}"
    
    # Generar HMAC
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Token final: timestamp:signature
    return f"{timestamp}:{signature}"

def validate_unsubscribe_token(email: str, token: str) -> bool:
    """
    Valida si un token de desuscripción es válido y no ha expirado.
    """
    try:
        # Separar timestamp y signature
        timestamp_str, signature = token.split(':', 1)
        timestamp = int(timestamp_str)
        
        # Verificar que no haya expirado (30 días = 2592000 segundos)
        current_time = int(time.time())
        if current_time - timestamp > 2592000:  # 30 días
            return False
        
        # Regenerar el token esperado
        expected_token = generate_unsubscribe_token(email)
        expected_timestamp, expected_signature = expected_token.split(':', 1)
        
        # Comparar signatures de forma segura (no el timestamp, que será diferente)
        secret_key = os.getenv('UNSUBSCRIBE_SECRET', 'pseudosapiens-default-secret-2025')
        message = f"{email}:{timestamp_str}"
        expected_sig = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_sig)
        
    except (ValueError, IndexError):
        return False


# CSV loading functions removed - now using Supabase only
# See scripts/database_phrases.py for phrase loading functions


def current_hour_slot() -> int:
    """Return the current UTC hour slot (epoch hours)."""
    now = datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    return epoch // 3600


def get_optimal_send_hours(frequency: int) -> List[int]:
    """
    Return optimal sending hours for NEW 2025 MODEL (Deliverability-Safe).
    Returns list of hours (0-23) in UTC.
    
    NUEVO MODELO (Plan ID = Emails por día):
    - 56: Plan 0 - Gratuito (3/semana L-M-V, 8:00)
    - 24: Plan 1 - Premium 1/día (8:00)
    - 12: Plan 2 - Premium 2/día (8:00, 17:00)
    - 8: Plan 3 - Premium 3/día (8:00, 14:00, 20:00)
    - 6: Plan 4 - Premium 4/día (8:00, 12:00, 17:00, 21:00)
    - 1: Plan 13 - Power User 13/día (cada hora 8:00-20:00)
    """
    # Convert Peru time to UTC (Peru = UTC-5)
    
    if frequency == 56:  # Plan gratuito (3 por semana L-M-V)
        # Solo Lunes-Miércoles-Viernes a las 8:00 AM Peru = 13:00 UTC
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        weekday = now_utc.weekday()  # 0=Monday, 1=Tuesday, 2=Wednesday, 6=Sunday
        
        if weekday in [0, 2, 4]:  # Monday, Wednesday, Friday
            return [13]  # 8:00 AM Peru = 13:00 UTC
        else:
            return []  # No envíos otros días
    
    elif frequency == 24:  # Plan 1 - Premium 1/día
        return [13]  # 8:00 Peru = 13:00 UTC
    
    elif frequency == 12:  # Plan 2 - Premium 2/día 
        return [13, 22]  # 8:00, 17:00 Peru = 13:00, 22:00 UTC
    
    elif frequency == 8:  # Plan 3 - Premium 3/día
        return [13, 19, 1]  # 8:00, 14:00, 20:00 Peru = 13:00, 19:00, 01:00 UTC
    
    elif frequency == 6:  # Plan 4 - Premium 4/día
        return [13, 17, 22, 2]  # 8:00, 12:00, 17:00, 21:00 Peru = 13:00, 17:00, 22:00, 02:00 UTC
    
    elif frequency == 1:  # Plan 13 - Power User 13/día (manual/VIP)
        # 8:00-20:00 Peru (13 horas) = 13:00-01:00 UTC (next day)  
        return list(range(13, 24)) + list(range(0, 2))  # 13-23 UTC + 0-1 UTC (total: 13 horas)
    
    else:
        # Default: plan gratuito para frecuencias no reconocidas
        logger.warning("Unknown frequency in get_optimal_send_hours, defaulting to free plan", frequency=frequency)
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        weekday = now_utc.weekday()
        if weekday in [0, 2, 4]:  # L-M-V
            return [13]
        else:
            return []


def should_send_at_current_hour(frequency: int) -> bool:
    """
    Check if email should be sent at current UTC hour based on NEW 2025 MODEL.
    Includes day-of-week logic for free plan (L-M-V only).
    """
    now = datetime.now(timezone.utc)
    current_utc_hour = now.hour
    
    optimal_hours = get_optimal_send_hours(frequency)
    result = current_utc_hour in optimal_hours
    
    # Extra logging for debugging new model
    if result:
        logger.debug("Should send email", 
                    frequency=frequency, 
                    current_utc_hour=current_utc_hour,
                    optimal_hours=optimal_hours,
                    weekday=now.weekday())
    
    return result


def is_sending_hours() -> bool:
    """Check if current UTC time corresponds to Peru sending hours (5:00 AM - 11:59 PM PET)."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    # Peru time = UTC-5, so 5 AM PET = 10 AM UTC, 11:59 PM PET = 4:59 AM UTC (next day)
    return hour >= 10 or hour <= 4


def get_forms(site_id: str, token: str) -> List[Dict[str, any]]:
    """Fetch forms from Netlify with proper error handling."""
    try:
        response = requests.get(
            f"{NETLIFY_API}/sites/{site_id}/forms",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("Netlify API timeout getting forms", site_id=site_id)
        raise
    except requests.exceptions.HTTPError as e:
        logger.error("Netlify API HTTP error getting forms", 
                    site_id=site_id, status_code=e.response.status_code)
        raise
    except requests.exceptions.ConnectionError:
        logger.error("Netlify API connection error getting forms", site_id=site_id)
        raise


def get_submissions(form_id: str, token: str) -> List[Dict[str, any]]:
    """Fetch form submissions from Netlify with proper error handling."""
    try:
        response = requests.get(
            f"{NETLIFY_API}/forms/{form_id}/submissions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("Netlify API timeout getting submissions", form_id=form_id)
        raise
    except requests.exceptions.HTTPError as e:
        logger.error("Netlify API HTTP error getting submissions", 
                    form_id=form_id, status_code=e.response.status_code)
        raise
    except requests.exceptions.ConnectionError:
        logger.error("Netlify API connection error getting submissions", form_id=form_id)
        raise


def get_subscribers_from_netlify(netlify_config: NetlifyConfig) -> List[Subscriber]:
    """Get subscribers with their preferences from Netlify Forms."""
    try:
        forms = get_forms(netlify_config.site_id, netlify_config.access_token)
        form = next((f for f in forms if f.get('name') == netlify_config.form_name), None)
        if not form:
            logger.warning("Form not found", form_name=netlify_config.form_name)
            return []
        
        submissions = get_submissions(form.get('id'), netlify_config.access_token)
        
        # Track latest preference for each email
        email_prefs = {}
        invalid_emails = 0
        
        for submission in submissions:
            data = submission.get('data') or {}
            email = data.get('email') or data.get('Email') or data.get('correo')
            frequency = data.get('frequency', '1')  # default to every hour
            
            if email:
                email = str(email).strip()
                # Keep the latest submission for each email
                submission_time = submission.get('created_at', '')
                if email not in email_prefs or submission_time > email_prefs[email]['time']:
                    email_prefs[email] = {
                        'frequency': int(frequency),
                        'time': submission_time
                    }
        
        # Convert to validated Subscriber objects
        subscribers = []
        for email, prefs in email_prefs.items():
            try:
                subscriber = Subscriber(
                    email=email,
                    frequency=prefs['frequency']
                )
                subscribers.append(subscriber)
            except Exception as e:
                logger.warning("Invalid subscriber data", email=email, error=str(e))
                invalid_emails += 1
                continue
        
        logger.info("Subscribers loaded from Netlify", 
                   valid_count=len(subscribers), 
                   invalid_count=invalid_emails,
                   form_name=netlify_config.form_name)
        
        return subscribers
        
    except Exception as e:
        logger.error("Failed to get subscribers from Netlify", error=str(e))
        return []


def get_subscribers_from_supabase() -> List[Subscriber]:
    """Get active subscribers from Supabase database."""
    if get_db is None:
        logger.error("Supabase database module not available")
        return []
    
    try:
        db = get_db()
        
        # Get all active subscribers with their plan details
        subscribers_data = db.get_all_active_subscribers()
        
        subscribers = []
        invalid_count = 0
        
        for sub_data in subscribers_data:
            try:
                # Map frequency hours to FrequencyEnum (NEW 2025 MODEL - Plan ID = Emails por día)
                frequency_hours = sub_data['frequency_hours']
                if frequency_hours == 56:  # Plan 0 - Gratuito (3/semana L-M-V)
                    frequency = FrequencyEnum.FREE_WEEKLY_3
                elif frequency_hours == 24:  # Plan 1 - Premium 1/día
                    frequency = FrequencyEnum.DAILY
                elif frequency_hours == 12:  # Plan 2 - Premium 2/día
                    frequency = FrequencyEnum.TWICE_DAILY
                elif frequency_hours == 8:  # Plan 3 - Premium 3/día
                    frequency = FrequencyEnum.THREE_DAILY
                elif frequency_hours == 6:  # Plan 4 - Premium 4/día
                    frequency = FrequencyEnum.EVERY_6_HOURS
                elif frequency_hours == 1:  # Plan 13 - Power User (13/día manual/VIP)
                    frequency = FrequencyEnum.HOURLY
                else:
                    logger.warning("Unknown frequency, defaulting to free plan", 
                                  email=sub_data['email'], 
                                  frequency_hours=frequency_hours)
                    frequency = FrequencyEnum.FREE_WEEKLY_3  # Default to free plan
                
                subscriber = Subscriber(
                    email=sub_data['email'],
                    frequency=frequency
                )
                subscribers.append(subscriber)
                
            except Exception as e:
                logger.warning("Invalid subscriber data from Supabase", 
                              email=sub_data.get('email', 'unknown'), 
                              error=str(e))
                invalid_count += 1
                continue
        
        logger.info("Subscribers loaded from Supabase", 
                   valid_count=len(subscribers), 
                   invalid_count=invalid_count,
                   source="supabase")
        
        return subscribers
        
    except Exception as e:
        logger.error("Failed to get subscribers from Supabase", error=str(e))
        return []


def get_contextual_greeting(hour_peru: int, frequency: FrequencyEnum) -> Tuple[str, str]:
    """
    Retorna (saludo, introducción) contextual según hora y frecuencia.
    hour_peru: hora en Perú (0-23)
    frequency: frecuencia del usuario
    """
    
    # Saludos por momento del día
    if 5 <= hour_peru < 12:  # Mañana
        greetings = ["¡Buenos días!", "Arrancando el día", "Para empezar bien"]
        if frequency == FrequencyEnum.DAILY:  # Diario - más personal
            intros = ["Que tengas un día increíble.", "Espero que sea un gran día para ti.", "Comenzamos con energía."]
        else:  # Frecuente - más breve
            intros = ["Un impulso matutino:", "Para arrancar:", "Energía para la mañana:"]
    elif 12 <= hour_peru < 18:  # Tarde
        greetings = ["Mitad del día", "Un momento para reflexionar", "Pausa para inspirarte"]
        if frequency == FrequencyEnum.DAILY:
            intros = ["Espero que el día vaya bien.", "Un momento de reflexión:", "Para acompañar tu tarde:"]
        else:
            intros = ["Para la tarde:", "Mantén el impulso:", "Continuamos:"]
    else:  # Noche (18-23)
        greetings = ["Cerrando el día", "Para la tarde", "Reflexión nocturna"]
        if frequency == FrequencyEnum.DAILY:
            intros = ["Para cerrar el día con buena energía.", "Espero que haya sido un buen día.", "Al final del día:"]
        else:
            intros = ["Para la noche:", "Cerrando bien:", "Última reflexión:"]
    
    # Selección determinística basada en hora
    greeting_idx = hour_peru % len(greetings)
    intro_idx = (hour_peru + 1) % len(intros)
    
    return greetings[greeting_idx], intros[intro_idx]


def generate_unique_timestamp(recipient_email: str, phrase_id: str) -> int:
    """Generate ultra-unique timestamp to prevent email grouping."""
    base_time = int(time.time() * 1000000)  # Microsegundos para mayor precisión
    email_hash = hash(recipient_email) % 100000
    random_factor = secrets.randbelow(999999)  # Cryptographically secure random
    phrase_hash = hash(phrase_id) % 10000
    return base_time + email_hash + random_factor + phrase_hash


def build_email_content(subscriber: Subscriber, phrase: Phrase) -> EmailContent:
    """Build complete email content for a subscriber."""
    # Obtener hora actual en Perú (UTC-5)
    from datetime import timedelta
    peru_tz = timezone(timedelta(hours=-5))
    now_peru = datetime.now(peru_tz)
    hour_peru = now_peru.hour
    
    unique_timestamp = generate_unique_timestamp(subscriber.email, phrase.id)
    
    # Generate subject - rotación entre 3 opciones simples
    subjects = ["Reflexión", "Pensamiento", "Inspiración"]
    subject_index = hash(phrase.id) % len(subjects)
    subject = subjects[subject_index]
    
    # Obtener primer nombre del autor para la firma
    author_first_name = phrase.author.split()[0]  # "Steve" de "Steve Jobs"
    
    # Build HTML content - Ultra-minimalista
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:20px;font-family:system-ui,sans-serif;line-height:1.5;color:#333">

<!-- SOLO LA FRASE CON SU ESTILO ACTUAL -->
<p style="margin:20px 0;font-size:17px;font-style:italic;color:#444;padding:15px;background:#f8f9fa;border-left:3px solid #ddd">
{phrase.text}
</p>

<!-- FIRMA MINIMA -->
<p style="margin:20px 0 5px;font-size:14px;color:#666">
{author_first_name}
</p>

<!-- ENLACES DEL FOOTER (CONSERVADOS) -->
<p style="margin:30px 0 0;font-size:12px;color:#999">
<a href="https://pseudosapiens.com/preferences" style="color:#999">Cambiar frecuencia</a> • 
<a href="https://pseudosapiens.com/unsubscribe" style="color:#999">Desuscribirse</a>
</p>

<!-- Timestamp invisible único para evitar agrupación en Gmail -->
<div style="display:none;font-size:1px;color:transparent">{unique_timestamp}</div>

</body>
</html>"""

    # Build text content - Ultra-minimalista
    text = f"""{phrase.text}

{author_first_name}

---
Cambiar frecuencia: https://pseudosapiens.com/preferences
Desuscribirse: https://pseudosapiens.com/unsubscribe
"""

    return EmailContent(
        recipient=subscriber,
        phrase=phrase,
        subject=subject,
        html=html,
        text=text,
        unique_timestamp=unique_timestamp
    )


# =============================================================================
# EMAIL SENDING FUNCTIONS (Modernized)
# =============================================================================

class EmailSendError(Exception):
    """Custom exception for email sending errors."""
    def __init__(self, message: str, email: str = "", status_code: Optional[int] = None):
        super().__init__(message)
        self.email = email
        self.status_code = status_code


def update_user_email_stats(user_email: str) -> None:
    """Update email statistics for user after successful email send"""
    if get_db is None:
        logger.warning("Database module not available for stats update")
        return
    
    try:
        from supabase import create_client, Client
        import os
        from datetime import datetime, timezone
        
        # Connect directly to Supabase
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            logger.warning("Supabase credentials not available for stats update")
            return
            
        supabase = create_client(url, key)
        now = datetime.now(timezone.utc)
        
        # Get current user stats
        user_result = supabase.table('users').select('id, total_emails_sent').eq('email', user_email).execute()
        
        if not user_result.data:
            logger.warning("User not found for email stats update", email=user_email)
            return
        
        user = user_result.data[0]
        new_count = (user.get('total_emails_sent') or 0) + 1
        
        # Update user statistics
        update_result = supabase.table('users').update({
            'total_emails_sent': new_count,
            'last_email_sent_at': now.isoformat(),
            'updated_at': now.isoformat()
        }).eq('id', user['id']).execute()
        
        if update_result.data:
            logger.debug("User email stats updated", 
                        email=user_email,
                        total_emails_sent=new_count,
                        timestamp=now.isoformat())
        
    except Exception as e:
        # Don't fail the email send if stats update fails
        logger.error("Failed to update user email stats", 
                    email=user_email, 
                    error=str(e))
        raise  # Re-raise to be caught by calling function


def send_single_email(config: EmailConfig, content: EmailContent) -> None:
    """Send a single email with proper error handling and retries."""
    if resend is None:
        raise EmailSendError("Resend package not installed", content.recipient.email)
    
    resend.api_key = config.api_key
    slot = str(current_hour_slot())
    
    # Create idempotency key
    idem = hashlib.sha256(
        (content.subject + "|" + slot + "|" + content.recipient.email).encode('utf-8')
    ).hexdigest()
    
    # Generate dynamic sender based on phrase author
    dynamic_sender = f'"{content.phrase.author}" <reflexiones@pseudosapiens.com>'
    
    email_data = {
        "from": dynamic_sender,  # Sender dinámico por autor
        "to": [content.recipient.email],
        "subject": content.subject,
        "html": content.html,
        "text": content.text,
        "reply_to": "reflexiones@pseudosapiens.com",
        "headers": {
            "Idempotency-Key": idem,
            "Message-ID": f"<{idem}@pseudosapiens.com>",
            # Headers básicos - sin List-Unsubscribe por ahora
            # "List-Unsubscribe": f"<https://pseudosapiens.com/unsubscribe>",
            # "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
        }
    }
    
    attempts = 0
    while attempts <= config.max_retries:
        try:
            resend.Emails.send(email_data)
            
            # Update user email statistics in Supabase
            try:
                update_user_email_stats(content.recipient.email)
            except Exception as stats_error:
                logger.warning("Failed to update email stats, but email was sent", 
                             recipient=content.recipient.email,
                             error=str(stats_error))
            
            logger.info("Email sent successfully", 
                       recipient=content.recipient.email,
                       subject=content.subject,
                       phrase_id=content.phrase.id,
                       author=content.phrase.author,
                       sender=dynamic_sender)
            # Respect rate limits
            time.sleep(config.throttle_seconds)
            return
            
        except Exception as e:
            # Handle rate limiting (429)
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            if status_code == 429:
                attempts += 1
                if attempts > config.max_retries:
                    raise EmailSendError(
                        f"Max retries exceeded due to rate limiting",
                        content.recipient.email,
                        429
                    )
                
                # Get retry-after header
                response = getattr(e, 'response', None)
                retry_after = None
                if response and hasattr(response, 'headers'):
                    retry_after = response.headers.get('Retry-After') or response.headers.get('retry-after')
                    if retry_after:
                        try:
                            retry_after = int(retry_after)
                        except ValueError:
                            retry_after = None
                
                sleep_time = retry_after if retry_after else 1.5
                logger.warning("Rate limited, retrying", 
                              recipient=content.recipient.email,
                              attempt=attempts,
                              sleep_time=sleep_time)
                time.sleep(sleep_time)
                continue
            
            # Other errors
            logger.error("Email send failed", 
                        recipient=content.recipient.email,
                        error=str(e),
                        status_code=status_code)
            raise EmailSendError(f"Email send failed: {str(e)}", content.recipient.email, status_code)


def send_email_batch(config: EmailConfig, contents: List[EmailContent]) -> Tuple[int, int]:
    """Send multiple emails with error handling. Returns (success_count, error_count)."""
    success_count = 0
    error_count = 0
    
    logger.info("Starting email batch", total_emails=len(contents))
    
    for content in contents:
        try:
            send_single_email(config, content)
            success_count += 1
        except EmailSendError as e:
            logger.error("Failed to send email", 
                        recipient=e.email,
                        error=str(e),
                        status_code=e.status_code)
            error_count += 1
        except Exception as e:
            logger.error("Unexpected error sending email",
                        recipient=content.recipient.email,
                        error=str(e))
            error_count += 1
    
    logger.info("Email batch completed", 
               success_count=success_count,
               error_count=error_count,
               total=len(contents))
    
    return success_count, error_count


# =============================================================================
# MAIN FUNCTION (Modernized)
# =============================================================================

def main_modernized(argv: List[str]) -> int:
    """Modernized main function with proper error handling and type safety."""
    dry_run = "--dry-run" in argv
    test_mode = "--test" in argv or os.getenv('TEST_MODE', 'false').lower() == 'true'

    logger.info("Starting email automation", 
                dry_run=dry_run, 
                test_mode=test_mode)

    # Check if we're in sending hours (5:00 AM - 11:59 PM Peru time)
    if not dry_run and not is_sending_hours():
        logger.info("Outside sending hours - no emails will be sent",
                   sending_hours="5:00 AM - 11:59 PM Peru time")
        return 0

    try:
        # Load configurations - only load email config if not dry-run
        if not dry_run:
            email_config = EmailConfig.from_env()
        else:
            email_config = None
        netlify_config = NetlifyConfig.from_env()
        
        # Load and select phrase from Supabase
        try:
            from database_phrases import get_random_phrase
            phrase_data = get_random_phrase()
            if phrase_data:
                phrase = Phrase(
                    id=phrase_data['id'],
                    text=phrase_data['text'],
                    author=phrase_data['author']
                )
                phrases = [phrase]  # Single phrase format for compatibility
            else:
                logger.error("No phrases found in Supabase database")
                return
        except ImportError as e:
            logger.error("Database module not available", error=str(e))
            return
        except Exception as e:
            logger.error("Error loading phrase from database", error=str(e))
            return
        
        # Choose pseudo-random phrase per hour (deterministic within the hour)
        slot = current_hour_slot()
        seed_bytes = hashlib.sha256(f"{slot}:{len(phrases)}".encode('utf-8')).digest()
        seed_int = int.from_bytes(seed_bytes[:8], 'big')
        idx = seed_int % len(phrases)
        selected_phrase = phrases[idx]
        
        logger.info("Phrase selected", 
                   phrase_id=selected_phrase.id, 
                   phrase_preview=selected_phrase.text[:50] + "..." if len(selected_phrase.text) > 50 else selected_phrase.text)

        # Get subscribers from Supabase
        all_subscribers: List[Subscriber] = []
        
        if test_mode:
            # Test mode: use only test emails
            test_emails = os.getenv('TEST_EMAILS', '').split(',')
            test_emails = [email.strip() for email in test_emails if email.strip()]
            if test_emails:
                for email in test_emails:
                    try:
                        subscriber = Subscriber(email=email, frequency=FrequencyEnum.HOURLY)
                        all_subscribers.append(subscriber)
                    except Exception as e:
                        logger.warning("Invalid test email", email=email, error=str(e))
                        
                logger.info("Test mode active", test_emails_count=len(all_subscribers))
            else:
                logger.error("No test emails found - add TEST_EMAILS=your-email@gmail.com in .env")
                return 1
                
        else:
            # Production mode: get subscribers from Supabase
            all_subscribers = get_subscribers_from_supabase()

        # Filter subscribers based on their frequency preference and optimal hours
        active_subscribers = []
        for subscriber in all_subscribers:
            if should_send_at_current_hour(int(subscriber.frequency.value)):
                active_subscribers.append(subscriber)

        logger.info("Subscriber filtering complete", 
                   total_subscribers=len(all_subscribers),
                   active_this_hour=len(active_subscribers))

        if dry_run:
            logger.info("DRY RUN - Email content preview", 
                       hour_slot=slot, 
                       phrase_index=idx,
                       total_subscribers=len(all_subscribers),
                       active_subscribers=len(active_subscribers))
            
            # Show preview of first few subscribers
            for i, subscriber in enumerate(active_subscribers[:3]):
                content = build_email_content(subscriber, selected_phrase)
                logger.info(f"Preview {i+1}", 
                           recipient=subscriber.email,
                           frequency=subscriber.frequency.name,
                           subject=content.subject)
            return 0

        if not active_subscribers:
            logger.info("No active subscribers for this hour", 
                       hour_slot=slot,
                       total_subscribers=len(all_subscribers))
            return 0

        # Build email content for all active subscribers
        email_contents = []
        for subscriber in active_subscribers:
            try:
                content = build_email_content(subscriber, selected_phrase)
                email_contents.append(content)
            except Exception as e:
                logger.error("Failed to build email content", 
                            subscriber_email=subscriber.email,
                            error=str(e))

        logger.info("Email content generated", 
                   emails_to_send=len(email_contents))

        # Send emails (only if not dry-run)
        if email_config:
            success_count, error_count = send_email_batch(email_config, email_contents)
        else:
            success_count, error_count = 0, 0

        if error_count == 0:
            logger.info("All emails sent successfully", 
                       success_count=success_count,
                       total_subscribers=len(all_subscribers))
            return 0
        else:
            logger.warning("Some emails failed to send", 
                          success_count=success_count,
                          error_count=error_count)
            return 1 if success_count == 0 else 0  # Return error only if ALL failed

    except Exception as e:
        logger.error("Fatal error in email automation", error=str(e))
        return 1


def build_email_html(phrase_id: str, phrase_text: str, recipient_email: str = "", frequency: int = 1) -> str:
    """
    Email ultra personal - como un mensaje de texto de un amigo.
    Sin footers corporativos ni elementos que parezcan newsletter.
    """
    
    # Obtener hora actual en Perú (UTC-5)
    import hashlib
    from datetime import datetime, timezone, timedelta
    from urllib.parse import quote
    
    peru_tz = timezone(timedelta(hours=-5))
    now_peru = datetime.now(peru_tz)
    hour_peru = now_peru.hour
    
    # Usar la frecuencia pasada como parámetro
    
    greeting, intro = get_contextual_greeting(hour_peru, frequency)
    
    # Timestamp ultra-único por email (múltiples factores de unicidad)
    import random
    import time
    base_time = int(time.time() * 1000000)  # Microsegundos para mayor precisión
    email_hash = hash(recipient_email) % 100000
    random_factor = random.randint(100000, 999999)  # Factor aleatorio grande
    phrase_hash = hash(phrase_id) % 10000
    unique_timestamp = base_time + email_hash + random_factor + phrase_hash
    
    # Ya no necesitamos pasar datos por URL - entrada manual más segura
    
    # HTML mínimo que parece mensaje personal
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:20px;font-family:system-ui,sans-serif;line-height:1.5;color:#333">

<p style="margin:0 0 20px;font-size:16px">
{greeting}
</p>

<p style="margin:20px 0;font-size:16px;color:#555">
{intro}
</p>

<p style="margin:20px 0;font-size:17px;font-style:italic;color:#444;padding:15px;background:#f8f9fa;border-left:3px solid #ddd">
{phrase_text}
</p>

<p style="margin:20px 0 5px;font-size:14px;color:#666">
Un saludo,<br>
Pseudosapiens
</p>

<p style="margin:30px 0 0;font-size:12px;color:#999">
<a href="https://pseudosapiens.com/preferences" style="color:#999">Cambiar frecuencia</a> • 
<a href="https://pseudosapiens.com/unsubscribe" style="color:#999">Desuscribirse</a>
</p>

<!-- Timestamp invisible único para evitar agrupación en Gmail -->
<div style="display:none;font-size:1px;color:transparent">{unique_timestamp}</div>

</body>
</html>"""
    return html


def build_email_text(phrase_text: str, recipient_email: str = "", frequency: int = 1) -> str:
    """
    Texto plano ultra personal - como un mensaje de WhatsApp.
    """
    # Obtener hora actual en Perú (UTC-5)
    from datetime import datetime, timezone, timedelta
    from urllib.parse import quote
    
    peru_tz = timezone(timedelta(hours=-5))
    now_peru = datetime.now(peru_tz)
    hour_peru = now_peru.hour
    
    # Usar la frecuencia pasada como parámetro
    
    greeting, intro = get_contextual_greeting(hour_peru, frequency)
    
    # Timestamp ultra-único por email (múltiples factores de unicidad) 
    import random
    import secrets
    base_time = int(time.time() * 1000000)  # Microsegundos para mayor precisión
    email_hash = hash(recipient_email) % 100000
    secure_random = secrets.randbelow(999999)  # Cryptographically secure random
    phrase_hash = hash(phrase_text[:20]) % 10000  # Usar parte de la frase
    unique_timestamp = base_time + email_hash + secure_random + phrase_hash
    
    # Ya no necesitamos pasar datos por URL - entrada manual más segura
    
    return f"""{greeting}

{intro}

{phrase_text}

Un saludo,
Pseudosapiens

---
Cambiar frecuencia: https://pseudosapiens.com/preferences
Desuscribirse: https://pseudosapiens.com/unsubscribe

"""


def send_via_resend_with_context(sender: str, recipients_data: List[Dict], subject: str, phrase_id: str, phrase_text: str) -> None:
    """
    Envia correos con contexto personalizado por destinatario.
    recipients_data: lista de {'email': str, 'frequency': int}
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

    for recipient_data in recipients_data:
        email = recipient_data['email']
        frequency = recipient_data['frequency']
        
        # Generar contenido personalizado para este destinatario
        html = build_email_html(phrase_id, phrase_text, email, frequency)
        text = build_email_text(phrase_text, email, frequency)
        
        # URL limpia para compliance headers
        unsubscribe_url = "https://pseudosapiens.com/unsubscribe"
        
        # Idempotency por destinatario
        idem = hashlib.sha256((subject + "|" + slot + "|" + email).encode('utf-8')).hexdigest()

        attempts = 0
        while True:
            try:
                email_data = {
                    "from": sender,
                    "to": [email],  # Envío individual
                    "subject": subject,
                    "html": html,
                    "reply_to": "reflexiones@pseudosapiens.com",
                    "headers": {
                        "Idempotency-Key": idem,
                        "Message-ID": f"<{idem}@pseudosapiens.com>",
                        # Headers básicos - sin List-Unsubscribe por ahora
                        # "List-Unsubscribe": f"<{unsubscribe_url}>",
                        # "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
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
    form_name = os.getenv('NETLIFY_FORM_NAME', 'subscribe')
    site_id = os.getenv('NETLIFY_SITE_ID', '')
    token = os.getenv('NETLIFY_ACCESS_TOKEN', '')
    sender = os.getenv('SENDER_EMAIL', 'Frases <no-reply@example.com>')

    # Load phrases from Supabase
    try:
        from database_phrases import load_phrases as load_phrases_from_db
        phrases = load_phrases_from_db()  # Load from Supabase
        if not phrases:
            logger.error("No phrases found in Supabase database")
            return
    except ImportError as e:
        logger.error("Database module not available", error=str(e))
        return
    except Exception as e:
        logger.error("Error loading phrases from database", error=str(e))
        return
        
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

    # Filter subscribers based on their frequency preference and optimal hours
    recipients_with_frequency = []
    for subscriber in all_subscribers:
        email = subscriber['email']
        frequency = subscriber['frequency']
        
        # Send if current hour is optimal for user's frequency
        if should_send_at_current_hour(frequency):
            recipients_with_frequency.append({'email': email, 'frequency': frequency})
    
    # Mantener lista simple para compatibilidad
    recipients = [r['email'] for r in recipients_with_frequency]

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
    
    # No generar HTML/text aquí - se hará individualmente para cada destinatario

    if dry_run:
        print("[DRY-RUN] HourSlot:", slot, "Index:", idx)
        print(f"[DRY-RUN] Frase: {phrase_id} -> {phrase_text[:80]}{'...' if len(phrase_text)>80 else ''}")
        print(f"[DRY-RUN] Total suscriptores: {len(all_subscribers)}")
        print(f"[DRY-RUN] Filtrados para esta hora: {len(recipients)}")
        for sub in all_subscribers[:5]:  # Show first 5 for debugging
            will_receive = "SI" if should_send_at_current_hour(sub['frequency']) else "NO"
            print(f"[DRY-RUN] {sub['email']} (cada {sub['frequency']}h) {will_receive}")
        return 0

    if not recipients:
        print(f"[INFO] No hay destinatarios para esta hora (slot {slot}). {len(all_subscribers)} suscriptores totales.")
        return 0

    try:
        send_via_resend_with_context(sender, recipients_with_frequency, subject, phrase_id, phrase_text)
        print(f"[OK] Enviados {len(recipients)} correos de {len(all_subscribers)} suscriptores con asunto: {subject}")
        return 0
    except Exception as e:
        print("[ERROR] Falló el envío:", e)
        return 1


if __name__ == "__main__":
    # Use modernized main function with fallback to legacy
    try:
        raise SystemExit(main_modernized(sys.argv[1:]))
    except Exception as e:
        logger.error("Modernized main failed, falling back to legacy", error=str(e))
        raise SystemExit(main(sys.argv[1:]))
