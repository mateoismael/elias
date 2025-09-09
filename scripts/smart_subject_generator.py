"""
Sistema Inteligente de Generación de Asuntos para Emails
Genera asuntos únicos y naturales usando OpenAI API con fallback robusto
COMPATIBLE con el sistema existente - CERO FRICCIÓN
"""
import os
import hashlib
from typing import Optional, List, Dict
import structlog
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = structlog.get_logger()

# =====================================================
# CONFIGURACIÓN Y CONSTANTES
# =====================================================

# Límites de seguridad
MAX_SUBJECT_LENGTH = 50
DEFAULT_TEMPERATURE = 0.8
DEFAULT_MAX_TOKENS = 20

# Bancos de asuntos de fallback organizados por momento del día
FALLBACK_SUBJECTS = {
    'morning': [
        "Para comenzar bien", "Tu momento es ahora", "Algo importante",
        "Para reflexionar", "Pensamiento matutino", "Una perspectiva nueva",
        "Energía para hoy", "Comienza fuerte", "Tu impulso diario",
        "Algo que necesitas", "Para empezar", "Momento perfecto"
    ],
    'afternoon': [
        "Pausa para pensar", "Necesitabas escuchar esto", "Un recordatorio",
        "Para la tarde", "Momento de reflexión", "Algo que importa",
        "A mitad del día", "Para continuar", "Tu pausa necesaria",
        "Impulso vespertino", "Sigue adelante", "Para reflexionar"
    ],
    'evening': [
        "Al final del día", "Para cerrar bien", "Una reflexión",
        "Antes de descansar", "Para contemplar", "Pensamiento nocturno",
        "Cerrando fuerte", "Tu reflexión", "Para la noche",
        "Último impulso", "Para finalizar", "Contempla esto"
    ]
}

# =====================================================
# FUNCIÓN PRINCIPAL - OPENAI INTEGRATION  
# =====================================================

def generate_smart_subject_with_openai(
    phrase_text: str, 
    author: str, 
    hour_peru: int,
    use_openai: bool = True,
    hybrid_mode: bool = False  # Deshabilitado - solo OpenAI con GPT-4o mini
) -> Dict[str, any]:
    """
    🧠 GENERA ASUNTO ÚNICO usando OpenAI API con fallback robusto
    
    Args:
        phrase_text: Texto de la frase motivacional
        author: Autor de la frase  
        hour_peru: Hora en Perú (0-23) para contexto temporal
        use_openai: Si usar OpenAI o ir directo al fallback
        
    Returns:
        Dict: {
            'subject': str,           # Asunto generado
            'method': str,           # 'openai' o 'fallback'  
            'success': bool,         # Si la generación fue exitosa
            'cost_estimate': float   # Estimación de costo en USD
        }
    """
    
    # Determinar contexto temporal
    time_context = _get_time_context(hour_peru)
    
    # Si OpenAI está deshabilitado, ir directo al fallback
    if not use_openai:
        return _generate_fallback_subject(phrase_text, hour_peru, "openai_disabled")
    
    # MODO HÍBRIDO: Alternar entre OpenAI y fallback para más variedad
    if hybrid_mode:
        import random
        # 70% OpenAI, 30% fallback mejorado para variedad
        if random.random() < 0.3:
            result = _generate_fallback_subject(phrase_text, hour_peru, "hybrid_variety")
            result['method'] = 'hybrid_fallback'
            return result
    
    # Verificar configuración de OpenAI
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning("OPENAI_API_KEY not found, using fallback")
        return _generate_fallback_subject(phrase_text, hour_peru, "no_api_key")
    
    try:
        # Importar OpenAI solo cuando se necesita
        from openai import OpenAI
        
        # Crear cliente OpenAI (nueva API v1.x)
        client = OpenAI(api_key=api_key)
        
        # Construir prompt optimizado
        prompt = _build_optimized_prompt(phrase_text, author, time_context)
        
        # Llamada a OpenAI API con GPT-4o mini
        # GPT-4o mini: mejor balance precio/creatividad para asuntos
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # GPT-4o mini - mejor para creatividad y variabilidad
            messages=[{
                "role": "user", 
                "content": prompt
            }],
            max_tokens=DEFAULT_MAX_TOKENS,  # GPT-4o mini usa max_tokens
            temperature=0.8  # Más creatividad para variabilidad
        )
        
        # Extraer y limpiar respuesta
        subject = response.choices[0].message.content.strip()
        subject = _clean_and_validate_subject(subject)
        
        # Calcular costo estimado
        cost_estimate = _calculate_cost_estimate(prompt, subject)
        
        logger.info(
            "OpenAI subject generated successfully",
            subject=subject,
            phrase_preview=phrase_text[:30] + "...",
            author=author,
            cost_estimate=cost_estimate
        )
        
        return {
            'subject': subject,
            'method': 'openai',
            'success': True,
            'cost_estimate': cost_estimate
        }
        
    except ImportError as e:
        logger.warning("OpenAI library not installed, using fallback", error=str(e))
        return _generate_fallback_subject(phrase_text, hour_peru, "openai_not_installed")
        
    except Exception as e:
        logger.error(
            "OpenAI subject generation failed", 
            error=str(e),
            phrase_preview=phrase_text[:30] + "..."
        )
        return _generate_fallback_subject(phrase_text, hour_peru, f"openai_error: {str(e)[:50]}")

