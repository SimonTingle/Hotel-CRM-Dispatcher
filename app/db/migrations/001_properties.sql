CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    address TEXT,
    checkin_time TIME,
    checkout_time TIME,
    wifi_password_enc TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
