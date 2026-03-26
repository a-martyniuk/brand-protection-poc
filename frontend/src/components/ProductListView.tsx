import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Trash2, RotateCcw } from 'lucide-react';
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
        if (product.meli_id && product.meli_id !== 'N/A') {
            const cleanId = product.meli_id.replace(/\D/g, '');
            return `https://articulo.mercadolibre.com.ar/MLA-${cleanId}`;
        }
        const idMatch = product.url.match(/MLA-?(\d+)/);
        if (idMatch) {
            return `https://articulo.mercadolibre.com.ar/MLA-${idMatch[1]}`;
        }
        return product.url;
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

                <input
                    type="text"
                    placeholder="Buscar por producto o vendedor..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 md:max-w-md px-4 py-2 bg-slate-800 border border-white/10 rounded-xl text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-brand-500/50"
                />
            </div>

            {/* Contador de Resultados */}
            <div className="text-sm text-slate-400 font-medium">
                Mostrando <span className="text-brand-400 font-bold">{sortedProducts.length}</span> de <span className="text-white font-bold">{products.length}</span> productos
            </div>

            {/* Tabla de Productos */}
            {loading ? (
                <div className="space-y-3">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="h-24 bg-slate-900/40 rounded-2xl border border-white/5 animate-pulse" />
                    ))}
                </div>
            ) : sortedProducts.length === 0 ? (
                <div className="h-64 flex items-center justify-center bg-slate-900/20 rounded-2xl border border-dashed border-white/5">
                    <p className="text-slate-500 font-medium">No hay productos que coincidan con los filtros</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {/* Encabezado de Tabla */}
                    <div className="hidden md:grid grid-cols-[80px_1fr_120px_150px_200px_120px_100px_80px_100px] gap-4 px-4 py-2 text-[10px] uppercase tracking-wider font-black text-slate-500">
                        <div></div>
                        <div>Producto</div>
                        <div>Búsqueda</div>
                        <div
                            className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                            onClick={() => toggleSort('brand')}
                        >
                            Marca {sortBy === 'brand' && (sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                        </div>
                        <div>Vendedor</div>
                        <div
                            className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                            onClick={() => toggleSort('price')}
                        >
                            Precio {sortBy === 'price' && (sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                        </div>
                        <div
                            className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                            onClick={() => toggleSort('match_level')}
                        >
                            Coincid. {sortBy === 'match_level' && (sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                        </div>
                        <div>Stock</div>
                        <div className="flex justify-end">Acciones</div>
                    </div>

                    {/* Filas de Productos */}
                    {sortedProducts.map(product => (
                        <div
                            key={product.id}
                            onClick={() => setSelectedProduct(product)}
                            className="grid grid-cols-1 md:grid-cols-[80px_1fr_120px_150px_200px_120px_100px_80px_100px] gap-4 items-center p-4 bg-slate-900/40 hover:bg-slate-900/60 border border-white/5 hover:border-brand-500/30 rounded-2xl cursor-pointer transition-all group"
                        >
                            {/* Miniatura */}
                            <div className="hidden md:block">
                                {product.thumbnail ? (
                                    <img src={product.thumbnail} alt={product.title} className="w-16 h-16 rounded-xl object-cover border border-white/10" />
                                ) : (
                                    <div className="w-16 h-16 rounded-xl bg-slate-800 border border-white/10" />
                                )}
                            </div>

                            {/* Título */}
                            <div className="flex flex-col">
                                <span className="text-sm font-bold text-white group-hover:text-brand-400 transition-colors">{product.title}</span>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="text-xs text-slate-500">ID: {product.meli_id}</span>
                                    <a
                                        href={getResilientUrl(product)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={(e) => e.stopPropagation()}
                                        className="p-1 hover:bg-white/10 rounded transition-all text-slate-500 hover:text-brand-400"
                                        title="Abrir en MercadoLibre"
                                    >
                                        <ExternalLink className="w-3 h-3" />
                                    </a>
                                </div>
                            </div>
                            
                            {/* Palabra de Búsqueda */}
                            <div className="flex flex-col">
                                <span className="text-[10px] uppercase font-bold text-slate-500 mb-1 md:hidden">Búsqueda</span>
                                <span className="text-sm font-bold text-brand-200/80 truncate" title={product.search_keyword}>
                                    {product.search_keyword || 'N/A'}
                                </span>
                            </div>

                            {/* Marca Coincidente */}
                            <div className="flex flex-col">
                                <span className={`text-sm font-bold ${product.master_product?.brand ? 'text-brand-300' : 'text-slate-600'}`}>
                                    {product.master_product?.brand || 'Identificando...'}
                                </span>
                            </div>

                            {/* Vendedor */}
                            <div className="flex flex-col">
                                {product.seller && product.seller !== 'N/A' && product.seller !== 'Vendedor Desconocido' ? (
                                    <>
                                        <span className="text-sm text-slate-300">{product.seller}</span>
                                        {product.seller_location && product.seller_location !== 'N/A' && (
                                            <span className="text-xs text-slate-500">{product.seller_location}</span>
                                        )}
                                    </>
                                ) : (
                                    <span className="text-[10px] font-bold text-slate-600 uppercase tracking-tighter/50 italic">Sin datos</span>
                                )}
                            </div>

                            {/* Precio */}
                            <div className="text-sm font-bold text-emerald-400">
                                ${product.price.toLocaleString('es-AR')}
                            </div>

                            {/* Nivel de Coincidencia */}
                            <div>
                                {getMatchBadge(product.match_level)}
                            </div>

                            {/* Stock */}
                            <div className="flex flex-col">
                                <span className="text-[10px] uppercase font-bold text-slate-500 mb-1 md:hidden">Stock</span>
                                <div className="flex flex-col gap-0.5">
                                    <span className={`text-sm font-bold ${product.available_stock ? 'text-white' : 'text-slate-600'}`}>
                                        {product.available_stock ?? 'N/A'}
                                    </span>
                                    {getStatusBadge(product.item_status)}
                                </div>
                            </div>

                             <div className="flex items-center justify-end gap-3 px-2">
                                 <div className="flex items-center gap-2">
                                     {viewMode === 'NOISE' ? (
                                         <button
                                             onClick={(e) => {
                                                 e.stopPropagation();
                                                 if (onRestore) onRestore(product.meli_id);
                                             }}
                                             title="Restaurar a Audit"
                                             className="p-2 hover:bg-emerald-500/20 text-slate-500 hover:text-emerald-400 rounded-lg transition-colors"
                                         >
                                             <RotateCcw className="w-4 h-4" />
                                         </button>
                                     ) : (
                                         <button
                                             onClick={(e) => {
                                                 e.stopPropagation();
                                                 if (onDiscard) onDiscard(product.meli_id);
                                             }}
                                             title="Descartar (Noise)"
                                             className="p-2 hover:bg-red-500/20 text-slate-500 hover:text-red-400 rounded-lg transition-colors"
                                         >
                                             <Trash2 className="w-4 h-4" />
                                         </button>
                                     )}
                                     <ExternalLink
                                         onClick={(e) => {
                                             e.stopPropagation();
                                             window.open(getResilientUrl(product), '_blank');
                                         }}
                                         className="w-4 h-4 text-slate-500 hover:text-brand-400 transition-colors cursor-pointer"
                                     />
                                 </div>
                             </div>
                        </div>
                    ))}
                </div>
            )}

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
