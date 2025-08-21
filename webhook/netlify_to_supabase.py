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
    """Mapear frecuencia string a plan_id de Supabase"""
    frequency_map = {
        '1': 4,   # Intensivo (cada hora)
        '3': 3,   # Pro (cada 3 horas)  
        '6': 2,   # Premium (cada 6 horas)
        '24': 1,  # Gratuito (diario)
    }
    
    # Default a plan gratuito si no se especifica o es inválido
    return frequency_map.get(str(frequency), 1)

@app.route('/webhook/netlify-form', methods=['POST'])
def handle_netlify_form():
    """Endpoint principal para recibir webhooks de Netlify Forms"""
    
    try:
        # Obtener datos del webhook
        if request.is_json:
            data = request.get_json()
        else:
            # Netlify puede enviar como form data
            data = request.form.to_dict()
        
        logger.info("Webhook received from Netlify", data=data)
        print(f"[DEBUG] Raw webhook data: {data}")
        print(f"[DEBUG] Data type: {type(data)}")
        print(f"[DEBUG] Email: {data.get('email', 'MISSING')}")
        print(f"[DEBUG] Frequency: {data.get('frequency', 'MISSING')}")
        print(f"[DEBUG] Form-name: {data.get('form-name', 'MISSING')}")
        print(f"[DEBUG] All keys: {list(data.keys())}")
        
        # Validar datos
        if not validate_netlify_webhook(data):
            return jsonify({
                'status': 'error',
                'message': 'Invalid webhook data'
            }), 400
        
        # Extraer datos del formulario
        email = data.get('email', '').strip().lower()
        frequency = data.get('frequency', '24')  # Default: diario
        plan_id = map_frequency_to_plan_id(frequency)
        
        print(f"[DEBUG] Processed - Email: {email}")
        print(f"[DEBUG] Processed - Frequency: {frequency}")
        print(f"[DEBUG] Processed - Plan ID: {plan_id}")
        
        # Conectar a Supabase
        supabase = get_supabase()
        
        # Verificar si el usuario ya existe
        existing_user = get_user_by_email(supabase, email)
        
        if existing_user:
            logger.info("User already exists, updating subscription", 
                       email=email, 
                       existing_user_id=existing_user['id'])
            
            # Actualizar suscripción existente si cambió el plan
            existing_subscription = get_user_subscription(supabase, email)
            if existing_subscription and existing_subscription['plan_id'] != plan_id:
                # Actualizar plan
                update_response = supabase.table('subscriptions').update({
                    'plan_id': plan_id,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('user_id', existing_user['id']).eq('status', 'active').execute()
                
                if update_response.data:
                    logger.info("Subscription plan updated", 
                               email=email, 
                               old_plan=existing_subscription['plan_id'],
                               new_plan=plan_id)
                    return jsonify({
                        'status': 'success',
                        'message': 'Subscription updated',
                        'user_id': existing_user['id'],
                        'action': 'updated'
                    })
            
            return jsonify({
                'status': 'success', 
                'message': 'User already exists',
                'user_id': existing_user['id'],
                'action': 'existing'
            })
        
        # Crear nuevo usuario
        user = create_user(supabase, email)
        if not user:
            logger.error("Failed to create user", email=email)
            return jsonify({
                'status': 'error',
                'message': 'Failed to create user'
            }), 500
        
        # Crear suscripción con el plan correspondiente
        subscription_response = supabase.table('subscriptions').insert({
            'user_id': user['id'],
            'plan_id': plan_id,
            'status': 'active'
        }).execute()
        
        if not subscription_response.data:
            logger.error("Failed to create subscription", 
                        email=email, 
                        user_id=user['id'],
                        plan_id=plan_id)
            return jsonify({
                'status': 'error',
                'message': 'Failed to create subscription'
            }), 500
        
        logger.info("New user and subscription created successfully",
                   email=email,
                   user_id=user['id'],
                   plan_id=plan_id,
                   frequency=frequency)
        
        return jsonify({
            'status': 'success',
            'message': 'User created successfully',
            'user_id': user['id'],
            'plan_id': plan_id,
            'action': 'created'
        })
        
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

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

@app.route('/unsubscribe', methods=['POST'])
def handle_unsubscribe():
    """Endpoint para procesar desuscripciones desde unsubscribe.html"""
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
        
        # Cancelar suscripción activa
        response = supabase.table('subscriptions').update({
            'status': 'cancelled',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('user_id', user['id']).eq('status', 'active').execute()
        
        if response.data:
            logger.info("Subscription cancelled successfully", email=email, user_id=user['id'])
            return jsonify({
                'status': 'success',
                'message': 'Suscripción cancelada exitosamente',
                'email': email
            })
        else:
            logger.warning("No active subscription found", email=email, user_id=user['id'])
            return jsonify({
                'status': 'error',
                'message': 'No se encontró suscripción activa para este email'
            }), 404
            
    except Exception as e:
        logger.error("Unsubscribe processing failed", error=str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error interno del servidor'
        }), 500

if __name__ == '__main__':
    # Solo para testing local
    app.run(debug=True, port=5000)