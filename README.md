# 💭 Pseudosapiens - Documentación Interna

**Repositorio Privado de Negocio - Sistema Inteligente de Email Marketing con Pagos**

Plataforma automatizada para el envío personalizado de frases motivacionales utilizando OpenAI GPT-4o mini para la generación única de asuntos. Sistema de suscripciones premium con Izipay, gestión avanzada de usuarios, algoritmos anti-repetición y análisis integral.

> **⚠️ CONFIDENCIAL**: Este es un repositorio privado de negocio. Todo el código, estrategias y documentación son propietarios y confidenciales.

## 🚀 Características Principales

### ✨ Asuntos Inteligentes con IA
- **GPT-4o mini Integration**: Genera asuntos únicos basados en el contenido de cada frase
- **Contextualización temporal**: Adapta el tono según la hora del día
- **Variabilidad real**: Cada email tiene un asunto específico y profesional
- **Ultra-económico**: ~$0.000013 por asunto (~$0.47/año para 100 emails diarios)

### 💳 Sistema de Suscripciones Premium (NEW - Sept 2025)
- **Izipay Integration**: Pagos seguros con tarjetas, Yape, Plin
- **Planes freemium**: Desde gratuito hasta 13 frases diarias
- **Webhooks automáticos**: Activación instantánea de suscripciones
- **Dashboard integrado**: Selección de planes desde el panel de usuario

### 🎯 Sistema Anti-Repetición
- **Tracking inteligente**: Cada usuario recibe frases únicas, sin repeticiones
- **Base de datos PostgreSQL**: Historial completo de frases enviadas por usuario
- **Algoritmo optimizado**: Selección eficiente de contenido no visto

### 📧 Gestión Avanzada de Emails
- **Resend API**: Entrega confiable y profesional
- **Modo TEST**: Pruebas seguras sin enviar a toda la base
- **Rate limiting**: Control de velocidad de envío
- **Reintentos automáticos**: Manejo robusto de errores

### 🛠 Infraestructura Robusta
- **Supabase**: Base de datos PostgreSQL en la nube
- **Netlify Functions**: Endpoints serverless para pagos y webhooks
- **Netlify Forms**: Captura de suscripciones desde el frontend
- **Logging estructurado**: Monitoreo completo con structlog
- **Configuración flexible**: Variables de entorno para todos los ajustes

## 📁 Estructura del Proyecto (Actualizada Sept 2025)

```
elias/
├── scripts/                          # Módulos Python principales
│   ├── send_emails.py                # Sistema principal de envío
│   ├── smart_subject_generator.py    # Generación IA de asuntos
│   ├── database.py                   # Gestión de usuarios y suscripciones
│   ├── database_phrases.py           # Gestión de frases y anti-repetición
│   ├── smart_phrase_system.py        # Lógica de selección inteligente
│   ├── izipay_manager.py             # Manager de integración Izipay
│   └── check_dns.py                  # Verificación DNS
├── netlify/functions/                # Endpoints serverless
│   ├── create_payment.py             # API para crear tokens de pago
│   └── webhook_handler.py            # Webhook para procesar pagos Izipay
├── webhook/                          # Webhooks adicionales
│   ├── netlify_to_supabase.py        # Webhook forms → Supabase
│   └── izipay_webhook.py             # Webhook local de referencia
├── index.html                        # Landing page de suscripción
├── dashboard.html                    # Panel de control centralizado con integración de pagos
├── unsubscribe.html                  # Página de desuscripción
├── payment-success.html              # Página de pago exitoso
├── payment-failed.html               # Página de pago fallido
├── .env                             # Configuración de producción
├── requirements.txt                 # Dependencias Python
└── netlify.toml                     # Configuración de despliegue y routing
```

## 💰 Modelo de Negocio y Planes (Sept 2025)

