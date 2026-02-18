import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../supabaseClient';
import { ProductAudit, DashboardStats, FieldStatus } from '../types';

/**
 * Parses violation_details JSONB into structured field-level comparison
 */
function parseFieldStatus(audit: any, listing: any, master: any): ProductAudit['fields'] {
    const details = audit.violation_details || {};

    return {
        ean: {
            scraped: listing?.ean_published || 'Not provided',
            master: master?.ean || 'N/A',
            status: details.missing_ean ? 'warning' : (listing?.ean_published ? 'approved' : 'n/a'),
            details: details.missing_ean ? 'EAN not provided in listing' : undefined,
            score_impact: details.missing_ean ? 20 : 0
        },
        brand: {
            scraped: details.brand_mismatch?.found || listing?.brand_detected || details.detected_brand || 'Not detected',
            master: details.brand_mismatch?.expected || master?.brand || 'N/A',
            status: details.brand_mismatch ? 'rejected' : 'approved',
            details: details.brand_mismatch ? `Expected "${details.brand_mismatch.expected}", found "${details.brand_mismatch.found}"` : undefined,
            score_impact: details.brand_mismatch ? 30 : 0
        },
        price: {
            scraped: listing?.price ? `$${listing.price.toLocaleString('es-AR')}` : 'N/A',
            master: details.low_price?.min_allowed
                ? `$${details.low_price.min_allowed.toLocaleString('es-AR')} (min)`
                : (master?.list_price ? `$${master.list_price.toLocaleString('es-AR')}` : 'N/A'),
            status: details.low_price ? 'rejected' : 'approved',
            details: details.low_price
                ? `Price $${listing?.price?.toLocaleString('es-AR')} is below minimum $${details.low_price.min_allowed?.toLocaleString('es-AR')}`
                : (details.unit_price_info?.is_pack ? `Unit Price: $${details.unit_price_info.unit_price?.toLocaleString('es-AR')}` : undefined),
            score_impact: details.low_price ? 100 : 0,
            unit_price: details.unit_price_info?.unit_price
        },
        volume: {
            scraped: details.volumetric_info?.detected_total_kg ?? (typeof details.volumetric_mismatch?.detected_in_listing === 'number' ? details.volumetric_mismatch.detected_in_listing : (typeof details.detected_volume === 'number' ? details.detected_volume : 0))
                ? `${details.volumetric_info?.detected_total_kg || details.volumetric_mismatch?.detected_in_listing || details.detected_volume} kg`
                : 'Not detected',
            master: (details.volumetric_info?.expected_total_kg || details.volumetric_mismatch?.expected_kg || master?.fc_net)
                ? `${details.volumetric_info?.expected_total_kg || details.volumetric_mismatch?.expected_kg || master?.fc_net} kg`
                : 'N/A',
            status: details.volumetric_mismatch ? 'rejected' : 'approved',
            details: details.volumetric_mismatch
                ? `Volume mismatch detected (Expected ${details.volumetric_info?.expected_total_kg || details.volumetric_mismatch?.expected_kg || master?.fc_net}kg)`
                : undefined,
            score_impact: details.volumetric_mismatch ? 100 : 0,
            unit_weight: details.volumetric_info?.unit_weight
        },
        quantity: {
            scraped: details.combo_mismatch?.listing
                ? `${details.combo_mismatch.listing} units`
                : '1 unit',
            master: details.combo_mismatch?.master
                ? `${details.combo_mismatch.master} units`
                : (master?.units_per_pack || '1 unit'),
            status: details.combo_mismatch ? 'rejected' : 'approved',
            details: details.combo_mismatch
                ? `Expected ${details.combo_mismatch.master} units, found ${details.combo_mismatch.listing}`
                : undefined,
            score_impact: details.combo_mismatch ? 20 : 0
        },
        discount: {
            scraped: details.unauthorized_discount ? 'Yes (unauthorized)' : 'No',
            master: details.unauthorized_discount ? 'Not allowed' : 'Allowed',
            status: details.unauthorized_discount ? 'rejected' : 'approved',
            details: details.unauthorized_discount
                ? 'This product should never have a discount'
                : undefined,
            score_impact: details.unauthorized_discount ? 60 : 0
        },
        publishable: {
            scraped: listing?.status_publicacion || 'Active',
            master: details.restricted_sku_violation ? 'Not publishable' : 'Publishable',
            status: details.restricted_sku_violation ? 'rejected' : 'approved',
            details: details.restricted_sku_violation
                ? 'This SKU should not be published on marketplace'
                : undefined,
            score_impact: details.restricted_sku_violation ? 100 : 0
        }
    };
}

