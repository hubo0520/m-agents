"""
业务逻辑单元测试：规则引擎、指标计算、现金流预测
"""
import json
from datetime import datetime, timedelta, date

import pytest
from sqlalchemy.orm import Session

from app.models.models import (
    Merchant, Order, Return, Settlement,
)
from app.engine.metrics import (
    compute_return_rate,
    compute_baseline_return_rate,
    compute_return_amplification,
    compute_avg_settlement_delay,
    compute_refund_pressure,
    compute_anomaly_score,
    get_all_metrics,
)
from app.engine.cashflow import forecast_cash_gap


# ─────── 指标计算测试 ───────

class TestMetrics:
    """指标计算单元测试"""

    def test_return_rate_no_orders(self, db_session, mock_merchant):
        """无订单时退货率应为 0"""
        rate = compute_return_rate(db_session, mock_merchant.id, days=7)
        assert rate == 0.0

    def test_return_rate_no_returns(self, db_session, mock_merchant):
        """有订单但无退货时退货率应为 0"""
        now = datetime.utcnow()
        for i in range(5):
            order = Order(
                merchant_id=mock_merchant.id,
                sku_id=f"SKU-{i}",
                order_amount=100.0,
                order_time=now - timedelta(days=i),
            )
            db_session.add(order)
        db_session.flush()

        rate = compute_return_rate(db_session, mock_merchant.id, days=7)
        assert rate == 0.0

    def test_return_rate_with_returns(self, db_session, mock_merchant):
        """有退货时应计算正确的退货率"""
        now = datetime.utcnow()
        # 创建 4 个订单，其中 2 个有退货
        for i in range(4):
            order = Order(
                merchant_id=mock_merchant.id,
                sku_id=f"SKU-{i}",
                order_amount=100.0,
                order_time=now - timedelta(days=1),
                delivered_time=now - timedelta(hours=12),
            )
            db_session.add(order)
            db_session.flush()

            if i < 2:  # 前 2 个有退货
                ret = Return(
                    order_id=order.id,
                    return_reason="不想要了",
                    refund_amount=80.0,
                    return_time=now,
                )
                db_session.add(ret)
        db_session.flush()

        rate = compute_return_rate(db_session, mock_merchant.id, days=7)
        assert rate == 0.5  # 2/4

    def test_return_amplification_normal(self, db_session, mock_merchant_with_orders):
        """有历史数据时退货放大倍数应可计算"""
        amp = compute_return_amplification(db_session, mock_merchant_with_orders.id)
        # mock_merchant_with_orders 近 7 天每天 2 个订单，其中 1 个退货 (50%)
        # 28 天基线退货率较低（7天之外没有退货）
        # 放大倍数应 > 1
        assert amp >= 1.0

    def test_return_amplification_no_baseline(self, db_session, mock_merchant):
        """无基线数据时放大倍数应为 0"""
        amp = compute_return_amplification(db_session, mock_merchant.id)
        assert amp == 0.0

    def test_avg_settlement_delay(self, db_session, mock_merchant):
        """结算延迟天数应正确计算"""
        today = date.today()
        # 创建 3 笔结算，各延迟 1、2、3 天
        for delay_days in [1, 2, 3]:
            expected = today - timedelta(days=delay_days + 5)
            actual = expected + timedelta(days=delay_days)
            settlement = Settlement(
                merchant_id=mock_merchant.id,
                amount=1000.0,
                expected_settlement_date=expected,
                actual_settlement_date=actual,
            )
            db_session.add(settlement)
        db_session.flush()

        avg_delay = compute_avg_settlement_delay(db_session, mock_merchant.id)
        assert avg_delay == 2.0  # (1+2+3)/3 = 2.0

    def test_avg_settlement_delay_no_data(self, db_session, mock_merchant):
        """无结算数据时延迟应为 0"""
        avg_delay = compute_avg_settlement_delay(db_session, mock_merchant.id)
        assert avg_delay == 0.0

    def test_refund_pressure(self, db_session, mock_merchant):
        """退款压力应正确计算总退款金额"""
        now = datetime.utcnow()
        for i in range(3):
            order = Order(
                merchant_id=mock_merchant.id,
                sku_id=f"SKU-{i}",
                order_amount=200.0,
                order_time=now - timedelta(days=1),
            )
            db_session.add(order)
            db_session.flush()

            ret = Return(
                order_id=order.id,
                return_reason="质量问题",
                refund_amount=150.0,
                return_time=now,
            )
            db_session.add(ret)
        db_session.flush()

        pressure = compute_refund_pressure(db_session, mock_merchant.id, days=7)
        assert pressure == 450.0  # 3 * 150

    def test_get_all_metrics(self, db_session, mock_merchant_with_orders):
        """get_all_metrics 应返回所有指标"""
        metrics = get_all_metrics(db_session, mock_merchant_with_orders.id)
        expected_keys = [
            "return_rate_7d", "baseline_return_rate", "return_amplification",
            "avg_settlement_delay", "refund_pressure_7d", "refund_pressure_14d",
            "anomaly_score",
        ]
        for key in expected_keys:
            assert key in metrics, f"缺少指标: {key}"
            assert isinstance(metrics[key], (int, float)), f"指标 {key} 类型错误"


# ─────── 现金流预测测试 ───────

class TestCashflowForecast:
    """现金流预测测试"""

    def test_forecast_no_data(self, db_session, mock_merchant):
        """无历史数据时也应返回有效结构"""
        result = forecast_cash_gap(db_session, mock_merchant.id, horizon_days=14)
        assert "daily_forecast" in result
        assert "predicted_gap" in result
        assert "lowest_cash_day" in result
        assert "confidence" in result
        assert isinstance(result["daily_forecast"], list)
        assert len(result["daily_forecast"]) == 14

    def test_forecast_with_data(self, db_session, mock_merchant_with_orders):
        """有历史数据时应生成预测"""
        result = forecast_cash_gap(db_session, mock_merchant_with_orders.id, horizon_days=14)
        assert len(result["daily_forecast"]) == 14

        # 每日预测应包含完整字段
        for day in result["daily_forecast"]:
            assert "date" in day
            assert "inflow" in day
            assert "outflow" in day
            assert "netflow" in day

        # 预测缺口应为非负数
        assert result["predicted_gap"] >= 0

        # 置信度应在合理范围
        assert 0 <= result["confidence"] <= 1

    def test_forecast_custom_horizon(self, db_session, mock_merchant_with_orders):
        """自定义预测天数"""
        result = forecast_cash_gap(db_session, mock_merchant_with_orders.id, horizon_days=7)
        assert len(result["daily_forecast"]) == 7


# ─────── 规则引擎测试 ───────

class TestRuleEngine:
    """规则引擎单元测试"""

    def test_evaluate_risk_no_data(self, db_session, mock_merchant):
        """无业务数据的商家风险应为 low"""
        from app.engine.rules import evaluate_risk
        result = evaluate_risk(db_session, mock_merchant.id)
        assert "risk_level" in result
        assert "risk_score" in result
        assert "factors" in result
        assert "summary" in result
        assert result["risk_level"] == "low"
        assert result["risk_score"] == 0

    def test_evaluate_risk_with_data(self, db_session, mock_merchant_with_orders):
        """有业务数据的商家应计算出风险等级"""
        from app.engine.rules import evaluate_risk
        result = evaluate_risk(db_session, mock_merchant_with_orders.id)
        assert result["risk_level"] in ("low", "medium", "high")
        assert isinstance(result["risk_score"], (int, float))
        assert isinstance(result["factors"], dict)
