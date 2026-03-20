"""
Triage Agent Hybrid 架构单元测试
"""
import pytest
from unittest.mock import patch, MagicMock

from app.agents.schemas import AgentInput, TriageOutput, CaseType, Priority


@pytest.fixture
def agent_input():
    return AgentInput(case_id="RC-0001", merchant_id="M-1001")


@pytest.fixture
def base_case_context():
    return {
        "has_insurance": False,
        "operation_days": 120,
    }


class TestTriageLevel1:
    """Level 1 规则预过滤测试"""

    def test_high_anomaly_score_direct_fraud(self, agent_input, base_case_context):
        """anomaly_score >= 0.8 直接判定 SUSPECTED_FRAUD"""
        from app.agents.triage_agent import run_triage

        metrics = {"anomaly_score": 0.85, "predicted_gap": 50000, "return_amplification": 1.5}
        result = run_triage(agent_input, metrics, base_case_context)

        assert result.case_type == CaseType.SUSPECTED_FRAUD
        assert result.priority == Priority.HIGH
        assert "0.85" in result.reasoning

    def test_very_low_risk_direct_low(self, agent_input, base_case_context):
        """anomaly_score <= 0.1 且 gap=0 直接判定 LOW"""
        from app.agents.triage_agent import run_triage

        metrics = {"anomaly_score": 0.05, "predicted_gap": 0, "return_amplification": 0.8}
        result = run_triage(agent_input, metrics, base_case_context)

        assert result.case_type == CaseType.CASH_GAP
        assert result.priority == Priority.LOW

    def test_boundary_anomaly_08(self, agent_input, base_case_context):
        """anomaly_score == 0.8 应走 Level 1"""
        from app.agents.triage_agent import run_triage

        metrics = {"anomaly_score": 0.8, "predicted_gap": 10000, "return_amplification": 1.0}
        result = run_triage(agent_input, metrics, base_case_context)

        assert result.case_type == CaseType.SUSPECTED_FRAUD
        assert result.priority == Priority.HIGH


class TestTriageLevel2:
    """Level 2 LLM 精细分类测试"""

    @patch("app.core.llm_client.is_llm_enabled", return_value=True)
    @patch("app.core.llm_client.structured_output")
    @patch("app.core.llm_client.load_prompt", return_value=("mock prompt", "default"))
    def test_fuzzy_zone_triggers_llm(self, mock_load_prompt, mock_structured, mock_llm_enabled, agent_input, base_case_context):
        """模糊区间触发 LLM 分类"""
        from app.agents.triage_agent import run_triage

        mock_structured.return_value = TriageOutput(
            case_type=CaseType.CASH_GAP,
            priority=Priority.MEDIUM,
            recommended_path="forecast → diagnosis → advance_settlement",
            reasoning="退货放大1.5倍，缺口75000，属于现金缺口类型",
        )

        metrics = {"anomaly_score": 0.4, "predicted_gap": 75000, "return_amplification": 1.5}
        result = run_triage(agent_input, metrics, base_case_context)

        assert result.case_type == CaseType.CASH_GAP
        assert result.priority == Priority.MEDIUM
        mock_structured.assert_called_once()


class TestTriageFallback:
    """LLM 失败回退测试"""

    @patch("app.core.llm_client.is_llm_enabled", return_value=True)
    @patch("app.core.llm_client.structured_output", side_effect=Exception("LLM 超时"))
    @patch("app.core.llm_client.load_prompt", return_value=("mock prompt", "default"))
    def test_llm_failure_fallback_to_rules(self, mock_load_prompt, mock_structured, mock_llm_enabled, agent_input, base_case_context):
        """LLM 失败时回退到规则引擎"""
        from app.agents.triage_agent import run_triage

        metrics = {"anomaly_score": 0.55, "predicted_gap": 30000, "return_amplification": 1.2}
        result = run_triage(agent_input, metrics, base_case_context)

        # 应该使用规则引擎的结果（anomaly >= 0.5 → suspected_fraud）
        assert result.case_type == CaseType.SUSPECTED_FRAUD
        assert isinstance(result, TriageOutput)

    @patch("app.core.llm_client.is_llm_enabled", return_value=False)
    def test_llm_disabled_uses_rules(self, mock_llm_enabled, agent_input, base_case_context):
        """LLM 未启用时使用规则引擎"""
        from app.agents.triage_agent import run_triage

        metrics = {"anomaly_score": 0.3, "predicted_gap": 80000, "return_amplification": 1.8}
        result = run_triage(agent_input, metrics, base_case_context)

        # 规则引擎逻辑: operation_days >= 60 + predicted_gap >= 50000 → BUSINESS_LOAN
        assert isinstance(result, TriageOutput)
        assert result.case_type == CaseType.BUSINESS_LOAN


class TestTriageLevel3:
    """Level 3 安全网测试"""

    def test_safety_net_validates_output(self):
        """安全网校验 LLM 输出合法性"""
        from app.agents.triage_agent import _level3_safety_net

        result = TriageOutput(
            case_type=CaseType.CASH_GAP,
            priority=Priority.HIGH,
            recommended_path="test",
            reasoning="test",
        )
        validated = _level3_safety_net(result)
        assert validated.case_type == CaseType.CASH_GAP
        assert validated.priority == Priority.HIGH
