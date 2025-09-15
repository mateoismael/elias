"""
Izipay Webhook Handler - Septiembre 2025
Implementación autocontenida según mejores prácticas 2025:
- Response < 10 segundos
- Retry logic compatible
- HMAC verification estándar Izipay
- Error handling robusto
"""
import os
import hmac
import hashlib
import json
import time
from typing import Dict, Optional, Any
from datetime import datetime, timezone
from urllib.parse import parse_qs

# Autocontenido - no dependencies externas
class IzipayWebhook2025:
    """
    Webhook handler optimizado para Izipay según estándares 2025
    """

    def __init__(self):
        self.test_mode = os.environ.get('IZIPAY_TEST_MODE', 'true').lower() == 'true'
        self.shop_id = os.environ.get('IZIPAY_SHOP_ID', '34172081')

        # HMAC keys según modo
        if self.test_mode:
            self.hmac_key = os.environ.get('IZIPAY_HMAC_TEST_KEY', '')
            self.password = os.environ.get('IZIPAY_TEST_PASSWORD', '')
        else:
            self.hmac_key = os.environ.get('IZIPAY_HMAC_PROD_KEY', '')
            self.password = os.environ.get('IZIPAY_PROD_PASSWORD', '')

    def verify_izipay_signature(self, form_data: Dict[str, str]) -> bool:
        """
        Verificación HMAC según documentación oficial Izipay 2025
        Formato correcto: kr-hash, kr-hash-algorithm, kr-answer
        """
        try:
            # Izipay envía signature en kr-hash
            received_signature = form_data.get('kr-hash', '')
            hash_algorithm = form_data.get('kr-hash-algorithm', 'sha256_hmac')
            
            if not received_signature or hash_algorithm != 'sha256_hmac':
                print(f"[ERROR] Missing or invalid signature format")
                return False

            # Obtener kr-answer que contiene los datos del pago
            kr_answer = form_data.get('kr-answer', '')
            if not kr_answer:
                print(f"[ERROR] Missing kr-answer in webhook")
                return False

            # Calcular HMAC usando kr-answer + password
            verification_string = kr_answer + self.password
            
            # Calcular SHA256 HMAC
            calculated_signature = hmac.new(
                self.password.encode('utf-8'),
                kr_answer.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Comparación segura
            is_valid = hmac.compare_digest(
                received_signature.lower(),
                calculated_signature.lower()
            )
            
            if not is_valid:
                print(f"[ERROR] HMAC verification failed")
                print(f"Expected: {calculated_signature}")
                print(f"Received: {received_signature}")
            
            return is_valid

        except Exception as e:
            print(f"[ERROR] Signature verification failed: {e}")
            return False

    def process_payment_fast(self, payment_data: Dict[str, str]) -> bool:
        """
        Procesamiento rápido (<10s) de suscripciones según mejores prácticas 2025
        Maneja formato correcto de Izipay con kr-answer JSON
        """
        try:
            # Parse kr-answer JSON
            kr_answer_str = payment_data.get('kr-answer', '{}')
            try:
                kr_answer = json.loads(kr_answer_str) if isinstance(kr_answer_str, str) else kr_answer_str
            except json.JSONDecodeError:
                print(f"[ERROR] Invalid kr-answer JSON format")
                return False

            # Extraer datos del kr-answer
            order_status = kr_answer.get('orderStatus', '')
            order_details = kr_answer.get('orderDetails', {})
            customer = kr_answer.get('customer', {})
            order_info = kr_answer.get('orderInfo', {})
            transactions = kr_answer.get('transactions', [])
            
            order_id = order_details.get('orderId', '')
            customer_email = customer.get('email', '')
            
            # Obtener datos de la transacción
            transaction = transactions[0] if transactions else {}
            amount = transaction.get('amount', 0)
            subscription_id = order_info.get('subscriptionId', '')

            # Log mínimo para debugging
            print(f"[WEBHOOK] Processing: {order_status} | Order: {order_id} | Email: {customer_email} | Sub: {subscription_id}")

            # Procesar según estado
            if order_status == 'PAID':
                if subscription_id:
                    # Es una suscripción recurrente
                    self._process_subscription_payment({
                        'type': 'subscription_payment_success',
                        'subscription_id': subscription_id,
                        'order_id': order_id,
                        'customer_email': customer_email,
                        'amount': amount / 100,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                else:
                    # Es un pago inicial de suscripción
                    self._process_initial_subscription({
                        'type': 'subscription_created',
                        'order_id': order_id,
                        'customer_email': customer_email,
                        'amount': amount / 100,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                return True

            elif order_status in ['REFUSED', 'CANCELLED']:
                # Log para follow-up manual
                self._queue_for_processing({
                    'type': 'payment_failed',
                    'order_id': order_id,
                    'subscription_id': subscription_id,
                    'status': order_status,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                return True

            return False

        except Exception as e:
            print(f"[ERROR] Payment processing failed: {e}")
            return False

    def _queue_for_processing(self, data: Dict[str, Any]):
        """
        Enviar a queue para procesamiento asíncrono
        En futuro: usar Netlify Background Functions o external queue
        Por ahora: log estructurado para manual processing
        """
        print(f"[QUEUE] {json.dumps(data)}")

        # TODO: Integrar con Background Function o external service
        # Para MVP: manual processing via logs

    def _process_initial_subscription(self, data: Dict[str, Any]):
        """
        Procesar pago inicial de nueva suscripción
        Activar plan premium en Supabase
        """
        try:
            order_id = data.get('order_id', '')
            customer_email = data.get('customer_email', '')
            amount = data.get('amount', 0)
            
            # Extraer plan_id del order_id (formato: pseudosapiens_plan_X_timestamp_hash)
            plan_id = self._extract_plan_from_order_id(order_id)
            
            if plan_id and customer_email:
                # TODO: Conectar con Supabase para activar suscripción
                # 1. Buscar usuario por email
                # 2. Actualizar suscripción a plan premium
                # 3. Crear registro en tabla payments
                print(f"[SUBSCRIPTION] Activating Plan {plan_id} for {customer_email} - Amount: S/{amount}")
                
                # Log para procesamiento manual por ahora
                self._queue_for_processing({
                    **data,
                    'action_required': 'activate_subscription',
                    'plan_id': plan_id,
                    'user_email': customer_email
                })
            
        except Exception as e:
            print(f"[ERROR] Processing initial subscription: {e}")

    def _process_subscription_payment(self, data: Dict[str, Any]):
        """
        Procesar pago recurrente de suscripción existente
        Actualizar fecha de próximo pago
        """
        try:
            subscription_id = data.get('subscription_id', '')
            customer_email = data.get('customer_email', '')
            amount = data.get('amount', 0)
            
            print(f"[RECURRING] Payment received for subscription {subscription_id} - Amount: S/{amount}")
            
            # TODO: Conectar con Supabase para actualizar pago
            # 1. Actualizar registro en tabla payments
            # 2. Calcular próxima fecha de pago
            # 3. Mantener suscripción activa
            
            self._queue_for_processing({
                **data,
                'action_required': 'update_recurring_payment',
                'subscription_id': subscription_id
            })
            
        except Exception as e:
            print(f"[ERROR] Processing recurring payment: {e}")

    def _extract_plan_from_order_id(self, order_id: str) -> Optional[int]:
        """
        Extraer plan_id del order_id generado
        Formato esperado: pseudosapiens_plan_X_timestamp_hash
        """
        try:
            if 'pseudosapiens_plan_' in order_id:
                parts = order_id.split('_')
                if len(parts) >= 3:
                    return int(parts[2])  # plan_X -> X
        except (ValueError, IndexError):
            pass
        return None

def handler(event, context):
    """
    Netlify Function handler optimizado para webhooks Izipay 2025
    Endpoints: /.netlify/functions/webhook_handler
    """
    start_time = time.time()

    # CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, X-Signature',
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
        webhook = IzipayWebhook2025()

        # Parse body (Izipay envía form-encoded)
        body = event.get('body', '')
        if not body:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Empty body'})
            }

        # Parse form data
        try:
            if body.startswith('{'):
                # JSON fallback
                form_data = json.loads(body)
            else:
                # Form-encoded (estándar Izipay)
                parsed = parse_qs(body)
                form_data = {k: v[0] if isinstance(v, list) and len(v) > 0 else v
                           for k, v in parsed.items()}
                
            # Log formato recibido para debugging
            if 'kr-hash' in form_data:
                print(f"[WEBHOOK] Received Izipay format webhook")
            else:
                print(f"[WEBHOOK] WARNING: Unexpected webhook format, keys: {list(form_data.keys())[:5]}")
                
        except Exception as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid body format: {str(e)}'})
            }

        # Verificar firma HMAC
        if not webhook.verify_izipay_signature(form_data):
            print(f"[ERROR] Invalid HMAC signature from {event.get('headers', {}).get('x-forwarded-for', 'unknown')}")
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid signature'})
            }

        # Procesar pago (rápido)
        success = webhook.process_payment_fast(form_data)

        # Medir tiempo de respuesta
        response_time = time.time() - start_time
        print(f"[PERF] Webhook processed in {response_time:.3f}s")

        # Respuesta según estándares 2025
        if success:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/plain'},
                'body': 'OK'  # Izipay espera respuesta simple
            }
        else:
            return {
                'statusCode': 422,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Processing failed'})
            }

    except Exception as e:
        # Log error pero responder rápido
        print(f"[CRITICAL] Webhook handler error: {str(e)}")

        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }

# Local testing
if __name__ == '__main__':
    test_event = {
        'httpMethod': 'POST',
        'headers': {'content-type': 'application/x-www-form-urlencoded'},
        'body': 'vads_trans_status=AUTHORISED&vads_trans_uuid=test123&vads_order_id=pseudosapiens_plan_2_12345&signature=abc123'
    }

    result = handler(test_event, {})
    print(f"Test result: {result}")