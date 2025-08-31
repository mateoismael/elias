-- Crear tabla email_logs para trackear estadísticas reales
-- Ejecutar en Supabase SQL Editor

CREATE TABLE IF NOT EXISTS email_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    user_email TEXT NOT NULL, -- Backup del email por si se borra el usuario
    phrase_id TEXT NOT NULL,
    phrase_content TEXT NOT NULL,
    phrase_author TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    email_status VARCHAR(20) DEFAULT 'sent', -- sent, failed, bounced
    provider VARCHAR(50) DEFAULT 'resend',
    provider_message_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_email_logs_user_id ON email_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_user_email ON email_logs(user_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_logs(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(email_status);

-- Habilitar RLS (Row Level Security)
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;

-- Policy básica - solo lectura para usuarios autenticados
CREATE POLICY "Allow read access to own email logs" ON email_logs
    FOR SELECT 
    USING (user_email = auth.email() OR auth.role() = 'service_role');

-- Comentarios para documentación
COMMENT ON TABLE email_logs IS 'Registro de emails enviados para estadísticas del dashboard';
COMMENT ON COLUMN email_logs.user_id IS 'Referencia al usuario que recibió el email';
COMMENT ON COLUMN email_logs.phrase_content IS 'Contenido de la frase enviada';
COMMENT ON COLUMN email_logs.sent_at IS 'Timestamp cuando se envió el email';