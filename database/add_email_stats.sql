-- Agregar estadísticas de email a tabla users
-- Ejecutar en Supabase SQL Editor

-- Agregar columnas para estadísticas
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_emails_sent INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_email_sent_at TIMESTAMP WITH TIME ZONE;

-- Índice para performance en consultas de dashboard
CREATE INDEX IF NOT EXISTS idx_users_total_emails ON users(total_emails_sent);
CREATE INDEX IF NOT EXISTS idx_users_last_email ON users(last_email_sent_at);

-- Comentarios para documentación
COMMENT ON COLUMN users.total_emails_sent IS 'Contador total de emails enviados al usuario desde el registro';
COMMENT ON COLUMN users.last_email_sent_at IS 'Timestamp del último email enviado para confirmación de servicio';

-- Verificar que se agregaron correctamente
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('total_emails_sent', 'last_email_sent_at');