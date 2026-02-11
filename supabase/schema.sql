-- Products table to store scraped data
CREATE TABLE public.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meli_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    price DECIMAL(12, 2),
    url TEXT,
    seller_id TEXT,
    seller_name TEXT,
    seller_location TEXT,
    thumbnail TEXT,
    is_authorized BOOLEAN DEFAULT false,
    is_official BOOLEAN DEFAULT false,
    reputation TEXT,
    last_scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Policies table to define brand rules
CREATE TABLE public.policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_name TEXT NOT NULL,
    min_price DECIMAL(12, 2), -- MAP (Minimum Advertised Price)
    keywords_blacklist TEXT[], -- e.g. ["alternativo", "replica"]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Violations table to store detected issues
CREATE TABLE public.violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES public.products(id),
    policy_id UUID REFERENCES public.policies(id),
    violation_type TEXT, -- "PRICE", "KEYWORD", "UNAUTHORIZED_SELLER"
    details JSONB,
    status TEXT DEFAULT 'PENDING', -- "PENDING", "REPORTED", "DISMISSED"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
