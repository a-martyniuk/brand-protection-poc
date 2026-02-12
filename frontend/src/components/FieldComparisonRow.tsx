import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Minus } from 'lucide-react';
import { FieldStatus } from '../types';

interface FieldComparisonRowProps {
    fieldName: string;
    field: FieldStatus;
}

const FieldComparisonRow: React.FC<FieldComparisonRowProps> = ({ fieldName, field }) => {
    const getStatusIcon = () => {
        switch (field.status) {
            case 'approved':
                return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
            case 'rejected':
                return <XCircle className="w-5 h-5 text-red-500" />;
            case 'warning':
                return <AlertTriangle className="w-5 h-5 text-amber-500" />;
            case 'n/a':
            default:
                return <Minus className="w-5 h-5 text-slate-500" />;
        }
    };

    const getStatusBadge = () => {
        const baseClasses = "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider";
        switch (field.status) {
            case 'approved':
                return <span className={`${baseClasses} bg-emerald-500/10 text-emerald-400 border border-emerald-500/30`}>✓ OK</span>;
            case 'rejected':
                return <span className={`${baseClasses} bg-red-500/10 text-red-400 border border-red-500/30`}>✗ Rejected</span>;
            case 'warning':
                return <span className={`${baseClasses} bg-amber-500/10 text-amber-400 border border-amber-500/30`}>⚠ Warning</span>;
            case 'n/a':
            default:
                return <span className={`${baseClasses} bg-slate-500/10 text-slate-500 border border-slate-500/30`}>- N/A</span>;
        }
    };

    const getRowBgClass = () => {
        switch (field.status) {
            case 'rejected':
                return 'bg-red-500/5 hover:bg-red-500/10';
            case 'warning':
                return 'bg-amber-500/5 hover:bg-amber-500/10';
            case 'approved':
                return 'bg-slate-900/20 hover:bg-slate-900/40';
            default:
                return 'bg-slate-900/10 hover:bg-slate-900/20';
        }
    };

    return (
        <div className={`grid grid-cols-[140px_1fr_1fr_140px] gap-4 items-center p-4 rounded-xl border border-white/5 transition-all ${getRowBgClass()}`}>
            {/* Field Name */}
            <div className="flex items-center gap-2">
                {getStatusIcon()}
                <span className="font-bold text-sm text-slate-300">{fieldName}</span>
            </div>

            {/* Scraped Value */}
            <div className="flex flex-col">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">Scraped</span>
                <span className="text-sm text-white font-medium">{field.scraped}</span>
            </div>

            {/* Master Value */}
            <div className="flex flex-col">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-1">Master</span>
                <span className="text-sm text-brand-400 font-medium">{field.master}</span>
            </div>

            {/* Status Badge */}
            <div className="flex flex-col items-end gap-1">
                {getStatusBadge()}
                {field.score_impact && field.score_impact > 0 && (
                    <span className="text-[10px] text-red-400 font-bold">+{field.score_impact} pts</span>
                )}
            </div>

            {/* Details (if any) */}
            {field.details && (
                <div className="col-span-4 mt-2 pt-3 border-t border-white/5">
                    <p className="text-xs text-slate-400 italic">{field.details}</p>
                </div>
            )}
        </div>
    );
};

export default FieldComparisonRow;
