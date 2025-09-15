"""
Izipay Payment Token API - Septiembre 2025
Endpoint autocontenido para crear tokens de formulario de pago
Optimizado para Netlify Functions según mejores prácticas 2025
"""
import os
import json
import hashlib
import time
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import base64

class IzipayTokenGenerator:
    """
    Generador de tokens autocontenido para Izipay
    """

    def __init__(self):
        # Configuración desde environment variables
        self.shop_id = os.environ.get('IZIPAY_SHOP_ID', '34172081')
        self.test_mode = os.environ.get('IZIPAY_TEST_MODE', 'true').lower() == 'true'
        self.api_url = os.environ.get('IZIPAY_API_URL', 'https://api.micuentaweb.pe')

        # Credenciales según modo
        if self.test_mode:
            self.password = os.environ.get('IZIPAY_TEST_PASSWORD', '')
            self.public_key = os.environ.get('IZIPAY_PUBLIC_TEST_KEY', '')
        else:
            self.password = os.environ.get('IZIPAY_PROD_PASSWORD', '')
            self.public_key = os.environ.get('IZIPAY_PUBLIC_PROD_KEY', '')

        # Plan amounts (centavos) - Actualizado Sep 2025
        self.plan_amounts = {
            1: 500,    # S/5.00
            2: 1000,   # S/10.00
            # Planes 3, 4, 13 removidos - solo Plan 1 y 2 activos
        }

    def generate_order_id(self, user_email: str, plan_id: int) -> str:
        """Generar order_id único"""
        timestamp = int(time.time())
        email_hash = hashlib.md5(user_email.encode()).hexdigest()[:8]
        return f"pseudosapiens_plan_{plan_id}_{timestamp}_{email_hash}"

    def get_auth_header(self) -> str:
        """Generar header de autenticación básica"""
        auth_string = f"{self.shop_id}:{self.password}"
        return base64.b64encode(auth_string.encode()).decode()

    def create_form_token(self, user_email: str, plan_id: int) -> Optional[Dict[str, Any]]:
        """
        Crear token de suscripción recurrente usando API de Izipay
        Implementa suscripciones mensuales automáticas según mejores prácticas 2025
        """
        try:
            # Validar plan
            if plan_id not in self.plan_amounts:
                return None

            amount = self.plan_amounts[plan_id]
            order_id = self.generate_order_id(user_email, plan_id)

            # Endpoint de Izipay para crear suscripción recurrente
            endpoint = f"{self.api_url}/api-payment/V4/Charge/CreateSubscription"

            # Datos de la suscripción mensual
            subscription_data = {
                "amount": amount,
                "currency": "PEN",
                "orderId": order_id,
                "customer": {
                    "email": user_email
                },
                # Configuración de suscripción recurrente mensual
                "subscription": {
                    "effectDate": None,  # Inicia inmediatamente
                    "rrule": "RRULE:FREQ=MONTHLY;BYMONTHDAY=1",  # Cada mes el día 1
                    "description": f"Suscripción Premium Plan {plan_id} - Pseudosapiens"
                },
                "metadata": {
                    "plan_id": plan_id,
                    "source": "pseudosapiens_dashboard",
                    "subscription_type": "monthly_recurring"
                }
            }

            # Headers
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {self.get_auth_header()}'
            }

            # Hacer petición con timeout
            response = requests.post(
                endpoint,
                json=subscription_data,
                headers=headers,
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                form_token = result.get('answer', {}).get('formToken')

                if form_token:
                    return {
                        'form_token': form_token,
                        'public_key': self.public_key,
                        'amount': amount,
                        'currency': 'PEN',
                        'order_id': order_id,
                        'customer_email': user_email,
                        'plan_id': plan_id,
                        'test_mode': self.test_mode
                    }

            # Log error para debugging
            print(f"[ERROR] Izipay API error: {response.status_code} - {response.text}")
            return None

        except requests.exceptions.Timeout:
            print("[ERROR] Izipay API timeout")
            return None
        except Exception as e:
            print(f"[ERROR] Token creation failed: {str(e)}")
            return None

def handler(event, context):
    """
    Netlify Function handler para crear tokens de pago
    Endpoint: /.netlify/functions/create_payment
    """

    # CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': ''
        }

    # Solo POST
    if event.get('httpMethod') != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method not allowed'})
        }

    try:
        # Parse body
        body = event.get('body', '{}')
        try:
            data = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON'})
            }

        # Validar datos requeridos
        user_email = data.get('user_email', '').strip()
        plan_id = data.get('plan_id')

        if not user_email or not plan_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': 'user_email and plan_id are required'
                })
            }

        # Validar email format básico
        if '@' not in user_email or '.' not in user_email:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Invalid email format'
                })
            }

        # Validar plan_id - Solo planes activos Sept 2025
        valid_plans = [1, 2]  # Solo Plan 1 (S/5) y Plan 2 (S/10) activos
        if plan_id not in valid_plans:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': f'Invalid plan_id. Must be one of: {valid_plans}'
                })
            }

        # Crear token
        token_generator = IzipayTokenGenerator()
        payment_config = token_generator.create_form_token(user_email, plan_id)

        if payment_config:
            # Respuesta exitosa
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'success',
                    'data': payment_config,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            }
        else:
            # Error creando token
            return {
                'statusCode': 502,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'error',
                    'message': 'Failed to create payment token. Please try again.'
                })
            }

    except Exception as e:
        # Error interno
        print(f"[CRITICAL] Payment API error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'error',
                'message': 'Internal server error'
            })
        }

# Local testing
if __name__ == '__main__':
    test_event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'user_email': 'test@pseudosapiens.com',
            'plan_id': 2
        })
    }

    result = handler(test_event, {})
    print(f"Test result: {result}")