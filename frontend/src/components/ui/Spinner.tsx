import React from "react";

type SpinnerSize = "sm" | "md" | "lg";

const sizeStyles: Record<SpinnerSize, string> = {
  sm: "h-4 w-4 border-[1.5px]",
  md: "h-6 w-6 border-2",
  lg: "h-8 w-8 border-2",
};

interface SpinnerProps {
  size?: SpinnerSize;
  className?: string;
  label?: string;
}

export function Spinner({ size = "md", className = "", label }: SpinnerProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 py-12 animate-fade-in ${className}`}>
      <div
        className={`rounded-full border-slate-200 border-t-blue-500 animate-spin ${sizeStyles[size]}`}
      />
      {label && <p className="text-xs text-slate-400">{label}</p>}
    </div>
  );
}
