-- Migration: Add detailed item status to meli_listings
-- Purpose: Track if a listing is active, paused, or closed.

ALTER TABLE public.meli_listings 
    ADD COLUMN IF NOT EXISTS item_status TEXT DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS status_description TEXT;

CREATE INDEX IF NOT EXISTS idx_listings_status ON public.meli_listings(item_status);
