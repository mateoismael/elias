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

## Desarrollo local (dry-run)

1. Crea un entorno Python 3.11 y instala dependencias:
   - `pip install -r requirements.txt`
2. Ejecuta dry-run (no envía emails):
   - `PHRASES_CSV=frases_pilot.csv python scripts/send_emails.py --dry-run`

## Notas

- Zona horaria: el cron corre en UTC; la selección de frase se fija por hora UTC para evitar duplicados.
- Idempotencia: se añade un encabezado `Idempotency-Key` por slot para evitar duplicados si hay reintentos.
- Baja: el correo indica responder con "UNSUBSCRIBE" (implementar lógica de baja automática sería un siguiente paso, p.ej. lista en KV o Supabase y filtrado en el script).

## Próximos pasos sugeridos

- Confirmación de doble opt-in y enlace de desuscripción.
- Auditoría de entregabilidad (SPF/DKIM/DMARC en Resend y dominio propio).
- Persistir suscriptores en una BD (Supabase) y marcar estados (activo/baja/rebote).
