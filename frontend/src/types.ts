// Field-level validation status
export interface FieldStatus {
    scraped: string | number;
    master: string | number;
    status: 'approved' | 'rejected' | 'warning' | 'n/a';
    details?: string;
    score_impact?: number;
}

// Complete product audit with field breakdown
export interface ProductAudit {
    id: string;
    meli_id: string;
    title: string;
    seller: string;
    seller_location?: string;
    price: number;
    thumbnail?: string;
    url: string;

    // Match and compliance info
    match_level: number; // 0-3 (0=unidentified, 1=EAN, 2=Fuzzy, 3=Suspicious)
    fraud_score: number; // 0-100
    risk_level: string; // "Alto" | "Medio" | "Bajo"
    status: string; // "PENDING" | "REPORTED" | "CLEAN"

    // Field-level breakdown
    fields: {
        ean: FieldStatus;
        brand: FieldStatus;
        price: FieldStatus;
        volume: FieldStatus;
        quantity: FieldStatus;
        discount: FieldStatus;
        publishable: FieldStatus;
    };

    // Master product reference
    master_product?: {
        id: string;
        product_name: string;
        brand: string;
        list_price: number;
        fc_net: number;
        ean: string;
    };

    // Raw violation details for debugging
    violation_details?: any;
}

export interface DashboardStats {
    scanned: number;
    active: number;
    cleaned: number;
    high_risk: number;
    medium_risk: number;
    low_risk: number;
}

export type RiskFilter = 'ALL' | 'Alto' | 'Medio' | 'Bajo';
export type MatchFilter = 'ALL' | 'EAN' | 'Fuzzy' | 'Suspicious' | 'Unidentified';

// Legacy type for backward compatibility (will be removed)
export interface Violation {
    id: string;
    meli_id?: string;
    type: 'PRICE' | 'KEYWORD' | 'UNAUTHORIZED_SELLER' | 'INSPECTED' | string;
    product: string;
    seller: string;
    seller_location?: string;
    is_authorized?: boolean;
    price: number;
    expected: number;
    diff_pct?: number;
    found_keywords?: string[];
    measure_mismatch?: string[];
    unauthorized_discount?: boolean;
    status: string;
    url: string;
    thumbnail?: string;
}

export type FilterType = 'ALL' | 'PRICE' | 'BRAND_MISM' | 'RESTRICTED' | 'SUSPICIOUS' | 'TOTAL_ANALYZED';
