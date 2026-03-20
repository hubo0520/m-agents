"""
案件 API 测试：案件列表分页、案件详情、触发分析
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from app.models.models import RiskCase, Merchant


class TestCaseList:
    """案件列表分页测试"""

    def test_list_cases_empty(self, auth_client):
        """无案件时返回空列表"""
        resp = auth_client.get("/api/risk-cases")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_cases_with_data(self, auth_client, mock_case):
        """有案件时返回正确的列表"""
        resp = auth_client.get("/api/risk-cases")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_cases_pagination(self, auth_client, db_session, mock_merchant):
        """分页参数应正确生效"""
        # 创建多个案件
        for i in range(5):
            case = RiskCase(
                merchant_id=mock_merchant.id,
                risk_score=50.0 + i * 10,
                risk_level="medium",
                status="NEW",
            )
            db_session.add(case)
        db_session.flush()

        # 第1页，每页2条
        resp = auth_client.get("/api/risk-cases?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

        # 第2页
        resp = auth_client.get("/api/risk-cases?page=2&page_size=2")
        data = resp.json()
        assert len(data["items"]) == 2

    def test_list_cases_filter_by_risk_level(self, auth_client, db_session, mock_merchant):
        """按风险等级筛选"""
        for level in ["high", "medium", "low"]:
            case = RiskCase(
                merchant_id=mock_merchant.id,
                risk_score=50.0,
                risk_level=level,
                status="NEW",
            )
            db_session.add(case)
        db_session.flush()

        resp = auth_client.get("/api/risk-cases?risk_level=high")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["risk_level"] == "high"

    def test_list_cases_filter_by_status(self, auth_client, db_session, mock_merchant):
        """按状态筛选"""
        for status in ["NEW", "ANALYZED"]:
            case = RiskCase(
                merchant_id=mock_merchant.id,
                risk_score=50.0,
                risk_level="medium",
                status=status,
            )
            db_session.add(case)
        db_session.flush()

        resp = auth_client.get("/api/risk-cases?status=ANALYZED")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] == "ANALYZED"


class TestCaseDetail:
    """案件详情测试"""

    def test_get_case_detail_success(self, auth_client, mock_case):
        """获取存在的案件详情应成功"""
        resp = auth_client.get(f"/api/risk-cases/{mock_case.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == mock_case.id
        assert data["risk_level"] == "high"
        assert data["status"] == "NEW"
        assert "merchant" in data

    def test_get_case_detail_not_found(self, auth_client):
        """获取不存在的案件应返回 404"""
        resp = auth_client.get("/api/risk-cases/99999")
        assert resp.status_code == 404

    def test_get_analyzed_case_detail(self, auth_client, mock_analyzed_case):
        """已分析的案件应包含 agent_output"""
        resp = auth_client.get(f"/api/risk-cases/{mock_analyzed_case.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ANALYZED"
        assert data["agent_output"] is not None
        assert "case_summary" in data["agent_output"]


class TestTriggerAnalysis:
    """触发分析测试"""

    @patch("app.api.risk_cases.agent_analyze")
    def test_trigger_analysis_success(self, mock_analyze, auth_client, mock_case):
        """触发分析应成功（mock Agent）"""
        mock_analyze.return_value = {
            "case_summary": "测试分析结果",
            "risk_level": "high",
            "root_causes": [],
            "cash_gap_forecast": {"predicted_gap": 50000},
            "recommendations": [],
        }

        resp = auth_client.post(f"/api/risk-cases/{mock_case.id}/analyze")
        assert resp.status_code == 200

    def test_trigger_analysis_case_not_found(self, auth_client):
        """对不存在的案件触发分析应返回 404"""
        resp = auth_client.post("/api/risk-cases/99999/analyze")
        assert resp.status_code == 404
