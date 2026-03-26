import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../supabaseClient';
import { ProductAudit, DashboardStats, FieldStatus } from '../types';

/**
 * Parsea violation_details JSONB a una comparación estructurada a nivel de campo
 */
function parseFieldStatus(audit: any, listing: any, master: any): ProductAudit['fields'] {
    const details = audit.violation_details || {};

    return {
        ean: {
            scraped: listing?.ean_published || 'No provisto',
            master: master?.ean || 'N/A',
            status: 'approved',
            details: details.missing_ean ? 'EAN no provisto en la publicación' : undefined,
            score_impact: 0
        },
        brand: {
            scraped: details.brand_mismatch?.found || listing?.brand_detected || details.detected_brand || 'No detectada',
            master: details.brand_mismatch?.expected || master?.brand || 'N/A',
            status: 'approved',
            details: details.brand_mismatch ? `Esperado "${details.brand_mismatch.expected}", encontrado "${details.brand_mismatch.found}"` : undefined,
            score_impact: 0
        },
        price: {
            scraped: listing?.price ? `$${listing.price.toLocaleString('es-AR')}` : 'N/A',
            master: details.low_price?.min_allowed
                ? `$${details.low_price.min_allowed.toLocaleString('es-AR')} (min)`
                : (master?.list_price ? `$${master.list_price.toLocaleString('es-AR')}` : 'N/A'),
            status: 'approved',
            details: details.low_price
                ? (details.unit_price_info?.is_pack
                    ? `Precio Unitario $${details.unit_price_info.unit_price?.toLocaleString('es-AR')} (Referencia: $${details.low_price.min_allowed?.toLocaleString('es-AR')})`
                    : `Precio $${listing?.price?.toLocaleString('es-AR')} (Referencia: $${details.low_price.min_allowed?.toLocaleString('es-AR')})`)
                : (details.unit_price_info?.is_pack ? `Precio Unitario: $${details.unit_price_info.unit_price?.toLocaleString('es-AR')}` : undefined),
            score_impact: 0,
            unit_price: details.unit_price_info?.unit_price,
            qty_multiplier: details.unit_price_info?.detected_qty,
            master_unit_value: master?.list_price
        },
        volume: {
            scraped: details.volumetric_info?.detected_total_kg ?? (typeof details.volumetric_mismatch?.detected_in_listing === 'number' ? details.volumetric_mismatch.detected_in_listing : (typeof details.detected_volume === 'number' ? details.detected_volume : 0))
                ? `${details.volumetric_info?.detected_total_kg || details.volumetric_mismatch?.detected_in_listing || details.detected_volume} kg`
                : 'No detectado',
            master: (details.volumetric_info?.expected_total_kg || details.volumetric_mismatch?.expected_kg || master?.fc_net)
                ? `${details.volumetric_info?.expected_total_kg || details.volumetric_mismatch?.expected_kg || master?.fc_net} kg`
                : 'N/A',
            status: 'approved',
            details: details.volumetric_mismatch
                ? `Referencia esperada: ${details.volumetric_info?.expected_total_kg || details.volumetric_mismatch?.expected_kg || master?.fc_net}kg`
                : undefined,
            score_impact: 0,
            unit_weight: details.volumetric_info?.unit_weight,
            qty_multiplier: details.volumetric_info?.detected_qty,
            master_unit_value: master?.fc_net ? (master.fc_net < 1 ? `${master.fc_net * 1000}g` : `${master.fc_net}kg`) : 'N/A'
        },
        quantity: {
            scraped: (details.detected_qty || details.volumetric_info?.detected_qty || details.combo_mismatch?.listing)
                ? `${details.detected_qty || details.volumetric_info?.detected_qty || details.combo_mismatch.listing} unidades`
                : '1 unidad',
            master: (master?.units_per_pack || details.combo_mismatch?.master || 1)
                ? `${master?.units_per_pack || details.combo_mismatch?.master || 1} unidades`
                : '1 unidad',
            status: 'approved',
            details: details.combo_mismatch
                ? `Referencia esperada: ${details.combo_mismatch.master} unidades`
                : undefined,
            score_impact: 0
        },
        discount: {
            scraped: details.unauthorized_discount ? 'Detectado' : 'No',
            master: 'Info',
            status: 'approved',
            details: undefined,
            score_impact: 0
        },
        publishable: {
            scraped: listing?.status_publicacion || 'Activa',
            master: details.restricted_sku_violation ? 'Restringido' : 'Normal',
            status: 'approved',
            details: details.restricted_sku_violation
                ? 'Este SKU tiene restricciones de venta'
                : undefined,
            score_impact: 0
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
            console.warn('API Bridge local no alcanzable');
        }
    }, []);

    const runPipeline = async () => {
        try {
            await fetch('http://localhost:8000/pipeline/run', { method: 'POST' });
            fetchEnrichmentStats();
        } catch (err) {
            alert('Error iniciando pipeline. ¿Está corriendo api_bridge.py?');
        }
    };

    const refreshScores = async () => {
        try {
            await fetch('http://localhost:8000/audit/refresh', { method: 'POST' });
            setTimeout(fetchData, 2000); // Give it a moment to start
        } catch (err) {
            alert('Error actualizando puntajes. ¿Está corriendo api_bridge.py?');
        }
    };

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            // Obtener datos de cumplimiento con paginación (evitando límite de 1000 filas)
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

            // Conteos de estadísticas (usando count: 'exact' es más seguro y evita límites)
            const { count: listingCount } = await supabase.from('meli_listings').select('*', { count: 'exact', head: true });
            const { count: highRiskCount } = await supabase.from('compliance_audit').select('*', { count: 'exact', head: true }).eq('risk_level', 'Alto');
            const { count: mediumRiskCount } = await supabase.from('compliance_audit').select('*', { count: 'exact', head: true }).eq('risk_level', 'Medio');
            const { count: lowRiskCount } = await supabase.from('compliance_audit').select('*', { count: 'exact', head: true }).eq('risk_level', 'Bajo');

            if (allAuditData) {
                const fetchedProducts: ProductAudit[] = allAuditData.map((a: any) => ({
                    id: a.id,
                    meli_id: a.meli_listings?.meli_id || 'N/A',
                    title: a.meli_listings?.title || 'Publicación Desconocida',
                    seller: a.meli_listings?.seller_name || 'Vendedor Desconocido',
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
                    available_stock: a.meli_listings?.available_quantity,
                    search_keyword: a.meli_listings?.search_keyword || 'N/A',
                    item_status: a.meli_listings?.item_status || 'active'
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
            console.error('Error de fetch:', err);
        } finally {
            setLoading(false);
        }
    }, [fetchEnrichmentStats]);

    useEffect(() => {
        fetchData();
        // Consultar estado de enriquecimiento cada 5s si está corriendo
        const interval = setInterval(() => {
            fetchEnrichmentStats();
        }, 5000);
        return () => clearInterval(interval);
    }, [fetchData, fetchEnrichmentStats]);

    const discardProduct = async (meliId: string) => {
        try {
            // Actualizar Supabase
            const { error } = await supabase
                .from('meli_listings')
                .update({ item_status: 'noise_manual' })
                .eq('meli_id', meliId);

            if (error) throw error;

            // Actualizar estado local inmediatamente para UI responsiva
            setProducts(prev => prev.filter(p => p.meli_id !== meliId));
            
            // Refrescar estadísticas para mayor precisión
            fetchEnrichmentStats();
        } catch (err) {
            console.error('Error descartando producto:', err);
            alert('Fallo al descartar producto');
        }
    };

    const restoreProduct = async (meliId: string) => {
        try {
            // Actualizar Supabase
            const { error } = await supabase
                .from('meli_listings')
                .update({ item_status: 'active' })
                .eq('meli_id', meliId);

            if (error) throw error;

            // Refrescar datos para actualizar apropiadamente
            fetchData();
        } catch (err) {
            console.error('Error restaurando producto:', err);
            alert('Fallo al restaurar producto');
        }
    };

    return { products, stats, enrichmentStats, loading, fetchData, runPipeline, refreshScores, discardProduct, restoreProduct };
};
