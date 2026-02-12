import React, { useMemo } from 'react';
import { Violation } from '../types';
import { BarChart3, TrendingDown, AlertCircle, CheckCircle2, Users } from 'lucide-react';

interface AnalyticsViewProps {
    violations: Violation[];
}

const AnalyticsView: React.FC<AnalyticsViewProps> = ({ violations }) => {
    // 1. Calculate Statistics
    const stats = useMemo(() => {
        const total = violations.length;
        const activeViolations = violations.filter(v => v.status !== 'CLEAN');
        const cleanCount = total - activeViolations.length;
        const complianceRate = total > 0 ? (cleanCount / total) * 100 : 100;

        // Top Violators
        const sellerCounts: Record<string, number> = {};
        activeViolations.forEach(v => {
            if (v.seller) {
                sellerCounts[v.seller] = (sellerCounts[v.seller] || 0) + 1;
            }
        });

        const topSellers = Object.entries(sellerCounts)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5)
            .map(([name, count]) => ({
                name,
                count,
                percentage: (count / activeViolations.length) * 100
            }));

        // Violation Types
        const typeCounts = {
            PRICE: activeViolations.filter(v => v.type === 'PRICE').length,
            BRAND: activeViolations.filter(v => v.type === 'BRAND_MISM').length,
            RESTRICTED: activeViolations.filter(v => v.type === 'RESTRICTED').length,
            SUSPICIOUS: activeViolations.filter(v => v.type === 'SUSPICIOUS').length,
        };

        // Price Deviations
        const priceViolations = activeViolations.filter(v => v.type === 'PRICE' && v.diff_pct);
        const avgDeviation = priceViolations.length > 0
            ? priceViolations.reduce((acc, v) => acc + (v.diff_pct || 0), 0) / priceViolations.length
            : 0;

        return {
            total,
            activeCount: activeViolations.length,
            complianceRate,
            topSellers,
            typeCounts,
            avgDeviation,
        };
    }, [violations]);

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* KPI Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-900/40 border border-white/5 p-4 rounded-3xl">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                        <CheckCircle2 className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">Compliance</span>
                    </div>
                    <div className="text-3xl font-black text-white">
                        {stats.complianceRate.toFixed(1)}%
                    </div>
                </div>

                <div className="bg-slate-900/40 border border-white/5 p-4 rounded-3xl">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">Active</span>
                    </div>
                    <div className="text-3xl font-black text-rose-500">
                        {stats.activeCount}
                    </div>
                </div>

                <div className="bg-slate-900/40 border border-white/5 p-4 rounded-3xl">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                        <TrendingDown className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">Avg. Drop</span>
                    </div>
                    <div className="text-3xl font-black text-amber-500">
                        -{stats.avgDeviation.toFixed(1)}%
                    </div>
                </div>

                <div className="bg-slate-900/40 border border-white/5 p-4 rounded-3xl">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                        <Users className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">Sellers</span>
                    </div>
                    <div className="text-3xl font-black text-indigo-400">
                        {stats.topSellers.length}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Visual: Top Violators Bar Chart */}
                <div className="bg-slate-900/40 border border-white/5 p-6 rounded-3xl flex flex-col gap-6">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-black text-white flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-brand-500" />
                            Top Violators
                        </h3>
                        <span className="text-xs text-slate-500 bg-white/5 px-2 py-1 rounded-full">By Violation Count</span>
                    </div>

                    <div className="space-y-4">
                        {stats.topSellers.map((seller, index) => (
                            <div key={seller.name} className="space-y-1 group">
                                <div className="flex justify-between text-xs font-bold">
                                    <span className="text-white group-hover:text-brand-400 transition-colors">{seller.name}</span>
                                    <span className="text-slate-500">{seller.count} violations</span>
                                </div>
                                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-brand-600 to-brand-400 rounded-full transition-all duration-1000 ease-out group-hover:shadow-[0_0_10px_rgba(var(--brand-500),0.5)]"
                                        style={{ width: `${Math.max(seller.percentage, 5)}%` }} // Min width for visibility
                                    // key={`bar-${index}`} 
                                    />
                                </div>
                            </div>
                        ))}
                        {stats.topSellers.length === 0 && (
                            <div className="text-center py-10 text-slate-500 text-sm">
                                No active violators found.
                            </div>
                        )}
                    </div>
                </div>

                {/* Visual: Violation Type Distribution */}
                <div className="bg-slate-900/40 border border-white/5 p-6 rounded-3xl flex flex-col h-full">
                    <h3 className="text-lg font-black text-white mb-6">Violation Distribution</h3>

                    <div className="flex-1 flex items-center justify-center gap-8">
                        {/* Circular CSS Chart (Donut alternative) */}
                        <div className="relative w-40 h-40 rounded-full border-[12px] border-slate-800 flex items-center justify-center">
                            <div className="text-center">
                                <span className="block text-3xl font-black text-white">{stats.activeCount}</span>
                                <span className="text-[10px] uppercase tracking-widest text-slate-500">Total</span>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-3">
                            <div className="flex items-center gap-3">
                                <div className="w-3 h-3 rounded-full bg-rose-500" />
                                <div>
                                    <div className="text-white font-bold text-xs">Price</div>
                                    <div className="text-[10px] text-slate-500">{stats.typeCounts.PRICE}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-3 h-3 rounded-full bg-amber-500" />
                                <div>
                                    <div className="text-white font-bold text-xs">Brand</div>
                                    <div className="text-[10px] text-slate-500">{stats.typeCounts.BRAND}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-3 h-3 rounded-full bg-purple-500" />
                                <div>
                                    <div className="text-white font-bold text-xs">Restrict</div>
                                    <div className="text-[10px] text-slate-500">{stats.typeCounts.RESTRICTED}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-3 h-3 rounded-full bg-brand-500" />
                                <div>
                                    <div className="text-white font-bold text-xs">Fraud</div>
                                    <div className="text-[10px] text-slate-500">{stats.typeCounts.SUSPICIOUS}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="bg-gradient-to-r from-brand-900/20 to-slate-900/40 border border-brand-500/10 p-6 rounded-3xl flex items-center justify-between">
                <div>
                    <h4 className="text-brand-400 font-bold mb-1">Export Analysis</h4>
                    <p className="text-xs text-slate-400">Download the full report including historical data and seller trends.</p>
                </div>
                <button className="bg-white/5 hover:bg-white/10 text-white px-4 py-2 rounded-xl text-sm font-bold transition-colors border border-white/5">
                    Download PDF
                </button>
            </div>
        </div>
    );
};

export default AnalyticsView;
