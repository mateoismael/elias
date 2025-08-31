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
import mercadopago
import requests
import hashlib
import hmac

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

# Initialize MercadoPago SDK
def get_mercadopago_sdk():
    """Get MercadoPago SDK client"""
    environment = os.getenv('MERCADOPAGO_ENVIRONMENT', 'sandbox')
    
    if environment == 'production':
        access_token = os.getenv('MERCADOPAGO_ACCESS_TOKEN')
    else:
        access_token = os.getenv('MERCADOPAGO_ACCESS_TOKEN_TEST')
    
    if not access_token:
        raise ValueError(f"MercadoPago access token not found for {environment} environment")
    
    sdk = mercadopago.SDK(access_token)
    logger.info("MercadoPago SDK initialized", environment=environment)
    return sdk

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

@app.route('/webhook/user-subscription', methods=['POST', 'OPTIONS'])
def get_user_subscription():
    """Obtener estado de suscripción del usuario para dashboard"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            response = jsonify({
                'success': False,
                'error': 'Email válido requerido'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400
        
        logger.info("Getting user subscription status", email=email)
        
        # Conectar a Supabase
        supabase = get_supabase()
        
        # Obtener usuario con estadísticas de email
        user = get_user_by_email(supabase, email)
        if not user:
            response = jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 404
        
        # Obtener suscripción activa con detalles del plan
        subscription_response = supabase.table('subscriptions').select(
            '*, subscription_plans!inner(*)'
        ).eq('user_id', user['id']).eq('status', 'active').execute()
        
        if subscription_response.data:
            subscription = subscription_response.data[0]
            plan = subscription['subscription_plans']
            
            response_data = {
                'success': True,
                'user_id': user['id'],
                'user_stats': {
                    'total_emails_sent': user.get('total_emails_sent', 0),
                    'last_email_sent_at': user.get('last_email_sent_at'),
                    'member_since': user.get('created_at')
                },
                'subscription': {
                    'id': subscription['id'],
                    'plan_id': subscription['plan_id'],
                    'status': subscription['status'],
                    'started_at': subscription['started_at'],
                    'plan_details': {
                        'name': plan['name'],
                        'display_name': plan['display_name'],
                        'price_soles': plan['price_soles'],
                        'frequency_hours': plan['frequency_hours'],
                        'max_emails_per_day': plan['max_emails_per_day'],
                        'description': plan['description']
                    }
                },
                'plan_id': subscription['plan_id']
            }
        else:
            # No active subscription, return default free plan
            response_data = {
                'success': True,
                'user_id': user['id'],
                'user_stats': {
                    'total_emails_sent': user.get('total_emails_sent', 0),
                    'last_email_sent_at': user.get('last_email_sent_at'),
                    'member_since': user.get('created_at')
                },
                'subscription': None,
                'plan_id': 0
            }
        
        logger.info("User subscription retrieved", email=email, plan_id=response_data['plan_id'])
        
        response = jsonify(response_data)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error("Error getting user subscription", error=str(e), exc_info=True)
        response = jsonify({
            'success': False,
            'error': 'Error interno del servidor'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

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

def create_subscription_plan(mp_sdk, plan_details):
    """Crear plan de suscripción mensual en MercadoPago"""
    try:
        plan_data = {
            "reason": f"Pseudosapiens {plan_details['display_name']} - Suscripción Mensual",
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "billing_day": 1,  # Día 1 de cada mes
                "billing_day_proportional": True,  # Prorratear primer pago
                "transaction_amount": float(plan_details['price_soles']),
                "currency_id": "PEN"
            },
            "payment_methods_allowed": {
                "payment_types": [
                    {"id": "credit_card"},
                    {"id": "debit_card"},
                    {"id": "account_money"},  # Yape/billetera
                    {"id": "digital_wallet"}
                ],
                "payment_methods": []
            },
            "back_url": "https://pseudosapiens.com/success.html?premium=true"
        }
        
        # Usar API directa porque el SDK Python no soporta subscriptions aún
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('MERCADOPAGO_ACCESS_TOKEN_TEST') if os.getenv('MERCADOPAGO_ENVIRONMENT') == 'sandbox' else os.getenv('MERCADOPAGO_ACCESS_TOKEN')}"
        }
        
        base_url = "https://api.mercadolibre.com" if os.getenv('MERCADOPAGO_ENVIRONMENT') == 'sandbox' else "https://api.mercadopago.com"
        response = requests.post(f"{base_url}/preapproval_plan", json=plan_data, headers=headers)
        
        if response.status_code == 201:
            return response.json()
        else:
            logger.error("Failed to create subscription plan", 
                        status=response.status_code, 
                        error=response.text)
            return None
            
    except Exception as e:
        logger.error("Error creating subscription plan", error=str(e))
        return None

def create_monthly_subscription(user, plan_details, plan_id):
    """Crear suscripción mensual automática"""
    try:
        # Primero crear el plan si no existe
        plan_response = create_subscription_plan(None, plan_details)
        if not plan_response:
            return None
        
        # Crear suscripción mensual
        subscription_data = {
            "preapproval_plan_id": plan_response['id'],
            "reason": f"Suscripción Mensual Pseudosapiens {plan_details['display_name']}",
            "external_reference": f"pseudosapiens_sub_{user['id']}_{plan_id}",
            "payer_email": user['email'],
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "start_date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "transaction_amount": float(plan_details['price_soles']),
                "currency_id": "PEN"
            },
            "back_urls": {
                "success": "https://pseudosapiens.com/success.html?premium=true&subscription=true",
                "failure": "https://pseudosapiens.com/?error=subscription_failed",
                "pending": "https://pseudosapiens.com/?status=subscription_pending"
            },
            "notification_url": "https://elias-webhook.vercel.app/webhook/mercadopago-subscription"
        }
        
        # API directa para suscripciones
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('MERCADOPAGO_ACCESS_TOKEN_TEST') if os.getenv('MERCADOPAGO_ENVIRONMENT') == 'sandbox' else os.getenv('MERCADOPAGO_ACCESS_TOKEN')}"
        }
        
        base_url = "https://api.mercadolibre.com" if os.getenv('MERCADOPAGO_ENVIRONMENT') == 'sandbox' else "https://api.mercadopago.com"
        response = requests.post(f"{base_url}/preapproval", json=subscription_data, headers=headers)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error("Failed to create subscription", 
                        status=response.status_code, 
                        error=response.text)
            return None
            
    except Exception as e:
        logger.error("Error creating subscription", error=str(e))
        return None

@app.route('/webhook/create-premium-subscription', methods=['POST', 'OPTIONS'])
def create_premium_subscription():
    """Crear suscripción premium mensual automática con MercadoPago"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        plan_id = data.get('plan_id', 2)  # Default premium plan
        
        if not email or '@' not in email:
            response = jsonify({
                'success': False,
                'error': 'Email válido requerido'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 400
        
        logger.info("Creating monthly subscription", email=email, plan_id=plan_id)
        
        # Conectar a Supabase para verificar usuario
        supabase = get_supabase()
        user = get_user_by_email(supabase, email)
        
        if not user:
            # Crear usuario si no existe
            user = create_user(supabase, email)
            if not user:
                response = jsonify({
                    'success': False,
                    'error': 'Error creating user'
                })
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 500
        
        # Obtener detalles del plan
        plan_response = supabase.table('subscription_plans').select('*').eq('id', plan_id).execute()
        if not plan_response.data:
            response = jsonify({
                'success': False,
                'error': 'Plan no encontrado'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 404
        
        plan = plan_response.data[0]
        
        # Crear suscripción mensual automática
        subscription_result = create_monthly_subscription(user, plan, plan_id)
        
        if subscription_result:
            logger.info("Monthly subscription created successfully", 
                       email=email,
                       subscription_id=subscription_result.get('id'),
                       user_id=user['id'],
                       init_point=subscription_result.get('init_point'))
            
            response = jsonify({
                'success': True,
                'subscription_id': subscription_result.get('id'),
                'init_point': subscription_result.get('init_point'),
                'sandbox_init_point': subscription_result.get('sandbox_init_point'),
                'plan_name': plan['display_name'],
                'amount': plan['price_soles'],
                'billing_type': 'monthly_recurring',
                'next_billing_date': subscription_result.get('next_payment_date')
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        else:
            response = jsonify({
                'success': False,
                'error': 'Error creando suscripción mensual'
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500
            
    except Exception as e:
        logger.error("Monthly subscription creation failed", error=str(e), exc_info=True)
        response = jsonify({
            'success': False,
            'error': 'Error interno del servidor'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

def validate_mercadopago_signature(request_body: str, signature_header: str, secret_key: str) -> bool:
    """Validar la firma de MercadoPago según especificación 2025"""
    try:
        if not signature_header:
            logger.warning("Missing x-signature header")
            return False
        
        # Extraer timestamp y firma del header x-signature
        signature_parts = signature_header.split(',')
        if len(signature_parts) != 2:
            logger.warning("Invalid x-signature format")
            return False
        
        ts = None
        v1_signature = None
        
        for part in signature_parts:
            if part.startswith('ts='):
                ts = part.split('=')[1]
            elif part.startswith('v1='):
                v1_signature = part.split('=')[1]
        
        if not ts or not v1_signature:
            logger.warning("Missing ts or v1 in x-signature")
            return False
        
        # Crear template según especificación MercadoPago 2025
        # Format: id:PAYMENT_ID;request-id:REQUEST_ID;ts:TIMESTAMP;
        data = json.loads(request_body)
        payment_id = data.get('data', {}).get('id', '')
        request_id = request.headers.get('x-request-id', '')
        
        template = f"id:{payment_id};request-id:{request_id};ts:{ts};"
        
        # Calcular HMAC SHA256
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            template.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Comparar firmas
        is_valid = hmac.compare_digest(expected_signature, v1_signature)
        
        logger.info("MercadoPago signature validation", 
                   is_valid=is_valid,
                   payment_id=payment_id,
                   template=template)
        
        return is_valid
        
    except Exception as e:
        logger.error("Error validating MercadoPago signature", error=str(e))
        return False

@app.route('/webhook/mercadopago-notification', methods=['POST'])
def handle_mercadopago_notification():
    """Procesar notificaciones de MercadoPago"""
    try:
        # Obtener datos de la notificación
        request_body = request.get_data(as_text=True)
        signature_header = request.headers.get('x-signature', '')
        
        logger.info("MercadoPago webhook received", 
                   headers=dict(request.headers),
                   body_length=len(request_body))
        
        # Validar firma (en producción)
        environment = os.getenv('MERCADOPAGO_ENVIRONMENT', 'sandbox')
        if environment == 'production':
            secret_key = os.getenv('MERCADOPAGO_WEBHOOK_SECRET')
            if secret_key and not validate_mercadopago_signature(request_body, signature_header, secret_key):
                logger.warning("Invalid MercadoPago signature")
                return jsonify({'status': 'invalid_signature'}), 401
        
        # Parsear datos
        try:
            data = json.loads(request_body)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in MercadoPago webhook")
            return jsonify({'status': 'invalid_json'}), 400
        
        # Procesar solo notificaciones de pago
        if data.get('type') == 'payment':
            payment_id = data.get('data', {}).get('id')
            
            if not payment_id:
                logger.warning("Missing payment ID in notification")
                return jsonify({'status': 'missing_payment_id'}), 400
            
            logger.info("Processing payment notification", payment_id=payment_id)
            
            # Obtener detalles del pago usando MercadoPago SDK
            mp_sdk = get_mercadopago_sdk()
            payment_response = mp_sdk.payment().get(payment_id)
            
            if payment_response['status'] != 200:
                logger.error("Failed to get payment details from MercadoPago", 
                           payment_id=payment_id,
                           status=payment_response['status'])
                return jsonify({'status': 'payment_not_found'}), 404
            
            payment_info = payment_response['response']
            logger.info("Payment details retrieved", 
                       payment_id=payment_id,
                       status=payment_info.get('status'),
                       external_reference=payment_info.get('external_reference'))
            
            # Procesar pago aprobado
            if payment_info.get('status') == 'approved':
                external_ref = payment_info.get('external_reference', '')
                
                if external_ref.startswith('pseudosapiens_'):
                    try:
                        # Parsear referencia: pseudosapiens_{user_id}_{plan_id}
                        parts = external_ref.split('_')
                        if len(parts) >= 3:
                            user_id = parts[1]
                            plan_id = int(parts[2])
                            
                            # Conectar a Supabase
                            supabase = get_supabase()
                            
                            # Activar suscripción premium
                            action = create_or_update_subscription(supabase, user_id, plan_id)
                            
                            if action:
                                # Registrar pago en base de datos
                                payment_record = {
                                    'subscription_id': None,  # Will be updated with subscription ID
                                    'mercadopago_payment_id': str(payment_id),
                                    'amount': float(payment_info.get('transaction_amount', 0)),
                                    'currency': payment_info.get('currency_id', 'PEN'),
                                    'status': 'approved',
                                    'payment_date': payment_info.get('date_approved'),
                                    'payment_method': payment_info.get('payment_type_id', 'mercadopago')
                                }
                                
                                # Obtener subscription_id actual
                                subscription = supabase.table('subscriptions').select('id').eq(
                                    'user_id', user_id
                                ).eq('status', 'active').execute()
                                
                                if subscription.data:
                                    payment_record['subscription_id'] = subscription.data[0]['id']
                                
                                # Insertar registro de pago
                                supabase.table('payments').insert(payment_record).execute()
                                
                                logger.info("Premium subscription activated and payment recorded",
                                           user_id=user_id,
                                           plan_id=plan_id,
                                           payment_id=payment_id,
                                           amount=payment_record['amount'])
                            else:
                                logger.error("Failed to activate premium subscription",
                                           user_id=user_id,
                                           plan_id=plan_id,
                                           payment_id=payment_id)
                        else:
                            logger.warning("Invalid external_reference format", external_ref=external_ref)
                            
                    except (ValueError, IndexError) as e:
                        logger.error("Error parsing external_reference", 
                                   external_ref=external_ref,
                                   error=str(e))
                else:
                    logger.info("Payment not for Pseudosapiens", external_ref=external_ref)
            
            elif payment_info.get('status') in ['cancelled', 'rejected']:
                logger.info("Payment was cancelled or rejected", 
                           payment_id=payment_id,
                           status=payment_info.get('status'))
            
            else:
                logger.info("Payment in pending status", 
                           payment_id=payment_id,
                           status=payment_info.get('status'))
        
        else:
            logger.info("Non-payment notification received", type=data.get('type'))
        
        # IMPORTANTE: Siempre devolver 200 OK para evitar reenvíos
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error("MercadoPago webhook processing failed", error=str(e), exc_info=True)
        # Devolver 200 para evitar reenvíos en caso de errores
        return jsonify({'status': 'error'}), 200

@app.route('/webhook/mercadopago-subscription', methods=['POST'])
def handle_mercadopago_subscription():
    """Procesar notificaciones de suscripciones MercadoPago"""
    try:
        # Obtener datos de la notificación
        request_body = request.get_data(as_text=True)
        signature_header = request.headers.get('x-signature', '')
        
        logger.info("MercadoPago subscription webhook received", 
                   headers=dict(request.headers),
                   body_length=len(request_body))
        
        # Validar firma (en producción)
        environment = os.getenv('MERCADOPAGO_ENVIRONMENT', 'sandbox')
        if environment == 'production':
            secret_key = os.getenv('MERCADOPAGO_WEBHOOK_SECRET')
            if secret_key and not validate_mercadopago_signature(request_body, signature_header, secret_key):
                logger.warning("Invalid MercadoPago subscription signature")
                return jsonify({'status': 'invalid_signature'}), 401
        
        # Parsear datos
        try:
            data = json.loads(request_body)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in MercadoPago subscription webhook")
            return jsonify({'status': 'invalid_json'}), 400
        
        # Procesar notificaciones de suscripción
        if data.get('type') == 'subscription':
            subscription_id = data.get('data', {}).get('id')
            
            if not subscription_id:
                logger.warning("Missing subscription ID in notification")
                return jsonify({'status': 'missing_subscription_id'}), 400
            
            logger.info("Processing subscription notification", subscription_id=subscription_id)
            
            # Obtener detalles de la suscripción usando API directa
            headers = {
                "Authorization": f"Bearer {os.getenv('MERCADOPAGO_ACCESS_TOKEN_TEST') if environment == 'sandbox' else os.getenv('MERCADOPAGO_ACCESS_TOKEN')}"
            }
            
            base_url = "https://api.mercadolibre.com" if environment == 'sandbox' else "https://api.mercadopago.com"
            subscription_response = requests.get(f"{base_url}/preapproval/{subscription_id}", headers=headers)
            
            if subscription_response.status_code != 200:
                logger.error("Failed to get subscription details from MercadoPago", 
                           subscription_id=subscription_id,
                           status=subscription_response.status_code)
                return jsonify({'status': 'subscription_not_found'}), 404
            
            subscription_info = subscription_response.json()
            logger.info("Subscription details retrieved", 
                       subscription_id=subscription_id,
                       status=subscription_info.get('status'),
                       external_reference=subscription_info.get('external_reference'))
            
            # Procesar estados de suscripción
            subscription_status = subscription_info.get('status')
            external_ref = subscription_info.get('external_reference', '')
            
            if external_ref.startswith('pseudosapiens_sub_'):
                try:
                    # Parsear referencia: pseudosapiens_sub_{user_id}_{plan_id}
                    parts = external_ref.split('_')
                    if len(parts) >= 4:
                        user_id = parts[2]
                        plan_id = int(parts[3])
                        
                        # Conectar a Supabase
                        supabase = get_supabase()
                        
                        if subscription_status == 'authorized':
                            # Suscripción autorizada - activar premium
                            action = create_or_update_subscription(supabase, user_id, plan_id)
                            
                            if action:
                                logger.info("Monthly subscription activated",
                                           user_id=user_id,
                                           plan_id=plan_id,
                                           subscription_id=subscription_id)
                            else:
                                logger.error("Failed to activate monthly subscription",
                                           user_id=user_id,
                                           plan_id=plan_id,
                                           subscription_id=subscription_id)
                        
                        elif subscription_status in ['cancelled', 'paused']:
                            # Suscripción cancelada - desactivar premium
                            cancel_existing_subscriptions(supabase, user_id)
                            logger.info("Monthly subscription cancelled/paused", 
                                       user_id=user_id,
                                       subscription_id=subscription_id,
                                       status=subscription_status)
                        
                        else:
                            logger.info("Subscription status change", 
                                       subscription_id=subscription_id,
                                       status=subscription_status)
                
                except (ValueError, IndexError) as e:
                    logger.error("Error parsing subscription external_reference", 
                               external_ref=external_ref,
                               error=str(e))
            else:
                logger.info("Subscription not for Pseudosapiens", external_ref=external_ref)
        
        # Procesar pagos recurrentes
        elif data.get('type') == 'payment':
            # Los pagos recurrentes también llegan aquí
            payment_id = data.get('data', {}).get('id')
            
            if payment_id:
                logger.info("Processing recurring payment notification", payment_id=payment_id)
                # Reutilizar lógica del webhook de pagos existente
                # (El webhook de pagos ya maneja esto correctamente)
        
        else:
            logger.info("Non-subscription notification received", type=data.get('type'))
        
        # IMPORTANTE: Siempre devolver 200 OK
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error("MercadoPago subscription webhook processing failed", error=str(e), exc_info=True)
        # Devolver 200 para evitar reenvíos en caso de errores
        return jsonify({'status': 'error'}), 200

if __name__ == '__main__':
    # Solo para testing local
    app.run(debug=True, port=5000)