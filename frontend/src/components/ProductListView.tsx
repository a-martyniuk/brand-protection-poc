import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { ProductAudit, RiskFilter, MatchFilter } from '../types';
import ProductDetailPanel from './ProductDetailPanel';

interface ProductListViewProps {
    products: ProductAudit[];
    loading: boolean;
}

const ProductListView: React.FC<ProductListViewProps> = ({ products, loading }) => {
    const [selectedProduct, setSelectedProduct] = useState<ProductAudit | null>(null);
    const [riskFilter, setRiskFilter] = useState<RiskFilter>('ALL');
    const [matchFilter, setMatchFilter] = useState<MatchFilter>('ALL');
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState<'fraud_score' | 'price' | 'match_level' | 'brand'>('fraud_score');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

    // Filtering logic
    const filteredProducts = products.filter(p => {
        if (riskFilter !== 'ALL' && p.risk_level !== riskFilter) return false;
        if (matchFilter !== 'ALL') {
            const matchLevels = { 'Unidentified': 0, 'EAN': 1, 'Fuzzy': 2, 'Suspicious': 3 };
            if (p.match_level !== matchLevels[matchFilter as keyof typeof matchLevels]) return false;
        }
        if (searchQuery && !p.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
            !p.seller.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        return true;
    });

    // Sorting logic
    const sortedProducts = [...filteredProducts].sort((a, b) => {
        let aVal: any;
        let bVal: any;

        if (sortBy === 'brand') {
            aVal = a.master_product?.brand || 'Unidentified';
            bVal = b.master_product?.brand || 'Unidentified';
        } else {
            aVal = a[sortBy as keyof ProductAudit];
            bVal = b[sortBy as keyof ProductAudit];
        }

        if (aVal === bVal) return 0;
        return sortOrder === 'asc' ? (aVal > bVal ? 1 : -1) : (aVal < bVal ? 1 : -1);
    });

    const getRiskBadge = (risk: string) => {
        const colors = {
            'Alto': 'bg-red-500/20 text-red-400 border-red-500/40',
            'Medio': 'bg-amber-500/20 text-amber-400 border-amber-500/40',
            'Bajo': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
        };
        return (
            <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${colors[risk as keyof typeof colors]}`}>
                {risk}
            </span>
        );
    };

    const getMatchBadge = (level: number) => {
        const levels = ['Unidentified', 'EAN', 'Fuzzy', 'Suspicious'];
        const colors = ['bg-slate-600/20 text-slate-400', 'bg-emerald-600/20 text-emerald-400', 'bg-blue-600/20 text-blue-400', 'bg-amber-600/20 text-amber-400'];
        return (
            <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${colors[level]}`}>
                {levels[level]}
            </span>
        );
    };

    const toggleSort = (field: 'fraud_score' | 'price' | 'match_level' | 'brand') => {
        if (sortBy === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortOrder(field === 'brand' ? 'asc' : 'desc');
        }
    };

    return (
        <div className="space-y-6">
            {/* Filters */}
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between bg-slate-900/40 border border-white/5 rounded-2xl p-4">
                <div className="flex flex-wrap gap-3">
                    <select
                        value={riskFilter}
                        onChange={(e) => setRiskFilter(e.target.value as RiskFilter)}
                        className="px-4 py-2 bg-slate-800 border border-white/10 rounded-xl text-sm font-bold text-slate-300 focus:outline-none focus:border-brand-500/50"
                    >
                        <option value="ALL">All Risks</option>
                        <option value="Alto">Alto</option>
                        <option value="Medio">Medio</option>
                        <option value="Bajo">Bajo</option>
                    </select>

                    <select
                        value={matchFilter}
                        onChange={(e) => setMatchFilter(e.target.value as MatchFilter)}
                        className="px-4 py-2 bg-slate-800 border border-white/10 rounded-xl text-sm font-bold text-slate-300 focus:outline-none focus:border-brand-500/50"
                    >
                        <option value="ALL">All Matches</option>
                        <option value="EAN">EAN Match</option>
                        <option value="Fuzzy">Fuzzy Match</option>
                        <option value="Suspicious">Suspicious</option>
                        <option value="Unidentified">Unidentified</option>
                    </select>
                </div>

                <input
                    type="text"
                    placeholder="Search by title or seller..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 md:max-w-md px-4 py-2 bg-slate-800 border border-white/10 rounded-xl text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-brand-500/50"
                />
            </div>

            {/* Results Count */}
            <div className="text-sm text-slate-400 font-medium">
                Showing <span className="text-brand-400 font-bold">{sortedProducts.length}</span> of <span className="text-white font-bold">{products.length}</span> products
            </div>

            {/* Product Table */}
            {loading ? (
                <div className="space-y-3">
                    {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className="h-24 bg-slate-900/40 rounded-2xl border border-white/5 animate-pulse" />
                    ))}
                </div>
            ) : sortedProducts.length === 0 ? (
                <div className="h-64 flex items-center justify-center bg-slate-900/20 rounded-2xl border border-dashed border-white/5">
                    <p className="text-slate-500 font-medium">No products match your filters</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {/* Table Header */}
                    <div className="hidden md:grid grid-cols-[80px_1fr_150px_200px_120px_100px_100px_120px] gap-4 px-4 py-2 text-[10px] uppercase tracking-wider font-black text-slate-500">
                        <div></div>
                        <div>Product</div>
                        <div
                            className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                            onClick={() => toggleSort('brand')}
                        >
                            Brand {sortBy === 'brand' && (sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                        </div>
                        <div>Seller</div>
                        <div
                            className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                            onClick={() => toggleSort('price')}
                        >
                            Price {sortBy === 'price' && (sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                        </div>
                        <div
                            className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                            onClick={() => toggleSort('match_level')}
                        >
                            Match {sortBy === 'match_level' && (sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                        </div>
                        <div
                            className="cursor-pointer hover:text-brand-400 transition-colors flex items-center gap-1"
                            onClick={() => toggleSort('fraud_score')}
                        >
                            Score {sortBy === 'fraud_score' && (sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                        </div>
                        <div>Risk</div>
                    </div>

                    {/* Product Rows */}
                    <div
                        key={product.id}
                        onClick={() => setSelectedProduct(product)}
                        className="grid grid-cols-1 md:grid-cols-[80px_1fr_150px_200px_120px_100px_100px_120px] gap-4 items-center p-4 bg-slate-900/40 hover:bg-slate-900/60 border border-white/5 hover:border-brand-500/30 rounded-2xl cursor-pointer transition-all group"
                    >
                        {/* Thumbnail */}
                        <div className="hidden md:block">
                            {product.thumbnail ? (
                                <img src={product.thumbnail} alt={product.title} className="w-16 h-16 rounded-xl object-cover border border-white/10" />
                            ) : (
                                <div className="w-16 h-16 rounded-xl bg-slate-800 border border-white/10" />
                            )}
                        </div>

                        {/* Title */}
                        <div className="flex flex-col">
                            <span className="text-sm font-bold text-white group-hover:text-brand-400 transition-colors line-clamp-2">{product.title}</span>
                            <span className="text-xs text-slate-500 mt-1">ID: {product.meli_id}</span>
                        </div>

                        {/* Matched Brand */}
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase font-bold text-slate-500 mb-1">Brand</span>
                            <span className={`text-sm font-bold ${product.master_product?.brand ? 'text-brand-300' : 'text-slate-600'}`}>
                                {product.master_product?.brand || 'Identificando...'}
                            </span>
                        </div>

                        {/* Seller */}
                        <div className="flex flex-col">
                            <span className="text-sm text-slate-300">{product.seller}</span>
                            <span className="text-xs text-slate-500">{product.seller_location}</span>
                        </div>

                        {/* Price */}
                        <div className="text-sm font-bold text-emerald-400">
                            ${product.price.toLocaleString('es-AR')}
                        </div>

                        {/* Match Level */}
                        <div>
                            {getMatchBadge(product.match_level)}
                        </div>

                        {/* Fraud Score */}
                        <div className="flex items-center gap-2">
                            <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                                <div
                                    className={`h-full transition-all ${product.fraud_score > 60 ? 'bg-red-500' : product.fraud_score > 30 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                    style={{ width: `${product.fraud_score}%` }}
                                />
                            </div>
                            <span className="text-xs font-bold text-slate-400">{product.fraud_score}</span>
                        </div>

                        {/* Risk Level */}
                        <div className="flex items-center justify-between">
                            {getRiskBadge(product.risk_level)}
                            <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-brand-400 transition-colors" />
                        </div>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
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
