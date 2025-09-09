"""
Sistema Inteligente de Frases - Anti Repetición
Reemplaza get_random_phrase() con lógica inteligente que previene duplicados
COMPATIBLE con el sistema existente - CERO FRICCIÓN
"""
import os
import random
from typing import Dict, List, Optional, Tuple
from supabase import create_client
import structlog
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = structlog.get_logger()

def get_supabase_client():
    """Get Supabase client usando la configuración existente"""
    return create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )

def get_smart_phrase_for_user(user_id: str) -> Optional[Dict]:
    """
    FUNCIÓN PRINCIPAL: Obtiene una frase inteligente para el usuario
    
    🎯 LÓGICA ANTI-REPETICIÓN:
    1. Busca frases NO enviadas al usuario
    2. Si encuentra, selecciona una aleatoria
    3. Si NO encuentra (recibió todas), reinicia el ciclo
    4. Registra el envío en el historial
    
    Args:
        user_id: UUID del usuario
        
    Returns:
        Dict con phrase data o None si hay error
    """
    try:
        supabase = get_supabase_client()
        
        # Usar la función SQL optimizada si está disponible
        try:
            result = supabase.rpc('get_smart_phrase_for_user', {'p_user_id': user_id}).execute()
            
            if result.data and len(result.data) > 0:
                phrase_data = result.data[0]
                phrase_result = {
                    'id': phrase_data['phrase_id'],
                    'text': phrase_data['phrase_text'],
                    'author': phrase_data['phrase_author']
                }
                
                # Registrar el envío
                record_phrase_sent(user_id, phrase_result['id'])
                
                logger.info(
                    "Smart phrase selected via SQL function",
                    user_id=user_id,
                    phrase_id=phrase_result['id'],
                    author=phrase_result['author']
                )
                
                return phrase_result
                
        except Exception as sql_error:
            logger.warning(
                "SQL function not available, using Python fallback", 
                error=str(sql_error)
            )
        
        # FALLBACK: Implementación Python (si no hay función SQL)
        return _get_smart_phrase_python_fallback(user_id, supabase)
        
    except Exception as e:
        logger.error("Error in get_smart_phrase_for_user", user_id=user_id, error=str(e))
        # Fallback al sistema original si falla todo
        return _get_original_random_phrase()

def _get_smart_phrase_python_fallback(user_id: str, supabase) -> Optional[Dict]:
    """
    Implementación Python del algoritmo inteligente
    Fallback si la función SQL no está disponible
    """
    try:
        # 1. Obtener todas las frases
        all_phrases_result = supabase.table('phrases').select('*').execute()
        if not all_phrases_result.data:
            logger.warning("No phrases found in database")
            return None
        
        all_phrases = all_phrases_result.data
        total_phrases = len(all_phrases)
        
        # 2. Obtener frases ya enviadas al usuario
        sent_phrases_result = supabase.table('user_phrase_history').select('phrase_id').eq('user_id', user_id).eq('email_status', 'sent').execute()
        
        sent_phrase_ids = set()
        if sent_phrases_result.data:
            sent_phrase_ids = {row['phrase_id'] for row in sent_phrases_result.data}
        
        logger.info(
            "Phrase analysis for user",
            user_id=user_id,
            total_phrases=total_phrases,
            sent_phrases=len(sent_phrase_ids)
        )
        
        # 3. Filtrar frases NO enviadas
        unsent_phrases = [p for p in all_phrases if p['id'] not in sent_phrase_ids]
        
        # 4. Si no hay frases sin enviar, reiniciar ciclo
        if not unsent_phrases:
            logger.info(
                "User completed all phrases, resetting cycle",
                user_id=user_id,
                total_completed=len(sent_phrase_ids)
            )
            
            # Opcional: limpiar historial parcialmente (mantener últimas 50)
            _cleanup_user_history(user_id, supabase, keep_last=50)
            
            # Seleccionar aleatoriamente de todas las frases
            unsent_phrases = all_phrases
        
        # 5. Seleccionar frase aleatoria de las disponibles
        selected_phrase = random.choice(unsent_phrases)
        
        # 6. Registrar envío
        record_phrase_sent(user_id, selected_phrase['id'])
        
        phrase_result = {
            'id': selected_phrase['id'],
            'text': selected_phrase['text'], 
            'author': selected_phrase['author']
        }
        
        logger.info(
            "Smart phrase selected via Python fallback",
            user_id=user_id,
            phrase_id=phrase_result['id'],
            author=phrase_result['author'],
            was_cycle_reset=len(unsent_phrases) == total_phrases
        )
        
        return phrase_result
        
    except Exception as e:
        logger.error("Error in Python fallback", user_id=user_id, error=str(e))
        return _get_original_random_phrase()

def record_phrase_sent(user_id: str, phrase_id: str, plan_id: Optional[int] = None) -> bool:
    """
    Registra que una frase fue enviada a un usuario
    
    Args:
        user_id: UUID del usuario
        phrase_id: UUID de la frase
        plan_id: Plan activo del usuario (opcional)
        
    Returns:
        True si se registró correctamente, False si hubo error
    """
    try:
        supabase = get_supabase_client()
        
        # Intentar usar función SQL optimizada
        try:
            result = supabase.rpc('record_phrase_sent', {
                'p_user_id': user_id,
                'p_phrase_id': phrase_id,
                'p_plan_id': plan_id
            }).execute()
            
            if result.data:
                return True
                
        except Exception:
            # Fallback a INSERT directo
            pass
        
        # Fallback: INSERT manual con ON CONFLICT
        data_to_insert = {
            'user_id': user_id,
            'phrase_id': phrase_id,
            'email_status': 'sent'
        }
        
        if plan_id is not None:
            data_to_insert['plan_id'] = plan_id
        
        result = supabase.table('user_phrase_history').upsert(
            data_to_insert,
            on_conflict='user_id,phrase_id'
        ).execute()
        
        logger.info(
            "Phrase delivery recorded",
            user_id=user_id,
            phrase_id=phrase_id,
            plan_id=plan_id
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to record phrase delivery", 
            user_id=user_id, 
            phrase_id=phrase_id,
            error=str(e)
        )
        # No es crítico si falla el registro, el email se envía igual
        return False

