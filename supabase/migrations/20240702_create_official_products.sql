CREATE TABLE public.official_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sap_code INTEGER,
    ean TEXT,               -- Mapped from 'EAN'
    product_name TEXT,      -- Mapped from 'Unificador'
    distributor TEXT,       -- Mapped from 'R. Social comercializadora'
    business_unit TEXT,     -- Mapped from 'BU'
    therapeutic_area TEXT,  -- Mapped from 'TA'
    brand TEXT,             -- Mapped from 'Marca'
    stage TEXT,             -- Mapped from 'Etapa'
    substance TEXT,         -- Mapped from 'Sustancia'
    format TEXT,            -- Mapped from 'Formato'
    fc_dry DECIMAL,         -- Mapped from 'FC (Dry)'
    fc_net DECIMAL,         -- Mapped from 'FC (Net)'
    status TEXT,            -- Mapped from 'Estado'
    is_publishable BOOLEAN DEFAULT false, -- Mapped from 'Publicable si o no'
    list_price DECIMAL(12,2), -- Mapped from 'PVP minimo/lista'
    discount_allowed BOOLEAN DEFAULT false, -- Mapped from 'Descuento si o no'
    units_per_pack INTEGER, -- Mapped from 'Unidad por Presentación'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
