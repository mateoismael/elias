"""
Izipay Webhook Handler - Septiembre 2025
Implementación con mejores prácticas de seguridad HMAC-SHA256
Compatible con tu arquitectura Pseudosapiens existente
"""
import os
import hmac
import hashlib
import json
import time
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import structlog
from flask import Flask, request, jsonify

# Import your existing database functions
try:
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(current_dir, '..', 'scripts')
    sys.path.append(scripts_dir)
    from database import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("[WARN] Database module not available")

logger = structlog.get_logger()

app = Flask(__name__)

class IzipayWebhookHandler:
    """
    Manejador de webhooks Izipay con verificación HMAC-SHA256
    Implementa las mejores prácticas de seguridad para 2025
    """

    def __init__(self):
        self.test_mode = os.getenv('IZIPAY_TEST_MODE', 'true').lower() == 'true'
        self.hmac_key = self._get_hmac_key()
        self.shop_id = os.getenv('IZIPAY_SHOP_ID', '34172081')

    def _get_hmac_key(self) -> str:
        """Obtener clave HMAC según el modo (test/producción)"""
        if self.test_mode:
            return os.getenv('IZIPAY_HMAC_TEST_KEY', 'wB1h1mJYvEfPIroP8lN4wQBKezz4yq1BT66zHkA4nRmSO')
        else:
            return os.getenv('IZIPAY_HMAC_PROD_KEY', 'vXJNstRfwjTfu2kQe52v0wgxN6rE80x6or3SAVPGVZAJV')

    def verify_hmac_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verificar firma HMAC-SHA256 según mejores prácticas 2025
        Implementa comparación segura contra timing attacks
        """
        try:
            # Calcular HMAC esperado usando SHA256
            expected_signature = hmac.new(
                self.hmac_key.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Comparación segura contra timing attacks
            # Usar hmac.compare_digest() en lugar de == directo
            return hmac.compare_digest(
                signature.lower(),
                expected_signature.lower()
            )

        except Exception as e:
            logger.error("Error verifying HMAC signature", error=str(e))
            return False

    def process_payment_notification(self, data: Dict[str, Any]) -> bool:
        """
        Procesar notificación de pago de Izipay
        Actualizar suscripción en Supabase
        """
        try:
            # Extraer información clave del webhook
            transaction_status = data.get('vads_trans_status')
            transaction_uuid = data.get('vads_trans_uuid')
            order_id = data.get('vads_order_id')
            amount = data.get('vads_amount')
            currency = data.get('vads_currency')
            customer_email = data.get('vads_cust_email')

            logger.info("Processing Izipay payment notification",
                       transaction_uuid=transaction_uuid,
                       status=transaction_status,
                       order_id=order_id,
                       amount=amount,
                       customer_email=customer_email)

            # Verificar que el pago fue exitoso
            if transaction_status == 'AUTHORISED':
                return self._handle_successful_payment(data)
            elif transaction_status == 'REFUSED':
                return self._handle_failed_payment(data)
            elif transaction_status == 'CANCELLED':
                return self._handle_cancelled_payment(data)
            else:
                logger.warning("Unknown transaction status", status=transaction_status)
                return False

        except Exception as e:
            logger.error("Error processing payment notification", error=str(e))
            return False

    def _handle_successful_payment(self, data: Dict[str, Any]) -> bool:
        """Manejar pago exitoso - activar suscripción premium"""
        if not DB_AVAILABLE:
            logger.error("Database not available for payment processing")
            return False

        try:
            db = get_db()
            customer_email = data.get('vads_cust_email')
            order_id = data.get('vads_order_id')
            amount = int(data.get('vads_amount', 0)) / 100  # Convertir de centavos

            # Extraer plan_id del order_id (formato: pseudosapiens_plan_X_timestamp)
            plan_id = self._extract_plan_id_from_order(order_id)

            if not plan_id:
                logger.error("Could not extract plan_id from order_id", order_id=order_id)
                return False

            # Obtener o crear usuario
            user = db.get_user_by_email(customer_email)
            if not user:
                user = db.create_user(customer_email)

            if not user:
                logger.error("Could not create/get user", email=customer_email)
                return False

            # Crear suscripción premium
            success = self._create_premium_subscription(
                user_id=user.id,
                plan_id=plan_id,
                izipay_data=data
            )

            if success:
                logger.info("Premium subscription activated",
                           user_email=customer_email,
                           plan_id=plan_id,
                           transaction_uuid=data.get('vads_trans_uuid'))

                # TODO: Enviar email de confirmación
                # TODO: Activar características premium

            return success

        except Exception as e:
            logger.error("Error handling successful payment", error=str(e))
            return False

    def _extract_plan_id_from_order(self, order_id: str) -> Optional[int]:
        """Extraer plan_id del order_id generado por el frontend"""
        try:
            # Formato esperado: pseudosapiens_plan_X_timestamp
            if 'plan_' in order_id:
                parts = order_id.split('plan_')
                if len(parts) > 1:
                    plan_part = parts[1].split('_')[0]
                    return int(plan_part)
            return None
        except (ValueError, IndexError):
            return None

    def _create_premium_subscription(self, user_id: str, plan_id: int, izipay_data: Dict) -> bool:
        """Crear suscripción premium en Supabase"""
        try:
            db = get_db()

            # Cancelar suscripción anterior si existe
            existing_subscription = db.supabase.table('subscriptions').select('*').eq(
                'user_id', user_id
            ).eq('status', 'active').execute()

            if existing_subscription.data:
                # Cancelar suscripción anterior
                db.supabase.table('subscriptions').update({
                    'status': 'cancelled',
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }).eq('id', existing_subscription.data[0]['id']).execute()

            # Crear nueva suscripción premium
            subscription_data = {
                'user_id': user_id,
                'plan_id': plan_id,
                'status': 'active',
                'started_at': datetime.now(timezone.utc).isoformat(),
                'izipay_transaction_uuid': izipay_data.get('vads_trans_uuid'),
                'izipay_subscription_id': izipay_data.get('vads_subscription'),
                'payment_method': 'izipay',
                'amount_paid': int(izipay_data.get('vads_amount', 0)) / 100
            }

            result = db.supabase.table('subscriptions').insert(subscription_data).execute()

            return bool(result.data)

        except Exception as e:
            logger.error("Error creating premium subscription", error=str(e))
            return False

    def _handle_failed_payment(self, data: Dict[str, Any]) -> bool:
        """Manejar pago fallido"""
        logger.warning("Payment failed",
                      transaction_uuid=data.get('vads_trans_uuid'),
                      customer_email=data.get('vads_cust_email'),
                      reason=data.get('vads_result'))
        # TODO: Enviar email de notificación de fallo
        return True

    def _handle_cancelled_payment(self, data: Dict[str, Any]) -> bool:
        """Manejar pago cancelado"""
        logger.info("Payment cancelled",
                   transaction_uuid=data.get('vads_trans_uuid'),
                   customer_email=data.get('vads_cust_email'))
        # TODO: Enviar email de notificación de cancelación
        return True

# Instancia global del handler
webhook_handler = IzipayWebhookHandler()

@app.route('/payment/callback/test', methods=['POST'])
@app.route('/payment/callback/production', methods=['POST'])
def izipay_webhook():
    """
    Endpoint principal para recibir webhooks de Izipay
    Implementa verificación HMAC-SHA256 según mejores prácticas 2025
    """
    try:
        # Obtener payload raw (importante para verificación HMAC)
        payload = request.get_data()

        # Obtener signature del header (puede variar según Izipay)
        signature = request.headers.get('X-Izipay-Signature') or \
                   request.headers.get('X-Signature-SHA256') or \
                   request.form.get('signature')

        if not signature:
            logger.warning("No signature provided in webhook")
            return jsonify({'error': 'Missing signature'}), 400

        # Verificar firma HMAC-SHA256
        if not webhook_handler.verify_hmac_signature(payload, signature):
            logger.error("Invalid HMAC signature")
            return jsonify({'error': 'Invalid signature'}), 401

        # Parsear datos del webhook
        if request.content_type == 'application/json':
            webhook_data = request.json
        else:
            # Form data (más común en Izipay)
            webhook_data = request.form.to_dict()

        # Log del webhook recibido
        logger.info("Valid Izipay webhook received",
                   transaction_uuid=webhook_data.get('vads_trans_uuid'),
                   status=webhook_data.get('vads_trans_status'),
                   timestamp=datetime.now(timezone.utc).isoformat())

        # Procesar notificación
        success = webhook_handler.process_payment_notification(webhook_data)

        if success:
            # Respuesta exitosa (requerida por Izipay para confirmar recepción)
            return "OK", 200
        else:
            # Error en procesamiento
            return jsonify({'error': 'Processing failed'}), 500

    except Exception as e:
        logger.error("Webhook processing error", error=str(e))
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'izipay-webhook',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'test_mode': webhook_handler.test_mode
    })

if __name__ == '__main__':
    # Para desarrollo local
    app.run(debug=True, port=5001)