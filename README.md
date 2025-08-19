# elias

Servicio de frases motivacionales por email cada hora (frase aleatoria) usando Netlify (Forms) + GitHub Actions + Resend (Agosto 2025).

## Arquitectura

- Landing estática en Netlify con formulario (Netlify Forms).
- GitHub Actions corre cada hora (UTC), lee `frases_pilot.csv`, elige una frase aleatoria (determinística dentro de la hora) y la envía a los suscriptores capturados por Netlify Forms.
- Envío de emails via Resend.

## Requisitos

- Cuenta en Netlify y sitio creado a partir de este repo.
- Activar Netlify Forms (se detecta automáticamente al desplegar `index.html`).
- Cuenta en Resend, con dominio verificado o dirección de prueba.
- Configurar Secrets en GitHub: `RESEND_API_KEY`, `SENDER_EMAIL`, `NETLIFY_SITE_ID`, `NETLIFY_ACCESS_TOKEN`.

## Archivos clave

- `index.html`: formulario `name="subscribe"` con `data-netlify="true"`.
- `netlify.toml`: config del sitio.
- `frases_pilot.csv`: fuente de frases (columnas `id,text`).
- `scripts/send_emails.py`: script Python que:
  - lee frases
  - obtiene suscriptores desde Netlify Forms
  - envía una frase aleatoria por hora vía Resend
- `.github/workflows/send_emails.yml`: cron cada hora.

## Configuración (pasos)

1. Despliega en Netlify

   - Conecta el repo y despliega. Netlify detectará el formulario `subscribe` al primer deploy.
   - En Netlify, ve a Site Settings > General > Site details para copiar el `Site ID`.
   - Crea un personal access token en Netlify (User settings > Applications > Personal access tokens).

2. Configura Secrets en GitHub (Settings > Secrets and variables > Actions)

   - `RESEND_API_KEY`: tu API key de Resend.
   - `SENDER_EMAIL`: e.g. `Frases <no-reply@tu-dominio.com>` (usa un dominio verificado en Resend).
   - `NETLIFY_SITE_ID`: el Site ID del sitio.
   - `NETLIFY_ACCESS_TOKEN`: tu token personal de Netlify con acceso de lectura a forms.

3. Prueba el flujo
   - Haz una suscripción desde `index.html` desplegado (ingresa un email tuyo).
   - Ejecuta manualmente el workflow en GitHub (tab Actions > Send Motivational Phrases > Run workflow) o espera al cron.

## Mejoras Python 2025 🚀

### Nuevas Características Implementadas
- **Logging Estructurado JSON**: Logs en formato JSON con contexto enriquecido para monitoreo profesional
- **Validación de Datos con Pydantic**: Modelos type-safe para emails, frecuencias y contenido
- **Sistema de Fallback Automático**: Función principal modernizada con fallback robusto a versión legacy
- **Horarios Psicológicamente Optimizados**: Envíos en horarios de mayor impacto emocional (Peru timezone)
- **Seguridad Mejorada**: Tokens HMAC para desuscripción segura y timestamps únicos anti-agrupación
- **Manejo de Errores Específico**: Tratamiento diferenciado por tipo de error (red, rate limiting, etc.)

### Nuevas Dependencias
- `structlog>=25.0.0`: Logging estructurado JSON
- `pydantic[email]>=2.0.0`: Validación de datos y emails
- `python-dotenv>=1.0.0`: Carga automática de archivos .env

### Variables de Entorno Avanzadas (Opcionales)
- `RESEND_THROTTLE_SECONDS`: Segundos entre emails (default: 0.6)
- `RESEND_MAX_RETRIES`: Reintentos máximos en rate limiting (default: 8)
- `UNSUBSCRIBE_SECRET`: Clave secreta para tokens de desuscripción HMAC

## Desarrollo Local (Modernizado)

1. **Instalación completa:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Variables de entorno (.env):**
   ```bash
   # Copia .env desde el ejemplo y configura:
   RESEND_API_KEY=tu_api_key
   SENDER_EMAIL="Tu Nombre <tu@dominio.com>"
   TEST_MODE=true
   TEST_EMAILS=tu-email@gmail.com
   ```

3. **Testing y validación:**
   ```bash
   # Dry-run con logging estructurado JSON
   python scripts/send_emails.py --dry-run
   
   # Test mode con envío real
   python scripts/send_emails.py --test
   
   # Validación de datos automática
   python scripts/send_emails.py --dry-run  # Detecta emails inválidos
   ```

## Logging y Monitoreo

El sistema usa **logging estructurado JSON** para facilitar el monitoreo:
- Logs en formato JSON con timestamps ISO 8601
- Contexto enriquecido por operación (recipient, phrase_id, status_code)
- Niveles apropiados: INFO (operaciones), WARNING (validación), ERROR (fallos)
- Compatible con Elasticsearch, Splunk, y sistemas de agregación

**Ejemplo de log:**
```json
{
  "event": "Email sent successfully",
  "recipient": "user@example.com",
  "subject": "Buenos días",
  "phrase_id": "P131",
  "timestamp": "2025-08-19T15:46:55.382111Z",
  "level": "info"
}
```

## Troubleshooting

### Problemas Comunes
- **"Pydantic not installed"**: Ejecuta `pip install pydantic[email]`
- **"structlog not found"**: Ejecuta `pip install structlog>=25.0.0`
- **Rate limiting (429 errors)**: Ajusta `RESEND_THROTTLE_SECONDS=1.0` en .env
- **Emails inválidos**: El sistema los detecta automáticamente y continúa con válidos

### Validación de Configuración
El script valida automáticamente:
- ✅ Formato de emails con Pydantic EmailStr
- ✅ Frecuencias válidas (1, 3, 6, 24 horas únicamente)
- ✅ Variables de entorno requeridas (API keys, configuración)
- ✅ Conexión a servicios externos (Netlify, Resend)

### Modo Debug Avanzado
```bash
# Ver todos los logs detallados
python scripts/send_emails.py --dry-run

# Forzar test de fallback (solo desarrollo)
python scripts/send_emails.py --test-fallback --dry-run
```

## Notas

- Zona horaria: el cron corre en UTC; la selección de frase se fija por hora UTC para evitar duplicados.
- Idempotencia: se añade un encabezado `Idempotency-Key` por slot para evitar duplicados si hay reintentos.
- Baja: el correo indica responder con "UNSUBSCRIBE" (implementar lógica de baja automática sería un siguiente paso, p.ej. lista en KV o Supabase y filtrado en el script).

## Próximos pasos sugeridos

- Confirmación de doble opt-in y enlace de desuscripción.
- Auditoría de entregabilidad (SPF/DKIM/DMARC en Resend y dominio propio).
- Persistir suscriptores en una BD (Supabase) y marcar estados (activo/baja/rebote).
