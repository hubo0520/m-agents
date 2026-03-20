"""
analysis_context 传递集成测试
"""
import pytest
from app.workflow.state import GraphState, append_analysis_context


class TestAppendAnalysisContext:
    """append_analysis_context 工具函数测试"""

    def test_initial_append(self):
        """首次追加到空 context"""
        state: GraphState = {"analysis_context": ""}
        result = append_analysis_context(state, "triage", "case_type=cash_gap, priority=medium")

        assert "[triage] case_type=cash_gap, priority=medium" == result

    def test_multi_agent_append(self):
        """多个 Agent 依次追加"""
        state: GraphState = {"analysis_context": ""}

        ctx = append_analysis_context(state, "triage", "case_type=cash_gap")
        state["analysis_context"] = ctx

        ctx = append_analysis_context(state, "diagnosis", "risk_level=medium, root_causes=退货异常")
        state["analysis_context"] = ctx

        assert "[triage]" in ctx
        assert "[diagnosis]" in ctx
        assert "退货异常" in ctx

    def test_per_agent_truncation(self):
        """单条洞察超过 200 字时被截断"""
        state: GraphState = {"analysis_context": ""}
        long_insight = "A" * 300

        result = append_analysis_context(state, "triage", long_insight, max_per_agent=200)

        # [triage] 前缀 + 200 字 = 不超过 210 字
        agent_content = result.replace("[triage] ", "")
        assert len(agent_content) == 200

    def test_total_limit_truncation(self):
        """总长度超过限制时截断最早的条目"""
        state: GraphState = {"analysis_context": ""}

        # 追加多条使总长度超过 max_total
        for i in range(20):
            ctx = append_analysis_context(state, f"agent_{i}", "X" * 100, max_total=500)
            state["analysis_context"] = ctx

        assert len(state["analysis_context"]) <= 500

    def test_empty_state_key(self):
        """state 中没有 analysis_context key 时也能正常工作"""
        state: GraphState = {}
        result = append_analysis_context(state, "triage", "测试内容")

        assert "[triage] 测试内容" == result

    def test_downstream_receives_upstream_context(self):
        """验证下游 Agent 能收到上游的推理链路"""
        state: GraphState = {"analysis_context": ""}

        # 模拟完整链路
        ctx = append_analysis_context(state, "triage", "case_type=suspected_fraud, priority=high")
        state["analysis_context"] = ctx

        ctx = append_analysis_context(state, "evidence", "共收集8条证据, 5条退货+2条回款延迟")
        state["analysis_context"] = ctx

        ctx = append_analysis_context(state, "diagnosis", "risk_level=high, root_causes=[退货率异常, 回款延迟]")
        state["analysis_context"] = ctx

        ctx = append_analysis_context(state, "recommendation", "建议回款加速+异常复核")
        state["analysis_context"] = ctx

        final_context = state["analysis_context"]

        # 验证所有 Agent 的洞察都存在
        assert "[triage]" in final_context
        assert "[evidence]" in final_context
        assert "[diagnosis]" in final_context
        assert "[recommendation]" in final_context
        assert "suspected_fraud" in final_context
        assert "退货率异常" in final_context
