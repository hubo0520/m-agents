import React from "react";

interface StatCardProps {
  label: string;
  value: string;
  icon?: React.ReactNode;
  trend?: { value: string; positive: boolean };
  color?: string;
  className?: string;
  onClick?: () => void;
}

export function StatCard({ label, value, icon, trend, color = "text-slate-900", className = "", onClick }: StatCardProps) {
  return (
    <div
      className={`bg-white rounded-xl border border-slate-200/80 p-4 sm:p-5 shadow-xs hover:shadow-sm transition-all duration-200 min-w-0 ${onClick ? "cursor-pointer hover:border-slate-300" : ""} ${className}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>
      <div className="flex items-baseline gap-2">
        <p className={`text-xl sm:text-2xl font-bold tracking-tight truncate ${color}`}>{value}</p>
        {trend && (
          <span className={`text-xs font-medium ${trend.positive ? "text-emerald-600" : "text-red-600"}`}>
            {trend.positive ? "↑" : "↓"} {trend.value}
          </span>
        )}
      </div>
    </div>
  );
}
