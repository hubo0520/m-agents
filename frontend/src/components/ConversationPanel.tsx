"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  createConversation,
  getConversations,
  getMessages,
  type ConversationItem,
  type ConversationMessageItem,
} from "@/lib/api";
import { chatStream } from "@/lib/sse";
import MarkdownRenderer from "@/components/MarkdownRenderer";

interface ConversationPanelProps {
  caseId: number;
  caseStatus: string;
}

// ─────────── localStorage 持久化键 ───────────
const PANEL_POS_KEY = "conv-panel-position";
const PANEL_SIZE_KEY = "conv-panel-size";
const MIN_WIDTH = 520;
const MIN_HEIGHT = 480;
const DEFAULT_WIDTH = 580;
const DEFAULT_HEIGHT = 620;
const SIDEBAR_WIDTH = 180;
const MOBILE_BREAKPOINT = 640; // sm 断点

function loadPanelSize(): { width: number; height: number } {
  try {
    const raw = localStorage.getItem(PANEL_SIZE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        width: Math.max(parsed.width || DEFAULT_WIDTH, MIN_WIDTH),
        height: Math.max(parsed.height || DEFAULT_HEIGHT, MIN_HEIGHT),
      };
    }
  } catch { /* ignore */ }
  return { width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT };
}

function savePanelSize(size: { width: number; height: number }) {
  try { localStorage.setItem(PANEL_SIZE_KEY, JSON.stringify(size)); } catch { /* ignore */ }
}

function loadPanelPosition(): { x: number; y: number } | null {
  try {
    const raw = localStorage.getItem(PANEL_POS_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
}

function savePanelPosition(pos: { x: number; y: number }) {
  try { localStorage.setItem(PANEL_POS_KEY, JSON.stringify(pos)); } catch { /* ignore */ }
}

/** 消息气泡 */
function MessageBubble({
  role,
  content,
  isStreaming,
}: {
  role: string;
  content: string;
  isStreaming?: boolean;
}) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl ${
          isUser
            ? "bg-blue-600 text-white rounded-br-md"
            : "bg-slate-100 text-slate-800 rounded-bl-md"
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{content}</p>
        ) : (
          <MarkdownRenderer content={content} />
        )}
        {isStreaming && (
          <span className="inline-flex items-center gap-1 mt-1">
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse [animation-delay:300ms]" />
          </span>
        )}
      </div>
    </div>
  );
}

