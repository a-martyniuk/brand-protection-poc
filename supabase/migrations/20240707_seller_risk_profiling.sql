-- Migration: Seller Risk Profiling for Brand Protection
-- Purpose: Aggregates violations by seller to identify systematic offenders.

CREATE OR REPLACE VIEW public.seller_risk_summary AS
WITH seller_metrics AS (
    SELECT 
        l.seller_name,
        COUNT(l.id) as total_listings,
        COUNT(a.id) FILTER (WHERE a.fraud_score >= 30) as total_violations,
        COUNT(a.id) FILTER (WHERE a.is_price_ok = false) as price_violations,
        COUNT(a.id) FILTER (WHERE a.fraud_score >= 60 AND a.is_brand_correct = false) as brand_risk_violations,
        COUNT(a.id) FILTER (WHERE a.fraud_score >= 60 AND (a.violation_details->>'volumetric_mismatch' IS NOT NULL)) as format_fraud_violations,
        AVG(a.fraud_score) as avg_fraud_score,
        MAX(a.processed_at) as last_violation_at
    FROM 
        public.meli_listings l
    LEFT JOIN 
        public.compliance_audit a ON l.id = a.listing_id
    GROUP BY 
        l.seller_name
)
SELECT 
    *,
    CASE 
        WHEN total_violations > 5 OR avg_fraud_score > 50 THEN 'Alto'
        WHEN total_violations > 2 THEN 'Medio'
        ELSE 'Bajo'
    END as risk_level,
    (total_violations::float / NULLIF(total_listings, 0)) * 100 as violation_rate_pct
FROM 
    seller_metrics
ORDER BY 
    total_violations DESC, avg_fraud_score DESC;

-- Add comment to view
COMMENT ON VIEW public.seller_risk_summary IS 'Summarizes brand protection compliance risk at the seller level.';
