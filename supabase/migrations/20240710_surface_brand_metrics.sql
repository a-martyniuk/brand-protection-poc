-- Migration: Surface meta fields for better Brand Protection analytics
-- Purpose: Promotes deep-scraped metadata from JSONB to top-level columns for filtering/sorting.

ALTER TABLE public.meli_listings 
    ADD COLUMN IF NOT EXISTS is_official_store BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS sold_quantity INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS condition TEXT,
    ADD COLUMN IF NOT EXISTS last_enriched_at TIMESTAMP WITH TIME ZONE;

-- Update Indexing for the new filters
CREATE INDEX IF NOT EXISTS idx_listings_official ON public.meli_listings(is_official_store);
CREATE INDEX IF NOT EXISTS idx_listings_sold ON public.meli_listings(sold_quantity);
