-- MODELO FREEMIUM OPTIMIZADO 2025: DELIVERABILITY-SAFE + CONVERSION-FOCUSED
-- Ejecutar en Supabase SQL Editor
-- Mantiene opción 1h para uso manual/VIP

-- Eliminar planes y suscripciones existentes (reset limpio)
DELETE FROM subscriptions;
DELETE FROM subscription_plans;

-- INSERTAR NUEVO MODELO DE PLANES 2025 (Plan ID = Emails por día)
INSERT INTO subscription_plans (id, name, display_name, price_soles, frequency_hours, max_emails_per_day, description, is_active) VALUES

-- Plan 0: GRATUITO (3 por semana = L-M-V)
(0, 'free', 'Gratuito', 0.00, 56, 3, '3 frases por semana (Lunes-Miércoles-Viernes a las 8:00)', true),

-- Plan 1: PREMIUM - 1 por día
(1, 'premium_1_day', 'Premium 1/día', 5.00, 24, 1, '1 frase al día (8:00)', true),

-- Plan 2: PREMIUM - 2 por día
(2, 'premium_2_day', 'Premium 2/día', 5.00, 12, 2, '2 frases al día (8:00, 17:00)', true),

-- Plan 3: PREMIUM - 3 por día
(3, 'premium_3_day', 'Premium 3/día', 5.00, 8, 3, '3 frases al día (8:00, 14:00, 20:00)', true),

-- Plan 4: PREMIUM - 4 por día
(4, 'premium_4_day', 'Premium 4/día', 5.00, 6, 4, '4 frases al día (8:00, 12:00, 17:00, 21:00)', true),

-- Plan 13: PREMIUM - Power User (13 por día) - OCULTO/MANUAL SOLO
(13, 'premium_power_user', 'Premium Power User', 5.00, 1, 13, '13 frases al día (cada hora 8:00-20:00)', false);

-- Reiniciar secuencia de IDs
ALTER SEQUENCE subscription_plans_id_seq RESTART WITH 14;

-- VERIFICAR PLANES CREADOS
SELECT 
    id, 
    name, 
    display_name, 
    price_soles, 
    frequency_hours,
    max_emails_per_day, 
    description,
    is_active
FROM subscription_plans 
ORDER BY id;

-- MIGRAR USUARIOS EXISTENTES AL PLAN GRATUITO NUEVO
INSERT INTO subscriptions (user_id, plan_id, status, started_at)
SELECT 
    id, 
    0,  -- Plan gratuito nuevo (Plan 0 = 3/semana)
    'active', 
    NOW()
FROM users 
WHERE id NOT IN (SELECT DISTINCT user_id FROM subscriptions WHERE status = 'active');

-- ACTUALIZAR SUSCRIPCIONES EXISTENTES AL NUEVO MODELO
UPDATE subscriptions 
SET plan_id = 0, updated_at = NOW()
WHERE status = 'active' AND plan_id NOT IN (0,1,2,3,4,13);

-- VERIFICAR MIGRACIÓN
SELECT 
    u.email,
    sp.display_name as plan,
    sp.price_soles as precio,
    sp.frequency_hours as frecuencia_horas,
    sp.max_emails_per_day as emails_por_dia,
    s.status
FROM subscriptions s
JOIN users u ON s.user_id = u.id
JOIN subscription_plans sp ON s.plan_id = sp.id
WHERE s.status = 'active'
ORDER BY u.email;

-- AGREGAR CAMPOS PARA MERCADOPAGO INTEGRATION
ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20) DEFAULT 'mercadopago';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS yape_phone VARCHAR(15);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_preference_id VARCHAR(100);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_type_id VARCHAR(50);

-- Índices adicionales para performance
CREATE INDEX IF NOT EXISTS idx_payments_method ON payments(payment_method);
CREATE INDEX IF NOT EXISTS idx_payments_preference ON payments(payment_preference_id);
CREATE INDEX IF NOT EXISTS idx_payments_mercadopago_id ON payments(mercadopago_payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date DESC);

-- Agregar webhook secret para validación MercadoPago
CREATE TABLE IF NOT EXISTS webhook_secrets (
    id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL,
    secret_key TEXT NOT NULL,
    environment VARCHAR(20) DEFAULT 'production',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(service, environment)
);

-- Insertar secreto placeholder para MercadoPago
INSERT INTO webhook_secrets (service, secret_key, environment) VALUES
('mercadopago', 'placeholder_secret_key', 'sandbox'),
('mercadopago', 'placeholder_secret_key', 'production')
ON CONFLICT (service, environment) DO NOTHING;

-- Agregar tabla de logs para auditoría de pagos
CREATE TABLE IF NOT EXISTS payment_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    payment_id UUID REFERENCES payments(id),
    mercadopago_payment_id VARCHAR(100),
    event_type VARCHAR(50) NOT NULL, -- webhook_received, payment_processed, error, etc.
    event_data JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_logs_payment_id ON payment_logs(payment_id);
CREATE INDEX IF NOT EXISTS idx_payment_logs_event_type ON payment_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_payment_logs_created_at ON payment_logs(created_at DESC);

-- COMENTARIOS IMPORTANTES:
-- NUEVA ESTRUCTURA: Plan ID = Emails por día
-- Plan 0 (Free): 3/semana (L-M-V), frequency_hours = 56
-- Plan 1-4 (Premium): 1/día, 2/día, 3/día, 4/día respectivamente  
-- Plan 13 (Power User): 13/día, is_active = false (oculto, solo asignación manual)
-- Todos los premium cuestan S/5.00 (modelo simplificado)
-- Horarios optimizados para Peru timezone (UTC-5)
-- MERCADOPAGO: Tabla payments extendida con campos para Yape y tracking completo