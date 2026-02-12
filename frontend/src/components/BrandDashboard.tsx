import React, { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle2, Search, ExternalLink } from 'lucide-react';
import { useBrandData } from '../hooks/useBrandData';
import { exportToCSV } from '../utils/exportUtils';
import { FilterType, Violation } from '../types';
import StatCard from './StatCard';
import ViolationCard from './ViolationCard';
import AnalyticsView from './AnalyticsView';

const BrandDashboard: React.FC = () => {
    const { violations, stats, loading, fetchData } = useBrandData();
    const [activeFilter, setActiveFilter] = useState<FilterType>('ALL');
    const [activeTab, setActiveTab] = useState<'feed' | 'analytics'>('feed');

    const filteredViolations = violations.filter((v: Violation) => {
        if (activeFilter === 'ALL') return v.status !== 'CLEAN';
        if (activeFilter === 'TOTAL_ANALYZED') return true;
        return v.type === activeFilter;
    });

    const handleExport = () => exportToCSV(violations);

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
                        <button
                            onClick={handleExport}
                            className="flex items-center gap-2 bg-brand-500/10 hover:bg-brand-500/20 text-brand-400 px-5 py-2 rounded-full border border-brand-500/30 transition-all hover:shadow-[0_0_20px_rgba(var(--brand-500),0.15)] active:scale-95"
                        >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span className="text-xs font-bold uppercase tracking-wider">Report</span>
                        </button>
                        <button
                            onClick={fetchData}
                            disabled={loading}
                            className="group flex items-center gap-2 bg-white/5 hover:bg-white/10 px-5 py-2 rounded-full border border-white/10 transition-all active:scale-95 disabled:opacity-50"
                        >
                            <Search className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : 'text-brand-400'}`} />
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Refresh</span>
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
                            onClick={() => setActiveTab('feed')}
                            className={`px-5 py-2 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all duration-300 ${activeTab === 'feed'
                                ? 'bg-brand-500 text-white shadow-[0_0_20px_rgba(var(--brand-500),0.3)]'
                                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                }`}
                        >
                            Live Feed
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
                    <AnalyticsView violations={violations} />
                ) : (
                    <>
                        {/* Stats Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <StatCard
                                title="Total Scanned"
                                value={stats.scanned.toLocaleString()}
                                label="Products in monitoring pool"
                                icon={<Search className="text-blue-400" />}
                            />
                            <StatCard
                                title="Active Violations"
                                value={stats.active.toString()}
                                label="Requiring immediate review"
                                variant="warning"
                                icon={<AlertTriangle className="text-amber-400" />}
                            />
                            <StatCard
                                title="Cleaned"
                                value={stats.cleaned.toString()}
                                label="Resolved & reported issues"
                                variant="success"
                                icon={<CheckCircle2 className="text-emerald-400" />}
                            />
                        </div>

                        {/* Violations Feed Area */}
                        <div className="space-y-8">
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-amber-500/10 rounded-lg">
                                        <AlertTriangle className="w-5 h-5 text-amber-500" />
                                    </div>
                                    <h2 className="text-xl font-black text-white tracking-tight">Intelligence Feed</h2>
                                </div>

                                <div className="flex bg-slate-900/80 border border-white/5 rounded-2xl p-1.5 backdrop-blur-md overflow-x-auto max-w-full">
                                    {(['ALL', 'PRICE', 'BRAND_MISM', 'RESTRICTED', 'SUSPICIOUS', 'TOTAL_ANALYZED'] as FilterType[]).map((filter) => (
                                        <button
                                            key={filter}
                                            onClick={() => setActiveFilter(filter)}
                                            className={`px-4 py-2 text-[9px] font-black uppercase tracking-widest rounded-xl transition-all duration-300 whitespace-nowrap ${activeFilter === filter
                                                ? (filter === 'TOTAL_ANALYZED' ? 'bg-slate-700 text-white shadow-lg' : 'bg-brand-500 text-white shadow-[0_0_20px_rgba(var(--brand-500),0.3)]')
                                                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                                }`}
                                        >
                                            {filter.replace('_', ' ')}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {loading ? (
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {[1, 2, 3, 4, 5, 6].map((i) => (
                                        <div key={i} className="h-48 bg-slate-900/40 rounded-3xl border border-white/5 animate-pulse" />
                                    ))}
                                </div>
                            ) : filteredViolations.length === 0 ? (
                                <div className="h-80 flex flex-col items-center justify-center bg-slate-900/20 rounded-[2.5rem] border border-dashed border-white/5 gap-4">
                                    <div className="p-4 bg-emerald-500/10 rounded-full">
                                        <CheckCircle2 className="w-12 h-12 text-emerald-500/50" />
                                    </div>
                                    <div className="text-center space-y-1">
                                        <p className="text-white font-bold text-lg">All products secure</p>
                                        <p className="text-slate-500 text-sm font-medium">No active violations found for the selected filter.</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {filteredViolations.map((v) => (
                                        <ViolationCard key={v.id} data={v} />
                                    ))}
                                </div>
                            )}
                        </div>
                    </>
                )}
            </main>

            <footer className="max-w-7xl mx-auto px-8 py-12 border-t border-white/5 opacity-50">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                    <span>BeOn Brand Protection</span>
                    <span>&copy; {new Date().getFullYear()} POc Dashboard</span>
                </div>
            </footer>
        </div>
    );
};

export default BrandDashboard;
