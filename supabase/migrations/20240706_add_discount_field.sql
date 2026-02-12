-- Add discount_allowed column to master_products
ALTER TABLE public.master_products ADD COLUMN IF NOT EXISTS discount_allowed BOOLEAN DEFAULT true;
