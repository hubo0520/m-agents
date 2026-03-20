"""
审批 API 测试：审批列表、批准、驳回、权限校验
"""
import json

import pytest

from app.models.models import ApprovalTask


class TestApprovalList:
    """审批列表测试"""

    def test_list_approvals_empty(self, auth_client):
        """无审批任务时返回空列表"""
        resp = auth_client.get("/api/approvals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_approvals_with_data(self, auth_client, mock_approval):
        """有审批任务时返回正确的列表"""
        resp = auth_client.get("/api/approvals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        items = data["items"]
        assert len(items) >= 1
        assert items[0]["approval_type"] == "business_loan"

    def test_list_approvals_filter_by_status(self, auth_client, mock_approval):
        """按状态筛选"""
        resp = auth_client.get("/api/approvals?status=PENDING")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] in ("PENDING", "OVERDUE")

    def test_list_approvals_filter_by_type(self, auth_client, mock_approval):
        """按审批类型筛选"""
        resp = auth_client.get("/api/approvals?approval_type=business_loan")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["approval_type"] == "business_loan"


class TestApprovalDetail:
    """审批详情测试"""

    def test_get_approval_detail(self, auth_client, mock_approval):
        """获取审批详情应成功"""
        resp = auth_client.get(f"/api/approvals/{mock_approval.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == mock_approval.id
        assert data["status"] == "PENDING"
        assert data["approval_type"] == "business_loan"

    def test_get_approval_not_found(self, auth_client):
        """获取不存在的审批应返回 404"""
        resp = auth_client.get("/api/approvals/99999")
        assert resp.status_code == 404


class TestApprove:
    """批准审批测试"""

    def test_approve_success(self, auth_client, mock_approval):
        """批准 PENDING 状态的审批应成功"""
        resp = auth_client.post(f"/api/approvals/{mock_approval.id}/approve", json={
            "reviewer_id": "test_admin",
            "comment": "测试批准",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "APPROVED"

    def test_approve_already_approved(self, auth_client, db_session, mock_approval):
        """不能重复批准已批准的任务"""
        mock_approval.status = "APPROVED"
        db_session.flush()

        resp = auth_client.post(f"/api/approvals/{mock_approval.id}/approve", json={
            "reviewer_id": "test_admin",
            "comment": "再次批准",
        })
        assert resp.status_code == 400

    def test_approve_not_found(self, auth_client):
        """批准不存在的审批应返回 404"""
        resp = auth_client.post("/api/approvals/99999/approve", json={
            "reviewer_id": "test_admin",
            "comment": "不存在",
        })
        assert resp.status_code == 404


class TestReject:
    """驳回审批测试"""

    def test_reject_success(self, auth_client, mock_approval):
        """驳回 PENDING 状态的审批应成功"""
        resp = auth_client.post(f"/api/approvals/{mock_approval.id}/reject", json={
            "reviewer_id": "test_admin",
            "comment": "测试驳回理由",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "REJECTED"

    def test_reject_without_comment(self, auth_client, mock_approval):
        """驳回时必须填写理由（comment 不能为空）"""
        resp = auth_client.post(f"/api/approvals/{mock_approval.id}/reject", json={
            "reviewer_id": "test_admin",
            "comment": "",
        })
        # RejectRequest 的 comment 有 min_length=1 校验
        assert resp.status_code == 422

    def test_reject_already_rejected(self, auth_client, db_session, mock_approval):
        """不能重复驳回已驳回的任务"""
        mock_approval.status = "REJECTED"
        db_session.flush()

        resp = auth_client.post(f"/api/approvals/{mock_approval.id}/reject", json={
            "reviewer_id": "test_admin",
            "comment": "再次驳回",
        })
        assert resp.status_code == 400


class TestBatchApproval:
    """批量审批测试"""

    def test_batch_approve(self, auth_client, db_session, mock_case):
        """批量批准多个审批任务"""
        approvals = []
        for i in range(3):
            a = ApprovalTask(
                case_id=mock_case.id,
                approval_type="fraud_review",
                status="PENDING",
                payload_json=json.dumps({"index": i}),
            )
            db_session.add(a)
            db_session.flush()
            approvals.append(a)

        ids = [a.id for a in approvals]
        resp = auth_client.post("/api/approvals/batch", json={
            "approval_ids": ids,
            "action": "approve",
            "reviewer_id": "test_admin",
            "comment": "批量通过",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 3
        for r in data["results"]:
            assert r["status"] == "ok"
            assert r["new_status"] == "APPROVED"

    def test_batch_reject(self, auth_client, db_session, mock_case):
        """批量驳回"""
        a = ApprovalTask(
            case_id=mock_case.id,
            approval_type="fraud_review",
            status="PENDING",
            payload_json=json.dumps({"index": 0}),
        )
        db_session.add(a)
        db_session.flush()

        resp = auth_client.post("/api/approvals/batch", json={
            "approval_ids": [a.id],
            "action": "reject",
            "reviewer_id": "test_admin",
            "comment": "批量驳回",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["new_status"] == "REJECTED"


class TestPermissions:
    """权限校验测试"""

    def test_unauthenticated_access_denied(self, client):
        """未认证请求应被拒绝"""
        resp = client.get("/api/approvals")
        assert resp.status_code == 401

    def test_public_endpoint_accessible(self, client):
        """公开端点（health）应无需认证"""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_auth_endpoints_public(self, client):
        """认证相关端点（login/check-init）应无需认证"""
        resp = client.get("/api/auth/check-init")
        assert resp.status_code == 200
