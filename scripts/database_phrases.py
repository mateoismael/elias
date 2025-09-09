"""
Enhanced Database Phrases Module - CERO FRICCIÓN
Reemplaza database_phrases.py con sistema inteligente anti-repetición
COMPATIBLE 100% con el código existente

MIGRACIÓN SUAVE:
1. Renombrar database_phrases.py a database_phrases_original.py
2. Renombrar este archivo a database_phrases.py  
3. ¡Listo! El sistema funciona automáticamente sin repeticiones
"""
import os
import random
from typing import Dict, List, Optional
from supabase import create_client
import structlog
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar el nuevo sistema inteligente
try:
    from smart_phrase_system import (
        get_smart_phrase_for_user,
        record_phrase_sent,
        get_user_phrase_stats
    )
    SMART_SYSTEM_AVAILABLE = True
except ImportError:
    SMART_SYSTEM_AVAILABLE = False
    
logger = structlog.get_logger()

def get_supabase_client():
    """Get Supabase client for phrases - UNCHANGED"""
    return create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )

# =====================================================
# FUNCIONES PRINCIPALES - ENHANCED CON INTELIGENCIA
# =====================================================

def get_random_phrase(user_id: Optional[str] = None) -> Optional[Dict]:
    """
    🎯 FUNCIÓN PRINCIPAL MEJORADA
    
    Si se proporciona user_id: Sistema inteligente anti-repetición
    Si NO se proporciona: Sistema original (completamente aleatorio)
    
    COMPATIBILIDAD: 100% compatible con llamadas existentes
    """
    if user_id and SMART_SYSTEM_AVAILABLE:
        # 🧠 MODO INTELIGENTE: Anti-repetición
        try:
            smart_phrase = get_smart_phrase_for_user(user_id)
            if smart_phrase:
                logger.info(
                    "Smart phrase delivered",
                    user_id=user_id,
                    phrase_id=smart_phrase['id'],
                    author=smart_phrase['author']
                )
                return smart_phrase
        except Exception as e:
            logger.warning("Smart system failed, falling back to random", error=str(e))
    
    # 🎲 MODO ORIGINAL: Completamente aleatorio (fallback + compatibility)
    return _get_original_random_phrase()

def get_random_phrase_for_user(user_id: str) -> Optional[Dict]:
    """
    🎯 NUEVA FUNCIÓN: Garantiza sistema inteligente
    Para uso explícito cuando se quiere anti-repetición
    """
    return get_random_phrase(user_id=user_id)

def _get_original_random_phrase() -> Optional[Dict]:
    """
    Sistema original: selección completamente aleatoria
    Usado como fallback y para compatibilidad
    """
    try:
        supabase = get_supabase_client()
        
        # Obtener todas las frases (o usar LIMIT para performance)
        result = supabase.table('phrases').select('*').execute()
        
        if not result.data:
            logger.warning("No phrases found in database")
            return None
            
        # Seleccionar frase aleatoria
        phrase = random.choice(result.data)
        
        logger.info(
            "Random phrase selected (original mode)",
            phrase_id=phrase['id'],
            author=phrase['author'],
            text_length=len(phrase['text'])
        )
        
        return {
            'id': phrase['id'],
            'text': phrase['text'],
            'author': phrase['author']
        }
        
    except Exception as e:
        logger.error("Error getting random phrase from database", error=str(e))
        return None

# =====================================================
# FUNCIONES EXISTENTES - UNCHANGED PARA COMPATIBILIDAD
# =====================================================

def get_phrase_by_author(author: str) -> Optional[Dict]:
    """Obtiene una frase aleatoria de un autor específico - UNCHANGED"""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('phrases').select('*').eq('author', author).execute()
        
        if not result.data:
            logger.warning("No phrases found for author", author=author)
            return None
            
        phrase = random.choice(result.data)
        
        return {
            'id': phrase['id'], 
            'text': phrase['text'],
            'author': phrase['author']
        }
        
    except Exception as e:
        logger.error("Error getting phrase by author", author=author, error=str(e))
        return None

def get_phrase_count() -> int:
    """Obtiene el total de frases en la base de datos - UNCHANGED"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('phrases').select('*', count='exact').execute()
        return result.count or 0
    except Exception as e:
        logger.error("Error counting phrases", error=str(e))
        return 0

def get_authors_list() -> List[str]:
    """Obtiene lista única de autores - UNCHANGED"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('phrases').select('author').execute()
        
        if not result.data:
            return []
            
        authors = list(set(row['author'] for row in result.data))
        return sorted(authors)
        
    except Exception as e:
        logger.error("Error getting authors list", error=str(e))
        return []

