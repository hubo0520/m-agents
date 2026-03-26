"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPut } from "@/lib/api-client";

// ═══════════════════════════════════════════════════════════════
// 类型定义
// ═══════════════════════════════════════════════════════════════

interface Notification {
  id: number;
  user_id: string;
  title: string;
  content: string | null;
  type: string;
  related_entity_type: string | null;
  related_entity_id: number | null;
  is_read: boolean;
  created_at: string;
}

interface NotificationListResponse {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
}

interface UnreadCountResponse {
  unread_count: number;
}

// ═══════════════════════════════════════════════════════════════
// API 封装
// ═══════════════════════════════════════════════════════════════

async function fetchUnreadCount(): Promise<number> {
  const res = await apiGet<UnreadCountResponse>("/api/notifications/unread-count");
  return res.unread_count;
}

async function fetchNotifications(page = 1, pageSize = 10): Promise<NotificationListResponse> {
  return apiGet<NotificationListResponse>(`/api/notifications?page=${page}&page_size=${pageSize}`);
}

async function markRead(id: number): Promise<void> {
  await apiPut(`/api/notifications/${id}/read`);
}

async function markAllRead(): Promise<void> {
  await apiPut("/api/notifications/read-all");
}

// ═══════════════════════════════════════════════════════════════
// 时间格式化
// ═══════════════════════════════════════════════════════════════

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} 小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return `${diffDay} 天前`;
  return date.toLocaleDateString("zh-CN");
}

// 通知类型图标
const TYPE_ICONS: Record<string, string> = {
  approval_pending: "📋",
  approval_result: "✅",
  analysis_complete: "📊",
  risk_alert: "🚨",
};

// ═══════════════════════════════════════════════════════════════
// 通知中心组件
// ═══════════════════════════════════════════════════════════════

const POLL_INTERVAL = 30000; // 30 秒轮询

export function NotificationCenter() {
  const router = useRouter();
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({});

  // 轮询未读数量
  const pollUnread = useCallback(async () => {
    try {
      const count = await fetchUnreadCount();
      setUnreadCount(count);
    } catch {
      // 静默忽略轮询错误
    }
  }, []);

  useEffect(() => {
    pollUnread();
    const timer = setInterval(pollUnread, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [pollUnread]);

  // 展开时加载通知列表
  const handleToggle = useCallback(async () => {
    if (!isOpen) {
      // 计算下拉面板位置（基于按钮位置，使用 fixed 定位避免被父容器裁剪）
      if (buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        const panelWidth = 360;
        const panelMaxHeight = 460; // 标题栏 + 列表最大高度
        const margin = 8;

        // 水平位置：优先右对齐按钮，如果超出左边界则左对齐
        let left = rect.right - panelWidth;
        if (left < margin) {
          left = rect.left;
        }
        // 如果还是超出右边界
        if (left + panelWidth > window.innerWidth - margin) {
          left = window.innerWidth - panelWidth - margin;
        }

        // 垂直位置：优先向下展开，空间不够则向上
        let top = rect.bottom + 6;
        if (top + panelMaxHeight > window.innerHeight - margin) {
          top = rect.top - panelMaxHeight - 6;
          if (top < margin) {
            top = margin;
          }
        }

        setDropdownStyle({ position: "fixed", left, top, width: panelWidth });
      }

      setIsOpen(true);
      setLoading(true);
      try {
        const res = await fetchNotifications();
        setNotifications(res.items);
      } catch {
        // 静默
      } finally {
        setLoading(false);
      }
    } else {
      setIsOpen(false);
    }
  }, [isOpen]);

  // 点击外部关闭
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClick);
    }
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen]);

  // 点击通知：标记已读 + 跳转
  const handleNotificationClick = useCallback(
    async (n: Notification) => {
      if (!n.is_read) {
        try {
          await markRead(n.id);
          setNotifications((prev) =>
            prev.map((item) => (item.id === n.id ? { ...item, is_read: true } : item))
          );
          setUnreadCount((c) => Math.max(0, c - 1));
        } catch {
          // 静默
        }
      }

      // 跳转到关联页面
      if (n.related_entity_type === "risk_case" && n.related_entity_id) {
        router.push(`/cases/${n.related_entity_id}`);
      } else if (n.related_entity_type === "review" && n.related_entity_id) {
        router.push("/approvals");
      }
      setIsOpen(false);
    },
    [router]
  );

  // 全部标记已读
  const handleMarkAllRead = useCallback(async () => {
    try {
      await markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // 静默
    }
  }, []);

  return (
    <div ref={dropdownRef} className="relative">
      {/* 通知图标按钮 */}
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className="relative p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        aria-label="通知中心"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.6}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
          />
        </svg>

        {/* 未读红点 */}
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] rounded-full bg-red-500 text-white text-[10px] font-bold px-1">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* 下拉通知列表 — 使用 fixed 定位避免被侧边栏裁剪 */}
      {isOpen && (
        <div
          style={dropdownStyle}
          className="bg-white rounded-xl border border-slate-200 shadow-xl z-[9999] overflow-hidden"
        >
          {/* 标题栏 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <span className="text-sm font-semibold text-slate-800">通知中心</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                全部标记已读
              </button>
            )}
          </div>

          {/* 通知列表 */}
          <div className="max-h-[400px] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-8 text-slate-400 text-sm">
                加载中...
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-slate-400">
                <svg className="w-10 h-10 mb-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                </svg>
                <span className="text-xs">暂无通知</span>
              </div>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleNotificationClick(n)}
                  className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors ${
                    !n.is_read ? "bg-blue-50/40" : ""
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    <span className="text-base mt-0.5 flex-shrink-0">
                      {TYPE_ICONS[n.type] || "📩"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        {!n.is_read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                        )}
                        <span className={`text-sm truncate ${!n.is_read ? "font-semibold text-slate-800" : "text-slate-600"}`}>
                          {n.title}
                        </span>
                      </div>
                      {n.content && (
                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.content}</p>
                      )}
                      <span className="text-[10px] text-slate-400 mt-1 block">
                        {timeAgo(n.created_at)}
                      </span>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
