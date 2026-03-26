"use client";

import { useEffect, useState, useCallback } from "react";

/**
 * 全局限流状态 Banner
 * 监听 api-client 派发的 rate-limit-triggered 事件，
 * 在页面顶部展示黄色警告 Banner 及倒计时。
 */
export function RateLimitBanner() {
  const [retryAfter, setRetryAfter] = useState(0);
  const [visible, setVisible] = useState(false);

  // 监听限流事件
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      const seconds = Math.max(detail?.retryAfter || 5, 1);
      setRetryAfter(seconds);
      setVisible(true);
    };

    window.addEventListener("rate-limit-triggered", handler);
    return () => window.removeEventListener("rate-limit-triggered", handler);
  }, []);

  // 倒计时
  useEffect(() => {
    if (!visible || retryAfter <= 0) return;

    const timer = setInterval(() => {
      setRetryAfter((prev) => {
        if (prev <= 1) {
          setVisible(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [visible, retryAfter]);

  if (!visible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] bg-amber-50 border-b border-amber-200 px-4 py-2.5 flex items-center justify-center gap-2 text-sm text-amber-800 shadow-sm animate-fade-in">
      <span className="text-base">⚠️</span>
      <span>
        系统繁忙，请求频率受限
        {retryAfter > 0 && (
          <span className="font-medium">，{retryAfter} 秒后自动恢复</span>
        )}
      </span>
    </div>
  );
}
