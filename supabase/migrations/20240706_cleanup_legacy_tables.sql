-- Recommendation: Cleanup Legacy Schema
-- Run this ONLY if you have already verified the new 4-layer system works and your data is migrated.

-- 1. Drop old violation logs (Replaced by compliance_audit)
DROP TABLE IF EXISTS public.violations;

-- 2. Drop old scraped products (Replaced by meli_listings)
DROP TABLE IF EXISTS public.products;

-- 3. Drop old official products (Replaced by master_products)
-- CAUTION: If you have other apps using this table, don't drop it yet.
DROP TABLE IF EXISTS public.official_products;

-- Note: 'policies' and 'authorized_sellers' can be kept if you plan 
-- to implement more complex business rules beyond price/brand matching.
