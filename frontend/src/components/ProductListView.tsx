import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Trash2, RotateCcw, Search } from 'lucide-react';
import { ProductAudit, MatchFilter } from '../types';
import ProductDetailPanel from './ProductDetailPanel';

interface ProductListViewProps {
    products: ProductAudit[];
    loading: boolean;
    onDiscard?: (meliId: string) => void;
    onRestore?: (meliId: string) => void;
    viewMode?: 'ACTIVE' | 'NOISE';
}

const ProductListView: React.FC<ProductListViewProps> = ({ products, loading, onDiscard, onRestore, viewMode = 'ACTIVE' }) => {
    const [selectedProduct, setSelectedProduct] = useState<ProductAudit | null>(null);
    const [matchFilter, setMatchFilter] = useState<MatchFilter>('ALL');
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState<'price' | 'match_level' | 'brand'>('match_level');
    const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

    // Lógica de filtrado
    const filteredProducts = products.filter(p => {
        if (matchFilter !== 'ALL') {
            const matchLevels = { 'Unidentified': 0, 'EAN': 1, 'Fuzzy': 2, 'Suspicious': 3 };
            if (p.match_level !== matchLevels[matchFilter as keyof typeof matchLevels]) return false;
        }
        if (searchQuery && !p.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
            !p.seller.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        return true;
    });

    // Lógica de ordenamiento
    const sortedProducts = [...filteredProducts].sort((a, b) => {
        let aVal: any;
        let bVal: any;

        if (sortBy === 'brand') {
            aVal = a.master_product?.brand || 'Unidentified';
            bVal = b.master_product?.brand || 'Unidentified';
        } else {
            // @ts-ignore
            aVal = a[sortBy];
            // @ts-ignore
            bVal = b[sortBy];
        }

        if (aVal === bVal) return 0;
        return sortOrder === 'asc' ? (aVal > bVal ? 1 : -1) : (aVal < bVal ? 1 : -1);
    });

    const getMatchBadge = (level: number) => {
        const levels = ['No Ident.', 'Directo', 'Alta Similitud', 'Por Búsqueda'];
        const colors = ['bg-slate-600/20 text-slate-400', 'bg-emerald-600/20 text-emerald-400', 'bg-blue-600/20 text-blue-400', 'bg-amber-600/20 text-amber-400'];
        return (
            <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${colors[level]}`}>
                {levels[level]}
            </span>
        );
    };

    const getResilientUrl = (product: ProductAudit) => {
        if (product.url && product.url.includes('mercadolibre.com.ar') && product.url !== '#') {
            return product.url;
        }
        if (product.meli_id && product.meli_id !== 'N/A') {
            const cleanId = product.meli_id.replace(/\D/g, '');
            return `https://articulo.mercadolibre.com.ar/MLA-${cleanId}`;
        }
        return product.url || '#';
    };

    const getStatusBadge = (status?: string) => {
        if (!status || status === 'active') return <span className="text-[10px] text-emerald-500 font-bold uppercase tracking-tighter">● Activo</span>;
        if (status === 'paused') return <span className="text-[10px] text-amber-500 font-bold uppercase tracking-tighter">● Pausado</span>;
        if (status === 'closed') return <span className="text-[10px] text-red-500 font-bold uppercase tracking-tighter">● Cerrado</span>;
        return <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter">● {status}</span>;
    };

    const toggleSort = (field: 'price' | 'match_level' | 'brand') => {
        if (sortBy === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortOrder(field === 'brand' ? 'asc' : 'desc');
        }
    };

    return (
        <div className="space-y-6">
            {/* Filtros */}
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between bg-slate-900/40 border border-white/5 rounded-2xl p-4">
                <div className="flex flex-wrap gap-3">
                    <select
                        value={matchFilter}
                        onChange={(e) => setMatchFilter(e.target.value as MatchFilter)}
                        className="px-4 py-2 bg-slate-800 border border-white/10 rounded-xl text-sm font-bold text-slate-300 focus:outline-none focus:border-brand-500/50"
                    >
                        <option value="ALL">Todas las Coincid.</option>
                        <option value="EAN">Match Directo</option>
                        <option value="Fuzzy">Alta Similitud</option>
                        <option value="Suspicious">Por Búsqueda</option>
                        <option value="Unidentified">No Identificado</option>
                    </select>
                </div>

                <div className="flex-1 md:max-w-md relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Filtrar por título o vendedor..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-white/10 rounded-xl text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-brand-500/50"
                    />
                </div>
            </div>

            {/* Tabla de Productos */}
            <div className="bg-slate-900/20 rounded-3xl border border-white/5 overflow-hidden">
                {/* Encabezado */}
                <div className="hidden md:grid grid-cols-[80px_2.5fr_1fr_1.2fr_1fr_80px] gap-6 px-6 py-4 bg-slate-900/40 border-b border-white/5 text-[10px] uppercase font-black tracking-widest text-slate-500">
                    <div></div>
                    <div>Producto / Referencia</div>
                    <div 
                        className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                        onClick={() => toggleSort('brand')}
                    >
                        Identificación {sortBy === 'brand' && (sortOrder === 'asc' ? <ChevronUp className="w-3" /> : <ChevronDown className="w-3" />)}
                    </div>
                    <div 
                        className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                        onClick={() => toggleSort('price')}
                    >
                        Comercial {sortBy === 'price' && (sortOrder === 'asc' ? <ChevronUp className="w-3" /> : <ChevronDown className="w-3" />)}
                    </div>
                    <div 
                        className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1 text-center justify-center"
                        onClick={() => toggleSort('match_level')}
                    >
                        Coincidencia {sortBy === 'match_level' && (sortOrder === 'asc' ? <ChevronUp className="w-3" /> : <ChevronDown className="w-3" />)}
                    </div>
                    <div className="text-right pr-2">Link</div>
                </div>

                {loading ? (
                    <div className="p-6 space-y-4">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-24 bg-white/5 rounded-2xl animate-pulse" />
                        ))}
                    </div>
                ) : sortedProducts.length === 0 ? (
                    <div className="p-20 text-center flex flex-col items-center gap-4">
                        <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center">
                            <Search className="w-8 h-8 text-slate-600" />
                        </div>
                        <p className="text-slate-500 font-medium">No se encontraron productos con estos filtros</p>
                    </div>
                ) : (
                    <div className="divide-y divide-white/5">
                        {sortedProducts.map(product => (
                            <div
                                key={product.id}
                                onClick={() => setSelectedProduct(product)}
                                className="grid grid-cols-1 md:grid-cols-[80px_2.5fr_1fr_1.2fr_1fr_80px] gap-6 items-center p-6 hover:bg-brand-500/[0.03] transition-all cursor-pointer group"
                            >
                                {/* Miniatura */}
                                <div className="hidden md:block">
                                    <div className="relative w-16 h-16 rounded-2xl overflow-hidden border border-white/10 bg-slate-800">
                                        {product.thumbnail ? (
                                            <img src={product.thumbnail} alt={product.title} className="w-full h-full object-cover" />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center"><Search className="text-slate-600 w-6 h-6" /></div>
                                        )}
                                    </div>
                                </div>

                                {/* Producto & Keyword */}
                                <div className="flex flex-col gap-2">
                                    <span className="text-sm font-bold text-white group-hover:text-brand-400 transition-colors leading-snug">
                                        {product.title}
                                    </span>
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="text-[9px] bg-brand-500/10 text-brand-400 px-2 py-0.5 rounded-md font-black uppercase tracking-tighter border border-brand-500/20">
                                            KW: {product.search_keyword}
                                        </span>
                                        <span className="text-[9px] text-slate-500 font-bold uppercase">ID: {product.meli_id}</span>
                                    </div>
                                </div>

                                {/* Marca & Vendedor */}
                                <div className="flex flex-col gap-1">
                                    <span className={`text-sm font-black ${product.master_product?.brand ? 'text-brand-400' : 'text-slate-600 italic'}`}>
                                        {product.master_product?.brand || 'Sin Marca'}
                                    </span>
                                    <div className="flex flex-col">
                                        {product.seller && product.seller !== 'N/A' ? (
                                            <>
                                                <span className="text-xs text-slate-300 font-medium truncate max-w-[150px]">{product.seller}</span>
                                                <span className="text-[10px] text-slate-500">{product.seller_location !== 'N/A' ? product.seller_location : ''}</span>
                                            </>
                                        ) : <span className="text-[10px] text-slate-600 italic font-bold">Sin datos de vendedor</span>}
                                    </div>
                                </div>

                                {/* Precio & Stock */}
                                <div className="flex flex-col gap-1">
                                    <span className="text-lg font-black text-emerald-400 tracking-tighter">
                                        ${product.price.toLocaleString('es-AR')}
                                    </span>
                                    <div className="flex flex-col gap-0.5">
                                        <div className="text-[10px] text-slate-400 font-bold uppercase flex items-center gap-1">
                                            Stock: <span className="text-white">{product.available_stock ?? '0'}</span>
                                        </div>
                                        {getStatusBadge(product.item_status)}
                                    </div>
                                </div>

                                {/* Match Level */}
                                <div className="flex justify-center">
                                    {getMatchBadge(product.match_level)}
                                </div>

                                {/* Acciones */}
                                <div className="flex items-center justify-end gap-2 pr-2">
                                    {viewMode === 'NOISE' ? (
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onRestore?.(product.meli_id); }}
                                            className="p-2 hover:bg-emerald-500/20 text-slate-500 hover:text-emerald-400 rounded-xl transition-colors"
                                            title="Restaurar"
                                        >
                                            <RotateCcw className="w-5 h-5" />
                                        </button>
                                    ) : (
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onDiscard?.(product.meli_id); }}
                                            className="p-2 hover:bg-red-500/20 text-slate-500 hover:text-red-400 rounded-xl transition-colors"
                                            title="Descartar"
                                        >
                                            <Trash2 className="w-5 h-5" />
                                        </button>
                                    )}
                                    <a
                                        href={getResilientUrl(product)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={(e) => e.stopPropagation()}
                                        className="p-2 hover:bg-brand-500/20 text-slate-500 hover:text-brand-400 rounded-xl transition-colors"
                                    >
                                        <ExternalLink className="w-5 h-5" />
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Modal de Detalles */}
            {selectedProduct && (
                <ProductDetailPanel
                    product={selectedProduct}
                    onClose={() => setSelectedProduct(null)}
                />
            )}
        </div>
    );
};

export default ProductListView;