export default function ConversationPanel({ caseId, caseStatus }: ConversationPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ConversationMessageItem[]>([]);
  const [inputText, setInputText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 拖拽/缩放状态
  const [panelSize, setPanelSize] = useState(loadPanelSize);
  const [panelPos, setPanelPos] = useState<{ x: number; y: number } | null>(null);
  const isDraggingRef = useRef(false);
  const isResizingRef = useRef<string | null>(null); // "left" | "top" | "top-left" | null
  const dragStartRef = useRef({ mx: 0, my: 0, px: 0, py: 0 });
  const resizeStartRef = useRef({ mx: 0, my: 0, w: 0, h: 0, px: 0, py: 0 });
  const panelRef = useRef<HTMLDivElement>(null);

  // 不允许 NEW 状态的案件创建对话
  const canChat = caseStatus !== "NEW";

  // 检测是否移动端
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // 初始化位置
  useEffect(() => {
    const saved = loadPanelPosition();
    if (saved) {
      setPanelPos(saved);
    } else {
      // 默认右下角
      setPanelPos({
        x: window.innerWidth - DEFAULT_WIDTH - 16,
        y: window.innerHeight - DEFAULT_HEIGHT - 16,
      });
    }
  }, []);

  // 加载对话列表
  const loadConversations = useCallback(async () => {
    try {
      const convs = await getConversations(caseId);
      setConversations(convs);
      if (convs.length > 0 && !activeConvId) {
        setActiveConvId(convs[0].id);
      }
    } catch (err) {
      console.error("加载对话列表失败:", err);
    }
  }, [caseId, activeConvId]);

  // 加载消息
  const loadMessages = useCallback(async () => {
    if (!activeConvId) return;
    setLoading(true);
    try {
      const msgs = await getMessages(activeConvId);
      setMessages(msgs);
    } catch (err) {
      console.error("加载消息失败:", err);
    } finally {
      setLoading(false);
    }
  }, [activeConvId]);

  useEffect(() => {
    if (isOpen) loadConversations();
  }, [isOpen, loadConversations]);

  useEffect(() => {
    if (activeConvId) loadMessages();
  }, [activeConvId, loadMessages]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // 创建新对话
  const handleNewConversation = async () => {
    try {
      const conv = await createConversation(caseId);
      setActiveConvId(conv.id);
      setMessages([]);
      await loadConversations();
    } catch (err) {
      console.error("创建对话失败:", err);
    }
  };

  // 发送消息
  const handleSend = async () => {
    if (!inputText.trim() || isStreaming || !activeConvId) return;

    const userMessage = inputText.trim();
    setInputText("");

    const tempUserMsg: ConversationMessageItem = {
      id: Date.now(),
      conversation_id: activeConvId,
      role: "user",
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    setIsStreaming(true);
    setStreamingContent("");

    const controller = chatStream(activeConvId, userMessage, {
      onChunk: (data) => {
        setStreamingContent((prev) => prev + data.content);
      },
      onDone: (data) => {
        const assistantMsg: ConversationMessageItem = {
          id: Date.now() + 1,
          conversation_id: activeConvId!,
          role: "assistant",
          content: data.content,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setStreamingContent("");
        setIsStreaming(false);
        // 完成后刷新对话列表（标题可能已更新）
        loadConversations();
      },
      onError: (data) => {
        console.error("对话错误:", data.error);
        const errorMsg: ConversationMessageItem = {
          id: Date.now() + 1,
          conversation_id: activeConvId!,
          role: "assistant",
          content: `⚠️ 对话出错: ${data.error}`,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
        setStreamingContent("");
        setIsStreaming(false);
      },
    });

    abortRef.current = controller;
  };

  // 切换对话
  const handleSwitchConversation = (convId: number) => {
    if (convId === activeConvId) return;
    setActiveConvId(convId);
    setMessages([]);
    setStreamingContent("");
  };

  // ─────────── 拖拽逻辑 ───────────
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    // 只在标题栏区域启动拖拽
    if ((e.target as HTMLElement).closest("button")) return;
    e.preventDefault();
    isDraggingRef.current = true;
    const pos = panelPos || { x: window.innerWidth - panelSize.width - 16, y: window.innerHeight - panelSize.height - 16 };
    dragStartRef.current = { mx: e.clientX, my: e.clientY, px: pos.x, py: pos.y };

    const handleDragMove = (ev: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const dx = ev.clientX - dragStartRef.current.mx;
      const dy = ev.clientY - dragStartRef.current.my;
      let newX = dragStartRef.current.px + dx;
      let newY = dragStartRef.current.py + dy;
      // 限制在视口内
      newX = Math.max(0, Math.min(newX, window.innerWidth - 100));
      newY = Math.max(0, Math.min(newY, window.innerHeight - 100));
      setPanelPos({ x: newX, y: newY });
    };

    const handleDragEnd = () => {
      isDraggingRef.current = false;
      document.removeEventListener("mousemove", handleDragMove);
      document.removeEventListener("mouseup", handleDragEnd);
      // 保存位置
      setPanelPos((prev) => {
        if (prev) savePanelPosition(prev);
        return prev;
      });
    };

    document.addEventListener("mousemove", handleDragMove);
    document.addEventListener("mouseup", handleDragEnd);
  }, [panelPos, panelSize]);

  // ─────────── 缩放逻辑 ───────────
  const handleResizeStart = useCallback((edge: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    isResizingRef.current = edge;
    const pos = panelPos || { x: window.innerWidth - panelSize.width - 16, y: window.innerHeight - panelSize.height - 16 };
    resizeStartRef.current = { mx: e.clientX, my: e.clientY, w: panelSize.width, h: panelSize.height, px: pos.x, py: pos.y };

    const handleResizeMove = (ev: MouseEvent) => {
      if (!isResizingRef.current) return;
      const dx = ev.clientX - resizeStartRef.current.mx;
      const dy = ev.clientY - resizeStartRef.current.my;
      const { w, h, px, py } = resizeStartRef.current;
      const resizeEdge = isResizingRef.current;

      let newW = w, newH = h, newX = px, newY = py;

      if (resizeEdge.includes("left")) {
        newW = Math.max(MIN_WIDTH, w - dx);
        newX = px + (w - newW);
      }
      if (resizeEdge.includes("top")) {
        newH = Math.max(MIN_HEIGHT, h - dy);
        newY = py + (h - newH);
      }

      setPanelSize({ width: newW, height: newH });
      setPanelPos({ x: newX, y: newY });
    };

    const handleResizeEnd = () => {
      isResizingRef.current = null;
      document.removeEventListener("mousemove", handleResizeMove);
      document.removeEventListener("mouseup", handleResizeEnd);
      setPanelSize((prev) => { savePanelSize(prev); return prev; });
      setPanelPos((prev) => { if (prev) savePanelPosition(prev); return prev; });
    };

    document.addEventListener("mousemove", handleResizeMove);
    document.addEventListener("mouseup", handleResizeEnd);
  }, [panelPos, panelSize]);

  // 组件卸载时取消 SSE
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // 折叠状态：显示浮动按钮
  if (!isOpen) {
    if (!canChat) return null;
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 hover:shadow-xl transition-all flex items-center justify-center text-xl"
        title="对话式分析"
      >
        💬
      </button>
    );
  }

  const pos = panelPos || { x: window.innerWidth - panelSize.width - 16, y: window.innerHeight - panelSize.height - 16 };

  // 展开状态：对话面板
  // 移动端全屏，桌面端使用拖拽窗口
  return (
    <div
      ref={panelRef}
      className={`fixed z-40 bg-white flex flex-col overflow-hidden ${
        isMobile
          ? "inset-0 rounded-none"
          : "border border-slate-200 shadow-2xl rounded-xl"
      }`}
      style={
        isMobile
          ? undefined
          : {
              left: pos.x,
              top: pos.y,
              width: panelSize.width,
              height: panelSize.height,
            }
      }
    >
      {/* 缩放手柄（仅桌面端） */}
      {!isMobile && (
        <>
          <div
            className="absolute left-0 top-0 w-1.5 h-full cursor-ew-resize hover:bg-blue-300/30 transition-colors z-10"
            onMouseDown={(e) => handleResizeStart("left", e)}
          />
          <div
            className="absolute top-0 left-0 w-full h-1.5 cursor-ns-resize hover:bg-blue-300/30 transition-colors z-10"
            onMouseDown={(e) => handleResizeStart("top", e)}
          />
          <div
            className="absolute top-0 left-0 w-3 h-3 cursor-nwse-resize z-20"
            onMouseDown={(e) => handleResizeStart("top-left", e)}
          />
        </>
      )}

      {/* 头部（桌面端可拖拽） */}
      <div
        className={`flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/80 select-none ${
          isMobile ? "" : "rounded-t-xl cursor-move"
        }`}
        onMouseDown={isMobile ? undefined : handleDragStart}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">💬</span>
          <h3 className="text-sm font-semibold text-slate-800">对话式分析</h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowSidebar((v) => !v)}
            className="text-xs px-2 py-1 text-slate-500 hover:bg-slate-100 rounded transition-colors"
            title={showSidebar ? "隐藏对话列表" : "显示对话列表"}
          >
            {showSidebar ? "◀" : "▶"}
          </button>
          <button
            onClick={handleNewConversation}
            className="text-xs px-2 py-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
            disabled={isStreaming}
          >
            + 新对话
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-100 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* 主体区域：左侧 Tab + 右侧消息 */}
      <div className="flex flex-1 min-h-0">
        {/* 左侧历史对话 Tab（移动端默认隐藏） */}
        {showSidebar && !isMobile && (
          <div
            className="border-r border-slate-100 bg-slate-50/50 flex flex-col flex-shrink-0"
            style={{ width: SIDEBAR_WIDTH }}
          >
            <div className="px-3 py-2 border-b border-slate-100">
              <span className="text-xs font-medium text-slate-500">历史对话</span>
            </div>
            <div className="flex-1 overflow-y-auto">
              {conversations.length === 0 ? (
                <div className="px-3 py-4 text-center">
                  <p className="text-xs text-slate-400">暂无对话</p>
                </div>
              ) : (
                conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => handleSwitchConversation(conv.id)}
                    className={`w-full text-left px-3 py-2.5 border-b border-slate-100/60 transition-colors ${
                      conv.id === activeConvId
                        ? "bg-blue-50 border-l-2 border-l-blue-500"
                        : "hover:bg-slate-100/80"
                    }`}
                  >
                    <p className={`text-xs font-medium truncate ${
                      conv.id === activeConvId ? "text-blue-700" : "text-slate-700"
                    }`}>
                      {conv.title || "新对话"}
                    </p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[10px] text-slate-400">
                        {conv.message_count} 条消息
                      </span>
                      {conv.updated_at && (
                        <span className="text-[10px] text-slate-300">
                          {new Date(conv.updated_at).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}
                        </span>
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        {/* 右侧：消息区 + 输入框 */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* 消息区域 */}
          <div className="flex-1 overflow-y-auto px-4 py-3">
            {!activeConvId ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <p className="text-sm text-slate-400 mb-3">还没有对话</p>
                <button
                  onClick={handleNewConversation}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                >
                  开始对话
                </button>
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center h-full">
                <span className="text-sm text-slate-400">加载中...</span>
              </div>
            ) : messages.length === 0 && !isStreaming ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <p className="text-2xl mb-2">🤖</p>
                <p className="text-sm text-slate-500">
                  你好！我是案件分析助手。
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  基于已有分析结果，你可以向我追问任何问题。
                </p>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
                ))}
                {isStreaming && streamingContent && (
                  <MessageBubble
                    role="assistant"
                    content={streamingContent}
                    isStreaming={true}
                  />
                )}
                {isStreaming && !streamingContent && (
                  <div className="flex justify-start mb-3">
                    <div className="bg-slate-100 rounded-2xl rounded-bl-md px-3.5 py-2.5">
                      <span className="text-sm text-slate-500 flex items-center gap-1.5">
                        思考中
                        <span className="inline-flex gap-0.5">
                          <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-pulse" />
                          <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-pulse [animation-delay:150ms]" />
                          <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-pulse [animation-delay:300ms]" />
                        </span>
                      </span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* 输入框 */}
          {activeConvId && (
            <div className="border-t border-slate-100 px-3 py-3">
              <div className="flex items-end gap-2">
                <textarea
                  className="flex-1 border border-slate-200 rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-300 focus:border-blue-300 max-h-[100px]"
                  rows={1}
                  placeholder="请输入你的问题..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  disabled={isStreaming}
                />
                <button
                  onClick={handleSend}
                  disabled={isStreaming || !inputText.trim()}
                  className="px-3 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                >
                  {isStreaming ? (
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
                  ) : (
                    "发送"
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
