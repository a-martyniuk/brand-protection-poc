import React, { useState } from 'react';
import { Search, ExternalLink, Activity, Database, CheckCircle2 } from 'lucide-react';
import { useBrandData } from '../hooks/useBrandData';
import { exportToCSV } from '../utils/exportUtils';
import StatCard from './StatCard';
import ProductListView from './ProductListView';

const BrandDashboard: React.FC = () => {
    const { products, stats, loading, fetchData, discardProduct, restoreProduct } = useBrandData();
    const [activeTab, setActiveTab] = useState<'products' | 'noise'>('products');

    const handleExport = () => {
        const cleanFormat = products.map(p => ({
            id: p.id,
            meli_id: p.meli_id,
            status_identificacion: p.match_level > 0 ? 'IDENTIFICADO' : 'SIN_IDENTIFICAR',
            product: p.title,
            keyword_busqueda: p.search_keyword,
            marca: p.master_product?.brand || 'N/A',
            vendedor: p.seller,
            ubicacion: p.seller_location,
            precio: p.price,
            stock: p.available_stock,
            url: p.url
        }));
        exportToCSV(cleanFormat);
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-brand-500/30">
            {/* Encabezado */}
            <nav className="border-b border-white/5 bg-slate-900/20 backdrop-blur-xl sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 h-16 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-brand-500/10 rounded-xl flex items-center justify-center border border-brand-500/20">
                            <Activity className="text-brand-400 w-5 h-5" />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-lg font-bold tracking-tight text-white leading-none mb-1">Brand Intelligence</span>
                            <span className="text-[10px] text-brand-400 font-black uppercase tracking-[0.2em]">MercadoLibre Arg PoC</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <button
                            onClick={handleExport}
                            className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 px-5 py-2 rounded-full text-white border border-brand-400/30 transition-all active:scale-95 shadow-[0_0_15px_rgba(var(--brand-500),0.2)]"
                        >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span className="text-xs font-bold uppercase tracking-wider">Exportar</span>
                        </button>

                        <button
                            onClick={fetchData}
                            disabled={loading}
                            title="Refrescar Listado"
                            className="p-2 hover:bg-white/5 rounded-full text-slate-400 hover:text-brand-400 transition-all active:scale-95 disabled:opacity-50"
                        >
                            <Search className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto p-4 md:p-8 space-y-10">
                {/* Sección Principal */}
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-white/5">
                    <div className="space-y-2">
                        <div className="flex items-center gap-2 mb-1">
                             <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                             <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">En Tiempo Real · {stats.last_audit ? new Date(stats.last_audit).toLocaleDateString() : ''}</span>
                        </div>
                        <h1 className="text-4xl font-black tracking-tighter text-white">Estado de Situación</h1>
                        <p className="text-slate-400 max-w-2xl text-sm font-medium">
                            Monitoreo de publicaciones asociado a <span className="text-brand-400 font-bold italic tracking-wide">Nutricia Bagó</span>.
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
                            Productos
                        </button>
                        <button
                            onClick={() => setActiveTab('noise')}
                            className={`px-5 py-2 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all duration-300 ${activeTab === 'noise'
                                ? 'bg-slate-700 text-white'
                                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                }`}
                        >
                            Ruido
                        </button>
                    </div>
                </header>

                {/* Cuadrícula de Estadísticas */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <StatCard
                        title="Total Escaneado"
                        value={stats.scanned.toLocaleString()}
                        label="Registros procesados"
                        icon={<Database className="text-blue-400" />}
                    />
                    <StatCard
                        title="Identificados"
                        value={stats.active.toString()}
                        label="Coincidencias de búsqueda"
                        variant="success"
                        icon={<CheckCircle2 className="text-emerald-400" />}
                    />
                    <StatCard
                        title="Sin Identificar"
                        value={stats.cleaned.toString()}
                        label="Pendientes de vinculación"
                        icon={<Search className="text-slate-400" />}
                    />
                    <StatCard
                        title="Filtrados (Ruido)"
                        value={stats.low_risk.toString()}
                        label="Marcados como ruido manualmente"
                        icon={<Search className="text-amber-400" />}
                    />
                </div>

                {/* Lista de Productos */}
                <div className="space-y-6">
                    <ProductListView 
                        products={
                            activeTab === 'noise' 
                                ? products.filter(p => p.item_status === 'noise' || p.item_status === 'noise_manual')
                                : products.filter(p => p.item_status !== 'noise' && p.item_status !== 'noise_manual')
                        } 
                        loading={loading} 
                        onDiscard={discardProduct}
                        onRestore={restoreProduct}
                        viewMode={activeTab === 'noise' ? 'NOISE' : 'ACTIVE'}
                    />
                </div>
            </main>

            <footer className="max-w-7xl mx-auto px-8 py-12 border-t border-white/5 opacity-50">
                <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                    <span>BeOn Brand Intelligence</span>
                    <span>&copy; {new Date().getFullYear()} Proof of Concept</span>
                </div>
            </footer>
        </div>
    );
};

export default BrandDashboard;
