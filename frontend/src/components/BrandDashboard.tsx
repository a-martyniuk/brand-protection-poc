import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle2, Search, Filter, ExternalLink } from 'lucide-react';

const BrandDashboard: React.FC = () => {
    const [violations, setViolations] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    // Mock data for PoC visualization while Supabase is being configured
    useEffect(() => {
        setTimeout(() => {
            setViolations([
                {
                    id: '1',
                    type: 'PRICE',
                    product: 'iPhone 15 128GB',
                    seller: 'ElectroWorld_BA',
                    price: 950000,
                    expected: 1100000,
                    status: 'PENDING',
                    url: 'https://articulo.mercadolibre.com.ar/MLA-123'
                },
                {
                    id: '2',
                    type: 'KEYWORD',
                    product: 'iPhone 15 Case - Símil Original',
                    seller: 'AccesoriosPremiumVIP',
                    price: 25000,
                    expected: 0,
                    status: 'REPORTED',
                    url: 'https://articulo.mercadolibre.com.ar/MLA-456'
                }
            ]);
            setLoading(false);
        }, 1000);
    }, []);

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200">
            {/* Sidebar / Nav */}
            <nav className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
                    <div className="flex items-center gap-2">
                        <Shield className="text-brand-500 w-8 h-8" />
                        <span className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                            Brand Protection Intelligence
                        </span>
                    </div>
                    <div className="flex gap-4">
                        <button className="bg-brand-600 hover:bg-brand-500 px-4 py-2 rounded-lg font-semibold transition-all">
                            Run Scraper Now
                        </button>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto p-6 space-y-8">
                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <StatCard title="Total Scanned" value="1,240" delta="+12%" icon={<Search className="text-brand-400" />} />
                    <StatCard title="Active Violations" value="86" delta="+5%" icon={<AlertTriangle className="text-warning" />} />
                    <StatCard title="Reported & Cleaned" value="412" delta="+18%" icon={<CheckCircle2 className="text-success" />} />
                </div>

                {/* Violations Table */}
                <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
                    <div className="p-6 border-b border-slate-800 flex justify-between items-center">
                        <h2 className="text-lg font-semibold">Real-time Violations Feed (MercadoLibre ARG)</h2>
                        <div className="flex gap-2">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    type="text"
                                    placeholder="Filter by seller or product..."
                                    className="bg-slate-800 border-none rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-2 focus:ring-brand-500 outline-none w-64"
                                />
                            </div>
                            <button className="bg-slate-800 p-2 rounded-lg hover:bg-slate-700">
                                <Filter className="w-5 h-5 text-slate-400" />
                            </button>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-800/50 text-slate-400 uppercase tracking-wider text-[10px] font-bold">
                                <tr>
                                    <th className="px-6 py-4">Status</th>
                                    <th className="px-6 py-4">Product</th>
                                    <th className="px-6 py-4">Seller</th>
                                    <th className="px-6 py-4">Violation</th>
                                    <th className="px-6 py-4">Details</th>
                                    <th className="px-6 py-4 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {violations.map((v) => (
                                    <tr key={v.id} className="hover:bg-slate-800/30 transition-colors">
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded-full text-[10px] font-bold ${v.status === 'PENDING' ? 'bg-warning/20 text-warning' : 'bg-success/20 text-success'
                                                }`}>
                                                {v.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 font-medium text-white">{v.product}</td>
                                        <td className="px-6 py-4 text-slate-400">{v.seller}</td>
                                        <td className="px-6 py-4">
                                            <span className={`font-semibold ${v.type === 'PRICE' ? 'text-danger' : 'text-brand-400'}`}>
                                                {v.type === 'PRICE' ? `MAP Violation` : `Keyword: "Símil"`}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-slate-400">
                                            {v.type === 'PRICE' ? (
                                                <span className="flex flex-col">
                                                    <span className="line-through text-xs font-mono">$ {v.expected.toLocaleString()}</span>
                                                    <span className="text-danger font-mono font-bold">$ {v.price.toLocaleString()}</span>
                                                </span>
                                            ) : (
                                                "Counterfeit indication in title"
                                            )}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <a
                                                href={v.url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 font-semibold"
                                            >
                                                View <ExternalLink className="w-3 h-3" />
                                            </a>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>
    );
};

const StatCard = ({ title, value, delta, icon }: any) => (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl hover:border-slate-700 transition-all group">
        <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-slate-800 rounded-xl group-hover:scale-110 transition-transform">
                {icon}
            </div>
            <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${delta.startsWith('+') ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
                }`}>
                {delta}
            </span>
        </div>
        <div className="text-slate-500 text-sm font-medium mb-1">{title}</div>
        <div className="text-3xl font-bold text-white tracking-tight">{value}</div>
    </div>
);

export default BrandDashboard;
