-- Schema para sistema de suscripciones de frases motivacionales
-- Ejecutar en Supabase SQL Editor

-- Tabla de usuarios y sus suscripciones
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de planes de suscripción
CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL, -- free, premium, pro, intensivo
    display_name VARCHAR(100) NOT NULL,
    price_soles DECIMAL(10,2) NOT NULL DEFAULT 0,
    frequency_hours INTEGER NOT NULL, -- 24, 6, 3, 1
    max_emails_per_day INTEGER NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de suscripciones activas
CREATE TABLE subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_id INTEGER REFERENCES subscription_plans(id),
    status VARCHAR(20) DEFAULT 'active', -- active, paused, cancelled, expired
    mercadopago_subscription_id VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de historial de pagos
CREATE TABLE payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subscription_id UUID REFERENCES subscriptions(id),
    mercadopago_payment_id VARCHAR(100),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'PEN',
    status VARCHAR(20), -- approved, pending, cancelled
    payment_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insertar planes iniciales
INSERT INTO subscription_plans (name, display_name, price_soles, frequency_hours, max_emails_per_day, description) VALUES
('free', 'Gratuito', 0, 24, 1, 'Una frase motivacional al día'),
('premium', 'Premium', 9.90, 6, 4, 'Frases cada 6 horas con contenido exclusivo'),
('pro', 'Pro', 19.90, 3, 8, 'Frases cada 3 horas con personalización'),
('intensivo', 'Intensivo', 29.90, 1, 19, 'Frases cada hora con IA personalizado');

-- Índices para performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_payments_subscription_id ON payments(subscription_id);

-- RLS (Row Level Security) - opcional por ahora
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();