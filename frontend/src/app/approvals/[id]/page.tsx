"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getApprovalDetail, approveTask, rejectTask, reviseAndApprove } from "@/lib/api";
import { getRoleName, getApprovalTypeLabel, getApprovalStatusLabel, getApprovalStatusColor, APPROVAL_TYPE_MAP } from "@/lib/constants";
import type { ApprovalTask } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "sonner";

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
    try {
      await approveTask(approvalId, { reviewer_id: "admin", comment });
      toast.success("审批已通过");
      router.push("/approvals");
    } catch (err) {
      toast.error("批准失败: " + (err as Error).message);
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!comment) {
      toast.warning("驳回必须填写理由");
      return;
    }
    setProcessing(true);
    try {
      await rejectTask(approvalId, { reviewer_id: "admin", comment });
      toast.success("审批已驳回");
      router.push("/approvals");
    } catch (err) {
      toast.error("驳回失败: " + (err as Error).message);
    } finally {
      setProcessing(false);
    }
  };

  if (loading) return <Spinner label="加载审批详情..." />;
  if (!task) return (
    <div className="flex flex-col items-center justify-center py-20">
      <p className="text-sm text-slate-500">审批任务不存在</p>
    </div>
  );

  const isPending = task.status === "PENDING" || task.status === "OVERDUE";

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <button onClick={() => router.back()} className="text-sm text-slate-500 hover:text-blue-600 transition-colors mb-6 inline-block">
        ← 返回审批列表
      </button>

      <div className="flex items-center gap-3 mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">审批详情 #{task.id}</h1>
        <Badge variant={task.status === "APPROVED" ? "success" : task.status === "REJECTED" ? "danger" : "warning"} size="md" dot>
          {getApprovalStatusLabel(task.status)}
        </Badge>
      </div>

      {/* 基本信息 */}
      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-slate-500">审批类型：</span>
            <Badge variant="info" size="sm" className="ml-1">{getApprovalTypeLabel(task.approval_type)}</Badge>
          </div>
          <div><span className="text-slate-500">状态：</span>
            <Badge variant={task.status === "APPROVED" ? "success" : task.status === "REJECTED" ? "danger" : "warning"} size="sm" className="ml-1">
              {getApprovalStatusLabel(task.status)}
            </Badge>
          </div>
          <div><span className="text-slate-500">关联案件：</span>#{task.case_id}</div>
          <div><span className="text-slate-500">分配角色：</span>{task.assignee_role ? getRoleName(task.assignee_role) : "-"}</div>
          <div><span className="text-slate-500">创建时间：</span>{task.created_at}</div>
          <div><span className="text-slate-500">到期时间：</span>{task.due_at || "-"}</div>
          {task.reviewer && <div><span className="text-slate-500">审批人：</span>{task.reviewer}</div>}
          {task.reviewed_at && <div><span className="text-slate-500">审批时间：</span>{task.reviewed_at}</div>}
        </div>
      </Card>

      {/* 审批内容 */}
      <Card className="mb-6">
        <CardTitle className="mb-4">审批内容</CardTitle>
        <PayloadCard raw={task.payload_json} />
      </Card>

      {/* 历史审批意见 */}
      {task.comment && (
        <Card className="mb-6">
          <CardTitle className="mb-3">审批意见</CardTitle>
          <p className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3">{task.comment}</p>
        </Card>
      )}

      {/* 操作区域 */}
      {isPending && (
        <Card>
          <CardTitle className="mb-4">审批操作</CardTitle>
          <textarea
            className="w-full border border-slate-200 rounded-lg p-3 text-sm mb-4 hover:border-slate-300 placeholder:text-slate-300 resize-none"
            rows={3}
            placeholder="输入审批意见（驳回时必填）"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <div className="flex gap-3">
            <button
              onClick={handleApprove}
              disabled={processing}
              className="bg-emerald-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-40"
            >
              {processing ? "处理中..." : "批准"}
            </button>
            <button
              onClick={handleReject}
              disabled={processing}
              className="bg-red-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-40"
            >
              {processing ? "处理中..." : "驳回"}
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}
