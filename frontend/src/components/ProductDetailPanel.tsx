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
        const levels = ['Unidentified', 'EAN Match', 'Fuzzy Match', 'Suspicious'];
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
                {product.risk_level} Risk
            </span>
        );
    };

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
            <div className="bg-slate-900 border border-white/10 rounded-3xl max-w-5xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
                {/* Header */}
                <div className="bg-slate-950/80 border-b border-white/10 p-6 flex items-start justify-between sticky top-0 z-10">
                    <div className="flex-1 pr-4">
                        <div className="flex items-center gap-3 mb-3">
                            {product.thumbnail && (
                                <img src={product.thumbnail} alt={product.title} className="w-16 h-16 rounded-xl object-cover border border-white/10" />
                            )}
                            <div className="flex-1">
                                <h2 className="text-xl font-black text-white tracking-tight mb-1">{product.title}</h2>
                                <p className="text-sm text-slate-400">
                                    <span className="font-bold">Seller:</span> {product.seller} • {product.seller_location}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 flex-wrap">
                            {getMatchLevelBadge()}
                            {getRiskBadge()}
                            <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-slate-700/50 text-slate-300">
                                Score: {product.fraud_score}/100
                            </span>
                            <a
                                href={product.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-brand-500/20 text-brand-400 border border-brand-500/30 hover:bg-brand-500/30 transition-all"
                            >
                                <ExternalLink className="w-3 h-3" />
                                View Listing
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

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
                    {/* Master Product Info */}
                    {product.master_product && (
                        <div className="mb-6 p-4 bg-brand-500/5 border border-brand-500/20 rounded-2xl">
                            <h3 className="text-sm font-black uppercase tracking-wider text-brand-400 mb-2">Matched Master Product</h3>
                            <p className="text-white font-bold">{product.master_product.product_name}</p>
                            <p className="text-slate-400 text-sm">
                                Brand: <span className="text-brand-400 font-bold">{product.master_product.brand}</span> •
                                EAN: <span className="text-brand-400 font-bold">{product.master_product.ean}</span>
                            </p>
                        </div>
                    )}

                    {/* Field Comparison */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-2 bg-amber-500/10 rounded-lg">
                                <AlertTriangle className="w-5 h-5 text-amber-500" />
                            </div>
                            <h3 className="text-lg font-black text-white tracking-tight">Field-Level Compliance Check</h3>
                        </div>

                        <FieldComparisonRow fieldName="EAN" field={product.fields.ean} />
                        <FieldComparisonRow fieldName="Brand" field={product.fields.brand} />
                        <FieldComparisonRow fieldName="Price" field={product.fields.price} />
                        <FieldComparisonRow fieldName="Volume/Weight" field={product.fields.volume} />
                        <FieldComparisonRow fieldName="Quantity" field={product.fields.quantity} />
                        <FieldComparisonRow fieldName="Discount Policy" field={product.fields.discount} />
                        <FieldComparisonRow fieldName="Publishable" field={product.fields.publishable} />
                    </div>

                    {/* Violation Summary */}
                    {product.fraud_score > 0 && (
                        <div className="mt-6 p-4 bg-red-500/5 border border-red-500/20 rounded-2xl">
                            <div className="flex items-center gap-2 mb-3">
                                <TrendingDown className="w-5 h-5 text-red-400" />
                                <h3 className="text-sm font-black uppercase tracking-wider text-red-400">Compliance Issues Detected</h3>
                            </div>
                            <ul className="space-y-2">
                                {Object.entries(product.fields).map(([key, field]) =>
                                    field.status === 'rejected' && field.details && (
                                        <li key={key} className="text-sm text-slate-300 flex items-start gap-2">
                                            <span className="text-red-400 font-bold">•</span>
                                            <span><span className="font-bold capitalize">{key}:</span> {field.details} <span className="text-red-400 font-bold">(+{field.score_impact} pts)</span></span>
                                        </li>
                                    )
                                )}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ProductDetailPanel;
