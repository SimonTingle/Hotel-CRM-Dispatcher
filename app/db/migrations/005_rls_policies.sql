ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE faq_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE crew_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE guest_messages ENABLE ROW LEVEL SECURITY;

-- Only the service_role key (backend) can read/write all tables.
-- The anon key has no access to anything.
CREATE POLICY "service_only" ON properties
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "service_only" ON faq_entries
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "service_only" ON crew_contacts
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "service_only" ON guest_messages
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
