"""
Evidence Agent LLM 分析层单元测试
"""
import pytest
from unittest.mock import patch, MagicMock

from app.agents.schemas import AgentInput, EvidenceOutput, EvidenceBundle


@pytest.fixture
def agent_input():
    return AgentInput(case_id="RC-0001", merchant_id="M-1001")


def _make_bundles(count: int) -> list:
    """创建指定数量的 EvidenceBundle"""
    return [
        EvidenceBundle(
            evidence_id=f"EV-{101 + i}",
            evidence_type="return" if i < count // 2 else "settlement",
            summary=f"测试证据 #{i + 1}",
            importance_score=0.7,
        )
        for i in range(count)
    ]


class TestEvidenceLLMTrigger:
    """LLM 分析触发条件测试"""

    @patch("app.core.llm_client.is_llm_enabled", return_value=True)
    @patch("app.agents.evidence_agent.collect_evidence")
    @patch("app.agents.evidence_agent._analyze_evidence_llm")
    def test_triggers_llm_when_evidence_gt_3(self, mock_analyze, mock_collect, mock_llm, agent_input):
        """证据数量 > 3 时触发 LLM 分析"""
        from app.agents.evidence_agent import run_evidence

        mock_collect.return_value = [
            {"evidence_id": f"EV-{101 + i}", "type": "return", "summary": f"证据{i}"}
            for i in range(5)
        ]
        mock_analyze.return_value = EvidenceOutput(
            evidence_bundle=_make_bundles(5),
            coverage_summary="LLM 增强摘要",
            total_evidence_count=5,
        )

        mock_case = MagicMock()
        mock_db = MagicMock()
        result = run_evidence(agent_input, mock_db, mock_case)

        mock_analyze.assert_called_once()
        assert result.coverage_summary == "LLM 增强摘要"

    @patch("app.core.llm_client.is_llm_enabled", return_value=True)
    @patch("app.agents.evidence_agent.collect_evidence")
    def test_skips_llm_when_evidence_le_3(self, mock_collect, mock_llm, agent_input):
        """证据数量 <= 3 时跳过 LLM 分析"""
        from app.agents.evidence_agent import run_evidence

        mock_collect.return_value = [
            {"evidence_id": "EV-101", "type": "return", "summary": "证据1"},
            {"evidence_id": "EV-102", "type": "settlement", "summary": "证据2"},
        ]

        mock_case = MagicMock()
        mock_db = MagicMock()
        result = run_evidence(agent_input, mock_db, mock_case)

        assert result.coverage_summary == "共收集 2 条证据"  # 保持原始摘要

    @patch("app.core.llm_client.is_llm_enabled", return_value=False)
    @patch("app.agents.evidence_agent.collect_evidence")
    def test_skips_llm_when_disabled(self, mock_collect, mock_llm, agent_input):
        """LLM 未启用时使用原始结果"""
        from app.agents.evidence_agent import run_evidence

        mock_collect.return_value = [
            {"evidence_id": f"EV-{101 + i}", "type": "return", "summary": f"证据{i}"}
            for i in range(5)
        ]

        mock_case = MagicMock()
        mock_db = MagicMock()
        result = run_evidence(agent_input, mock_db, mock_case)

        assert "共收集 5 条证据" in result.coverage_summary


class TestEvidenceLLMFallback:
    """LLM 失败回退测试"""

    @patch("app.core.llm_client.is_llm_enabled", return_value=True)
    @patch("app.agents.evidence_agent.collect_evidence")
    @patch("app.agents.evidence_agent._analyze_evidence_llm", side_effect=Exception("LLM 超时"))
    def test_llm_failure_preserves_phase1(self, mock_analyze, mock_collect, mock_llm, agent_input):
        """LLM 失败时保留 Phase 1 结果"""
        from app.agents.evidence_agent import run_evidence

        mock_collect.return_value = [
            {"evidence_id": f"EV-{101 + i}", "type": "return", "summary": f"证据{i}"}
            for i in range(5)
        ]

        mock_case = MagicMock()
        mock_db = MagicMock()
        result = run_evidence(agent_input, mock_db, mock_case)

        assert result.total_evidence_count == 5
        assert "共收集 5 条证据" in result.coverage_summary
        # importance_score 保持硬编码值
        for bundle in result.evidence_bundle:
            assert bundle.importance_score == 0.7
