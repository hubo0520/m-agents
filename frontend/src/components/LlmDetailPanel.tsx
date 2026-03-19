"use client";

import { useState, useRef, useEffect, useCallback } from "react";

/** LLM 交互数据 */
export interface LlmStepData {
  systemPrompt?: string;
  userPrompt?: string;
  streamingContent: string;
  fullContent?: string;
  isStreaming: boolean;
  elapsedMs?: number;
}

interface LlmDetailPanelProps {
  data: LlmStepData;
  isExpanded: boolean;
}

/**
 * LLM 交互详情面板 — 展示 Prompt 输入和模型回复（含打字机效果）
 */
export default function LlmDetailPanel({ data, isExpanded }: LlmDetailPanelProps) {
  const [showFullSystemPrompt, setShowFullSystemPrompt] = useState(false);
  const [showFullUserPrompt, setShowFullUserPrompt] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部（流式输出时）
  useEffect(() => {
    if (data.isStreaming && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [data.streamingContent, data.isStreaming]);

  if (!isExpanded) return null;

  const displayContent = data.fullContent || data.streamingContent;
  const truncatePrompt = (text: string, expanded: boolean) => {
    if (!text) return "（无）";
    if (expanded || text.length <= 200) return text;
    return text.slice(0, 200) + "...";
  };

  return (
    <div className="mt-1.5 mb-2 ml-8 animate-slide-down">
      <div className="border border-slate-200/80 rounded-lg overflow-hidden bg-white/50 shadow-sm">
        {/* Prompt 输入区域 */}
        {(data.systemPrompt || data.userPrompt) && (
          <div className="border-b border-slate-100">
            <div className="px-3 py-2">
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Prompt 输入</span>
              </div>

              {/* System Prompt */}
              {data.systemPrompt && (
                <div className="mb-1.5">
                  <div className="flex items-center gap-1 mb-0.5">
                    <span className="text-[10px] text-slate-400 font-medium">System</span>
                    {data.systemPrompt.length > 200 && (
                      <button
                        className="text-[10px] text-blue-500 hover:underline"
                        onClick={() => setShowFullSystemPrompt(!showFullSystemPrompt)}
                      >
                        {showFullSystemPrompt ? "收起" : "展开"}
                      </button>
                    )}
                  </div>
                  <pre className="text-[11px] text-slate-600 bg-slate-50 rounded px-2 py-1.5 whitespace-pre-wrap break-words max-h-[120px] overflow-y-auto font-mono leading-relaxed">
                    {truncatePrompt(data.systemPrompt, showFullSystemPrompt)}
                  </pre>
                </div>
              )}

              {/* User Prompt */}
              {data.userPrompt && (
                <div>
                  <div className="flex items-center gap-1 mb-0.5">
                    <span className="text-[10px] text-slate-400 font-medium">User</span>
                    {data.userPrompt.length > 200 && (
                      <button
                        className="text-[10px] text-blue-500 hover:underline"
                        onClick={() => setShowFullUserPrompt(!showFullUserPrompt)}
                      >
                        {showFullUserPrompt ? "收起" : "展开"}
                      </button>
                    )}
                  </div>
                  <pre className="text-[11px] text-slate-600 bg-slate-50 rounded px-2 py-1.5 whitespace-pre-wrap break-words max-h-[120px] overflow-y-auto font-mono leading-relaxed">
                    {truncatePrompt(data.userPrompt, showFullUserPrompt)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 模型回复区域 */}
        {(displayContent || data.isStreaming) && (
          <div className="px-3 py-2">
            <div className="flex items-center gap-1.5 mb-1.5">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">模型回复</span>
              {data.isStreaming && (
                <span className="text-[10px] text-blue-500 animate-pulse">生成中...</span>
              )}
              {data.elapsedMs !== undefined && !data.isStreaming && (
                <span className="text-[10px] text-slate-400 ml-auto tabular-nums">
                  {data.elapsedMs >= 1000
                    ? `${(data.elapsedMs / 1000).toFixed(1)}s`
                    : `${data.elapsedMs}ms`}
                </span>
              )}
            </div>
            <div
              ref={outputRef}
              className="text-[11px] text-slate-700 bg-white rounded px-2 py-1.5 max-h-[160px] overflow-y-auto leading-relaxed whitespace-pre-wrap break-words"
            >
              {displayContent || "等待模型回复..."}
              {data.isStreaming && (
                <span className="inline-block w-1.5 h-3.5 bg-blue-500 ml-0.5 animate-blink rounded-sm" />
              )}
            </div>
          </div>
        )}

        {/* 空状态（等待 LLM 调用） */}
        {!data.systemPrompt && !data.userPrompt && !displayContent && !data.isStreaming && (
          <div className="px-3 py-2 text-center">
            <span className="text-[11px] text-slate-400">正在准备调用大模型...</span>
          </div>
        )}
      </div>
    </div>
  );
}