export const useBrandData = () => {
    const [products, setProducts] = useState<ProductAudit[]>([]);
    const [stats, setStats] = useState<DashboardStats>({
        scanned: 0,
        active: 0,
        cleaned: 0,
        high_risk: 0,
        medium_risk: 0,
        low_risk: 0
    });
    const [enrichmentStats, setEnrichmentStats] = useState<{
        total: number;
        enriched: number;
        pending: number;
        isRunning: boolean;
    }>({ total: 0, enriched: 0, pending: 0, isRunning: false });
    const [loading, setLoading] = useState(true);

    const fetchEnrichmentStats = useCallback(async () => {
        try {
            const res = await fetch('http://localhost:8000/status');
            const data = await res.json();
            setEnrichmentStats({
                total: data.total_products || 0,
                enriched: data.enriched || 0,
                pending: (data.total_products || 0) - (data.processed || 0),
                isRunning: !!data.pipeline_running
            });
        } catch (err) {
            console.warn('Local API Bridge not reachable');
        }
    }, []);

    const runPipeline = async () => {
        try {
            await fetch('http://localhost:8000/pipeline/run', { method: 'POST' });
            fetchEnrichmentStats();
        } catch (err) {
            alert('Error starting pipeline. Is api_bridge.py running?');
        }
    };

    const refreshScores = async () => {
        try {
            await fetch('http://localhost:8000/audit/refresh', { method: 'POST' });
            setTimeout(fetchData, 2000); // Give it a moment to start
        } catch (err) {
            alert('Error refreshing scores. Is api_bridge.py running?');
        }
    };

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            // Fetch compliance data with pagination (bypassing 1000 row limit)
            let allAuditData: any[] = [];
            let offset = 0;
            const batchSize = 1000;

            while (true) {
                const { data: auditBatch, error: aError } = await supabase
                    .from('compliance_audit')
                    .select(`
                        *,
                        meli_listings(*),
                        master_products(*)
                    `)
                    .order('processed_at', { ascending: false })
                    .range(offset, offset + batchSize - 1);

                if (aError) throw aError;
                if (!auditBatch || auditBatch.length === 0) break;

                allAuditData = [...allAuditData, ...auditBatch];
                if (auditBatch.length < batchSize) break;
                offset += batchSize;
            }

            // Stats counts (using count: 'exact' is safer as it bypasses row limits)
            const { count: listingCount } = await supabase.from('meli_listings').select('*', { count: 'exact', head: true });
            const { count: highRiskCount } = await supabase.from('compliance_audit').select('*', { count: 'exact', head: true }).eq('risk_level', 'Alto');
            const { count: mediumRiskCount } = await supabase.from('compliance_audit').select('*', { count: 'exact', head: true }).eq('risk_level', 'Medio');
            const { count: lowRiskCount } = await supabase.from('compliance_audit').select('*', { count: 'exact', head: true }).eq('risk_level', 'Bajo');

            if (allAuditData) {
                const fetchedProducts: ProductAudit[] = allAuditData.map((a: any) => ({
                    id: a.id,
                    meli_id: a.meli_listings?.meli_id || 'N/A',
                    title: a.meli_listings?.title || 'Unknown Listing',
                    seller: a.meli_listings?.seller_name || 'Unknown Seller',
                    seller_location: a.meli_listings?.seller_location || 'N/A',
                    price: a.meli_listings?.price || 0,
                    thumbnail: a.meli_listings?.thumbnail,
                    url: a.meli_listings?.url || '#',
                    match_level: a.match_level || 0,
                    fraud_score: a.fraud_score || 0,
                    risk_level: a.risk_level || 'Bajo',
                    status: a.status || 'PENDING',
                    fields: parseFieldStatus(a, a.meli_listings, a.master_products),
                    master_product: a.master_products,
                    violation_details: a.violation_details
                }));
                setProducts(fetchedProducts);
            }

            setStats({
                scanned: listingCount || 0,
                active: 0,
                cleaned: 0,
                high_risk: highRiskCount || 0,
                medium_risk: mediumRiskCount || 0,
                low_risk: lowRiskCount || 0,
                last_audit: allAuditData?.[0]?.processed_at
            });

            await fetchEnrichmentStats();
        } catch (err) {
            console.error('Fetch error:', err);
        } finally {
            setLoading(false);
        }
    }, [fetchEnrichmentStats]);

    useEffect(() => {
        fetchData();
        // Poll enrichment status every 5s if running
        const interval = setInterval(() => {
            fetchEnrichmentStats();
        }, 5000);
        return () => clearInterval(interval);
    }, [fetchData, fetchEnrichmentStats]);

    return { products, stats, enrichmentStats, loading, fetchData, runPipeline, refreshScores };
};
