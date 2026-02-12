-- Migration: Add seller_location to meli_listings
ALTER TABLE public.meli_listings ADD COLUMN IF NOT EXISTS seller_location TEXT;
