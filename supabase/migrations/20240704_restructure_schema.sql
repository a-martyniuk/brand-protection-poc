-- Migration: Restructure Schema for Advanced Brand Protection
-- Layer 1: Master Data
CREATE TABLE IF NOT EXISTS public.master_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sap_code TEXT,
    ean TEXT UNIQUE,
    brand TEXT,
    product_name TEXT, -- Unificador
    format TEXT,
    fc_net DECIMAL,
    is_publishable BOOLEAN DEFAULT true,
    list_price DECIMAL(12, 2), -- PVP_Minimo
    status TEXT,
    units_per_pack INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Layer 2: Meli Listings (Scraped Data)
CREATE TABLE IF NOT EXISTS public.meli_listings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meli_id TEXT UNIQUE NOT NULL,
    seller_id TEXT,
    seller_name TEXT,
    title TEXT NOT NULL,
    brand_detected TEXT,
    ean_published TEXT,
    price DECIMAL(12, 2),
    url TEXT,
    thumbnail TEXT,
    status_publicacion TEXT,
    category TEXT,
    attributes JSONB,
    last_scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Layer 3: Compliance Audit Results
CREATE TABLE IF NOT EXISTS public.compliance_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id UUID REFERENCES public.meli_listings(id) ON DELETE CASCADE,
    master_product_id UUID REFERENCES public.master_products(id) ON DELETE SET NULL,
    match_level INTEGER, -- 1: EAN, 2: Fuzzy, 3: Suspicious
    is_brand_correct BOOLEAN DEFAULT true,
    is_price_ok BOOLEAN DEFAULT true,
    is_publishable_ok BOOLEAN DEFAULT true,
    fraud_score INTEGER DEFAULT 0,
    risk_level TEXT, -- "Bajo", "Medio", "Alto"
    violation_details JSONB,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_master_ean ON public.master_products(ean);
CREATE INDEX IF NOT EXISTS idx_listings_meli_id ON public.meli_listings(meli_id);
CREATE INDEX IF NOT EXISTS idx_audit_risk ON public.compliance_audit(risk_level);
