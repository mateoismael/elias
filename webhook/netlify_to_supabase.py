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
import jwt
import base64

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

# Global CORS configuration
@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

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

def get_user_by_google_id(supabase, google_id: str):
    """Get user by Google ID"""
    try:
        response = supabase.table('users').select('*').eq('google_id', google_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Failed to get user by Google ID", google_id=google_id, error=str(e))
        return None

def create_user_google(supabase, email: str, name: str, google_id: str, avatar_url: str = None):
    """Create new user with Google authentication"""
    try:
        user_data = {
            'email': email,
            'name': name,
            'google_id': google_id,
            'auth_method': 'google'
        }
        if avatar_url:
            user_data['avatar_url'] = avatar_url
            
        response = supabase.table('users').insert(user_data).execute()
        if response.data:
            logger.info("User created with Google", email=email, google_id=google_id, user_id=response.data[0]['id'])
            return response.data[0]
        return None
    except Exception as e:
        logger.error("Failed to create user with Google", email=email, google_id=google_id, error=str(e))
        return None

def create_user(supabase, email: str):
    """Create new user (legacy email method)"""
    try:
        response = supabase.table('users').insert({
            'email': email,
            'auth_method': 'email'
        }).execute()
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
    """Mapear frecuencia a plan_id - MODELO OPTIMIZADO 2025 (Deliverability-Safe)"""
    # NUEVO MODELO 2025 (Plan ID = Emails por día):
    # Plan 0 = GRATUITO (3/semana L-M-V) - S/ 0.00
    # Plan 1 = PREMIUM 1/día (24h) - S/ 5.00
    # Plan 2 = PREMIUM 2/día (12h) - S/ 5.00  
    # Plan 3 = PREMIUM 3/día (8h) - S/ 5.00
    # Plan 4 = PREMIUM 4/día (6h) - S/ 5.00
    # Plan 13 = PREMIUM Power User 13/día (1h) - OCULTO/MANUAL
    
    frequency_str = str(frequency)
    
    if frequency_str == 'weekly-3' or frequency_str == '56':
        plan_id = 0  # Plan gratuito (3/semana L-M-V)
    elif frequency_str == '1-daily' or frequency_str == '24':
        plan_id = 1  # Premium 1/día
    elif frequency_str == '2-daily' or frequency_str == '12':
        plan_id = 2  # Premium 2/día
    elif frequency_str == '3-daily' or frequency_str == '8':
        plan_id = 3  # Premium 3/día
    elif frequency_str == '4-daily' or frequency_str == '6':
        plan_id = 4  # Premium 4/día
    elif frequency_str == '1':
        plan_id = 13  # Premium Power User (13/día - solo manual/VIP)
    else:
        # Default a plan gratuito para frecuencias no reconocidas
        plan_id = 0
        logger.warning("Unknown frequency, defaulting to free plan", frequency=frequency)
    
    plan_type = "free" if plan_id == 0 else "premium"
    logger.info("Frequency mapping 2025", frequency=frequency, plan_id=plan_id, plan_type=plan_type)
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
        frequency = data.get('frequency', 'weekly-3')  # Default: 3 por semana (plan gratuito)
        
        # Solo permitir plan gratuito (3 por semana) por ahora desde landing page
        if frequency not in ['weekly-3', '56']:
            frequency = 'weekly-3'  # Force free plan (deliverability-safe)
        
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
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
    try:
        # Obtener datos del request
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                'status': 'error',
                'message': 'Email requerido'
            }), 400
        
        if '@' not in email:
            return jsonify({
                'status': 'error',
                'message': 'Email inválido'
            }), 400
        
        logger.info("Processing unsubscribe request", email=email)
        
        # Conectar a Supabase
        supabase = get_supabase()
        
        # Verificar si el usuario existe
        user = get_user_by_email(supabase, email)
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'Email no encontrado en nuestro sistema'
            }), 404
        
        # Cancelar todas las suscripciones activas
        cancelled = cancel_existing_subscriptions(supabase, user['id'])
        
        if cancelled:
            logger.info("Subscription cancelled successfully", email=email, user_id=user['id'])
            return jsonify({
                'status': 'success',
                'message': 'Suscripción cancelada exitosamente',
                'email': email
            })
        else:
            logger.warning("Failed to cancel subscription", email=email, user_id=user['id'])
            return jsonify({
                'status': 'error',
                'message': 'Error al cancelar la suscripción'
            }), 500
            
    except Exception as e:
        logger.error("Unsubscribe processing failed", error=str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error interno del servidor'
        }), 500