# =====================================================
# FUNCIONES DE APOYO - OPENAI
# =====================================================

def _get_time_context(hour_peru: int) -> str:
    """Determina contexto temporal para el prompt"""
    if 5 <= hour_peru < 12:
        return "mañana (energía para comenzar el día)"
    elif 12 <= hour_peru < 18:  
        return "tarde (momento de reflexión)"
    else:
        return "noche (cierre del día, contemplación)"

def _build_optimized_prompt(phrase_text: str, author: str, time_context: str) -> str:
    """Construye prompt simplificado y directo para GPT-5 nano"""
    
    # Extraer palabras clave principales
    frase_words = phrase_text.lower().split()
    key_words = [word.strip('.,!?') for word in frase_words if len(word.strip('.,!?')) > 4][:3]
    
    # Buscar conceptos específicos
    concepts = {
        'dinero': ['dinero', 'riqueza', 'comprar', 'económico'],
        'trabajo': ['trabajo', 'carrera', 'laboral', 'profesional'],
        'miedo': ['miedo', 'fallar', 'intentar', 'riesgo'],
        'música': ['música', 'ritmo', 'sonido', 'canción'],
        'amor': ['amor', 'corazón', 'sentir', 'amar'],
        'vida': ['vida', 'vivir', 'existir', 'mundo'],
        'éxito': ['éxito', 'lograr', 'alcanzar', 'ganar'],
        'felicidad': ['felicidad', 'alegría', 'sonreír', 'feliz']
    }
    
    detected_theme = "general"
    for theme, words in concepts.items():
        if any(word in phrase_text.lower() for word in words):
            detected_theme = theme
            break
    
    # Templates específicos por tema
    templates = {
        'dinero': ["Más que dinero", "Tu verdadera riqueza", "Valor real", "Riqueza interior"],
        'trabajo': ["Tu carrera espera", "Trabajo con propósito", "Tu futuro laboral", "Profesión y pasión"],
        'miedo': ["Sin miedo hoy", "Atrévete ahora", "Coraje para actuar", "Supera tus límites"],
        'música': ["Ritmo de vida", "Música que inspira", "Sonido del alma", "Armonía personal"],
        'amor': ["Amor que transforma", "Corazón abierto", "Amor verdadero", "Sentimientos reales"],
        'vida': ["Vive plenamente", "Tu vida cuenta", "Existir con sentido", "Vida auténtica"],
        'éxito': ["Éxito personal", "Logra más", "Tu momento brillante", "Alcanza tus metas"],
        'felicidad': ["Felicidad genuina", "Alegría interior", "Sonríe hoy", "Tu felicidad"],
        'general': ["Reflexiona hoy", "Tu momento", "Para ti", "Algo importante"]
    }
    
    import hashlib
    # Usar hash para selección determinística pero variada
    phrase_hash = int(hashlib.md5(phrase_text.encode()).hexdigest()[:8], 16)
    template_options = templates.get(detected_theme, templates['general'])
    selected_template = template_options[phrase_hash % len(template_options)]
    
    return f"""Crea un asunto de email de máximo 40 caracteres que capture la esencia de esta frase:

"{phrase_text}"

El asunto debe ser como: "{selected_template}" pero adaptado al contenido específico.
Responde solo el asunto, sin comillas ni explicaciones."""

def _clean_and_validate_subject(subject: str) -> str:
    """Limpia y valida el asunto generado por OpenAI"""
    # Remover comillas y espacios extra
    subject = subject.strip(' "\'')
    
    # Truncar si es muy largo
    if len(subject) > MAX_SUBJECT_LENGTH:
        subject = subject[:MAX_SUBJECT_LENGTH - 3] + "..."
    
    # Si quedó vacío, usar fallback
    if not subject:
        subject = "Tu momento de reflexión"
    
    return subject

