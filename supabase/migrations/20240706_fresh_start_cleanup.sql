-- Cleanup existing data for a fresh start with Attribute-Based logic
TRUNCATE TABLE public.meli_listings CASCADE;
-- CASCADE will also clear compliance_audit due to foreign key constraints
