-- MODELO FREEMIUM SIMPLIFICADO: GRATIS vs PREMIUM S/5
-- Ejecutar en Supabase SQL Editor

-- Eliminar planes existentes
DELETE FROM subscriptions; -- Primero eliminar suscripciones
DELETE FROM subscription_plans; -- Luego eliminar planes

-- Insertar solo 2 planes: GRATIS y PREMIUM
INSERT INTO subscription_plans (id, name, display_name, price_soles, frequency_hours, max_emails_per_day, description, is_active) VALUES
-- Plan 1: GRATIS (6 horas, 3 frases/día)
(1, 'free', 'Gratuito', 0.00, 6, 3, 'Recibe 3 frases motivacionales cada día', true),

-- Plan 2: PREMIUM (acceso a todas las frecuencias)
(2, 'premium', 'Premium', 5.00, 1, 19, 'Acceso completo: elige cualquier frecuencia de envío', true);

-- Reiniciar secuencia de IDs
ALTER SEQUENCE subscription_plans_id_seq RESTART WITH 3;

-- Verificar planes creados
SELECT id, name, display_name, price_soles, frequency_hours, max_emails_per_day, description 
FROM subscription_plans 
ORDER BY id;

-- Crear suscripciones gratuitas para usuarios existentes
INSERT INTO subscriptions (user_id, plan_id, status, started_at)
SELECT id, 1, 'active', NOW()
FROM users 
WHERE id NOT IN (SELECT DISTINCT user_id FROM subscriptions WHERE status = 'active');

-- Verificar suscripciones
SELECT 
    u.email,
    sp.display_name as plan,
    sp.price_soles as precio,
    s.status
FROM subscriptions s
JOIN users u ON s.user_id = u.id
JOIN subscription_plans sp ON s.plan_id = sp.id
ORDER BY u.email;