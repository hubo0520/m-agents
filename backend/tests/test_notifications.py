"""
通知系统测试

测试通知 CRUD API、权限校验、业务事件触发通知。
"""
import json
import pytest

from app.models.models import Notification, User
from app.services.notification import NotificationService


class TestNotificationService:
    """通知服务单元测试"""

    def test_create_notification(self, db_session, admin_user):
        """创建通知"""
        n = NotificationService.create(
            db=db_session,
            user_id=str(admin_user.id),
            title="测试通知",
            content="这是一条测试通知",
            notification_type="approval_pending",
            related_entity_type="risk_case",
            related_entity_id=1,
        )
        assert n.id is not None
        assert n.is_read is False
        assert n.type == "approval_pending"

    def test_get_unread_count(self, db_session, admin_user):
        """获取未读数量"""
        for i in range(3):
            NotificationService.create(
                db=db_session, user_id=str(admin_user.id),
                title=f"通知 {i}", notification_type="analysis_complete",
            )
        db_session.flush()
        count = NotificationService.get_unread_count(db_session, str(admin_user.id))
        assert count == 3

    def test_mark_read(self, db_session, admin_user):
        """标记单条已读"""
        n = NotificationService.create(
            db=db_session, user_id=str(admin_user.id),
            title="测试", notification_type="risk_alert",
        )
        db_session.flush()

        result = NotificationService.mark_read(db_session, n.id, str(admin_user.id))
        assert result is True
        assert n.is_read is True

    def test_mark_read_wrong_user(self, db_session, admin_user, normal_user):
        """不能标记他人通知"""
        n = NotificationService.create(
            db=db_session, user_id=str(admin_user.id),
            title="测试", notification_type="risk_alert",
        )
        db_session.flush()

        result = NotificationService.mark_read(db_session, n.id, str(normal_user.id))
        assert result is False

    def test_mark_all_read(self, db_session, admin_user):
        """全部标记已读"""
        for i in range(5):
            NotificationService.create(
                db=db_session, user_id=str(admin_user.id),
                title=f"通知 {i}", notification_type="analysis_complete",
            )
        db_session.flush()

        count = NotificationService.mark_all_read(db_session, str(admin_user.id))
        assert count == 5

        unread = NotificationService.get_unread_count(db_session, str(admin_user.id))
        assert unread == 0

    def test_get_list_with_filter(self, db_session, admin_user):
        """列表过滤"""
        n1 = NotificationService.create(
            db=db_session, user_id=str(admin_user.id),
            title="已读通知", notification_type="analysis_complete",
        )
        n1.is_read = True
        NotificationService.create(
            db=db_session, user_id=str(admin_user.id),
            title="未读通知", notification_type="risk_alert",
        )
        db_session.flush()

        # 获取未读
        items, total = NotificationService.get_list(
            db_session, str(admin_user.id), is_read=False
        )
        assert total == 1
        assert items[0].title == "未读通知"

    def test_notify_risk_alert(self, db_session, admin_user, normal_user):
        """高风险预警通知应发送给 admin 和 risk_ops"""
        notifications = NotificationService.notify_risk_alert(
            db=db_session, case_id=1, priority="HIGH"
        )
        # admin_user(admin) 和 normal_user(risk_ops) 都应收到
        assert len(notifications) >= 2


class TestNotificationAPI:
    """通知 API 集成测试"""

    def test_get_notifications(self, auth_client, db_session, admin_user):
        """获取通知列表"""
        NotificationService.create(
            db=db_session, user_id=str(admin_user.id),
            title="API 测试通知", notification_type="analysis_complete",
        )
        db_session.commit()

        resp = auth_client.get("/api/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_get_unread_count_api(self, auth_client, db_session, admin_user):
        """获取未读数量 API"""
        NotificationService.create(
            db=db_session, user_id=str(admin_user.id),
            title="未读测试", notification_type="risk_alert",
        )
        db_session.commit()

        resp = auth_client.get("/api/notifications/unread-count")
        assert resp.status_code == 200
        data = resp.json()
        assert "unread_count" in data
        assert data["unread_count"] >= 1

    def test_mark_read_api(self, auth_client, db_session, admin_user):
        """标记已读 API"""
        n = NotificationService.create(
            db=db_session, user_id=str(admin_user.id),
            title="标记测试", notification_type="approval_result",
        )
        db_session.commit()

        resp = auth_client.put(f"/api/notifications/{n.id}/read")
        assert resp.status_code == 200

    def test_mark_read_not_found(self, auth_client):
        """标记不存在的通知应返回 404"""
        resp = auth_client.put("/api/notifications/99999/read")
        assert resp.status_code == 404

    def test_mark_all_read_api(self, auth_client, db_session, admin_user):
        """全部标记已读 API"""
        for i in range(3):
            NotificationService.create(
                db=db_session, user_id=str(admin_user.id),
                title=f"批量测试 {i}", notification_type="analysis_complete",
            )
        db_session.commit()

        resp = auth_client.put("/api/notifications/read-all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 3

    def test_unauthenticated_access(self, client):
        """未认证请求应返回 401"""
        resp = client.get("/api/notifications")
        assert resp.status_code == 401
