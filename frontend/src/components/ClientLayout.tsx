"use client";

import { usePathname } from "next/navigation";
import { AuthProvider } from "@/lib/auth";
import { AuthGuard } from "@/components/AuthGuard";
import { Sidebar } from "@/components/ui/Sidebar";
import { Toaster } from "sonner";

/**
 * 客户端布局组件：
 * - 包裹 AuthProvider 管理全局登录态
 * - /login 页面不显示 Sidebar，不需要认证
 * - 其他页面由 AuthGuard 保护，显示 Sidebar
 */
export function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login" || pathname === "/register";

  return (
    <AuthProvider>
      <Toaster position="top-right" richColors closeButton duration={4000} />
      {isAuthPage ? (
        // 登录/注册页：无侧边栏，无认证守卫
        <>{children}</>
      ) : (
        // 受保护页面：带侧边栏 + 认证守卫
        <AuthGuard>
          <Sidebar />
          <main className="md:ml-[var(--sidebar-width)] min-h-screen pt-14 md:pt-0">
            <div className="max-w-[1400px] mx-auto px-3 py-4 sm:px-4 sm:py-6 md:px-8 md:py-8">
              {children}
            </div>
          </main>
        </AuthGuard>
      )}
    </AuthProvider>
  );
}
