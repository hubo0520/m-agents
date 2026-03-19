"""
RBAC 角色与权限定义

5 种角色：风险运营、融资运营、理赔运营、合规复核、管理员
"""
from enum import Enum
from typing import Set, Dict


class Role(str, Enum):
    RISK_OPS = "risk_ops"          # 风险运营
    FINANCE_OPS = "finance_ops"    # 融资运营
    CLAIM_OPS = "claim_ops"        # 理赔运营
    COMPLIANCE = "compliance"      # 合规复核
    ADMIN = "admin"                # 管理员


# 权限定义
class Permission(str, Enum):
    # 案件
    VIEW_CASES = "view_cases"
    TRIGGER_ANALYSIS = "trigger_analysis"
    REOPEN_CASE = "reopen_case"

    # 审批
    VIEW_APPROVALS = "view_approvals"
    APPROVE_FRAUD_REVIEW = "approve_fraud_review"
    APPROVE_FINANCE = "approve_finance"
    APPROVE_CLAIM = "approve_claim"

    # 工作流
    VIEW_WORKFLOWS = "view_workflows"
    RETRY_WORKFLOW = "retry_workflow"
    RESUME_WORKFLOW = "resume_workflow"

    # 配置
    MANAGE_PROMPTS = "manage_prompts"
    MANAGE_SCHEMAS = "manage_schemas"
    MANAGE_MODELS = "manage_models"
    MANAGE_TOOLS = "manage_tools"
    MANAGE_APPROVAL_RULES = "manage_approval_rules"

    # 评测
    VIEW_EVALS = "view_evals"
    CREATE_EVALS = "create_evals"

    # 审计
    VIEW_AUDIT = "view_audit"

    # 建议修改
    MODIFY_RECOMMENDATIONS = "modify_recommendations"


# 角色权限矩阵
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.RISK_OPS: {
        Permission.VIEW_CASES,
        Permission.TRIGGER_ANALYSIS,
        Permission.REOPEN_CASE,
        Permission.VIEW_APPROVALS,
        Permission.APPROVE_FRAUD_REVIEW,
        Permission.VIEW_WORKFLOWS,
        Permission.VIEW_EVALS,
        Permission.VIEW_AUDIT,
    },
    Role.FINANCE_OPS: {
        Permission.VIEW_CASES,
        Permission.VIEW_APPROVALS,
        Permission.APPROVE_FINANCE,
        Permission.MODIFY_RECOMMENDATIONS,
        Permission.VIEW_WORKFLOWS,
        Permission.VIEW_EVALS,
    },
    Role.CLAIM_OPS: {
        Permission.VIEW_CASES,
        Permission.VIEW_APPROVALS,
        Permission.APPROVE_CLAIM,
        Permission.MODIFY_RECOMMENDATIONS,
        Permission.VIEW_WORKFLOWS,
        Permission.VIEW_EVALS,
    },
    Role.COMPLIANCE: {
        Permission.VIEW_CASES,
        Permission.VIEW_APPROVALS,
        Permission.VIEW_WORKFLOWS,
        Permission.VIEW_EVALS,
        Permission.VIEW_AUDIT,
        # 合规可以拒绝建议，但不可修改
        Permission.APPROVE_FRAUD_REVIEW,
        Permission.APPROVE_FINANCE,
        Permission.APPROVE_CLAIM,
    },
    Role.ADMIN: {
        # 管理员拥有所有权限
        perm for perm in Permission
    },
}


def get_roles() -> list:
    """获取所有角色"""
    return [
        {"name": r.value, "label": {
            "risk_ops": "风险运营",
            "finance_ops": "融资运营",
            "claim_ops": "理赔运营",
            "compliance": "合规复核",
            "admin": "管理员",
        }[r.value]}
        for r in Role
    ]


def has_permission(role: str, permission: Permission) -> bool:
    """检查角色是否有指定权限"""
    try:
        role_enum = Role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(role_enum, set())


def get_role_permissions(role: str) -> Set[Permission]:
    """获取角色的所有权限"""
    try:
        role_enum = Role(role)
    except ValueError:
        return set()
    return ROLE_PERMISSIONS.get(role_enum, set())
