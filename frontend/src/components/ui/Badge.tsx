import React from "react";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "muted";
type BadgeSize = "sm" | "md";

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-slate-100 text-slate-700",
  success: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/60",
  warning: "bg-amber-50 text-amber-700 ring-1 ring-amber-200/60",
  danger: "bg-red-50 text-red-700 ring-1 ring-red-200/60",
  info: "bg-blue-50 text-blue-700 ring-1 ring-blue-200/60",
  muted: "bg-slate-50 text-slate-500 ring-1 ring-slate-200/60",
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: "px-1.5 py-0.5 text-[11px]",
  md: "px-2.5 py-0.5 text-xs",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
  dot?: boolean;
}

export function Badge({ children, variant = "default", size = "md", className = "", dot }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 font-medium rounded-full whitespace-nowrap ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            variant === "success" ? "bg-emerald-500" :
            variant === "warning" ? "bg-amber-500" :
            variant === "danger" ? "bg-red-500" :
            variant === "info" ? "bg-blue-500" :
            "bg-slate-400"
          }`}
        />
      )}
      {children}
    </span>
  );
}
