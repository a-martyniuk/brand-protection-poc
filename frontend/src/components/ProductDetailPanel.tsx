import React from 'react';
import { X, ExternalLink, TrendingDown, AlertTriangle } from 'lucide-react';
import { ProductAudit } from '../types';
import FieldComparisonRow from './FieldComparisonRow';

interface ProductDetailPanelProps {
    product: ProductAudit;
    onClose: () => void;
}

const ProductDetailPanel: React.FC<ProductDetailPanelProps> = ({ product, onClose }) => {
    const getMatchLevelBadge = () => {
        const levels = ['No Identificado', 'Match Directo', 'Alta Similitud', 'Por Búsqueda'];
        const colors = ['bg-slate-600', 'bg-emerald-600', 'bg-blue-600', 'bg-amber-600'];
        return (
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${colors[product.match_level]} text-white`}>
                {levels[product.match_level]}
            </span>
        );
    };

    const getRiskBadge = () => {
        const colors = {
            'Alto': 'bg-red-500/20 text-red-400 border-red-500/40',
            'Medio': 'bg-amber-500/20 text-amber-400 border-amber-500/40',
            'Bajo': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
        };
        return (
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${colors[product.risk_level as keyof typeof colors]}`}>
                Riesgo {product.risk_level}
            </span>
        );
    };

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
            <div className="bg-slate-900 border border-white/10 rounded-3xl max-w-5xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
                {/* Encabezado */}
                <div className="bg-slate-950/80 border-b border-white/10 p-6 flex items-start justify-between sticky top-0 z-10">
                    <div className="flex-1 pr-4">
                        <div className="flex items-center gap-3 mb-3">
                            {product.thumbnail && (
                                <img src={product.thumbnail} alt={product.title} className="w-16 h-16 rounded-xl object-cover border border-white/10" />
                            )}
                            <div className="flex-1">
                                <h2 className="text-xl font-black text-white tracking-tight mb-1">{product.title}</h2>
                                <div className="flex items-center gap-2 text-sm text-slate-400">
                                    <span className="font-bold">Vendedor:</span>
                                    <span className="text-slate-200">{product.seller}</span>
                                    {product.is_official_store && (
                                        <span className="bg-blue-500/20 text-blue-400 text-[9px] font-black px-2 py-0.5 rounded border border-blue-500/30 uppercase tracking-tighter">
                                            Tienda Oficial
                                        </span>
                                    )}
                                    <span className="text-slate-500">• {product.seller_location}</span>
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 flex-wrap">
                            {getMatchLevelBadge()}
                            <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-slate-700/50 text-slate-300">
                                <span>Stock: {product.available_stock ?? '0'}</span>
                                {product.is_full && (
                                    <span className="ml-1 text-yellow-400 italic">FULL</span>
                                )}
                                <span className="w-1 h-1 rounded-full bg-slate-500"></span>
                                <span className={`text-[10px] ${
                                    !product.item_status || product.item_status === 'active' ? 'text-emerald-400' : 
                                    product.item_status === 'paused' ? 'text-amber-400' : 'text-red-400'
                                }`}>
                                    {product.item_status || 'active'}
                                </span>
                            </div>
                            {product.sold_quantity_str && (
                                <div className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                    {product.sold_quantity_str}
                                </div>
                            )}
                            <a
                                href={(() => {
                                    // 1. Priorizar URL original si existe y parece válida
                                    if (product.url && product.url.includes('mercadolibre.com.ar') && product.url !== '#') {
                                        return product.url;
                                    }

                                    // 2. Reconstrucción por meli_id
                                    const mlaMatch = product.url.match(/MLA-?(\d+)/);
                                    const meliId = (product.meli_id && product.meli_id !== 'N/A') ? product.meli_id.replace(/\D/g, '') : (mlaMatch ? mlaMatch[1] : null);
                                    return meliId ? `https://articulo.mercadolibre.com.ar/MLA-${meliId}` : product.url;
                                })()}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-brand-500/20 text-brand-400 border border-brand-500/30 hover:bg-brand-500/30 transition-all"
                            >
                                <ExternalLink className="w-3 h-3" />
                                Ver Publicación
                            </a>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/10 rounded-full transition-all active:scale-95"
                    >
                        <X className="w-6 h-6 text-slate-400" />
                    </button>
                </div>

                {/* Contenido */}
                <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
                    {/* Info de Producto Maestro */}
                    {product.master_product && (
                        <div className="mb-6 p-4 bg-brand-500/5 border border-brand-500/20 rounded-2xl">
                            <h3 className="text-sm font-black uppercase tracking-wider text-brand-400 mb-2">Producto Maestro Coincidente</h3>
                            <p className="text-white font-bold text-lg mb-1">{product.master_product.product_name}</p>
                            <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
                                <p className="text-slate-400 font-medium">Marca: <span className="text-brand-300">{product.master_product.brand}</span></p>
                                <p className="text-slate-400 font-medium">EAN: <span className="text-brand-300">{product.master_product.ean || 'N/A'}</span></p>
                                <p className="text-slate-400 font-medium whitespace-nowrap">Keyword de Búsqueda: <span className="text-white font-black bg-brand-500/20 px-2 py-0.5 rounded border border-brand-500/30 uppercase tracking-tighter">{product.search_keyword || 'N/A'}</span></p>
                            </div>
                        </div>
                    )}
 
                    {/* Comparación de Campos */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-3 mb-4">
                            <h3 className="text-lg font-black text-white tracking-tight">Detalles Técnicos y Comparativa</h3>
                        </div>
                        
                        <FieldComparisonRow fieldName="EAN" field={product.fields.ean} />
                        <FieldComparisonRow fieldName="Marca" field={product.fields.brand} />
                        <FieldComparisonRow fieldName="Precio" field={product.fields.price} />
                        <FieldComparisonRow fieldName="Volumen/Peso" field={product.fields.volume} />
                        <FieldComparisonRow fieldName="Cantidad" field={product.fields.quantity} />
                        <FieldComparisonRow fieldName="Publicable" field={product.fields.publishable} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProductDetailPanel;
