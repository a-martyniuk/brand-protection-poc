import React from 'react';
import { Search, CheckCircle2, ExternalLink, MapPin, Shield } from 'lucide-react';
import { Violation } from '../types';

interface ViolationCardProps {
    data: Violation;
}

const ViolationCard: React.FC<ViolationCardProps> = ({ data }) => {
    const isClean = data.status === 'CLEAN';

    return (
        <div className={`bg-slate-900/40 border border-white/5 p-4 rounded-3xl flex flex-col gap-3 hover:bg-slate-800/60 hover:border-white/20 transition-all group relative overflow-hidden ${isClean ? 'opacity-70 grayscale-[0.5]' : ''}`}>
            <div className="flex gap-4">
                {/* Thumbnail */}
                <div className="w-16 h-16 bg-white/5 rounded-xl flex-shrink-0 overflow-hidden border border-white/5 relative group-hover:scale-105 transition-transform">
                    {data.thumbnail ? (
                        <img src={data.thumbnail} alt={data.product} className="w-full h-full object-contain p-1" />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center">
                            <Search className="text-slate-700 w-6 h-6" />
                        </div>
                    )}
                    {isClean && (
                        <div className="absolute inset-0 bg-emerald-500/10 flex items-center justify-center">
                            <CheckCircle2 className="text-emerald-500 w-4 h-4" />
                        </div>
                    )}
                </div>

                <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-black uppercase tracking-tighter ${data.status === 'PENDING' ? 'bg-amber-500/10 text-amber-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
                            {data.status}
                        </span>
                        <span className="text-[8px] text-slate-500 bg-white/5 px-1.5 py-0.5 rounded-full border border-white/5 font-mono">{data.meli_id}</span>
                    </div>
                    <a
                        href={data.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-white font-bold leading-tight line-clamp-1 hover:text-brand-400 transition-colors text-xs"
                    >
                        {data.product}
                    </a>
                    <div className="flex items-center gap-2 mt-1 min-w-0">
                        <span className="text-[9px] text-slate-500 font-medium truncate flex items-center gap-1">
                            <MapPin className="w-2 h-2" /> {data.seller_location}
                        </span>
                        <span className="text-[9px] text-slate-500 font-medium truncate">
                            • {data.seller}
                        </span>
                    </div>
                </div>

                <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <a
                        href={data.url}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 bg-white/5 rounded-full hover:bg-brand-500 transition-colors"
                    >
                        <ExternalLink className="w-3 h-3" />
                    </a>
                </div>
            </div>

            <div className="grid grid-cols-2 items-center gap-2 pt-3 border-t border-white/5">
                <div className="flex flex-col min-w-0">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-widest leading-none mb-1">Analysis</span>
                    {data.type === 'INSPECTED' ? (
                        <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-1">
                            <Shield className="w-3 h-3" /> Compliant
                        </span>
                    ) : (
                        <span className={`text-[10px] font-bold truncate ${data.type === 'PRICE' ? 'text-rose-400' : 'text-brand-400'}`}>
                            {data.type === 'PRICE' ? 'MAP Deviation' : 'Forbidden Keywords'}
                        </span>
                    )}
                </div>

                <div className="flex flex-col items-end min-w-0">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-widest leading-none mb-1">Price Matrix</span>
                    <div className="flex items-center gap-2 overflow-hidden">
                        {data.type === 'PRICE' && (
                            <div className="flex items-center gap-1 flex-shrink-0">
                                <span className="text-[9px] text-slate-600 line-through tracking-tighter">$ {data.expected.toLocaleString()}</span>
                                <span className="text-[9px] text-rose-500 font-black">-{data.diff_pct}%</span>
                            </div>
                        )}
                        <span className="text-white font-mono font-black text-sm whitespace-nowrap">$ {data.price.toLocaleString()}</span>
                    </div>
                </div>
            </div>

            {data.type === 'KEYWORD' && data.found_keywords && data.found_keywords.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1 pt-2 border-t border-white/5">
                    {data.found_keywords.slice(0, 3).map(kw => (
                        <span key={kw} className="text-[8px] bg-rose-500/10 text-rose-500 px-1 rounded border border-rose-500/10 font-bold italic">"{kw}"</span>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ViolationCard;
