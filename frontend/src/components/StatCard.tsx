import React from 'react';

interface StatCardProps {
    title: string;
    value: string;
    label: string;
    icon: React.ReactNode;
    variant?: 'default' | 'warning' | 'success';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, label, icon, variant = 'default' }) => {
    const borderClass = {
        default: 'border-white/5',
        warning: 'border-amber-500/20',
        success: 'border-emerald-500/20'
    }[variant];

    return (
        <div className={`bg-slate-900/40 border ${borderClass} p-6 rounded-3xl backdrop-blur-sm hover:border-white/10 transition-all group relative overflow-hidden`}>
            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                {React.isValidElement(icon) ? React.cloneElement(icon as React.ReactElement, { size: 80 } as any) : icon}
            </div>
            <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-white/5 rounded-xl group-hover:scale-110 transition-transform">
                    {icon}
                </div>
                <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider">{title}</span>
            </div>
            <div className="flex flex-col">
                <span className="text-3xl font-black text-white tracking-tighter mb-0.5">{value}</span>
                <span className="text-[10px] text-slate-500 font-medium">{label}</span>
            </div>
        </div>
    );
};

export default StatCard;
