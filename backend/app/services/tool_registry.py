"""
工具注册与连接器中心

提供统一工具注册、权限策略、幂等键、调用日志。
"""
import hashlib
import json
from datetime import datetime
from app.core.utils import utc_now
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import ToolInvocation, ApprovalTask


# ═══════════════════════════════════════════════════════════════
# 工具注册表
# ═══════════════════════════════════════════════════════════════

TOOL_REGISTRY = {
    "query_credit_score": {
        "name": "query_credit_score",
        "version": "1.0",
        "description": "查询商家信用评分（读操作）",
        "approval_policy": "NONE",  # 无需审批
        "type": "read",
    },
    "submit_advance_settlement": {
        "name": "submit_advance_settlement",
        "version": "1.0",
        "description": "提交回款加速申请（写操作）",
        "approval_policy": "REQUIRED",  # 需要审批
        "type": "write",
    },
    "create_financing_draft": {
        "name": "create_financing_draft",
        "version": "1.0",
        "description": "创建经营贷申请草稿（写操作）",
        "approval_policy": "REQUIRED",
        "type": "write",
    },
    "create_claim_draft": {
        "name": "create_claim_draft",
        "version": "1.0",
        "description": "创建理赔草稿（写操作）",
        "approval_policy": "REQUIRED",
        "type": "write",
    },
    "create_manual_review_task": {
        "name": "create_manual_review_task",
        "version": "1.0",
        "description": "创建人工复核任务",
        "approval_policy": "NONE",
        "type": "write",
    },
}


def get_tool_list() -> list:
    """获取所有已注册工具"""
    return list(TOOL_REGISTRY.values())


def get_tool_info(tool_name: str) -> dict:
    """获取指定工具信息"""
    return TOOL_REGISTRY.get(tool_name)


# ═══════════════════════════════════════════════════════════════
# 幂等键生成
# ═══════════════════════════════════════════════════════════════

def generate_idempotency_key(workflow_run_id: int, tool_name: str, input_data: dict) -> str:
    """生成幂等键"""
    payload = f"{workflow_run_id}:{tool_name}:{json.dumps(input_data, sort_keys=True)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


# ═══════════════════════════════════════════════════════════════
# 工具调用
# ═══════════════════════════════════════════════════════════════

def invoke_tool(
    db: Session,
    tool_name: str,
    workflow_run_id: int = None,
    input_data: dict = None,
) -> dict:
    """
    统一工具调用入口。

    1. 检查工具是否注册
    2. 检查幂等键防重
    3. 检查审批策略
    4. 执行工具
    5. 记录调用日志
    """
    input_data = input_data or {}

    # 1. 检查工具注册
    tool_info = TOOL_REGISTRY.get(tool_name)
    if not tool_info:
        return {"success": False, "message": f"工具 {tool_name} 未注册"}

    # 2. 幂等键防重
    idempotency_key = generate_idempotency_key(
        workflow_run_id or 0, tool_name, input_data
    )
    existing = db.query(ToolInvocation).filter(
        ToolInvocation.idempotency_key == idempotency_key,
        ToolInvocation.status == "SUCCESS",
    ).first()
    if existing:
        return {
            "success": True,
            "message": "幂等键命中，返回已有结果",
            "output": json.loads(existing.output_json) if existing.output_json else {},
        }

    # 3. 检查审批策略
    approval_required = tool_info["approval_policy"] == "REQUIRED"
    if approval_required:
        # 检查是否已有审批通过
        approved = db.query(ApprovalTask).filter(
            ApprovalTask.workflow_run_id == workflow_run_id,
            ApprovalTask.status == "APPROVED",
        ).first()
        if not approved:
            # 需要创建审批任务
            invocation = ToolInvocation(
                workflow_run_id=workflow_run_id,
                tool_name=tool_name,
                tool_version=tool_info["version"],
                input_json=json.dumps(input_data, ensure_ascii=False),
                approval_required=1,
                approval_status="PENDING",
                status="PENDING",
                idempotency_key=idempotency_key,
            )
            db.add(invocation)
            db.flush()
            return {
                "success": False,
                "message": f"工具 {tool_name} 需要审批，已创建审批前置拦截",
                "needs_approval": True,
            }

    # 4. 执行工具（Mock 连接器）
    output = _execute_mock_tool(tool_name, input_data)

    # 5. 记录调用日志
    invocation = ToolInvocation(
        workflow_run_id=workflow_run_id,
        tool_name=tool_name,
        tool_version=tool_info["version"],
        input_json=json.dumps(input_data, ensure_ascii=False),
        output_json=json.dumps(output, ensure_ascii=False),
        approval_required=1 if approval_required else 0,
        approval_status="APPROVED" if approval_required else None,
        status="SUCCESS" if output.get("success") else "FAILED",
        idempotency_key=idempotency_key,
    )
    db.add(invocation)
    db.flush()

    return output


# ═══════════════════════════════════════════════════════════════
# Mock 连接器
# ═══════════════════════════════════════════════════════════════

def _execute_mock_tool(tool_name: str, input_data: dict) -> dict:
    """Mock 连接器执行"""
    if tool_name == "query_credit_score":
        # Mock 读操作：查询商家信用评分
        merchant_id = input_data.get("merchant_id", 0)
        return {
            "success": True,
            "message": "信用评分查询成功",
            "data": {
                "merchant_id": merchant_id,
                "credit_score": 85,
                "credit_level": "优良",
                "updated_at": utc_now().isoformat(),
            },
        }
    elif tool_name == "submit_advance_settlement":
        # Mock 写操作：回款加速申请
        return {
            "success": True,
            "message": "回款加速申请已提交",
            "data": {
                "application_id": f"AS-{utc_now().strftime('%Y%m%d%H%M%S')}",
                "status": "submitted",
                "estimated_settlement_date": (utc_now()).isoformat(),
            },
        }
    elif tool_name == "create_financing_draft":
        return {
            "success": True,
            "message": "经营贷草稿已创建",
            "data": {"draft_id": f"FD-{utc_now().strftime('%Y%m%d%H%M%S')}"},
        }
    elif tool_name == "create_claim_draft":
        return {
            "success": True,
            "message": "理赔草稿已创建",
            "data": {"draft_id": f"CD-{utc_now().strftime('%Y%m%d%H%M%S')}"},
        }
    elif tool_name == "create_manual_review_task":
        return {
            "success": True,
            "message": "人工复核任务已创建",
            "data": {"task_id": f"MR-{utc_now().strftime('%Y%m%d%H%M%S')}"},
        }
    else:
        return {"success": False, "message": f"未知工具: {tool_name}"}
