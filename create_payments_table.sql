-- Crear tabla payments para MercadoPago integration
-- Ejecutar en Supabase SQL Editor

CREATE TABLE payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subscription_id UUID REFERENCES subscriptions(id),
    mercadopago_payment_id VARCHAR(100),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'PEN',
    status VARCHAR(20), -- approved, pending, cancelled  
    payment_date TIMESTAMP WITH TIME ZONE,
    payment_method VARCHAR(20) DEFAULT 'mercadopago',
    yape_phone VARCHAR(15),
    payment_preference_id VARCHAR(100), 
    payment_type_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_payments_subscription_id ON payments(subscription_id);
CREATE INDEX idx_payments_mercadopago_id ON payments(mercadopago_payment_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_date ON payments(payment_date DESC);

-- Comentario para documentación
COMMENT ON TABLE payments IS 'Tabla de pagos para integración MercadoPago + Yape';