@app.route('/webhook/google-signin', methods=['POST', 'OPTIONS'])
def handle_google_signin():
    """Endpoint para procesar autenticación con Google"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        data = request.get_json()
        credential = data.get('credential')
        frequency = data.get('frequency', 'weekly-3')  # Default to free plan
        
        if not credential:
            response = jsonify({
                'success': False,
                'error': 'Missing credential'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400
        
        # Verify JWT token from Google using Google's official method
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
            
            # Your Google client ID
            CLIENT_ID = "970302400473-3umkhto0uhqs08p5njnhbm90in9lcp49.apps.googleusercontent.com"
            
            # Verify the token with Google's official verification
            idinfo = id_token.verify_oauth2_token(credential, requests.Request(), CLIENT_ID)
            
            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            # Extract verified user information
            email = idinfo.get('email', '').strip().lower()
            name = idinfo.get('name', '')
            google_id = idinfo.get('sub')
            avatar_url = idinfo.get('picture')
            
            logger.info("Verified Google token successfully", 
                       email=email, 
                       has_name=bool(name),
                       has_google_id=bool(google_id))
            
            if not email or not google_id:
                raise ValueError(f"Missing required fields: email={bool(email)}, google_id={bool(google_id)}")
                
        except Exception as e:
            logger.error("Failed to verify Google token", 
                        error=str(e), 
                        credential_length=len(credential) if credential else 0)
            response = jsonify({
                'success': False,
                'error': f'Invalid Google token: {str(e)}'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400
        
        logger.info("Processing Google Sign-In", email=email, google_id=google_id[:10] + "...")
        
        # Connect to Supabase
        supabase = get_supabase()
        
        # Map frequency to plan ID (using new 2025 model)
        plan_id = map_frequency_to_plan_id(frequency)
        
        # Check if user exists by Google ID
        existing_user = get_user_by_google_id(supabase, google_id)
        
        if existing_user:
            # Update existing user subscription
            logger.info("Existing Google user found", 
                       email=email, 
                       user_id=existing_user['id'])
            
            # Update user info if needed
            if existing_user.get('name') != name or existing_user.get('avatar_url') != avatar_url:
                supabase.table('users').update({
                    'name': name,
                    'avatar_url': avatar_url,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', existing_user['id']).execute()
            
            action = create_or_update_subscription(supabase, existing_user['id'], plan_id)
            user = existing_user
        else:
            # Check if user exists by email (for migration from email-only accounts)
            email_user = get_user_by_email(supabase, email) if email else None
            
            if email_user:
                # Update existing email user with Google ID
                supabase.table('users').update({
                    'google_id': google_id,
                    'name': name,
                    'avatar_url': avatar_url,
                    'auth_method': 'both',
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', email_user['id']).execute()
                
                logger.info("Updated email user with Google ID", 
                           email=email, 
                           user_id=email_user['id'])
                
                action = create_or_update_subscription(supabase, email_user['id'], plan_id)
                user = email_user
            else:
                # Create new user with Google authentication
                user = create_user_google(supabase, email, name, google_id, avatar_url)
                if not user:
                    response = jsonify({
                        'success': False,
                        'error': 'Failed to create user'
                    })
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    return response, 500
                
                action = create_or_update_subscription(supabase, user['id'], plan_id)
        
        if not action:
            logger.error("Failed to create/update subscription", 
                        email=email, 
                        user_id=user['id'])
            response = jsonify({
                'success': False,
                'error': 'Failed to create subscription'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500
        
        logger.info("Google Sign-In completed successfully",
                   email=email,
                   user_id=user['id'],
                   plan_id=plan_id,
                   frequency=frequency,
                   action=action)
        
        response = jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user.get('name', ''),
                'auth_method': user.get('auth_method', 'google')
            },
            'subscription': {
                'plan_id': plan_id,
                'frequency': frequency,
                'action': action
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error("Google Sign-In processing failed", error=str(e), exc_info=True)
        response = jsonify({
            'success': False,
            'error': 'Internal server error'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

if __name__ == '__main__':
    # Solo para testing local
    app.run(debug=True, port=5000)