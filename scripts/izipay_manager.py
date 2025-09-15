"""
Izipay Integration Manager - Septiembre 2025
Maneja pagos, suscripciones y formularios de pago
Compatible con arquitectura Pseudosapiens existente
"""
import os
import json
import hashlib
import time
import requests
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()

@dataclass
class PaymentRequest:
    """Estructura para solicitudes de pago"""
    amount: int  # En centavos (ej: 500 = S/5.00, 1000 = S/10.00)
    currency: str = 'PEN'
    customer_email: str = ''
    order_id: str = ''
    plan_id: int = 1
    description: str = ''

@dataclass
class PaymentFormConfig:
    """Configuración del formulario de pago Izipay"""
    form_token: str
    public_key: str
    amount: int
    currency: str
    order_id: str
    customer_email: str

class IzipayManager:
    """
    Manager principal para integración con Izipay
    Maneja formularios de pago, tokens y verificaciones
    """

    def __init__(self):
        self.shop_id = os.getenv('IZIPAY_SHOP_ID', '34172081')
        self.test_mode = os.getenv('IZIPAY_TEST_MODE', 'true').lower() == 'true'
        self.api_url = os.getenv('IZIPAY_API_URL', 'https://api.micuentaweb.pe')

        # Credenciales según modo
        if self.test_mode:
            self.password = os.getenv('IZIPAY_TEST_PASSWORD')
            self.public_key = os.getenv('IZIPAY_PUBLIC_TEST_KEY')
        else:
            self.password = os.getenv('IZIPAY_PROD_PASSWORD')
            self.public_key = os.getenv('IZIPAY_PUBLIC_PROD_KEY')

        logger.info("IzipayManager initialized",
                   shop_id=self.shop_id,
                   test_mode=self.test_mode)

    def get_plan_amount(self, plan_id: int) -> int:
        """
        Obtener monto en centavos según plan_id
        Actualizado Sep 2025 - Solo Plan 1 y 2 activos
        """
        plan_amounts = {
            0: 0,      # Plan gratuito
            1: 500,    # Plan 1: S/5.00 monthly
            2: 1000,   # Plan 2: S/10.00 monthly (incluye Plan 1)
            # Planes 3, 4, 13 desactivados
        }
        return plan_amounts.get(plan_id, 500)

    def create_form_token(self, payment_request: PaymentRequest) -> Optional[str]:
        """
        Crear token de formulario de pago usando API REST de Izipay
        Implementa las mejores prácticas de 2025
        """
        try:
            # Endpoint para crear form token
            endpoint = f"{self.api_url}/api-payment/V4/Charge/CreatePayment"

            # Datos del pago
            payment_data = {
                "amount": payment_request.amount,
                "currency": payment_request.currency,
                "orderId": payment_request.order_id,
                "customer": {
                    "email": payment_request.customer_email
                },
                "metadata": {
                    "plan_id": payment_request.plan_id,
                    "description": payment_request.description
                }
            }

            # Headers de autenticación
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {self._get_auth_token()}'
            }

            # Realizar petición
            response = requests.post(endpoint, json=payment_data, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            form_token = result.get('answer', {}).get('formToken')

            if form_token:
                logger.info("Form token created successfully",
                           order_id=payment_request.order_id,
                           amount=payment_request.amount)
                return form_token
            else:
                logger.error("No form token in response", response=result)
                return None

        except requests.exceptions.RequestException as e:
            logger.error("Error creating form token", error=str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error creating form token", error=str(e))
            return None

    def _get_auth_token(self) -> str:
        """Generar token de autenticación básica"""
        import base64
        auth_string = f"{self.shop_id}:{self.password}"
        return base64.b64encode(auth_string.encode()).decode()

    def generate_order_id(self, user_email: str, plan_id: int) -> str:
        """
        Generar order_id único para tracking
        Formato: pseudosapiens_plan_{plan_id}_{timestamp}_{hash}
        """
        timestamp = int(time.time())
        email_hash = hashlib.md5(user_email.encode()).hexdigest()[:8]
        return f"pseudosapiens_plan_{plan_id}_{timestamp}_{email_hash}"

    def create_payment_form_config(self, user_email: str, plan_id: int) -> Optional[PaymentFormConfig]:
        """
        Crear configuración completa para formulario de pago frontend
        Retorna todo lo necesario para el JavaScript SDK
        """
        try:
            # Obtener monto según plan
            amount = self.get_plan_amount(plan_id)
            if amount == 0:
                logger.warning("Attempt to create payment for free plan", plan_id=plan_id)
                return None

            # Generar order_id único
            order_id = self.generate_order_id(user_email, plan_id)

            # Crear solicitud de pago
            payment_request = PaymentRequest(
                amount=amount,
                currency='PEN',
                customer_email=user_email,
                order_id=order_id,
                plan_id=plan_id,
                description=f"Pseudosapiens Plan {plan_id} - Suscripción Premium"
            )

            # Crear form token
            form_token = self.create_form_token(payment_request)
            if not form_token:
                return None

            # Retornar configuración completa
            return PaymentFormConfig(
                form_token=form_token,
                public_key=self.public_key,
                amount=amount,
                currency='PEN',
                order_id=order_id,
                customer_email=user_email
            )

        except Exception as e:
            logger.error("Error creating payment form config", error=str(e))
            return None

    def verify_payment_signature(self, payment_data: Dict[str, Any]) -> bool:
        """
        Verificar firma de pago recibido
        Implementa verificación HMAC según Izipay
        """
        try:
            # Obtener firma del pago
            received_signature = payment_data.get('signature')
            if not received_signature:
                return False

            # Construir string para verificación según formato Izipay
            signature_fields = [
                'vads_amount', 'vads_auth_number', 'vads_auth_result',
                'vads_capture_delay', 'vads_card_brand', 'vads_card_number',
                'vads_currency', 'vads_ctx_mode', 'vads_effective_amount',
                'vads_order_id', 'vads_payment_certificate', 'vads_result',
                'vads_shop_id', 'vads_trans_date', 'vads_trans_id',
                'vads_trans_status', 'vads_trans_uuid', 'vads_version'
            ]

            # Construir string de verificación
            verification_string = '+'.join([
                payment_data.get(field, '') for field in signature_fields if field in payment_data
            ])
            verification_string += '+' + self.password

            # Calcular SHA256
            import hashlib
            calculated_signature = hashlib.sha256(verification_string.encode()).hexdigest()

            return calculated_signature.upper() == received_signature.upper()

        except Exception as e:
            logger.error("Error verifying payment signature", error=str(e))
            return False

    def get_payment_status(self, transaction_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Consultar estado de un pago por UUID
        Útil para verificación manual
        """
        try:
            endpoint = f"{self.api_url}/api-payment/V4/Transaction/Get"

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {self._get_auth_token()}'
            }

            data = {
                "uuid": transaction_uuid
            }

            response = requests.post(endpoint, json=data, headers=headers, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error("Error getting payment status", error=str(e))
            return None

    def cancel_payment(self, transaction_uuid: str) -> bool:
        """
        Cancelar un pago (si está en estado pendiente)
        """
        try:
            endpoint = f"{self.api_url}/api-payment/V4/Transaction/CancelOrRefund"

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {self._get_auth_token()}'
            }

            data = {
                "uuid": transaction_uuid,
                "amount": None  # None = cancelar completamente
            }

            response = requests.post(endpoint, json=data, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            return result.get('status') == 'SUCCESS'

        except Exception as e:
            logger.error("Error cancelling payment", error=str(e))
            return False

    def create_subscription_payment(self, user_email: str, plan_id: int) -> Optional[PaymentFormConfig]:
        """
        Crear pago para suscripción recurrente
        Incluye configuración para recurrencia automática
        """
        try:
            # TODO: Implementar lógica de suscripción recurrente
            # Por ahora, crear pago simple y manejar recurrencia via webhook
            return self.create_payment_form_config(user_email, plan_id)

        except Exception as e:
            logger.error("Error creating subscription payment", error=str(e))
            return None

# Instancia global
izipay_manager = IzipayManager()

def get_izipay_manager() -> IzipayManager:
    """Obtener instancia del manager"""
    return izipay_manager