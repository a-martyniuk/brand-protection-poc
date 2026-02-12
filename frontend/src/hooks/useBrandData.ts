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
            score_impact: details.missing_ean ? 30 : 0
        },
        brand: {
            scraped: details.brand_mismatch?.found || listing?.brand_detected || 'Not detected',
            master: details.brand_mismatch?.expected || master?.brand || 'N/A',
            status: details.brand_mismatch ? 'rejected' : 'approved',
            details: details.brand_mismatch ? `Expected "${details.brand_mismatch.expected}", found "${details.brand_mismatch.found}"` : undefined,
            score_impact: details.brand_mismatch ? 20 : 0
        },
        price: {
            scraped: listing?.price ? `$${listing.price.toLocaleString('es-AR')}` : 'N/A',
            master: details.low_price?.min
                ? `$${details.low_price.min.toLocaleString('es-AR')} (min)`
                : (master?.list_price ? `$${master.list_price.toLocaleString('es-AR')}` : 'N/A'),
            status: details.low_price ? 'rejected' : 'approved',
            details: details.low_price
                ? `Price $${listing?.price} is below minimum $${details.low_price.min}`
                : undefined,
            score_impact: details.unauthorized_discount ? 60 : (details.low_price ? 20 : 0)
        },
        volume: {
            scraped: details.volumetric_mismatch?.listing_kg
                ? `${details.volumetric_mismatch.listing_kg} kg`
                : 'Not detected',
            master: details.volumetric_mismatch?.master_kg
                ? `${details.volumetric_mismatch.master_kg} kg`
                : (master?.fc_net ? `${master.fc_net} kg` : 'N/A'),
            status: details.volumetric_mismatch ? 'rejected' : 'approved',
            details: details.volumetric_mismatch
                ? `${details.volumetric_mismatch.diff_percent}% difference detected`
                : undefined,
            score_impact: details.volumetric_mismatch ? 40 : 0
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
            master: details.restricted_sku ? 'Not publishable' : 'Publishable',
            status: details.restricted_sku ? 'rejected' : 'approved',
            details: details.restricted_sku
                ? 'This SKU should not be published on marketplace'
                : undefined,
            score_impact: details.restricted_sku ? 50 : 0
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
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            // Fetch all compliance audits with joined data
            const { data: auditData, error: aError } = await supabase
                .from('compliance_audit')
                .select(`
                    *,
                    meli_listings(*),
                    master_products(*)
                `)
                .order('processed_at', { ascending: false });

            if (aError) throw aError;

            // Stats counts
            const { count: listingCount } = await supabase
                .from('meli_listings')
                .select('*', { count: 'exact', head: true });

            const { count: activeCount } = await supabase
                .from('compliance_audit')
                .select('*', { count: 'exact', head: true })
                .eq('status', 'PENDING');

            const { count: cleanedCount } = await supabase
                .from('compliance_audit')
                .select('*', { count: 'exact', head: true })
                .eq('status', 'REPORTED');

            const { count: highRiskCount } = await supabase
                .from('compliance_audit')
                .select('*', { count: 'exact', head: true })
                .eq('risk_level', 'Alto');

            const { count: mediumRiskCount } = await supabase
                .from('compliance_audit')
                .select('*', { count: 'exact', head: true })
                .eq('risk_level', 'Medio');

            const { count: lowRiskCount } = await supabase
                .from('compliance_audit')
                .select('*', { count: 'exact', head: true })
                .eq('risk_level', 'Bajo');

            if (auditData) {
                const fetchedProducts: ProductAudit[] = auditData.map((a: any) => {
                    const listing = a.meli_listings;
                    const master = a.master_products;

                    return {
                        id: a.id,
                        meli_id: listing?.meli_id || 'N/A',
                        title: listing?.title || 'Unknown Listing',
                        seller: listing?.seller_name || 'Unknown Seller',
                        seller_location: listing?.seller_location || 'N/A',
                        price: listing?.price || 0,
                        thumbnail: listing?.thumbnail,
                        url: listing?.url || '#',

                        match_level: a.match_level || 0,
                        fraud_score: a.fraud_score || 0,
                        risk_level: a.risk_level || 'Bajo',
                        status: a.status || 'PENDING',

                        fields: parseFieldStatus(a, listing, master),

                        master_product: master ? {
                            id: master.id,
                            product_name: master.product_name,
                            brand: master.brand,
                            list_price: master.list_price,
                            fc_net: master.fc_net,
                            ean: master.ean
                        } : undefined,

                        violation_details: a.violation_details
                    };
                });

                setProducts(fetchedProducts);
            }

            setStats({
                scanned: listingCount || 0,
                active: activeCount || 0,
                cleaned: cleanedCount || 0,
                high_risk: highRiskCount || 0,
                medium_risk: mediumRiskCount || 0,
                low_risk: lowRiskCount || 0
            });
        } catch (err) {
            console.error('Fetch error:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    return { products, stats, loading, fetchData };
};
