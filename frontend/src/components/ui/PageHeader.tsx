import React from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  badge?: React.ReactNode;
}

export function PageHeader({ title, description, actions, badge }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-6 sm:mb-8">
      <div className="space-y-1 min-w-0">
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          <h1 className="text-lg sm:text-xl md:text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
          {badge}
        </div>
        {description && (
          <p className="text-xs sm:text-sm text-slate-500 max-w-2xl">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">{actions}</div>}
    </div>
  );
}
