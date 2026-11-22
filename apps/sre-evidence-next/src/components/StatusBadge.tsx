import React from 'react';

interface StatusBadgeProps {
  status: string;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant = 'info',
  size = 'sm',
}) => {
  const variantStyles = {
    success: 'bg-emerald-950 text-emerald-400 border-emerald-700/60',
    warning: 'bg-amber-950 text-amber-300 border-amber-700/60',
    danger: 'bg-rose-950 text-rose-400 border-rose-700/60',
    info: 'bg-blue-950 text-blue-400 border-blue-700/60',
    neutral: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-0.5',
    md: 'text-sm px-3 py-1',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border font-mono tracking-tight ${variantStyles[variant]} ${sizeStyles[size]}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-80" />
      {status}
    </span>
  );
};
