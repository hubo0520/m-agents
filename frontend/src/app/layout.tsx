import type { Metadata } from "next";
import "./globals.css";
import { ClientLayout } from "@/components/ClientLayout";

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
      <body className="min-h-screen bg-slate-50/50" data-no-transition>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
