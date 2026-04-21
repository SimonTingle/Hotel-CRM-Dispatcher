CREATE TABLE guest_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_wa_id TEXT NOT NULL,
    property_id UUID REFERENCES properties(id),
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    intent TEXT,
    message_scrubbed TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX guest_messages_wa_id ON guest_messages(guest_wa_id, created_at DESC);
CREATE INDEX guest_messages_property ON guest_messages(property_id, created_at DESC);
