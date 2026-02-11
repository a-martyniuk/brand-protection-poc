import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle2, Search, ExternalLink, MapPin, CheckCircle } from 'lucide-react';
import { supabase } from '../supabaseClient';

interface Violation {
    id: string;
    meli_id?: string;
    type: 'PRICE' | 'KEYWORD' | 'UNAUTHORIZED_SELLER' | string;
    product: string;
    seller: string;
    seller_location?: string;
    is_authorized?: boolean;
    price: number;
    expected: number;
    diff_pct?: number;
    found_keywords?: string[];
    status: string;
    url: string;
}

const BrandDashboard: React.FC = () => {
    const [violations, setViolations] = useState<Violation[]>([]);
    const [stats, setStats] = useState({ scanned: 0, active: 0, cleaned: 0 });
    const [loading, setLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState<'ALL' | 'PRICE' | 'KEYWORD' | 'ALL_PRODUCTS'>('ALL');

    const exportToCSV = () => {
        const headers = ["ID MeLi", "Producto", "Vendedor", "Ubicacion", "Status", "Tipo", "Precio", "MAP", "URL"];
        const rows = violations.map((v: Violation) => [
            v.meli_id,
            v.product,
            v.seller,
            v.seller_location,
            v.status,
            v.type,
            v.price,
            v.expected,
            v.url
        ]);

        const csvContent = [
            headers.join(","),
            ...rows.map((row: (string | number | boolean | undefined)[]) =>
                row.map(cell => `"${cell ?? ''}"`).join(",")
            )
        ].join("\n");

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", `brand_protection_report_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const fetchData = async () => {
        setLoading(true);
        try {
            const { data: violationsData, error: vError } = await supabase
                .from('violations')
                .select('*, products(*)')
                .order('created_at', { ascending: false });

            if (vError) throw vError;

            const { count: prodCount } = await supabase.from('products').select('*', { count: 'exact', head: true });
            const { count: violCount } = await supabase.from('violations').select('*', { count: 'exact', head: true }).eq('status', 'PENDING');
            const { count: cleanCount } = await supabase.from('violations').select('*', { count: 'exact', head: true }).eq('status', 'REPORTED');

            if (violationsData) {
                const fetchedViolations = violationsData.map((v: any) => ({
                    id: v.id,
                    meli_id: v.products?.meli_id || 'N/A',
                    type: v.violation_type,
                    product: v.products?.title || 'Unknown Product',
                    seller: v.products?.seller_name || 'Generic Seller',
                    seller_location: v.products?.seller_location || 'N/A',
                    is_authorized: v.products?.is_authorized || false,
                    price: v.products?.price || v.details?.actual_price || 0,
                    expected: v.details?.expected_min || v.products?.price || 0,
                    diff_pct: v.details?.diff_pct || 0,
                    found_keywords: v.details?.found_keywords || [],
                    status: v.status,
                    url: v.products?.url || '#',
                }));

                // Also fetch clean products to show total worked
                const { data: allProds } = await supabase.from('products').select('*');
                if (allProds) {
                    const cleanViolations = allProds
                        .filter(p => !violationsData.find(v => v.products?.id === p.id))
                        .map(p => ({
                            id: `clean-${p.id}`,
                            meli_id: p.meli_id,
                            type: 'INSPECTED',
                            product: p.title,
                            seller: p.seller_name,
                            seller_location: p.seller_location,
                            is_authorized: p.is_authorized,
                            price: p.price,
                            expected: p.price,
                            status: 'CLEAN',
                            url: p.url
                        }));
                    setViolations([...fetchedViolations, ...cleanViolations]);
                } else {
                    setViolations(fetchedViolations);
                }
            }

            setStats({
                scanned: prodCount || 0,
                active: violCount || 0,
                cleaned: cleanCount || 0
            });
        } catch (err) {
            console.error('Fetch error:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const filteredViolations = violations.filter((v: Violation) => {
        if (activeFilter === 'ALL') return v.status !== 'CLEAN';
        if (activeFilter === 'ALL_PRODUCTS') return true;
        return v.type === activeFilter;
    });

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans">
            {/* Header */}
            <nav className="border-b border-white/10 bg-slate-900/40 backdrop-blur-xl sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 h-16 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-brand-500/20 rounded-xl flex items-center justify-center border border-brand-500/30">
                            <Shield className="text-brand-400 w-6 h-6" />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-lg font-bold tracking-tight text-white">Brand Intelligence</span>
                            <span className="text-[10px] text-brand-400 font-bold uppercase tracking-widest">MercadoLibre Arg PoC</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <button
                            onClick={exportToCSV}
                            className="flex items-center gap-2 bg-brand-500/10 hover:bg-brand-500/20 text-brand-400 px-5 py-2.5 rounded-full border border-brand-500/30 transition-all active:scale-95"
                        >
                            <ExternalLink className="w-4 h-4" />
                            <span className="text-sm font-semibold">Download Report</span>
                        </button>
                        <button
                            onClick={fetchData}
                            disabled={loading}
                            className="group relative flex items-center gap-2 bg-white/5 hover:bg-white/10 px-5 py-2.5 rounded-full border border-white/10 transition-all active:scale-95 disabled:opacity-50"
                        >
                            {loading ? <Search className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4 text-brand-400" />}
                            <span className="text-sm font-semibold">Refresh Insights</span>
                        </button>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto p-8 space-y-12">
                {/* Hero Section */}
                <section className="space-y-2">
                    <h1 className="text-4xl font-bold tracking-tight text-white">Estado de Situación</h1>
                    <p className="text-slate-400 max-w-2xl">
                        Monitoreo en tiempo real de políticas comerciales para <span className="text-brand-400 font-semibold italic">Nutricia Bagó</span>.
                    </p>
                </section>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <StatCard
                        title="Total Scanned"
                        value={stats.scanned.toLocaleString()}
                        label="Products Found"
                        icon={<Search className="text-blue-400" />}
                    />
                    <StatCard
                        title="Active Violations"
                        value={stats.active.toString()}
                        label="Needs Attention"
                        variant="warning"
                        icon={<AlertTriangle className="text-amber-400" />}
                    />
                    <StatCard
                        title="Cleaned"
                        value={stats.cleaned.toString()}
                        label="Successfully Reported"
                        variant="success"
                        icon={<CheckCircle2 className="text-emerald-400" />}
                    />
                </div>

                {/* Violations Feed */}
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <AlertTriangle className="w-5 h-5 text-amber-500" />
                            Violations Feed
                        </h2>
                        <div className="flex gap-4">
                            <div className="flex bg-slate-900 border border-white/5 rounded-lg p-1">
                                <button
                                    onClick={() => setActiveFilter('ALL')}
                                    className={`px-3 py-1.5 text-xs font-semibold rounded transition-all ${activeFilter === 'ALL' ? 'bg-brand-500 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                                >
                                    All
                                </button>
                                <button
                                    onClick={() => setActiveFilter('PRICE')}
                                    className={`px-3 py-1.5 text-xs font-semibold rounded transition-all ${activeFilter === 'PRICE' ? 'bg-brand-500 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                                >
                                    MAP Issues
                                </button>
                                <button
                                    onClick={() => setActiveFilter('KEYWORD')}
                                    className={`px-3 py-1.5 text-xs font-semibold rounded transition-all ${activeFilter === 'KEYWORD' ? 'bg-brand-500 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                                >
                                    Keywords
                                </button>
                                <button
                                    onClick={() => setActiveFilter('ALL_PRODUCTS')}
                                    className={`px-3 py-1.5 text-xs font-semibold rounded transition-all ${activeFilter === 'ALL_PRODUCTS' ? 'bg-slate-700 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                                >
                                    Total Analyzed
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="grid gap-4">
                        {loading ? (
                            <div className="h-64 flex items-center justify-center bg-slate-900/20 rounded-3xl border border-dashed border-white/5">
                                <span className="text-slate-500 animate-pulse font-medium">Loading data...</span>
                            </div>
                        ) : filteredViolations.length === 0 ? (
                            <div className="h-64 flex flex-col items-center justify-center bg-slate-900/20 rounded-3xl border border-dashed border-white/5 gap-3">
                                <CheckCircle2 className="w-10 h-10 text-emerald-500/50" />
                                <span className="text-slate-500 font-medium">No active violations detected.</span>
                            </div>
                        ) : (
                            filteredViolations.map((v: Violation) => (
                                <ViolationCard key={v.id} data={v} />
                            ))
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
};

const StatCard = ({ title, value, label, icon, variant = 'default' }: any) => {
    const borderClass = {
        default: 'border-white/5',
        warning: 'border-amber-500/20',
        success: 'border-emerald-500/20'
    }[variant as 'default' | 'warning' | 'success'];

    return (
        <div className={`bg-slate-900/40 border ${borderClass} p-8 rounded-[2rem] backdrop-blur-sm hover:border-white/10 transition-all group relative overflow-hidden`}>
            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                {React.cloneElement(icon as React.ReactElement, { size: 100 })}
            </div>
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2.5 bg-white/5 rounded-2xl group-hover:scale-110 transition-transform">
                    {icon}
                </div>
                <span className="text-slate-500 text-sm font-semibold uppercase tracking-wider">{title}</span>
            </div>
            <div className="flex flex-col">
                <span className="text-4xl font-black text-white tracking-tighter mb-1">{value}</span>
                <span className="text-xs text-slate-500 font-medium">{label}</span>
            </div>
        </div>
    );
};

const ViolationCard = ({ data }: { data: Violation }) => (
    <div className="bg-slate-900/60 border border-white/5 p-5 rounded-2xl flex items-center gap-6 hover:bg-slate-800/40 hover:border-white/10 transition-all group">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center border flex-shrink-0 ${data.type === 'PRICE' ? 'bg-rose-500/10 border-rose-500/20' : 'bg-brand-500/10 border-brand-500/20'
            }`}>
            {data.type === 'PRICE' ? <AlertTriangle className="text-rose-500 w-6 h-6" /> : <Search className="text-brand-400 w-6 h-6" />}
        </div>

        <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 text-[10px] font-bold uppercase tracking-widest">
                <span className={`px-2 py-0.5 rounded-full ${data.status === 'PENDING' ? 'bg-amber-500/10 text-amber-500' : 'bg-emerald-500/10 text-emerald-500'
                    }`}>
                    {data.status}
                </span>
                <span className="text-slate-600 bg-white/5 px-2 py-0.5 rounded-full border border-white/5">{data.meli_id}</span>
            </div>
            <div className="flex items-center gap-2 mb-1">
                <a
                    href={data.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-white font-bold truncate hover:text-brand-400 transition-colors"
                >
                    {data.product}
                </a>
            </div>
            {data.type === 'KEYWORD' && data.found_keywords && data.found_keywords.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                    <span className="text-[9px] text-slate-500 font-bold uppercase mr-1">Matches:</span>
                    {data.found_keywords.map(kw => (
                        <span key={kw} className="text-[9px] bg-rose-500/10 text-rose-500 px-1.5 rounded border border-rose-500/20 font-bold italic">
                            "{kw}"
                        </span>
                    ))}
                </div>
            )}
            <div className="flex items-center gap-4 text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {data.seller_location}</span>
                <span>Seller: {data.seller}</span>
            </div>
        </div>

        <div className="flex items-center gap-12 pr-4">
            <div className="flex flex-col items-end">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">Violation</span>
                <span className={`text-sm font-bold ${data.type === 'PRICE' ? 'text-rose-500' : 'text-brand-400'}`}>
                    {data.type === 'PRICE' ? 'Market Price below MAP' : 'Prohibited Keywords'}
                </span>
            </div>

            <div className="flex flex-col items-end w-24">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">Market Price</span>
                <div className="flex flex-col items-end">
                    {data.type === 'PRICE' && (
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] text-slate-600 line-through font-mono leading-none">$ {data.expected.toLocaleString()}</span>
                            <span className="text-[10px] bg-rose-500/10 text-rose-500 px-1 rounded font-bold">-{data.diff_pct}%</span>
                        </div>
                    )}
                    <span className="text-white font-mono font-bold leading-tight">$ {data.price.toLocaleString()}</span>
                </div>
            </div>

            <a
                href={data.url}
                target="_blank"
                rel="noreferrer"
                className="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center border border-white/5 hover:bg-brand-500 hover:border-brand-400 transition-all active:scale-90 shadow-lg"
            >
                <ExternalLink className="w-4 h-4 text-white" />
            </a>
        </div>
    </div>
);

export default BrandDashboard;
