-- Migration: Add official_product_id to products table
-- This allows linking scraped results to the master data in official_products

ALTER TABLE public.products 
ADD COLUMN official_product_id UUID REFERENCES public.official_products(id);

-- Optional: Index for better join performance
CREATE INDEX idx_products_official_id ON public.products(official_product_id);