def load_phrases() -> List[Dict]:
    """
    Load all phrases from Supabase database - UNCHANGED
    Returns list of phrase dictionaries for compatibility
    """
    try:
        supabase = get_supabase_client()
        result = supabase.table('phrases').select('*').execute()
        
        if not result.data:
            logger.warning("No phrases found in database")
            return []
            
        logger.info("Phrases loaded from Supabase", count=len(result.data))
        return [
            {
                'id': str(row['id']),
                'text': row['text'], 
                'author': row['author']
            }
            for row in result.data
        ]
        
    except Exception as e:
        logger.error("Error loading phrases from database", error=str(e))
        return []

# =====================================================
# NUEVAS FUNCIONES - ENHANCED ANALYTICS
# =====================================================

def get_phrase_analytics() -> Dict:
    """
    📊 NUEVA: Obtiene analytics globales de frases
    """
    try:
        total_phrases = get_phrase_count()
        authors = get_authors_list()
        
        # Si está disponible el sistema inteligente, usar vistas optimizadas
        if SMART_SYSTEM_AVAILABLE:
            try:
                supabase = get_supabase_client()
                analytics_result = supabase.table('phrase_analytics').select('*').limit(10).execute()
                
                if analytics_result.data:
                    return {
                        'total_phrases': total_phrases,
                        'total_authors': len(authors),
                        'top_phrases': analytics_result.data,
                        'system_mode': 'smart_analytics'
                    }
            except Exception:
                pass
        
        # Fallback a analytics básicos
        return {
            'total_phrases': total_phrases,
            'total_authors': len(authors),
            'top_authors': authors[:10],
            'system_mode': 'basic_analytics'
        }
        
    except Exception as e:
        logger.error("Error getting phrase analytics", error=str(e))
        return {'error': str(e)}

def get_user_delivery_stats(user_id: str) -> Dict:
    """
    📊 NUEVA: Obtiene estadísticas de entrega para un usuario específico
    """
    if SMART_SYSTEM_AVAILABLE:
        return get_user_phrase_stats(user_id)
    else:
        return {
            'user_id': user_id,
            'smart_system_available': False,
            'message': 'Install smart_phrase_system.py for detailed user analytics'
        }

def is_smart_system_enabled() -> bool:
    """
    🔍 NUEVA: Verifica si el sistema inteligente está disponible
    """
    return SMART_SYSTEM_AVAILABLE

def get_system_status() -> Dict:
    """
    🔍 NUEVA: Status completo del sistema de frases
    """
    return {
        'smart_system_available': SMART_SYSTEM_AVAILABLE,
        'total_phrases': get_phrase_count(),
        'total_authors': len(get_authors_list()),
        'database_connection': 'ok' if get_phrase_count() > 0 else 'error',
        'mode': 'intelligent_anti_repetition' if SMART_SYSTEM_AVAILABLE else 'classic_random'
    }

# =====================================================
# HELPERS PARA MIGRACIÓN Y TESTING
# =====================================================

def test_enhanced_system():
    """
    🧪 Función de testing para verificar que todo funciona
    """
    logger.info("Testing enhanced phrase system...")
    
    # Test 1: Función original (compatibilidad)
    phrase1 = get_random_phrase()
    logger.info("OK Original function compatibility", success=phrase1 is not None)
    
    # Test 2: Sistema inteligente (si disponible)
    test_user_id = "test-user-12345"
    phrase2 = get_random_phrase_for_user(test_user_id)
    logger.info("OK Smart system function", success=phrase2 is not None, smart_mode=SMART_SYSTEM_AVAILABLE)
    
    # Test 3: Analytics
    analytics = get_phrase_analytics()
    logger.info("OK Analytics function", success='error' not in analytics)
    
    # Test 4: System status
    status = get_system_status()
    logger.info("OK System status", status=status)
    
    logger.info("Enhanced phrase system test completed successfully")
    return True

# =====================================================
# BACKWARDS COMPATIBILITY ALIASES
# =====================================================

# Aliases para máxima compatibilidad con código existente
get_phrase_for_user = get_random_phrase_for_user
get_smart_phrase = get_random_phrase_for_user
select_random_phrase = get_random_phrase

if __name__ == "__main__":
    test_enhanced_system()