def _cleanup_user_history(user_id: str, supabase, keep_last: int = 50):
    """
    Limpia el historial de un usuario manteniendo solo los últimos N registros
    Esto previene que la tabla crezca indefinidamente
    """
    try:
        # Obtener IDs de registros a mantener
        keep_records = supabase.table('user_phrase_history').select('id').eq('user_id', user_id).order('sent_at', desc=True).limit(keep_last).execute()
        
        if keep_records.data and len(keep_records.data) >= keep_last:
            keep_ids = [record['id'] for record in keep_records.data]
            
            # Eliminar registros antiguos (mantener solo los últimos keep_last)
            # Nota: Supabase no soporta NOT IN directamente, usamos lógica inversa
            all_user_records = supabase.table('user_phrase_history').select('id').eq('user_id', user_id).execute()
            
            if all_user_records.data:
                delete_ids = [record['id'] for record in all_user_records.data if record['id'] not in keep_ids]
                
                # Eliminar en batches para evitar timeouts
                batch_size = 50
                for i in range(0, len(delete_ids), batch_size):
                    batch_ids = delete_ids[i:i + batch_size]
                    for delete_id in batch_ids:
                        supabase.table('user_phrase_history').delete().eq('id', delete_id).execute()
                
                logger.info(
                    "User history cleaned up",
                    user_id=user_id,
                    deleted_count=len(delete_ids),
                    kept_count=len(keep_ids)
                )
    
    except Exception as e:
        logger.warning("History cleanup failed", user_id=user_id, error=str(e))

def _get_original_random_phrase() -> Optional[Dict]:
    """
    Fallback al sistema original (completamente aleatorio)
    Se usa solo si el sistema inteligente falla completamente
    """
    try:
        from database_phrases import get_random_phrase
        return get_random_phrase()
    except Exception as e:
        logger.error("Even original system failed", error=str(e))
        return None

# =====================================================
# FUNCIONES DE COMPATIBILIDAD PARA TRANSICIÓN SUAVE
# =====================================================

def get_smart_phrase_for_user_with_plan(user_id: str, plan_id: int) -> Optional[Dict]:
    """
    Versión extendida que considera el plan del usuario
    Útil para analytics y personalización futura
    """
    phrase = get_smart_phrase_for_user(user_id)
    if phrase:
        # Re-registrar con plan_id para analytics
        record_phrase_sent(user_id, phrase['id'], plan_id)
    return phrase

def get_random_phrase_smart() -> Optional[Dict]:
    """
    Función de compatibilidad que funciona sin user_id
    Fallback al sistema original si no hay user_id disponible
    """
    logger.warning("get_random_phrase_smart called without user_id, falling back to original random")
    return _get_original_random_phrase()

# =====================================================
# FUNCIONES DE ANALYTICS Y DEBUGGING
# =====================================================

def get_user_phrase_stats(user_id: str) -> Dict:
    """
    Obtiene estadísticas de frases para un usuario
    Útil para debugging y analytics
    """
    try:
        supabase = get_supabase_client()
        
        # Total de frases disponibles
        total_phrases = supabase.table('phrases').select('*', count='exact').execute()
        total_count = total_phrases.count or 0
        
        # Frases recibidas por el usuario
        user_phrases = supabase.table('user_phrase_history').select('*', count='exact').eq('user_id', user_id).eq('email_status', 'sent').execute()
        received_count = user_phrases.count or 0
        
        # Última frase recibida
        last_phrase = None
        if user_phrases.data:
            last_phrase_record = max(user_phrases.data, key=lambda x: x['sent_at'])
            last_phrase = last_phrase_record['sent_at']
        
        completion_percentage = (received_count / max(total_count, 1)) * 100
        
        return {
            'user_id': user_id,
            'total_phrases_available': total_count,
            'phrases_received': received_count,
            'phrases_remaining': max(0, total_count - received_count),
            'completion_percentage': round(completion_percentage, 2),
            'last_phrase_sent': last_phrase,
            'cycle_completed': received_count >= total_count
        }
        
    except Exception as e:
        logger.error("Error getting user phrase stats", user_id=user_id, error=str(e))
        return {
            'user_id': user_id,
            'error': str(e)
        }

def test_smart_system():
    """
    Función de testing para verificar que el sistema funciona
    """
    logger.info("Testing smart phrase system...")
    
    # Test sin user_id (fallback)
    phrase1 = get_random_phrase_smart()
    logger.info("Test 1 (no user_id)", phrase=phrase1 is not None)
    
    # Test con user_id fake
    test_user_id = "12345678-1234-1234-1234-123456789012"
    phrase2 = get_smart_phrase_for_user(test_user_id)
    logger.info("Test 2 (with user_id)", phrase=phrase2 is not None, user_id=test_user_id)
    
    # Test estadísticas
    stats = get_user_phrase_stats(test_user_id)
    logger.info("Test 3 (stats)", stats=stats)
    
    logger.info("Smart phrase system test completed")

if __name__ == "__main__":
    test_smart_system()