"""风险案件 API 路由"""
import json
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.database import get_db
from app.models.models import (
    RiskCase, Merchant, EvidenceItem, Recommendation, Review, AuditLog,
    Order, Return, Settlement,
)
from app.schemas.schemas import (
    RiskCaseListItem, PaginatedResponse, CaseDetailResponse,
    EvidenceItemResponse, AuditLogResponse, ReviewRequest,
    MerchantInfo, TrendDataPoint,
)
from app.engine.metrics import get_all_metrics
from app.engine.cashflow import forecast_cash_gap
from app.agents.orchestrator import analyze as agent_analyze
from app.services.approval import review_case, transition_status, write_audit_log
from app.services.export import export_case_markdown, export_case_json
from app.services.task_generator import generate_tasks_for_case
from app.models.models import FinancingApplication, Claim, ManualReview

router = APIRouter()


# ─────── GET /api/risk-cases ─────────
@router.get("/risk-cases")
def list_risk_cases(
    risk_level: str = None,
    status: str = None,
    merchant_name: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = None,
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    """获取案件列表"""
    query = db.query(RiskCase).join(Merchant, RiskCase.merchant_id == Merchant.id)

    # 筛选
    if risk_level:
        query = query.filter(RiskCase.risk_level == risk_level)
    if status:
        query = query.filter(RiskCase.status == status)
    if merchant_name:
        query = query.filter(Merchant.name.contains(merchant_name))

    total = query.count()

    # 排序
    if sort_by == "predicted_gap":
        query = query.order_by(RiskCase.risk_score.desc())  # 近似用 risk_score 排序
    elif sort_by == "risk_level":
        # 自定义排序: high > medium > low
        from sqlalchemy import case as sql_case
        query = query.order_by(
            sql_case(
                (RiskCase.risk_level == "high", 1),
                (RiskCase.risk_level == "medium", 2),
                else_=3,
            )
        )
    else:
        if sort_order == "asc":
            query = query.order_by(RiskCase.updated_at.asc())
        else:
            query = query.order_by(RiskCase.updated_at.desc())

    # 分页
    cases = query.offset((page - 1) * page_size).limit(page_size).all()

    # 构造响应
    items = []
    for case in cases:
        merchant = case.merchant
        rec_count = db.query(func.count(Recommendation.id)).filter(
            Recommendation.case_id == case.id
        ).scalar()

        # 从 agent_output 或 trigger 中获取指标
        metrics_data = {}
        if case.agent_output_json:
            try:
                agent_out = json.loads(case.agent_output_json)
                gap = agent_out.get("cash_gap_forecast", {}).get("predicted_gap", 0)
                metrics_data["predicted_gap"] = gap
            except Exception:
                pass

        # 按需计算指标
        try:
            metrics = get_all_metrics(db, merchant.id)
        except Exception:
            metrics = {}

        items.append(RiskCaseListItem(
            id=case.id,
            merchant_id=merchant.id,
            merchant_name=merchant.name,
            industry=merchant.industry,
            risk_score=case.risk_score,
            risk_level=case.risk_level,
            status=case.status,
            return_rate_7d=metrics.get("return_rate_7d"),
            baseline_return_rate=metrics.get("baseline_return_rate"),
            return_amplification=metrics.get("return_amplification"),
            predicted_gap=metrics_data.get("predicted_gap"),
            recommendation_count=rec_count,
            created_at=str(case.created_at) if case.created_at else None,
            updated_at=str(case.updated_at) if case.updated_at else None,
        ))

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


# ─────── GET /api/risk-cases/{case_id} ─────────
@router.get("/risk-cases/{case_id}")
def get_risk_case_detail(case_id: int, db: Session = Depends(get_db)):
    """获取案件详情"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    merchant = case.merchant
    evidence = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
    recommendations = db.query(Recommendation).filter(Recommendation.case_id == case_id).all()
    reviews = db.query(Review).filter(Review.case_id == case_id).all()
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "risk_case", AuditLog.entity_id == case_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    # 指标
    try:
        metrics = get_all_metrics(db, merchant.id)
    except Exception:
        metrics = {}

    # 预测
    try:
        forecast = forecast_cash_gap(db, merchant.id, 14)
    except Exception:
        forecast = {}

    # 趋势数据 (近30天)
    trend_data = _get_trend_data(db, merchant.id, 30)

    # Agent 输出
    agent_output = json.loads(case.agent_output_json) if case.agent_output_json else None
    trigger = json.loads(case.trigger_json) if case.trigger_json else None

    # 推荐列表
    rec_list = []
    for rec in recommendations:
        content = json.loads(rec.content_json) if rec.content_json else {}
        content["id"] = rec.id
        content["db_requires_manual_review"] = bool(rec.requires_manual_review)
        rec_list.append(content)

    # 审批列表
    review_list = []
    for rv in reviews:
        review_list.append({
            "id": rv.id,
            "reviewer_id": rv.reviewer_id,
            "decision": rv.decision,
            "comment": rv.comment,
            "final_action_json": json.loads(rv.final_action_json) if rv.final_action_json else None,
            "created_at": str(rv.created_at) if rv.created_at else None,
        })

    return CaseDetailResponse(
        id=case.id,
        merchant=MerchantInfo(
            id=merchant.id,
            name=merchant.name,
            industry=merchant.industry,
            settlement_cycle_days=merchant.settlement_cycle_days,
            store_level=merchant.store_level,
        ),
        risk_score=case.risk_score,
        risk_level=case.risk_level,
        status=case.status,
        trigger_json=trigger,
        agent_output=agent_output,
        metrics=metrics,
        trend_data=trend_data,
        forecast=forecast,
        evidence=[EvidenceItemResponse.model_validate(ev) for ev in evidence],
        recommendations=rec_list,
        reviews=review_list,
        audit_logs=[
            AuditLogResponse(
                id=al.id,
                entity_type=al.entity_type,
                entity_id=al.entity_id,
                actor=al.actor,
                action=al.action,
                old_value=al.old_value,
                new_value=al.new_value,
                created_at=str(al.created_at) if al.created_at else None,
            )
            for al in audit_logs
        ],
        created_at=str(case.created_at) if case.created_at else None,
        updated_at=str(case.updated_at) if case.updated_at else None,
    )


# ─────── POST /api/risk-cases/{case_id}/analyze ─────────
@router.post("/risk-cases/{case_id}/analyze")
def analyze_case(
    case_id: int,
    mode: str = Query("v3", description="分析模式: v1（旧模式）或 v3（多Agent工作流）"),
    db: Session = Depends(get_db),
):
    """触发重新分析（支持 V1/V2 模式和 V3 工作流模式）"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    try:
        if mode == "v3":
            from app.agents.orchestrator import analyze_v3
            result = analyze_v3(db, case_id)
        else:
            result = agent_analyze(db, case_id)
        db.commit()
        return {
            "status": "success",
            "mode": mode,
            "agent_output": result,
            "workflow_run_id": result.get("workflow_run_id") if isinstance(result, dict) else None,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


# ─────── GET /api/risk-cases/{case_id}/evidence ─────────
@router.get("/risk-cases/{case_id}/evidence")
def get_evidence(case_id: int, db: Session = Depends(get_db)):
    """获取证据列表"""
    evidence = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
    return [EvidenceItemResponse.model_validate(ev) for ev in evidence]


# ─────── POST /api/risk-cases/{case_id}/review ─────────
@router.post("/risk-cases/{case_id}/review")
def review(case_id: int, req: ReviewRequest, db: Session = Depends(get_db)):
    """审批案件"""
    try:
        rv = review_case(
            db=db,
            case_id=case_id,
            decision=req.decision,
            comment=req.comment,
            final_actions=req.final_actions,
            reviewer_id=req.reviewer_id,
        )
        db.commit()
        return {
            "status": "success",
            "review_id": rv.id,
            "decision": rv.decision,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"审批失败: {str(e)}")


# ─────── GET /api/risk-cases/{case_id}/export ─────────
@router.get("/risk-cases/{case_id}/export")
def export_case(
    case_id: int,
    format: str = Query("markdown", pattern="^(markdown|json)$"),
    db: Session = Depends(get_db),
):
    """导出案件"""
    try:
        if format == "markdown":
            content = export_case_markdown(db, case_id)
            return PlainTextResponse(content=content, media_type="text/markdown")
        else:
            data = export_case_json(db, case_id)
            return JSONResponse(content=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─────── 辅助函数 ─────────

def _get_trend_data(db: Session, merchant_id: int, days: int) -> list:
    """获取近 N 天的趋势数据"""
    result = []
    today = date.today()

    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        d_start = datetime.combine(d, datetime.min.time())
        d_end = d_start + timedelta(days=1)

        # 当日订单金额
        order_amount = (
            db.query(func.sum(Order.order_amount))
            .filter(
                Order.merchant_id == merchant_id,
                Order.order_time >= d_start,
                Order.order_time < d_end,
            )
            .scalar()
        ) or 0

        # 当日订单数
        order_count = (
            db.query(func.count(Order.id))
            .filter(
                Order.merchant_id == merchant_id,
                Order.order_time >= d_start,
                Order.order_time < d_end,
            )
            .scalar()
        ) or 0

        # 当日退货数
        return_count = (
            db.query(func.count(func.distinct(Return.order_id)))
            .join(Order, Return.order_id == Order.id)
            .filter(
                Order.merchant_id == merchant_id,
                Return.return_time >= d_start,
                Return.return_time < d_end,
            )
            .scalar()
        ) or 0

        # 当日退款金额
        refund_amount = (
            db.query(func.sum(Return.refund_amount))
            .join(Order, Return.order_id == Order.id)
            .filter(
                Order.merchant_id == merchant_id,
                Return.return_time >= d_start,
                Return.return_time < d_end,
            )
            .scalar()
        ) or 0

        # 当日回款金额
        settlement_amount = (
            db.query(func.sum(Settlement.amount))
            .filter(
                Settlement.merchant_id == merchant_id,
                Settlement.actual_settlement_date == d,
            )
            .scalar()
        ) or 0

        return_rate = return_count / order_count if order_count > 0 else 0

        result.append(TrendDataPoint(
            date=str(d),
            order_amount=round(float(order_amount), 2),
            return_rate=round(return_rate, 4),
            refund_amount=round(float(refund_amount), 2),
            settlement_amount=round(float(settlement_amount), 2),
        ))

    return result


# ─────── V2: POST /api/risk-cases/{case_id}/generate-financing-application ─────────
@router.post("/risk-cases/{case_id}/generate-financing-application")
def generate_financing(
    case_id: int,
    req: dict = None,
    db: Session = Depends(get_db),
):
    """手动触发融资申请生成"""
    from app.schemas.schemas import FinancingApplicationCreate
    from app.engine.rules import check_financing_eligibility
    from app.engine.cashflow import forecast_cash_gap as fc_gap

    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    merchant = case.merchant

    # 获取预测缺口
    try:
        forecast = fc_gap(db, merchant.id, 14)
        predicted_gap = forecast.get("predicted_gap", 0)
    except Exception:
        predicted_gap = 0

    amount = (req or {}).get("amount_requested", predicted_gap)

    # 直接生成（手动触发忽略自动资格判断）
    application = FinancingApplication(
        merchant_id=merchant.id,
        case_id=case.id,
        recommendation_id=None,
        amount_requested=amount,
        loan_purpose=(req or {}).get("reason", f"手动触发 - 覆盖现金缺口 ¥{predicted_gap:,.2f}"),
        approval_status="DRAFT",
    )
    db.add(application)
    db.commit()

    return {
        "status": "success",
        "application_id": application.id,
        "message": "Financing application generated successfully.",
    }


# ─────── V2: POST /api/risk-cases/{case_id}/generate-claim-application ─────────
@router.post("/risk-cases/{case_id}/generate-claim-application")
def generate_claim(
    case_id: int,
    req: dict = None,
    db: Session = Depends(get_db),
):
    """手动触发理赔申请生成"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    merchant = case.merchant
    body = req or {}

    claim = Claim(
        merchant_id=merchant.id,
        case_id=case.id,
        recommendation_id=None,
        policy_id=None,
        claim_amount=body.get("claim_amount", 0),
        claim_reason=body.get("claim_reason", "手动触发"),
        claim_status="DRAFT",
    )
    db.add(claim)
    db.commit()

    return {
        "status": "success",
        "claim_id": claim.id,
        "message": "Claim application generated successfully.",
    }


# ─────── V2: POST /api/risk-cases/{case_id}/generate-manual-review ─────────
@router.post("/risk-cases/{case_id}/generate-manual-review")
def generate_manual_review(
    case_id: int,
    req: dict = None,
    db: Session = Depends(get_db),
):
    """手动触发复核任务生成"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    merchant = case.merchant
    body = req or {}

    review = ManualReview(
        merchant_id=merchant.id,
        case_id=case.id,
        recommendation_id=None,
        task_type=body.get("task_type", "return_fraud"),
        review_reason="手动触发复核任务",
        evidence_ids_json=json.dumps(body.get("evidence_ids", [])),
        assigned_to="unassigned",
        status="PENDING",
    )
    db.add(review)
    db.commit()

    return {
        "status": "success",
        "review_id": review.id,
        "message": "Manual review task generated successfully.",
    }


# ─────── V2: GET /api/risk-cases/{case_id}/tasks ─────────
@router.get("/risk-cases/{case_id}/tasks")
def get_case_tasks(case_id: int, db: Session = Depends(get_db)):
    """查询案件关联的所有执行任务"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    merchant = case.merchant
    tasks = []

    # 融资申请
    financings = db.query(FinancingApplication).filter(FinancingApplication.case_id == case_id).all()
    for fa in financings:
        tasks.append({
            "task_id": fa.id,
            "task_type": "financing",
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "case_id": case_id,
            "status": fa.approval_status,
            "amount": fa.amount_requested,
            "assigned_to": None,
            "created_at": str(fa.created_at) if fa.created_at else None,
        })

    # 理赔申请
    claims = db.query(Claim).filter(Claim.case_id == case_id).all()
    for cl in claims:
        tasks.append({
            "task_id": cl.id,
            "task_type": "claim",
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "case_id": case_id,
            "status": cl.claim_status,
            "amount": cl.claim_amount,
            "assigned_to": None,
            "created_at": str(cl.created_at) if cl.created_at else None,
        })

    # 复核任务
    reviews = db.query(ManualReview).filter(ManualReview.case_id == case_id).all()
    for mr in reviews:
        tasks.append({
            "task_id": mr.id,
            "task_type": "manual_review",
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "case_id": case_id,
            "status": mr.status,
            "amount": None,
            "assigned_to": mr.assigned_to,
            "created_at": str(mr.created_at) if mr.created_at else None,
        })

    return tasks