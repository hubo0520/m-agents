"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

/**
 * 通用 Markdown 渲染器
 * 封装 react-markdown + remark-gfm + Tailwind 样式映射
 */

const components: Components = {
  h1: ({ children }) => (
    <h1 className="text-lg font-bold text-slate-900 mt-4 mb-2">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-bold text-slate-800 mt-3 mb-2">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-slate-800 mt-2 mb-1">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-sm font-medium text-slate-700 mt-2 mb-1">{children}</h4>
  ),
  p: ({ children }) => (
    <p className="text-sm text-slate-700 mb-2 leading-relaxed">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-inside text-sm text-slate-700 mb-2 space-y-0.5 ml-2">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-inside text-sm text-slate-700 mb-2 space-y-0.5 ml-2">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="leading-relaxed">{children}</li>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-slate-600">{children}</em>
  ),
  code: ({ className, children, ...props }) => {
    // 判断是否是代码块（有 language- 前缀的 className）
    const isBlock = className?.startsWith("language-");
    if (isBlock) {
      return (
        <code className={`block bg-slate-100 p-3 rounded text-xs overflow-x-auto my-2 ${className || ""}`} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="bg-slate-100 px-1 py-0.5 rounded text-xs text-slate-800" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="bg-slate-50 border border-slate-200 rounded-lg p-3 my-2 overflow-x-auto text-xs">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="min-w-full text-sm border border-slate-200 rounded">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-slate-50">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-3 py-1.5 text-left text-xs font-semibold text-slate-600 border-b border-slate-200">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-1.5 text-xs text-slate-700 border-b border-slate-100">
      {children}
    </td>
  ),
  tr: ({ children }) => (
    <tr className="even:bg-slate-50/50">{children}</tr>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-3 border-slate-300 pl-3 my-2 text-sm text-slate-500 italic">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-slate-200" />,
  a: ({ href, children }) => (
    <a href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

interface MarkdownRendererProps {
  content: string;
  /** 额外的容器 className */
  className?: string;
}

export default function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  if (!content) return null;

  return (
    <div className={`markdown-renderer ${className || ""}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
