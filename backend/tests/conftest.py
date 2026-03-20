"""
测试核心 fixture：内存 SQLite 数据库、TestClient、认证用户、mock 数据
"""
import os
import json
from datetime import datetime, timedelta, date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# 在导入 app 之前设置测试环境变量
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["DEBUG_AUTH"] = "False"

from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.main import app
from app.models.models import (
    User, Merchant, Order, Return, Settlement,
    RiskCase, ApprovalTask, AuditLog,
)


# ─────── 数据库 Fixtures ───────

@pytest.fixture(scope="session")
def engine():
    """创建测试用内存 SQLite 引擎"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    """每个测试函数使用独立的事务，测试后自动回滚"""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """创建已覆盖 get_db 依赖的 TestClient"""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─────── 用户 Fixtures ───────

@pytest.fixture
def admin_user(db_session) -> User:
    """创建管理员用户"""
    user = User(
        username="test_admin",
        display_name="测试管理员",
        password_hash=hash_password("admin123"),
        role="admin",
        is_active=True,
        is_superadmin=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def normal_user(db_session) -> User:
    """创建普通操作员"""
    user = User(
        username="test_operator",
        display_name="测试操作员",
        password_hash=hash_password("operator123"),
        role="risk_ops",
        is_active=True,
        is_superadmin=False,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def admin_token(admin_user) -> str:
    """为管理员生成 Access Token"""
    payload = {
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "role": admin_user.role,
    }
    return create_access_token(payload)


@pytest.fixture
def normal_token(normal_user) -> str:
    """为普通用户生成 Access Token"""
    payload = {
        "sub": str(normal_user.id),
        "username": normal_user.username,
        "role": normal_user.role,
    }
    return create_access_token(payload)


@pytest.fixture
def auth_client(client, admin_token) -> TestClient:
    """带管理员 Token 的 TestClient"""
    client.headers["Authorization"] = f"Bearer {admin_token}"
    return client


@pytest.fixture
def normal_auth_client(client, normal_token) -> TestClient:
    """带普通用户 Token 的 TestClient"""
    client.headers["Authorization"] = f"Bearer {normal_token}"
    return client


# ─────── Mock 数据 Fixtures ───────

@pytest.fixture
def mock_merchant(db_session) -> Merchant:
    """创建测试用商家"""
    merchant = Merchant(
        name="测试商家-风控专用",
        industry="电商",
        settlement_cycle_days=7,
        store_level="gold",
    )
    db_session.add(merchant)
    db_session.flush()
    return merchant


@pytest.fixture
def mock_merchant_with_orders(db_session, mock_merchant) -> Merchant:
    """创建带有订单和退货数据的商家"""
    now = datetime.utcnow()

    # 创建近 30 天的订单（每天 2 笔）
    for day_offset in range(30):
        order_time = now - timedelta(days=day_offset)
        for i in range(2):
            order = Order(
                merchant_id=mock_merchant.id,
                sku_id=f"SKU-{day_offset:02d}-{i}",
                order_amount=1000.0 + day_offset * 10,
                order_time=order_time,
                delivered_time=order_time + timedelta(hours=24),
            )
            db_session.add(order)
            db_session.flush()

            # 近 7 天的订单中 50% 有退货（模拟高退货率）
            if day_offset < 7 and i == 0:
                ret = Return(
                    order_id=order.id,
                    return_reason="质量问题",
                    refund_amount=order.order_amount * 0.8,
                    return_time=order_time + timedelta(hours=48),
                )
                db_session.add(ret)

    # 创建结算记录
    for day_offset in range(0, 30, 7):
        expected_date = date.today() - timedelta(days=day_offset)
        settlement = Settlement(
            merchant_id=mock_merchant.id,
            amount=5000.0,
            expected_settlement_date=expected_date,
            actual_settlement_date=expected_date + timedelta(days=2),  # 延迟 2 天
        )
        db_session.add(settlement)

    db_session.flush()
    return mock_merchant


@pytest.fixture
def mock_case(db_session, mock_merchant) -> RiskCase:
    """创建测试用风险案件"""
    case = RiskCase(
        merchant_id=mock_merchant.id,
        risk_score=65.0,
        risk_level="high",
        status="NEW",
        trigger_json=json.dumps({"reason": "退货率异常"}),
    )
    db_session.add(case)
    db_session.flush()
    return case


@pytest.fixture
def mock_analyzed_case(db_session, mock_merchant) -> RiskCase:
    """创建已分析的测试案件"""
    case = RiskCase(
        merchant_id=mock_merchant.id,
        risk_score=72.0,
        risk_level="high",
        status="ANALYZED",
        trigger_json=json.dumps({"reason": "退货率异常"}),
        agent_output_json=json.dumps({
            "case_summary": "商家退货率异常偏高",
            "risk_level": "high",
            "root_causes": ["退货率放大 2.1x"],
            "cash_gap_forecast": {"predicted_gap": 86000},
            "recommendations": [],
        }),
    )
    db_session.add(case)
    db_session.flush()
    return case


@pytest.fixture
def mock_approval(db_session, mock_case) -> ApprovalTask:
    """创建测试用审批任务"""
    approval = ApprovalTask(
        case_id=mock_case.id,
        approval_type="business_loan",
        assignee_role="admin",
        status="PENDING",
        payload_json=json.dumps({"action": "经营贷", "amount": 50000}),
        due_at=datetime.utcnow() + timedelta(hours=24),
    )
    db_session.add(approval)
    db_session.flush()
    return approval
