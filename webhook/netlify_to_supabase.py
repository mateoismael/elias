#!/usr/bin/env python3
"""
Webhook endpoint para automatizar Netlify Forms → Supabase
Recibe nuevas suscripciones de Netlify y las crea automáticamente en Supabase
"""
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import structlog
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Import Supabase directly (webhook is standalone)
try:
    from supabase import create_client, Client
except ImportError:
    print("[ERROR] Supabase not installed. Run: pip install supabase")
    sys.exit(1)

# Configure logging
logger = structlog.get_logger()

app = Flask(__name__)

# Initialize Supabase client
def get_supabase():
    """Get Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
    
    return create_client(url, key)

def get_user_by_email(supabase, email: str):
    """Get user by email address"""
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Failed to get user by email", email=email, error=str(e))
        return None

def create_user(supabase, email: str):
    """Create new user"""
    try:
        response = supabase.table('users').insert({'email': email}).execute()
        if response.data:
            logger.info("User created", email=email, user_id=response.data[0]['id'])
            return response.data[0]
        return None
    except Exception as e:
        logger.error("Failed to create user", email=email, error=str(e))
        return None

def get_user_subscription(supabase, email: str):
    """Get active subscription for user"""
    try:
        response = supabase.table('subscriptions').select(
            '*, users!inner(email)'
        ).eq('users.email', email).eq('status', 'active').execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Failed to get user subscription", email=email, error=str(e))
        return None

def cancel_existing_subscriptions(supabase, user_id: str):
    """Cancel all existing active subscriptions for a user"""
    try:
        response = supabase.table('subscriptions').update({
            'status': 'cancelled',
            'cancelled_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }).eq('user_id', user_id).eq('status', 'active').execute()
        
        if response.data:
            logger.info("Cancelled existing subscriptions", user_id=user_id, count=len(response.data))
        return True
    except Exception as e:
        logger.error("Failed to cancel existing subscriptions", user_id=user_id, error=str(e))
        return False

def create_or_update_subscription(supabase, user_id: str, plan_id: int):
    """Create a new subscription or update existing one"""
    try:
        # First check if there's an active subscription
        existing = supabase.table('subscriptions').select('*').eq(
            'user_id', user_id
        ).eq('status', 'active').execute()
        
        if existing.data:
            # Update existing subscription
            response = supabase.table('subscriptions').update({
                'plan_id': plan_id,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', existing.data[0]['id']).execute()
            
            if response.data:
                logger.info("Subscription updated", 
                           user_id=user_id, 
                           subscription_id=existing.data[0]['id'],
                           new_plan_id=plan_id)
                return 'updated'
        else:
            # Create new subscription
            response = supabase.table('subscriptions').insert({
                'user_id': user_id,
                'plan_id': plan_id,
                'status': 'active',
                'started_at': datetime.utcnow().isoformat()
            }).execute()
            
            if response.data:
                logger.info("Subscription created", 
                           user_id=user_id,
                           subscription_id=response.data[0]['id'],
                           plan_id=plan_id)
                return 'created'
        
        return None
    except Exception as e:
        logger.error("Failed to create/update subscription", 
                    user_id=user_id, 
                    plan_id=plan_id, 
                    error=str(e))
        return None

def get_all_active_subscribers(supabase):
    """Get all active subscribers with their plan details"""
    try:
        response = supabase.table('subscriptions').select(
            '*, users!inner(email), subscription_plans!inner(*)'
        ).eq('status', 'active').execute()
        
        subscribers = []
        for data in response.data:
            subscribers.append({
                'email': data['users']['email'],
                'frequency_hours': data['subscription_plans']['frequency_hours'],
                'plan_name': data['subscription_plans']['name'],
                'max_emails_per_day': data['subscription_plans']['max_emails_per_day']
            })
        
        return subscribers
    except Exception as e:
        logger.error("Failed to get active subscribers", error=str(e))
        return []

def validate_netlify_webhook(data: Dict[str, Any]) -> bool:
    """Validar que el webhook viene de Netlify con los datos correctos"""
    required_fields = ['email']
    
    # Verificar que tenga los campos mínimos
    for field in required_fields:
        if field not in data:
            logger.warning("Missing required field in webhook", field=field, data=data)
            return False
    
    # Validar formato de email básico
    email = data.get('email', '').strip()
    if not email or '@' not in email:
        logger.warning("Invalid email format", email=email)
        return False
    
    return True

def map_frequency_to_plan_id(frequency: str) -> int:
    """Mapear frecuencia a plan_id - Modelo Simplificado"""
    # MODELO SIMPLIFICADO:
    # Plan 1 = GRATUITO (6 horas, 3 frases/día) - S/ 0.00
    # Plan 2 = PREMIUM (1h, 3h, 24h) - S/ 5.00
    
    if str(frequency) == '6':
        plan_id = 1  # Plan gratuito
    else:
        plan_id = 2  # Plan premium (cualquier otra frecuencia)
    
    logger.info("Frequency mapping", frequency=frequency, plan_id=plan_id, 
               plan_type="free" if plan_id == 1 else "premium")
    return plan_id

@app.route('/webhook/netlify-form', methods=['POST', 'OPTIONS'])
def handle_netlify_form():
    """Endpoint principal para recibir webhooks de Netlify Forms"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        # Obtener datos del webhook
        if request.is_json:
            data = request.get_json()
        else:
            # Netlify puede enviar como form data
            data = request.form.to_dict()
        
        logger.info("Webhook received", 
                   data=data,
                   content_type=request.content_type,
                   headers=dict(request.headers))
        
        # Validar datos
        if not validate_netlify_webhook(data):
            response = jsonify({
                'status': 'error',
                'message': 'Invalid webhook data'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400
        
        # Extraer datos del formulario
        email = data.get('email', '').strip().lower()
        frequency = data.get('frequency', '6')  # Default: 6 horas (3 frases/día)
        
        # Solo permitir plan gratuito (6 horas) por ahora
        if frequency != '6':
            frequency = '6'  # Force free plan
        
        plan_id = map_frequency_to_plan_id(frequency)
        
        logger.info("Processing subscription change", 
                   email=email, 
                   frequency=frequency, 
                   plan_id=plan_id)
        
        # Conectar a Supabase
        supabase = get_supabase()
        
        # Verificar si el usuario existe
        existing_user = get_user_by_email(supabase, email)
        
        if existing_user:
            # Usuario existe - actualizar o crear suscripción
            logger.info("Existing user found", 
                       email=email, 
                       user_id=existing_user['id'])
            
            action = create_or_update_subscription(supabase, existing_user['id'], plan_id)
            
            if action:
                response = jsonify({
                    'status': 'success',
                    'message': f'Subscription {action}',
                    'user_id': existing_user['id'],
                    'plan_id': plan_id,
                    'action': action
                })
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            else:
                response = jsonify({
                    'status': 'error',
                    'message': 'Failed to update subscription'
                })
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 500
        
        # Crear nuevo usuario
        user = create_user(supabase, email)
        if not user:
            logger.error("Failed to create user", email=email)
            response = jsonify({
                'status': 'error',
                'message': 'Failed to create user'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500
        
        # Crear suscripción para nuevo usuario
        action = create_or_update_subscription(supabase, user['id'], plan_id)
        
        if not action:
            logger.error("Failed to create subscription for new user", 
                        email=email, 
                        user_id=user['id'])
            response = jsonify({
                'status': 'error',
                'message': 'Failed to create subscription'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500
        
        logger.info("New user and subscription created successfully",
                   email=email,
                   user_id=user['id'],
                   plan_id=plan_id,
                   frequency=frequency)
        
        response = jsonify({
            'status': 'success',
            'message': 'User created successfully',
            'user_id': user['id'],
            'plan_id': plan_id,
            'action': 'created'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e), exc_info=True)
        response = jsonify({
            'status': 'error',
            'message': 'Internal server error'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

@app.route('/webhook/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test Supabase connection
        supabase = get_supabase()
        plans_response = supabase.table('subscription_plans').select('count').execute()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'supabase_connection': 'ok'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/webhook/stats', methods=['GET'])
def get_stats():
    """Endpoint para ver estadísticas de suscriptores"""
    try:
        supabase = get_supabase()
        subscribers = get_all_active_subscribers(supabase)
        
        # Calcular estadísticas por plan
        plan_stats = {}
        for sub in subscribers:
            plan_name = sub['plan_name']
            plan_stats[plan_name] = plan_stats.get(plan_name, 0) + 1
        
        return jsonify({
            'total_subscribers': len(subscribers),
            'plan_distribution': plan_stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/unsubscribe', methods=['POST', 'OPTIONS'])
def handle_unsubscribe():
    """Endpoint para procesar desuscripciones desde unsubscribe.html"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        # Obtener datos del request
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        email = data.get('email', '').strip().lower()
        
        if not email:
            response = jsonify({
                'status': 'error',
                'message': 'Email requerido'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400
        
        if '@' not in email:
            response = jsonify({
                'status': 'error',
                'message': 'Email inválido'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400
        
        logger.info("Processing unsubscribe request", email=email)
        
        # Conectar a Supabase
        supabase = get_supabase()
        
        # Verificar si el usuario existe
        user = get_user_by_email(supabase, email)
        if not user:
            response = jsonify({
                'status': 'error',
                'message': 'Email no encontrado en nuestro sistema'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 404
        
        # Cancelar todas las suscripciones activas
        cancelled = cancel_existing_subscriptions(supabase, user['id'])
        
        if cancelled:
            logger.info("Subscription cancelled successfully", email=email, user_id=user['id'])
            response = jsonify({
                'status': 'success',
                'message': 'Suscripción cancelada exitosamente',
                'email': email
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        else:
            logger.warning("Failed to cancel subscription", email=email, user_id=user['id'])
            response = jsonify({
                'status': 'error',
                'message': 'Error al cancelar la suscripción'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500
            
    except Exception as e:
        logger.error("Unsubscribe processing failed", error=str(e), exc_info=True)
        response = jsonify({
            'status': 'error',
            'message': 'Error interno del servidor'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

if __name__ == '__main__':
    # Solo para testing local
    app.run(debug=True, port=5000)