// Estado de validación a nivel de campo
export interface FieldStatus {
    scraped: string | number;
    master: string | number;
    status: 'approved' | 'rejected' | 'warning' | 'n/a';
    details?: string;
    score_impact?: number;
    unit_price?: number;
    unit_weight?: number;
    qty_multiplier?: number;
    master_unit_value?: string | number;
}

// Auditoría completa del producto con desglose de campos
export interface ProductAudit {
    id: string;
    meli_id: string;
    title: string;
    seller: string;
    seller_location?: string;
    price: number;
    thumbnail?: string;
    url: string;
    available_stock?: number;
    item_status?: string; // "active" | "paused" | "closed" | "noise" | "noise_manual"

    // Información de coincidencia y cumplimiento
    match_level: number; // 0-3 (0=unidentified, 1=EAN, 2=Fuzzy, 3=Suspicious)
    fraud_score: number; // 0-100
    risk_level: string; // "Alto" | "Medio" | "Bajo"
    status: string; // "PENDING" | "REPORTED" | "CLEAN"

    // Desglose de campos
    fields: {
        ean: FieldStatus;
        brand: FieldStatus;
        price: FieldStatus;
        volume: FieldStatus;
        quantity: FieldStatus;
        discount: FieldStatus;
        publishable: FieldStatus;
    };

    // Referencia del producto maestro
    master_product?: {
        id: string;
        product_name: string;
        brand: string;
        list_price: number;
        fc_net: number;
        ean: string;
    };

    // Detalles raw de violaciones para depuración
    violation_details?: any;
}

export interface DashboardStats {
    scanned: number;
    active: number;
    cleaned: number;
    high_risk: number;
    medium_risk: number;
    low_risk: number;
    last_audit?: string;
}

export type RiskFilter = 'ALL' | 'Alto' | 'Medio' | 'Bajo';
export type MatchFilter = 'ALL' | 'EAN' | 'Fuzzy' | 'Suspicious' | 'Unidentified';

// Tipo heredado para compatibilidad hacia atrás (será eliminado)
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

