"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getApprovalDetail, approveTask, rejectTask, reviseAndApprove } from "@/lib/api";
import { getRoleName, getApprovalTypeLabel, getApprovalStatusLabel, getApprovalStatusColor, APPROVAL_TYPE_MAP } from "@/lib/constants";
import type { ApprovalTask } from "@/types";

/** 解析 payload_json 并渲染为可读卡片 */
function PayloadCard({ raw }: { raw: string | null | undefined }) {
  if (!raw) return <p className="text-sm text-gray-400">无内容</p>;

  let data: Record<string, unknown>;
  try {
    data = JSON.parse(raw);
  } catch {
    return <pre className="bg-gray-50 p-4 rounded text-sm overflow-x-auto whitespace-pre-wrap">{raw}</pre>;
  }

  // retry 场景: {failed_node, error}
  if ("failed_node" in data && "error" in data) {
    return (
      <div className="space-y-3 text-sm">
        <div className="flex items-start gap-2">
          <span className="text-gray-500 shrink-0 w-20">失败节点：</span>
          <span className="font-medium text-red-700">{String(data.failed_node)}</span>
        </div>
        <div className="flex items-start gap-2">
          <span className="text-gray-500 shrink-0 w-20">错误信息：</span>
          <span className="text-red-600">{String(data.error)}</span>
        </div>
      </div>
    );
  }

  // mock 场景: {action, amount}
  if ("action" in data && "amount" in data && Object.keys(data).length <= 2) {
    return (
      <div className="space-y-3 text-sm">
        <div className="flex items-start gap-2">
          <span className="text-gray-500 shrink-0 w-20">操作：</span>
          <span className="font-medium">{String(data.action)}</span>
        </div>
        <div className="flex items-start gap-2">
          <span className="text-gray-500 shrink-0 w-20">金额：</span>
          <span className="font-semibold text-blue-700">¥{Number(data.amount).toLocaleString()}</span>
        </div>
      </div>
    );
  }

  // V3ActionRecommendation 标准结构
  const actionType = data.action_type as string | undefined;
  const title = data.title as string | undefined;
  const why = data.why as string | undefined;
  const confidence = data.confidence as number | undefined;
  const requiresReview = data.requires_manual_review as boolean | undefined;
  const evidenceIds = data.evidence_ids as string[] | undefined;
  const benefit = data.expected_benefit as { cash_relief?: number; time_horizon_days?: number; description?: string } | undefined;

  const ACTION_TYPE_LABEL: Record<string, string> = {
    ...APPROVAL_TYPE_MAP,
    anomaly_review: "异常审查",
    insurance_adjust: "保险调整",
  };

  return (
    <div className="space-y-4 text-sm">
      {/* 标题行 */}
      {title && (
        <div className="flex items-center gap-3">
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          {actionType && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700 font-medium">
              {ACTION_TYPE_LABEL[actionType] ?? actionType}
            </span>
          )}
        </div>
      )}

      {/* 建议理由 */}
      {why && (
        <div className="bg-amber-50 border-l-4 border-amber-400 p-3 rounded-r">
          <p className="text-xs text-amber-600 font-medium mb-1">建议理由</p>
          <p className="text-gray-700">{why}</p>
        </div>
      )}

      {/* 预期收益 */}
      {benefit && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <p className="text-xs text-green-600 font-medium mb-2">预期收益</p>
          <div className="grid grid-cols-3 gap-3">
            {benefit.cash_relief != null && (
              <div>
                <p className="text-gray-500 text-xs">资金缓解</p>
                <p className="font-semibold text-green-700">¥{Number(benefit.cash_relief).toLocaleString()}</p>
              </div>
            )}
            {benefit.time_horizon_days != null && (
              <div>
                <p className="text-gray-500 text-xs">时效周期</p>
                <p className="font-semibold text-green-700">{benefit.time_horizon_days} 天</p>
              </div>
            )}
            {benefit.description && (
              <div className="col-span-3">
                <p className="text-gray-500 text-xs">说明</p>
                <p className="text-gray-700">{benefit.description}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 置信度 & 复核 */}
      <div className="flex items-center gap-6">
        {confidence != null && (
          <div className="flex items-center gap-2">
            <span className="text-gray-500">置信度：</span>
            <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${confidence >= 0.7 ? 'bg-green-500' : confidence >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'}`}
                style={{ width: `${(confidence * 100).toFixed(0)}%` }}
              />
            </div>
            <span className="font-medium">{(confidence * 100).toFixed(0)}%</span>
          </div>
        )}
        {requiresReview != null && (
          <div className="flex items-center gap-1">
            <span className="text-gray-500">需人工复核：</span>
            <span className={requiresReview ? "text-orange-600 font-medium" : "text-green-600 font-medium"}>
              {requiresReview ? "是" : "否"}
            </span>
          </div>
        )}
      </div>

      {/* 关联证据 */}
      {evidenceIds && evidenceIds.length > 0 && (
        <div>
          <p className="text-gray-500 mb-1">关联证据：</p>
          <div className="flex flex-wrap gap-1.5">
            {evidenceIds.map((eid) => (
              <span key={eid} className="px-2 py-0.5 rounded bg-gray-100 text-gray-600 text-xs font-mono">
                {eid}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ApprovalDetailPage() {
  const params = useParams();
  const router = useRouter();
  const approvalId = Number(params.id);
  const [task, setTask] = useState<ApprovalTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState("");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (!approvalId) return;
    getApprovalDetail(approvalId).then(setTask).finally(() => setLoading(false));
  }, [approvalId]);

  const handleApprove = async () => {
    setProcessing(true);
    await approveTask(approvalId, { reviewer_id: "admin", comment });
    router.push("/approvals");
  };

  const handleReject = async () => {
    if (!comment) {
      alert("驳回必须填写理由");
      return;
    }
    setProcessing(true);
    await rejectTask(approvalId, { reviewer_id: "admin", comment });
    router.push("/approvals");
  };

  if (loading) return <div className="p-6">加载中...</div>;
  if (!task) return <div className="p-6">审批任务不存在</div>;

  const isPending = task.status === "PENDING" || task.status === "OVERDUE";

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button onClick={() => router.back()} className="text-blue-600 hover:underline mb-4 text-sm">
        ← 返回审批列表
      </button>

      <h1 className="text-2xl font-bold mb-6">审批详情 #{task.id}</h1>

      {/* 基本信息 */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-gray-500">审批类型：</span>{getApprovalTypeLabel(task.approval_type)}</div>
          <div><span className="text-gray-500">状态：</span>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getApprovalStatusColor(task.status)}`}>{getApprovalStatusLabel(task.status)}</span>
          </div>
          <div><span className="text-gray-500">关联案件：</span>#{task.case_id}</div>
          <div><span className="text-gray-500">分配角色：</span>{task.assignee_role ? getRoleName(task.assignee_role) : "-"}</div>
          <div><span className="text-gray-500">创建时间：</span>{task.created_at}</div>
          <div><span className="text-gray-500">到期时间：</span>{task.due_at || "-"}</div>
          {task.reviewer && <div><span className="text-gray-500">审批人：</span>{task.reviewer}</div>}
          {task.reviewed_at && <div><span className="text-gray-500">审批时间：</span>{task.reviewed_at}</div>}
        </div>
      </div>

      {/* 审批内容 */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-3">审批内容</h2>
        <PayloadCard raw={task.payload_json} />
      </div>

      {/* 历史审批意见 */}
      {task.comment && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-3">审批意见</h2>
          <p className="text-sm text-gray-700">{task.comment}</p>
        </div>
      )}

      {/* 操作区域 */}
      {isPending && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">审批操作</h2>
          <textarea
            className="w-full border rounded p-3 text-sm mb-4"
            rows={3}
            placeholder="输入审批意见（驳回时必填）"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <div className="flex gap-3">
            <button
              onClick={handleApprove}
              disabled={processing}
              className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50"
            >
              批准
            </button>
            <button
              onClick={handleReject}
              disabled={processing}
              className="bg-red-600 text-white px-6 py-2 rounded hover:bg-red-700 disabled:opacity-50"
            >
              驳回
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
