"""
通知服务 — 管理应用内通知的创建、查询和状态变更

支持四种通知类型：
- approval_pending: 审批待办
- approval_result: 审批结果
- analysis_complete: 分析完成
- risk_alert: 高风险预警
"""
from typing import Optional, List

from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Notification, User
from app.core.rbac import Role, Permission, ROLE_PERMISSIONS


class NotificationService:
    """通知服务"""

    @staticmethod
    def create(
        db: Session,
        user_id: str,
        title: str,
        content: str = "",
        notification_type: str = "approval_pending",
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
    ) -> Notification:
        """创建一条通知"""
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=notification_type,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
        db.add(notification)
        db.flush()
        logger.info(
            "📩 通知创建 | user={} | type={} | title={}",
            user_id, notification_type, title,
        )
        return notification

    @staticmethod
    def get_list(
        db: Session,
        user_id: str,
        is_read: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Notification], int]:
        """获取通知列表"""
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)

        total = query.count()
        items = (
            query.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    @staticmethod
    def get_unread_count(db: Session, user_id: str) -> int:
        """获取未读通知数量"""
        return (
            db.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .scalar()
        ) or 0

    @staticmethod
    def mark_read(db: Session, notification_id: int, user_id: str) -> bool:
        """标记单条通知已读。只能标记自己的通知，找不到返回 False。"""
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not notification:
            return False
        notification.is_read = True
        db.flush()
        return True

    @staticmethod
    def mark_all_read(db: Session, user_id: str) -> int:
        """全部标记已读，返回更新条数"""
        count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .update({"is_read": True})
        )
        db.flush()
        return count

    # ═══════════════════════════════════════════════════════════
    # 业务通知快捷方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def notify_approval_pending(
        db: Session,
        case_id: int,
        case_summary: str = "",
    ) -> List[Notification]:
        """
        通知审批人有新的待审批案件。

        查询具有审批相关权限（approve_fraud_review / approve_finance / approve_claim）的所有用户。
        """
        # 查找有审批权限的角色
        approval_perms = {
            Permission.APPROVE_FRAUD_REVIEW,
            Permission.APPROVE_FINANCE,
            Permission.APPROVE_CLAIM,
        }
        eligible_roles = []
        for role, perms in ROLE_PERMISSIONS.items():
            if perms & approval_perms:
                eligible_roles.append(role.value)

        # 查询这些角色的活跃用户
        users = (
            db.query(User)
            .filter(User.role.in_(eligible_roles), User.is_active == True)
            .all()
        )

        notifications = []
        for user in users:
            n = NotificationService.create(
                db=db,
                user_id=str(user.id),
                title=f"案件 RC-{case_id:04d} 待审批",
                content=case_summary or f"案件 RC-{case_id:04d} 已完成分析，等待您的审批。",
                notification_type="approval_pending",
                related_entity_type="risk_case",
                related_entity_id=case_id,
            )
            notifications.append(n)

        logger.info("📩 审批待办通知 | case_id={} | 通知人数={}", case_id, len(notifications))
        return notifications

    @staticmethod
    def notify_approval_result(
        db: Session,
        case_id: int,
        creator_user_id: str,
        decision: str,
        reviewer_name: str = "",
        comment: str = "",
    ) -> Optional[Notification]:
        """通知案件创建者审批结果"""
        status_text = "已通过" if decision in ("approve", "approve_with_changes") else "已驳回"
        content_parts = [f"案件 RC-{case_id:04d} {status_text}。"]
        if reviewer_name:
            content_parts.append(f"审批人：{reviewer_name}。")
        if comment:
            content_parts.append(f"意见：{comment}")

        return NotificationService.create(
            db=db,
            user_id=creator_user_id,
            title=f"案件 RC-{case_id:04d} 审批{status_text}",
            content=" ".join(content_parts),
            notification_type="approval_result",
            related_entity_type="risk_case",
            related_entity_id=case_id,
        )

    @staticmethod
    def notify_analysis_complete(
        db: Session,
        case_id: int,
        creator_user_id: str,
        success: bool = True,
    ) -> Optional[Notification]:
        """通知案件创建者分析已完成/失败"""
        if success:
            title = f"案件 RC-{case_id:04d} 分析完成"
            content = f"案件 RC-{case_id:04d} 的 AI 分析已成功完成，请查看分析结果。"
        else:
            title = f"案件 RC-{case_id:04d} 分析需人工处理"
            content = f"案件 RC-{case_id:04d} 的 AI 分析遇到问题，已转为人工处理。"

        return NotificationService.create(
            db=db,
            user_id=creator_user_id,
            title=title,
            content=content,
            notification_type="analysis_complete",
            related_entity_type="risk_case",
            related_entity_id=case_id,
        )

    @staticmethod
    def notify_risk_alert(
        db: Session,
        case_id: int,
        priority: str = "HIGH",
    ) -> List[Notification]:
        """通知所有管理员和风险运营高风险案件"""
        # admin 和 risk_ops 视为 supervisor 角色
        supervisor_roles = [Role.ADMIN.value, Role.RISK_OPS.value]

        users = (
            db.query(User)
            .filter(User.role.in_(supervisor_roles), User.is_active == True)
            .all()
        )

        notifications = []
        for user in users:
            n = NotificationService.create(
                db=db,
                user_id=str(user.id),
                title=f"⚠️ 高风险预警：案件 RC-{case_id:04d}（{priority}）",
                content=f"分诊 Agent 判定案件 RC-{case_id:04d} 为 {priority} 优先级，请及时关注。",
                notification_type="risk_alert",
                related_entity_type="risk_case",
                related_entity_id=case_id,
            )
            notifications.append(n)

        logger.info("🚨 高风险预警通知 | case_id={} | priority={} | 通知人数={}", case_id, priority, len(notifications))
        return notifications
