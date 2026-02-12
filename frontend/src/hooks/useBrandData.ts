import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../supabaseClient';
import { Violation, DashboardStats } from '../types';

export const useBrandData = () => {
    const [violations, setViolations] = useState<Violation[]>([]);
    const [stats, setStats] = useState<DashboardStats>({ scanned: 0, active: 0, cleaned: 0 });
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            // Fetch from compliance_audit joined with meli_listings
            const { data: auditData, error: aError } = await supabase
                .from('compliance_audit')
                .select('*, meli_listings(*)')
                .order('processed_at', { ascending: false });

            if (aError) throw aError;

            // Stats counts
            const { count: listingCount } = await supabase.from('meli_listings').select('*', { count: 'exact', head: true });
            const { count: activeCount } = await supabase.from('compliance_audit').select('*', { count: 'exact', head: true }).eq('status', 'PENDING');
            const { count: cleanedCount } = await supabase.from('compliance_audit').select('*', { count: 'exact', head: true }).eq('status', 'REPORTED');

            if (auditData) {
                const fetchedViolations: Violation[] = auditData.map((a: any) => {
                    const l = a.meli_listings;

                    // Determine violation type label
                    let vType = 'INSPECTED';
                    if (!a.is_publishable_ok) vType = 'RESTRICTED';
                    else if (!a.is_price_ok) vType = 'PRICE';
                    else if (!a.is_brand_correct) vType = 'BRAND_MISM';
                    else if (a.fraud_score > 60) vType = 'SUSPICIOUS';

                    return {
                        id: a.id,
                        meli_id: l?.meli_id || 'N/A',
                        type: vType,
                        product: l?.title || 'Unknown Listing',
                        seller: l?.seller_name || 'Generic Seller',
                        seller_location: l?.seller_location || 'N/A',
                        is_authorized: a.is_brand_correct, // Using brand correctness as proxy for PoC
                        price: l?.price || 0,
                        expected: a.violation_details?.low_price?.min || l?.price || 0,
                        diff_pct: a.violation_details?.low_price?.min
                            ? Math.round(((a.violation_details.low_price.min - l.price) / a.violation_details.low_price.min) * 100)
                            : 0,
                        found_keywords: a.violation_details?.brand_mismatch ? [a.violation_details.brand_mismatch.found] : [],
                        measure_mismatch: a.violation_details?.measure_mismatch || [],
                        unauthorized_discount: a.violation_details?.unauthorized_discount || false,
                        status: a.status || 'PENDING',
                        url: l?.url || '#',
                        thumbnail: l?.thumbnail
                    };
                });

                setViolations(fetchedViolations);
            }

            setStats({
                scanned: listingCount || 0,
                active: activeCount || 0,
                cleaned: cleanedCount || 0
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

    return { violations, stats, loading, fetchData };
};
