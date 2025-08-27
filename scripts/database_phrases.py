"""
Database functions para manejar frases desde Supabase
"""
import os
import random
from typing import Dict, List, Optional
from supabase import create_client
import structlog

logger = structlog.get_logger()

def get_supabase_client():
    """Get Supabase client for phrases"""
    return create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )

def get_random_phrase() -> Optional[Dict]:
    """
    Obtiene una frase aleatoria desde Supabase
    Reemplaza la función load_phrases() del CSV
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
            "Phrase selected",
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
        logger.error("Error getting phrase from database", error=str(e))
        return None

def get_phrase_by_author(author: str) -> Optional[Dict]:
    """Obtiene una frase aleatoria de un autor específico"""
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
    """Obtiene el total de frases en la base de datos"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('phrases').select('count').execute()
        return len(result.data) if result.data else 0
    except Exception as e:
        logger.error("Error counting phrases", error=str(e))
        return 0

def get_authors_list() -> List[str]:
    """Obtiene lista única de autores"""
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

# Función de compatibilidad con el código existente
def load_phrases() -> List[Dict]:
    """
    Load all phrases from Supabase database
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