import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "商家经营保障 Agent V3",
  description: "面向内部运营人员的多 Agent 风控执行系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh">
      <body className="min-h-screen bg-slate-50">
        <header className="bg-white border-b border-slate-200 px-6 py-3">
          <div className="flex items-center justify-between max-w-[1600px] mx-auto">
            <div className="flex items-center gap-6">
              <h1 className="text-lg font-bold text-slate-800">
                🛡️ 商家经营保障 Agent
              </h1>
              <nav className="flex items-center gap-4 text-sm">
                <a href="/" className="text-slate-600 hover:text-blue-600 transition-colors">
                  🎯 风险指挥台
                </a>
                <a href="/approvals" className="text-slate-600 hover:text-blue-600 transition-colors">
                  ✅ 审批中心
                </a>
                <a href="/workflows" className="text-slate-600 hover:text-blue-600 transition-colors">
                  ⚡ 工作流
                </a>
                <a href="/tasks" className="text-slate-600 hover:text-blue-600 transition-colors">
                  📋 任务管理
                </a>
                <a href="/settings" className="text-slate-600 hover:text-blue-600 transition-colors">
                  ⚙️ 设置
                </a>
                <a href="/evals" className="text-slate-600 hover:text-blue-600 transition-colors">
                  📊 评测
                </a>
              </nav>
            </div>
            <span className="text-sm text-slate-500">V3</span>
          </div>
        </header>
        <main className="max-w-[1600px] mx-auto px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
