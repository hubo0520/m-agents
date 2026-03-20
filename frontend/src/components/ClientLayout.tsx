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
  const isLoginPage = pathname === "/login";

  return (
    <AuthProvider>
      <Toaster position="top-right" richColors closeButton duration={4000} />
      {isLoginPage ? (
        // 登录页：无侧边栏，无认证守卫
        <>{children}</>
      ) : (
        // 受保护页面：带侧边栏 + 认证守卫
        <AuthGuard>
          <Sidebar />
          <main className="ml-[var(--sidebar-width)] min-h-screen">
            <div className="max-w-[1400px] mx-auto px-8 py-8">
              {children}
            </div>
          </main>
        </AuthGuard>
      )}
    </AuthProvider>
  );
}
