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

export interface DashboardStats {
    scanned: number;
    active: number;
    cleaned: number;
}

export type FilterType = 'ALL' | 'PRICE' | 'BRAND_MISM' | 'RESTRICTED' | 'SUSPICIOUS' | 'TOTAL_ANALYZED';