### Planes de Suscripción
- **Plan 0 (Gratuito)**: 3 frases por semana (L-M-V)
- **Plan 1 (Premium Básico)**: 1 frase diaria - **S/ 29.00/mes**
- **Plan 2 (Premium Plus)**: 2 frases diarias - **S/ 49.00/mes** 🔥 Más Popular
- **Plan 3 (Premium Pro)**: 3 frases diarias - **S/ 69.00/mes**
- **Plan 4 (Premium Max)**: 4 frases diarias - **S/ 89.00/mes**
- **Plan 13 (Power User)**: 13 frases diarias - **S/ 199.00/mes**

### Proyección de Ingresos
```
100 usuarios gratuitos: S/ 0/mes
20 usuarios Premium Plus: S/ 980/mes
10 usuarios Premium Pro: S/ 690/mes
5 usuarios Premium Max: S/ 445/mes
---
Total potencial: S/ 2,115/mes
```

## 🔧 Instalación y Configuración

### Prerrequisitos
- Python 3.8+
- Cuenta en [Supabase](https://supabase.com)
- API Key de [OpenAI](https://openai.com)
- API Key de [Resend](https://resend.com)
- Cuenta en [Izipay](https://izipay.pe) para pagos
- Cuenta en [Netlify](https://netlify.com)

### 1. Clonar el Repositorio
```bash
git clone <repository-url>
cd elias
```

### 2. Crear Entorno Virtual
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate     # Windows
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno
Crear archivo `.env` con:

```env
# === OPENAI ===
OPENAI_API_KEY=sk-proj-your-openai-key-here

# === EMAIL CONFIGURATION ===
RESEND_API_KEY=re_your-resend-key-here
SENDER_EMAIL=Pseudosapiens <reflexiones@pseudosapiens.com>

# === NETLIFY FORMS ===
NETLIFY_SITE_ID=your-site-id
NETLIFY_ACCESS_TOKEN=nfp_your-netlify-token
NETLIFY_FORM_NAME=subscribe

# === SUPABASE DATABASE ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# === IZIPAY CONFIGURATION (Septiembre 2025) ===
IZIPAY_SHOP_ID=34172081
IZIPAY_TEST_PASSWORD=testpassword_your-test-password
IZIPAY_PROD_PASSWORD=prodpassword_your-prod-password
IZIPAY_API_URL=https://api.micuentaweb.pe
IZIPAY_TEST_MODE=true

# HMAC Keys para verificación de webhooks
IZIPAY_HMAC_TEST_KEY=your-hmac-test-key
IZIPAY_HMAC_PROD_KEY=your-hmac-prod-key

# JavaScript SDK para frontend
IZIPAY_JS_URL=https://static.micuentaweb.pe/static/js/krypton-client/V4.0/stable/kr-payment-form.min.js
IZIPAY_PUBLIC_TEST_KEY=34172081:testpublickey_your-public-test-key
IZIPAY_PUBLIC_PROD_KEY=34172081:publickey_your-public-prod-key

# === TESTING ===
TEST_MODE=true
TEST_EMAILS=test@example.com

# === CONFIGURACIÓN AVANZADA ===
RESEND_THROTTLE_SECONDS=0.6
RESEND_MAX_RETRIES=8
```

### 5. Configurar Base de Datos

La base de datos se configura automáticamente en Supabase con las siguientes tablas:

- **`subscribers`**: Usuarios y sus preferencias
- **`phrases`**: Biblioteca de frases motivacionales
- **`user_phrase_history`**: Historial anti-repetición
- **`email_logs`**: Registro de emails enviados
- **`subscriptions`**: Suscripciones premium y planes

### 6. Configurar Izipay Back Office

1. **Acceder al Back Office**: https://secure.micuentaweb.pe/vads-merchant/
2. **Configurar URLs de notificación**:
   - URL TEST: `https://pseudosapiens.com/payment/callback/test`
   - URL PROD: `https://pseudosapiens.com/payment/callback/production`
   - IPN TEST: `https://pseudosapiens.com/webhook/izipay_webhook`
   - IPN PROD: `https://pseudosapiens.com/webhook/izipay_webhook`

## 🚀 Uso

### Envío Manual de Emails
```bash
cd scripts
python send_emails.py
```

### Crear Token de Pago (Testing)
```bash
cd netlify/functions
python create_payment.py
```

### Test Webhook Izipay
```bash
cd netlify/functions
python webhook_handler.py
```

### Modo de Prueba
```bash
# Activar en .env
TEST_MODE=true
TEST_EMAILS=test@example.com,test2@example.com
```

## 💳 Sistema de Pagos Izipay

### Flujo de Usuario
1. **Usuario accede al dashboard** → Ve plan actual
2. **Hace clic en "Upgrade a Premium"** → Se muestran planes
3. **Selecciona plan** → Se genera token de pago
4. **Completa pago en Izipay** → Webhook procesa resultado
5. **Suscripción se activa** → Usuario recibe más frases

### Endpoints de Pagos
- **`/.netlify/functions/create_payment`**: Crear token de formulario
- **`/.netlify/functions/webhook_handler`**: Procesar webhooks de pago

### URLs de Redirección
- **`/payment/success`**: Pago exitoso
- **`/payment/failed`**: Pago fallido

## 🧠 Sistema de IA para Asuntos

### GPT-4o mini Integration
El sistema utiliza OpenAI GPT-4o mini para generar asuntos inteligentes:

```python
# Ejemplo de asuntos generados
"El dinero no puede comprar la felicidad..." → "Placer dulce más allá del dinero"
"No tengas miedo de fallar..." → "Atrévete a intentar sin miedo"
"La música puede cambiar el mundo..." → "Melodías que transforman vidas"
```

### Características del Generador
- **Análisis contextual**: Extrae temas clave de cada frase
- **Templates inteligentes**: Categorización automática por temas
- **Variabilidad**: Usa hashing determinístico para consistencia
- **Profesionalismo**: Genera asuntos apropiados para email marketing

## 📊 Monitoreo y Logs

### Logging Estructurado
El sistema usa `structlog` para logging detallado:

```python
2025-09-14 20:18:18 [info] IzipayManager initialized
    shop_id=34172081 test_mode=True
2025-09-14 20:19:07 [error] No form token in response
    response={'webService': 'Charge/CreatePayment', 'status': 'ERROR'}
```

### Métricas Clave
- Emails enviados exitosamente
- Suscripciones premium activas
- Ingresos por pagos procesados
- Tasa de conversión freemium → premium
- Costos de IA por email
- Tiempo de procesamiento
- Frases utilizadas por usuario

## 💰 Costos Estimados (Actualizado Sept 2025)

### Costos Operativos
- **OpenAI GPT-4o mini**: ~$0.47/año (100 emails diarios)
- **Resend Email**: ~$30/año (post 3K gratis/mes)
- **Izipay Payments**: ~$0/año (primeras transacciones gratis)
- **Supabase**: $0/año (free tier)
- **Netlify**: $0/año (free tier)

### Total Operativo
**~$30.47/año** + **ingresos recurrentes por suscripciones premium**

### ROI Proyectado
Con solo 10 usuarios premium básicos: **S/ 290/mes** vs **S/ 2.54/mes** de costos = **11,400% ROI**

## 🔐 Seguridad y Privacidad

- **Variables de entorno**: Todas las claves sensibles en `.env`
- **HMAC verification**: Webhooks Izipay verificados con SHA-256
- **Tokens de desuscripción**: Generación segura de URLs únicas
- **Rate limiting**: Protección contra spam y abuso
- **Validación de emails**: Verificación de formato y dominio
- **HTTPS**: Todas las comunicaciones encriptadas
- **PCI compliance**: Pagos procesados por Izipay (certificado PCI DSS)

## 🚢 Despliegue en Producción

### Netlify (Recomendado)
1. Conectar repositorio GitHub a Netlify
2. Configurar variables de entorno en Netlify Dashboard
3. Configurar `TEST_MODE=false` e `IZIPAY_TEST_MODE=false` en producción
4. Establecer cron job para `scripts/send_emails.py`
5. Verificar que las Netlify Functions se desplieguen correctamente

### Verificación Post-Deploy
```bash
# Test endpoints
curl https://pseudosapiens.com/.netlify/functions/create_payment
curl https://pseudosapiens.com/payment/callback/test
```

## 🧪 Testing

### Test Completo del Sistema
```bash
cd scripts
python -c "
from smart_subject_generator import test_subject_generation
test_subject_generation()
"
```

### Test Integración Izipay
```bash
cd netlify/functions
python -c "
from create_payment import IzipayTokenGenerator
generator = IzipayTokenGenerator()
print('Izipay integration OK:', bool(generator.shop_id))
"
```

### Verificar Estado del Sistema
```bash
python -c "
from smart_subject_generator import get_system_status
import json
print(json.dumps(get_system_status(), indent=2))
"
```

## 🐛 Troubleshooting

### Errores Comunes

**Izipay Authentication Error**
```python
# Verificar credenciales
import os
print("Shop ID:", os.getenv('IZIPAY_SHOP_ID'))
print("Test mode:", os.getenv('IZIPAY_TEST_MODE'))
```

**Webhook No Recibido**
- Verificar URLs en Back Office Izipay
- Comprobar logs de Netlify Functions
- Validar configuración HMAC

**OpenAI API Error**
```python
# Verificar API key
import os
print("API Key configurada:", bool(os.getenv('OPENAI_API_KEY')))
```

**Supabase Connection Error**
```python
# Verificar conexión
from scripts.database import get_subscriber_count
print("Conexión DB:", get_subscriber_count())
```

## 📈 Roadmap Técnico

### ✅ Completado (Sept 2025)
- [x] Dashboard web con métricas en tiempo real
- [x] Integración de pagos con Izipay
- [x] Sistema de suscripciones premium
- [x] Webhooks automáticos
- [x] Clean URLs y SEO optimization

### 🔄 En Desarrollo
- [ ] A/B testing para asuntos y contenido
- [ ] Analytics avanzados con métricas de engagement
- [ ] Sistema de referidos

### 📋 Backlog
- [ ] Segmentación de usuarios por intereses
- [ ] API REST para integración externa
- [ ] Plantillas HTML personalizables
- [ ] Integración con más proveedores de pago
- [ ] App móvil

## 🔒 Acceso y Seguridad

- **Repositorio Privado**: Solo miembros autorizados del equipo tienen acceso
- **Claves de Producción**: Almacenadas de forma segura en Netlify Environment Variables
- **Base de Datos**: Supabase con seguridad a nivel de fila habilitada
- **Email**: Resend API con verificación de dominio
- **Pagos**: Izipay con certificación PCI DSS Level 1

## 📝 Licencia y Propiedad

**© 2025 Pseudosapiens - Todos los Derechos Reservados**

Este software y toda la documentación asociada son propietarios y confidenciales. La copia, distribución o uso no autorizado está estrictamente prohibido.

## 📞 Soporte Interno

- **Problemas Técnicos**: Contactar directamente al equipo de desarrollo
- **Lógica de Negocio**: Ver documentación en línea del código
- **Problemas de Producción**: Revisar logs de Netlify Functions y dashboard de Supabase
- **Pagos e Izipay**: Revisar Back Office en https://secure.micuentaweb.pe/vads-merchant/

---

**Sistema Interno Pseudosapiens - Equipo de Desarrollo**

*"Plataforma inteligente de entrega de inspiración diaria con monetización premium"*

**Última actualización**: Septiembre 14, 2025 - Integración Izipay completada