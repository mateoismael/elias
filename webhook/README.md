# Webhook Netlify → Supabase

Este webhook automatiza la captura de nuevos suscriptores desde Netlify Forms hacia Supabase.

## Deployment en Railway

1. **Crear cuenta en Railway**: https://railway.app
2. **Connect GitHub repo** y seleccionar la carpeta `webhook/`
3. **Configurar variables de entorno**:
   - `SUPABASE_URL`: URL de tu proyecto Supabase
   - `SUPABASE_KEY`: Anon public key de Supabase

## Endpoints

- **POST /webhook/netlify-form** - Recibe formularios de Netlify
- **GET /webhook/health** - Health check
- **GET /webhook/stats** - Estadísticas de suscriptores

## Configuración en Netlify

Una vez deployado, agregar la URL del webhook en:
Netlify Dashboard > Site Settings > Forms > Notifications > Add notification

URL webhook: `https://tu-webhook.railway.app/webhook/netlify-form`