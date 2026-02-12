-- Add missing identification attributes to master_products
ALTER TABLE public.master_products ADD COLUMN IF NOT EXISTS stage TEXT;
ALTER TABLE public.master_products ADD COLUMN IF NOT EXISTS substance TEXT;
ALTER TABLE public.master_products ADD COLUMN IF NOT EXISTS therapeutic_area TEXT;
ALTER TABLE public.master_products ADD COLUMN IF NOT EXISTS business_unit TEXT;
ALTER TABLE public.master_products ADD COLUMN IF NOT EXISTS fc_dry DECIMAL;
ALTER TABLE public.master_products ADD COLUMN IF NOT EXISTS distributor TEXT;