def _calculate_cost_estimate(prompt: str, response: str) -> float:
    """Calcula costo estimado de la llamada a OpenAI"""
    # gpt-4o-mini: $0.15 per 1M input tokens, $0.60 per 1M output tokens (Sept 2025)
    prompt_tokens = len(prompt.split()) * 1.3  # Aproximación
    response_tokens = len(response.split()) * 1.3
    
    input_cost = (prompt_tokens / 1_000_000) * 0.15
    output_cost = (response_tokens / 1_000_000) * 0.60
    
    return round(input_cost + output_cost, 6)

# =====================================================
# SISTEMA DE FALLBACK ROBUSTO
# =====================================================

def _generate_fallback_subject(
    phrase_text: str, 
    hour_peru: int, 
    reason: str = "fallback"
) -> Dict[str, any]:
    """
    🔄 SISTEMA DE FALLBACK INTELIGENTE
    Genera asuntos variados sin OpenAI usando lógica determinística
    """
    
    # Determinar momento del día
    if 5 <= hour_peru < 12:
        subject_pool = FALLBACK_SUBJECTS['morning']
    elif 12 <= hour_peru < 18:
        subject_pool = FALLBACK_SUBJECTS['afternoon']  
    else:
        subject_pool = FALLBACK_SUBJECTS['evening']
    
    # Selección determinística basada en hash de la frase
    # Esto garantiza consistencia: misma frase = mismo asunto
    phrase_hash = hashlib.md5(phrase_text.encode()).hexdigest()
    index = int(phrase_hash[:8], 16) % len(subject_pool)
    subject = subject_pool[index]
    
    logger.info(
        "Fallback subject generated",
        subject=subject,
        reason=reason,
        phrase_preview=phrase_text[:30] + "...",
        hour_peru=hour_peru
    )
    
    return {
        'subject': subject,
        'method': 'fallback', 
        'success': True,
        'cost_estimate': 0.0,
        'reason': reason
    }

# =====================================================
# FUNCIONES DE UTILIDAD Y TESTING
# =====================================================

def get_system_status() -> Dict[str, any]:
    """
    🔍 Obtiene status del sistema de generación de asuntos
    """
    api_key_configured = bool(os.getenv('OPENAI_API_KEY'))
    
    try:
        import openai
        openai_available = True
    except ImportError:
        openai_available = False
    
    return {
        'openai_api_key_configured': api_key_configured,
        'openai_library_available': openai_available,
        'fallback_subjects_count': sum(len(subjects) for subjects in FALLBACK_SUBJECTS.values()),
        'system_ready': True,  # Siempre listo gracias al fallback
        'default_method': 'openai' if (api_key_configured and openai_available) else 'fallback'
    }

def test_subject_generation(phrase_text: str = None, author: str = None) -> None:
    """
    🧪 Función de testing para verificar generación de asuntos
    """
    # Valores por defecto para testing
    if not phrase_text:
        phrase_text = "El éxito no es la clave de la felicidad. La felicidad es la clave del éxito."
    if not author:
        author = "Albert Einstein"
    
    print("=" * 60)
    print("TESTING SISTEMA DE ASUNTOS INTELIGENTES")
    print("=" * 60)
    
    # Test en diferentes horas
    test_hours = [8, 14, 21]  # Mañana, tarde, noche
    
    for hour in test_hours:
        print(f"\nHORA: {hour}:00")
        
        # Test con OpenAI
        result_ai = generate_smart_subject_with_openai(phrase_text, author, hour, use_openai=True)
        print(f"   OpenAI: '{result_ai['subject']}' ({result_ai['method']}) - ${result_ai['cost_estimate']:.6f}")
        
        # Test fallback
        result_fallback = generate_smart_subject_with_openai(phrase_text, author, hour, use_openai=False)
        print(f"   Fallback: '{result_fallback['subject']}' ({result_fallback['method']})")
    
    # System status
    print(f"\nSYSTEM STATUS:")
    status = get_system_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETADO")
    print("=" * 60)

# =====================================================
# BACKWARDS COMPATIBILITY 
# =====================================================

def generate_subject_for_email(phrase_text: str, author: str, hour_peru: int) -> str:
    """
    🔄 Función simple de compatibilidad
    Retorna solo el asunto (string) para integración fácil
    """
    result = generate_smart_subject_with_openai(phrase_text, author, hour_peru)
    return result['subject']

# Alias para compatibilidad
get_smart_subject = generate_subject_for_email
generate_email_subject = generate_subject_for_email

if __name__ == "__main__":
    test_subject_generation()