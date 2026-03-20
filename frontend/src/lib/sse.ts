/**
 * SSE 流式分析连接辅助函数
 *
 * 使用 fetch + ReadableStream 建立 SSE 连接（因为是 POST 请求，不能用原生 EventSource）
 */
import { getAccessToken, tryRefreshToken, clearTokens } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/** 分析进度事件 */
export interface AnalysisProgressEvent {
  step: string;
  step_name: string;
  step_index: number;
  total_steps: number;
  status: "running" | "completed" | "error";
  elapsed_ms: number;
  summary: string;
  llm_input_summary?: string;
  llm_output_summary?: string;
}

/** LLM 输入事件 */
export interface LlmInputEvent {
  event_type: "llm_input";
  agent_name: string;
  step: string;
  system_prompt: string;
  user_prompt: string;
}

/** LLM Chunk 事件 */
export interface LlmChunkEvent {
  event_type: "llm_chunk";
  agent_name: string;
  step: string;
  content: string;
}

/** LLM 完成事件 */
export interface LlmDoneEvent {
  event_type: "llm_done";
  agent_name: string;
  step: string;
  content: string;
  elapsed_ms: number;
}

/** SSE 事件回调 */
export interface AnalysisStreamCallbacks {
  onProgress?: (event: AnalysisProgressEvent) => void;
  onComplete?: (data: { agent_output: unknown }) => void;
  onError?: (data: { error: string; step?: string }) => void;
  onLlmInput?: (event: LlmInputEvent) => void;
  onLlmChunk?: (event: LlmChunkEvent) => void;
  onLlmDone?: (event: LlmDoneEvent) => void;
}

/**
 * 发起流式分析请求
 *
 * @returns AbortController，用于取消请求（组件卸载时调用 controller.abort()）
 */
export function analyzeCaseStream(
  caseId: number,
  callbacks: AnalysisStreamCallbacks
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const token = getAccessToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      let res = await fetch(
        `${API_BASE}/api/risk-cases/${caseId}/analyze/stream`,
        {
          method: "POST",
          headers,
          signal: controller.signal,
        }
      );

      // 处理 401 Token 过期
      if (res.status === 401 && token) {
        const newToken = await tryRefreshToken();
        if (newToken) {
          headers["Authorization"] = `Bearer ${newToken}`;
          res = await fetch(
            `${API_BASE}/api/risk-cases/${caseId}/analyze/stream`,
            {
              method: "POST",
              headers,
              signal: controller.signal,
            }
          );
        } else {
          clearTokens();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
          callbacks.onError?.({ error: "认证已过期，请重新登录" });
          return;
        }
      }

      if (!res.ok) {
        const text = await res.text();
        callbacks.onError?.({ error: `分析请求失败: ${res.status} ${text}` });
        return;
      }

      // 解析 SSE 流
      const reader = res.body?.getReader();
      if (!reader) {
        callbacks.onError?.({ error: "无法读取响应流" });
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 按双换行分割 SSE 事件
        const events = buffer.split("\n\n");
        buffer = events.pop() || ""; // 最后一个可能不完整，留在 buffer 中

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          // 跳过心跳注释
          if (eventBlock.trim().startsWith(":")) continue;

          // 解析 event 和 data
          let eventType = "";
          let dataStr = "";

          for (const line of eventBlock.split("\n")) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataStr += line.slice(5).trim();
            }
          }

          if (!eventType || !dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            switch (eventType) {
              case "progress":
                callbacks.onProgress?.(data as AnalysisProgressEvent);
                break;
              case "llm_input":
                callbacks.onLlmInput?.(data as LlmInputEvent);
                break;
              case "llm_chunk":
                callbacks.onLlmChunk?.(data as LlmChunkEvent);
                break;
              case "llm_done":
                callbacks.onLlmDone?.(data as LlmDoneEvent);
                break;
              case "complete":
                callbacks.onComplete?.(data);
                return; // 流结束
              case "error":
                callbacks.onError?.(data);
                return; // 流结束
            }
          } catch (parseErr) {
            console.warn("SSE 事件解析失败:", parseErr, dataStr);
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        // 正常取消，不报错
        return;
      }
      callbacks.onError?.({ error: `SSE 连接失败: ${String(err)}` });
    }
  })();

  return controller;
}

/* ═══════════ 对话式分析 SSE ═══════════ */

/** 对话 SSE 事件回调 */
export interface ChatStreamCallbacks {
  onChunk?: (data: { content: string }) => void;
  onDone?: (data: { content: string; elapsed_ms: number }) => void;
  onError?: (data: { error: string }) => void;
}

/**
 * 发起对话流式请求
 *
 * @param conversationId 对话 ID
 * @param message 用户消息
 * @param callbacks 事件回调
 * @returns AbortController
 */
export function chatStream(
  conversationId: number,
  message: string,
  callbacks: ChatStreamCallbacks
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const token = getAccessToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      let res = await fetch(
        `${API_BASE}/api/conversations/${conversationId}/chat/stream`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({ message }),
          signal: controller.signal,
        }
      );

      // 处理 401 Token 过期
      if (res.status === 401 && token) {
        const newToken = await tryRefreshToken();
        if (newToken) {
          headers["Authorization"] = `Bearer ${newToken}`;
          res = await fetch(
            `${API_BASE}/api/conversations/${conversationId}/chat/stream`,
            {
              method: "POST",
              headers,
              body: JSON.stringify({ message }),
              signal: controller.signal,
            }
          );
        } else {
          clearTokens();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
          callbacks.onError?.({ error: "认证已过期，请重新登录" });
          return;
        }
      }

      if (!res.ok) {
        const text = await res.text();
        callbacks.onError?.({ error: `对话请求失败: ${res.status} ${text}` });
        return;
      }

      // 解析 SSE 流
      const reader = res.body?.getReader();
      if (!reader) {
        callbacks.onError?.({ error: "无法读取响应流" });
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;
          if (eventBlock.trim().startsWith(":")) continue;

          let eventType = "";
          let dataStr = "";

          for (const line of eventBlock.split("\n")) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataStr += line.slice(5).trim();
            }
          }

          if (!eventType || !dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            switch (eventType) {
              case "chat_chunk":
                callbacks.onChunk?.(data);
                break;
              case "chat_done":
                callbacks.onDone?.(data);
                return;
              case "chat_error":
                callbacks.onError?.(data);
                return;
            }
          } catch (parseErr) {
            console.warn("Chat SSE 事件解析失败:", parseErr, dataStr);
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      callbacks.onError?.({ error: `Chat SSE 连接失败: ${String(err)}` });
    }
  })();

  return controller;
}
