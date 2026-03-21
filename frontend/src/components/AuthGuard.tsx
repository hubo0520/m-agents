"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

/**
 * 路由认证守卫：未登录用户自动跳转至 /login
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated && pathname !== "/login" && pathname !== "/register") {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, pathname, router]);

  // 加载中 — 显示全屏加载态
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50/50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-slate-400">加载中...</span>
        </div>
      </div>
    );
  }

  // 未登录 — 不渲染子组件
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
