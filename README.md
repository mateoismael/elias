# 💭 Pseudosapiens - Documentación Interna

**Repositorio Privado de Negocio - Sistema Inteligente de Email Marketing**

Plataforma automatizada para el envío personalizado de frases motivacionales utilizando OpenAI GPT-4o mini para la generación única de asuntos. Gestión avanzada de usuarios, algoritmos anti-repetición y análisis integral.

> **⚠️ CONFIDENCIAL**: Este es un repositorio privado de negocio. Todo el código, estrategias y documentación son propietarios y confidenciales.

## 🚀 Características Principales

### ✨ Asuntos Inteligentes con IA
- **GPT-4o mini Integration**: Genera asuntos únicos basados en el contenido de cada frase
- **Contextualización temporal**: Adapta el tono según la hora del día
- **Variabilidad real**: Cada email tiene un asunto específico y profesional
- **Ultra-económico**: ~$0.000013 por asunto (~$0.47/año para 100 emails diarios)

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
- **Netlify Forms**: Captura de suscripciones desde el frontend
- **Logging estructurado**: Monitoreo completo con structlog
- **Configuración flexible**: Variables de entorno para todos los ajustes

## 📁 Estructura del Proyecto

```
elias/
├── scripts/                          # Módulos Python principales
│   ├── send_emails.py                # Sistema principal de envío
│   ├── smart_subject_generator.py    # Generación IA de asuntos
│   ├── database.py                   # Gestión de usuarios y suscripciones
│   ├── database_phrases.py           # Gestión de frases y anti-repetición
│   └── smart_phrase_system.py        # Lógica de selección inteligente
├── index.html                        # Landing page de suscripción
├── dashboard.html                    # Panel de control centralizado (con tabs: overview, preferences, stats)
├── unsubscribe.html                  # Página de desuscripción
├── .env                             # Configuración de producción
├── requirements.txt                 # Dependencias Python
└── netlify.toml                     # Configuración de despliegue
```

## 🔧 Instalación y Configuración

### Prerrequisitos
- Python 3.8+
- Cuenta en [Supabase](https://supabase.com)
- API Key de [OpenAI](https://openai.com)
- API Key de [Resend](https://resend.com)
- Cuenta en [Netlify](https://netlify.com) (opcional)

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
SENDER_EMAIL=Tu Nombre <tu@dominio.com>

# === NETLIFY FORMS ===
NETLIFY_SITE_ID=your-site-id
NETLIFY_ACCESS_TOKEN=nfp_your-netlify-token
NETLIFY_FORM_NAME=subscribe

# === SUPABASE DATABASE ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

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

## 🚀 Uso

### Envío Manual de Emails
```bash
cd scripts
python send_emails.py
```

### Modo de Prueba
```bash
# Activar en .env
TEST_MODE=true
TEST_EMAILS=test@example.com,test2@example.com
```

### Configurar Cron Job (Automatización)
```bash
# Ejemplo: enviar cada día a las 9:00 AM
0 9 * * * cd /path/to/elias/scripts && python send_emails.py
```

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
2025-09-09 19:46:58 [info] OpenAI subject generated successfully
    subject=Levántate tras cada caída
    author=Confucio 
    cost_estimate=1.3e-05
    phrase_preview=La gloria no consiste en no ca...
```

### Métricas Clave
- Emails enviados exitosamente
- Tasa de error por proveedor
- Costos de IA por email
- Tiempo de procesamiento
- Frases utilizadas por usuario

## 💰 Costos Estimados

### OpenAI GPT-4o mini
- **Input**: $0.15/1M tokens
- **Output**: $0.60/1M tokens  
- **Costo promedio por asunto**: ~$0.000013
- **100 emails/día**: ~$0.47/año

### Resend Email
- **Precio**: $0.001 por email (después de 3,000 gratis/mes)
- **100 emails/día**: ~$30/año

### Total Operativo
**~$30.47/año para 100 emails diarios**

## 🔐 Seguridad y Privacidad

- **Variables de entorno**: Todas las claves sensibles en `.env`
- **Tokens de desuscripción**: Generación segura de URLs únicas
- **Rate limiting**: Protección contra spam y abuso
- **Validación de emails**: Verificación de formato y dominio
- **HTTPS**: Todas las comunicaciones encriptadas

## 🚢 Despliegue en Producción

### Netlify (Recomendado)
1. Conectar repositorio GitHub a Netlify
2. Configurar variables de entorno en Netlify Dashboard
3. Configurar `TEST_MODE=false` en producción
4. Establecer cron job para `scripts/send_emails.py`

### VPS/Servidor Dedicado
1. Clonar repositorio en servidor
2. Configurar cron jobs para automatización
3. Configurar nginx/apache para servir archivos estáticos
4. Establecer certificados SSL

## 🧪 Testing

### Test Manual del Sistema
```bash
cd scripts
python -c "
from smart_subject_generator import test_subject_generation
test_subject_generation()
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

**Emails no se envían**
```python  
# Verificar modo test
print("Modo TEST activo:", os.getenv('TEST_MODE'))
print("Emails de prueba:", os.getenv('TEST_EMAILS'))
```

## 📈 Próximas Funcionalidades

- [ ] Dashboard web con métricas en tiempo real
- [ ] A/B testing para asuntos y contenido
- [ ] Segmentación de usuarios por intereses  
- [ ] API REST para integración externa
- [ ] Plantillas HTML personalizables
- [ ] Analytics avanzados con Google Analytics
- [ ] Integración con más proveedores de email

## 🔒 Acceso y Seguridad

- **Repositorio Privado**: Solo miembros autorizados del equipo tienen acceso
- **Claves de Producción**: Almacenadas de forma segura en GitHub Secrets
- **Base de Datos**: Supabase con seguridad a nivel de fila habilitada
- **Email**: Resend API con verificación de dominio

## 📝 Licencia y Propiedad

**© 2025 Pseudosapiens - Todos los Derechos Reservados**

Este software y toda la documentación asociada son propietarios y confidenciales. La copia, distribución o uso no autorizado está estrictamente prohibido.

## 📞 Soporte Interno

- **Problemas Técnicos**: Contactar directamente al equipo de desarrollo
- **Lógica de Negocio**: Ver documentación en línea del código
- **Problemas de Producción**: Revisar logs de GitHub Actions y dashboard de Supabase

---

**Sistema Interno Pseudosapiens - Equipo de Desarrollo**

*"Plataforma inteligente de entrega de inspiración diaria"*