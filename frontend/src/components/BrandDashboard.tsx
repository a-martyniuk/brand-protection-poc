import React, { useState } from 'react';
import { Shield, Search, ExternalLink, TrendingUp, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useBrandData } from '../hooks/useBrandData';
import { exportToCSV } from '../utils/exportUtils';
import StatCard from './StatCard';
import ProductListView from './ProductListView';
import AnalyticsView from './AnalyticsView';

const BrandDashboard: React.FC = () => {
    const { products, stats, enrichmentStats, loading, fetchData, runPipeline, refreshScores } = useBrandData();
    const [activeTab, setActiveTab] = useState<'products' | 'analytics'>('products');

    const handleExport = () => {
        const legacyFormat = products.map(p => ({
            id: p.id,
            meli_id: p.meli_id,
            type: p.fraud_score > 60 ? 'HIGH_RISK' : p.fraud_score > 30 ? 'MEDIUM_RISK' : 'LOW_RISK',
            product: p.title,
            seller: p.seller,
            seller_location: p.seller_location,
            price: p.price,
            expected: p.master_product?.list_price || 0,
            status: p.status,
            url: p.url,
            thumbnail: p.thumbnail
        }));
        exportToCSV(legacyFormat);
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-brand-500/30">
            {/* Header */}
            <nav className="border-b border-white/10 bg-slate-900/40 backdrop-blur-xl sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 h-16 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-brand-500/20 rounded-xl flex items-center justify-center border border-brand-500/30 shadow-[0_0_15px_rgba(var(--brand-500),0.1)]">
                            <Shield className="text-brand-400 w-6 h-6" />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-lg font-bold tracking-tight text-white leading-none mb-1">Brand Intelligence</span>
                            <span className="text-[10px] text-brand-400 font-black uppercase tracking-[0.2em]">MercadoLibre Arg PoC</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* Status Info */}
                        <div className="hidden lg:flex flex-col items-end mr-4">
                            <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${enrichmentStats.isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`}></span>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                    {enrichmentStats.isRunning ? 'Scraping Active' : 'Auditoría al día'}
                                </span>
                            </div>
                            <span className="text-[9px] text-slate-500 font-medium">
                                {stats.last_audit ? `Último Audit: ${new Date(stats.last_audit).toLocaleString()}` : 'No audit data'}
                            </span>
                        </div>

                        <button
                            onClick={refreshScores}
                            className="flex items-center gap-2 px-5 py-2 rounded-full bg-brand-500 hover:bg-brand-600 text-white border border-brand-400/30 transition-all active:scale-95 shadow-[0_0_15px_rgba(var(--brand-500),0.2)]"
                        >
                            <Shield className="w-3.5 h-3.5" />
                            <span className="text-xs font-bold uppercase tracking-wider">
                                Refresh Scores
                            </span>
                        </button>

                        <button
                            onClick={handleExport}
                            className="flex items-center gap-2 bg-white/5 hover:bg-white/10 px-5 py-2 rounded-full border border-white/10 transition-all active:scale-95"
                        >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Export</span>
                        </button>

                        <button
                            onClick={fetchData}
                            disabled={loading}
                            className="group flex items-center gap-2 bg-white/5 hover:bg-white/10 px-5 py-2 rounded-full border border-white/10 transition-all active:scale-95 disabled:opacity-50"
                        >
                            <Search className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : 'text-brand-400'}`} />
                        </button>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto p-4 md:p-8 space-y-10">
                {/* Hero Section */}
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-white/5">
                    <div className="space-y-2">
                        <h1 className="text-4xl font-black tracking-tighter text-white">Estado de Situación</h1>
                        <p className="text-slate-400 max-w-2xl text-sm font-medium">
                            Monitoreo en tiempo real de políticas comerciales para <span className="text-brand-400 font-bold italic tracking-wide">Nutricia Bagó</span>.
                        </p>
                    </div>
                    <div className="flex bg-slate-900/80 border border-white/5 rounded-2xl p-1.5 backdrop-blur-md self-start md:self-end">
                        <button
                            onClick={() => setActiveTab('products')}
                            className={`px-5 py-2 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all duration-300 ${activeTab === 'products'
                                ? 'bg-brand-500 text-white shadow-[0_0_20px_rgba(var(--brand-500),0.3)]'
                                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                }`}
                        >
                            Product Audit
                        </button>
                        <button
                            onClick={() => setActiveTab('analytics')}
                            className={`px-5 py-2 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all duration-300 ${activeTab === 'analytics'
                                ? 'bg-brand-500 text-white shadow-[0_0_20px_rgba(var(--brand-500),0.3)]'
                                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                }`}
                        >
                            Analytics
                        </button>
                    </div>
                </header>

                {activeTab === 'analytics' ? (
                    <AnalyticsView violations={products.map(p => ({
                        id: p.id,
                        meli_id: p.meli_id,
                        type: p.fraud_score > 60 ? 'HIGH_RISK' : p.fraud_score > 30 ? 'MEDIUM_RISK' : 'LOW_RISK',
                        product: p.title,
                        seller: p.seller,
                        seller_location: p.seller_location,
                        price: p.price,
                        expected: p.master_product?.list_price || 0,
                        status: p.status,
                        url: p.url,
                        thumbnail: p.thumbnail
                    }))} />
                ) : (
                    <>
                        {/* Stats Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            <StatCard
                                title="Total Scanned"
                                value={stats.scanned.toLocaleString()}
                                label="Products in monitoring pool"
                                icon={<Search className="text-blue-400" />}
                            />
                            <StatCard
                                title="High Risk"
                                value={stats.high_risk.toString()}
                                label="Fraud score > 60"
                                variant="warning"
                                icon={<AlertTriangle className="text-red-400" />}
                            />
                            <StatCard
                                title="Medium Risk"
                                value={stats.medium_risk.toString()}
                                label="Fraud score 30-60"
                                icon={<TrendingUp className="text-amber-400" />}
                            />
                            <StatCard
                                title="Low Risk"
                                value={stats.low_risk.toString()}
                                label="Fraud score < 30"
                                variant="success"
                                icon={<CheckCircle2 className="text-emerald-400" />}
                            />
                        </div>

                        {/* Product List */}
                        <div className="space-y-6">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-brand-500/10 rounded-lg">
                                    <Shield className="w-5 h-5 text-brand-500" />
                                </div>
                                <h2 className="text-xl font-black text-white tracking-tight">Product Compliance Audit</h2>
                            </div>

                            <ProductListView products={products} loading={loading} />
                        </div>
                    </>
                )}
            </main>

            <footer className="max-w-7xl mx-auto px-8 py-12 border-t border-white/5 opacity-50">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                    <span>BeOn Brand Protection</span>
                    <span>&copy; {new Date().getFullYear()} PoC Dashboard</span>
                </div>
            </footer>
        </div>
    );
};

export default BrandDashboard;
