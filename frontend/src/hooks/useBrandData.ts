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
            const { data: violationsData, error: vError } = await supabase
                .from('violations')
                .select('*, products(*)')
                .order('created_at', { ascending: false });

            if (vError) throw vError;

            const { count: prodCount } = await supabase.from('products').select('*', { count: 'exact', head: true });
            const { count: violCount } = await supabase.from('violations').select('*', { count: 'exact', head: true }).eq('status', 'PENDING');
            const { count: cleanCount } = await supabase.from('violations').select('*', { count: 'exact', head: true }).eq('status', 'REPORTED');

            if (violationsData) {
                const fetchedViolations: Violation[] = violationsData.map((v: any) => ({
                    id: v.id,
                    meli_id: v.products?.meli_id || 'N/A',
                    type: v.violation_type,
                    product: v.products?.title || 'Unknown Product',
                    seller: v.products?.seller_name || 'Generic Seller',
                    seller_location: v.products?.seller_location || 'N/A',
                    is_authorized: v.products?.is_authorized || false,
                    price: v.products?.price || v.details?.actual_price || 0,
                    expected: v.details?.expected_min || v.products?.price || 0,
                    diff_pct: v.details?.diff_pct || 0,
                    found_keywords: v.details?.found_keywords || [],
                    status: v.status,
                    url: v.products?.url || '#',
                }));

                const { data: allProds } = await supabase.from('products').select('*');
                if (allProds) {
                    const cleanViolations: Violation[] = allProds
                        .filter(p => !violationsData.find(v => v.products?.id === p.id))
                        .map(p => ({
                            id: `clean-${p.id}`,
                            meli_id: p.meli_id,
                            type: 'INSPECTED',
                            product: p.title,
                            seller: p.seller_name,
                            seller_location: p.seller_location,
                            is_authorized: p.is_authorized,
                            price: p.price,
                            expected: p.price,
                            status: 'CLEAN',
                            url: p.url
                        }));
                    setViolations([...fetchedViolations, ...cleanViolations]);
                } else {
                    setViolations(fetchedViolations);
                }
            }

            setStats({
                scanned: prodCount || 0,
                active: violCount || 0,
                cleaned: cleanCount || 0
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
