CREATE TABLE faq_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    language CHAR(2) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX faq_property_lang ON faq_entries(property_id, language);
CREATE INDEX faq_tags ON faq_entries USING GIN(tags);
