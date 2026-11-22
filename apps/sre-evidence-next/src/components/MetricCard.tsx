import React from 'react';
import { StatusBadge } from './StatusBadge';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  badge?: {
    text: string;
    variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  };
  note?: string;
  isBoundary?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  subtitle,
  badge,
  note,
  isBoundary = false,
}) => {
  return (
    <div
      className={`rounded-xl border p-5 transition-all duration-200 ${
        isBoundary
          ? 'bg-amber-950/20 border-amber-600/50 shadow-sm shadow-amber-900/20'
          : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 shadow-sm'
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </h3>
        {badge && <StatusBadge status={badge.text} variant={badge.variant} />}
      </div>

      <div className="flex items-baseline gap-1.5 my-1">
        <span className="text-2xl sm:text-3xl font-bold font-mono text-slate-100">
          {value}
        </span>
        {unit && <span className="text-xs font-medium text-slate-400">{unit}</span>}
      </div>

      {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}

      {note && (
        <div
          className={`mt-3 pt-2.5 border-t text-[11px] leading-relaxed ${
            isBoundary
              ? 'border-amber-700/30 text-amber-300 font-medium'
              : 'border-slate-800 text-slate-400'
          }`}
        >
          {note}
        </div>
      )}
    </div>
  );
};
