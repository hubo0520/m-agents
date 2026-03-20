"""
向量存储封装 — 基于 ChromaDB 的语义检索

支持案件数据的向量化索引和语义检索，用于 RAG 对话系统。
ChromaDB 不可用时优雅降级。
"""
import json
import os
import time
from typing import Optional, List, Dict, Any
from loguru import logger

# ChromaDB 可用性标记
_chromadb_available = False
_chromadb_init_error = None
_client = None
_embedding_fn = None

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _chromadb_available = True
    logger.info("✅ chromadb 模块加载成功 | version={}", getattr(chromadb, '__version__', 'unknown'))
except ImportError as e:
    _chromadb_init_error = str(e)
    logger.warning("⚠️ chromadb 未安装，向量检索功能不可用（降级为 agent_output_json 模式）| error={}", e)
except Exception as e:
    _chromadb_init_error = str(e)
    logger.warning("⚠️ chromadb 加载失败（非 ImportError），向量检索功能不可用 | error_type={} | error={}", type(e).__name__, e)


# ─────────── 自定义嵌入函数（通过 OpenAI 兼容接口调用 text-embedding-v4） ───────────

def _get_embedding_function():
    """
    获取基于 OpenAI 兼容接口的嵌入函数（懒加载单例）。
    使用 settings.EMBEDDING_MODEL（默认 text-embedding-v4）。
    如果 OPENAI_API_KEY 未配置，返回 None，则回退到 ChromaDB 默认嵌入。
    """
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn

    if not _chromadb_available:
        return None

    try:
        from app.core.config import settings

        if not settings.OPENAI_API_KEY or not settings.EMBEDDING_MODEL:
            logger.info("嵌入模型未配置，使用 ChromaDB 默认嵌入")
            return None

        from chromadb import EmbeddingFunction, Documents, Embeddings

        class OpenAICompatibleEmbedding(EmbeddingFunction):
            """通过 OpenAI 兼容接口调用阿里云 text-embedding-v4"""

            def __init__(self):
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                )
                self._model = settings.EMBEDDING_MODEL
                self._batch_size = getattr(settings, "EMBEDDING_BATCH_SIZE", 6)
                logger.info(
                    "嵌入模型初始化成功 | model={} | base_url={}",
                    self._model, settings.OPENAI_BASE_URL,
                )

            def __call__(self, input: Documents) -> Embeddings:
                """ChromaDB 调用入口：接收文本列表，返回嵌入向量列表"""
                all_embeddings = []
                batch_size = self._batch_size
                # 分批调用，避免单次请求过大
                i = 0
                while i < len(input):
                    batch = input[i : i + batch_size]
                    try:
                        t0 = time.time()
                        response = self._client.embeddings.create(
                            model=self._model,
                            input=batch,
                        )
                        elapsed_ms = int((time.time() - t0) * 1000)
                        batch_embeddings = [item.embedding for item in response.data]
                        all_embeddings.extend(batch_embeddings)
                        logger.debug(
                            "嵌入批次完成 | batch={}-{} | 耗时={}ms",
                            i, i + len(batch), elapsed_ms,
                        )
                        i += batch_size
                    except Exception as e:
                        error_msg = str(e)
                        if "batch size" in error_msg.lower() or "InvalidParameter" in error_msg:
                            # API 拒绝当前 batch size，自动减半重试
                            new_batch_size = max(1, batch_size // 2)
                            logger.warning(
                                "嵌入 batch size {} 过大，自动降级为 {} 重试 | error={}",
                                batch_size, new_batch_size, e,
                            )
                            batch_size = new_batch_size
                            # 不递增 i，用更小的 batch_size 重试当前位置
                            continue
                        logger.error("嵌入调用失败 (batch {}-{}): {}", i, i + len(batch), e)
                        raise
                return all_embeddings

        _embedding_fn = OpenAICompatibleEmbedding()
        return _embedding_fn

    except Exception as e:
        logger.warning("自定义嵌入函数初始化失败，回退到 ChromaDB 默认嵌入: {}", e)
        return None


def _get_client():
    """获取 ChromaDB 持久化客户端（懒加载单例）"""
    global _client
    if _client is not None:
        return _client

    if not _chromadb_available:
        return None

    try:
        from app.core.config import settings
        persist_dir = getattr(settings, "VECTOR_STORE_DIR", None)
        if not persist_dir:
            # 默认存储到 backend/vector_data/
            persist_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "vector_data",
            )

        os.makedirs(persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(path=persist_dir)
        logger.info("ChromaDB 初始化成功 | persist_dir={}", persist_dir)
        return _client
    except Exception as e:
        logger.warning("ChromaDB 初始化失败: {}", e)
        return None


def is_vector_store_available() -> bool:
    """检查向量存储是否可用"""
    return _get_client() is not None


def _get_collection(case_id: int):
    """获取或创建案件对应的 collection"""
    client = _get_client()
    if client is None:
        return None

    collection_name = f"case_{case_id}"
    try:
        # 使用自定义嵌入函数（text-embedding-v4），若不可用则用 ChromaDB 默认
        ef = _get_embedding_function()
        kwargs = {
            "name": collection_name,
            "metadata": {"hnsw:space": "cosine"},
        }
        if ef is not None:
            kwargs["embedding_function"] = ef
        return client.get_or_create_collection(**kwargs)
    except Exception as e:
        logger.warning("获取 ChromaDB collection 失败 (case_id={}): {}", case_id, e)
        return None


def index_case_data(case_id: int, db=None) -> bool:
    """
    将案件分析数据向量化并索引到 ChromaDB。

    数据源：
    1. Agent 分析输出（diagnosis、recommendations、summary）
    2. 证据链（evidence_items）
    3. 商家基础信息

    Args:
        case_id: 案件 ID
        db: 数据库会话（可选，不传则自动创建）

    Returns:
        是否索引成功
    """
    collection = _get_collection(case_id)
    if collection is None:
        return False

    close_db = False
    if db is None:
        from app.core.database import SessionLocal
        db = SessionLocal()
        close_db = True

    try:
        from app.models.models import RiskCase, EvidenceItem, Merchant

        case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
        if not case:
            return False

        # 先清除旧数据
        try:
            existing = collection.get()
            if existing and existing.get("ids"):
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

        documents = []
        metadatas = []
        ids = []
        doc_counter = 0

        # 1. Agent 分析输出
        if case.agent_output_json:
            try:
                agent_output = json.loads(case.agent_output_json)

                # 案件摘要
                summary = agent_output.get("case_summary", "")
                if summary:
                    doc_counter += 1
                    documents.append(summary)
                    metadatas.append({"source": "summary_agent", "type": "case_summary", "case_id": str(case_id)})
                    ids.append(f"case_{case_id}_summary_{doc_counter}")

                # 根因分析
                for i, rc in enumerate(agent_output.get("root_causes", [])):
                    doc_counter += 1
                    rc_text = f"根因: {rc.get('label', '')} — {rc.get('explanation', '')} (置信度: {rc.get('confidence', 0):.0%})"
                    documents.append(rc_text)
                    ev_ids = rc.get("evidence_ids", [])
                    metadatas.append({
                        "source": "diagnosis_agent",
                        "type": "root_cause",
                        "evidence_ids": ",".join(ev_ids) if ev_ids else "",
                        "case_id": str(case_id),
                    })
                    ids.append(f"case_{case_id}_rc_{doc_counter}")

                # 动作建议
                for i, rec in enumerate(agent_output.get("recommendations", [])):
                    doc_counter += 1
                    rec_text = f"建议[{rec.get('action_type', '')}]: {rec.get('title', '')} — {rec.get('why', '')}"
                    documents.append(rec_text)
                    ev_ids = rec.get("evidence_ids", [])
                    metadatas.append({
                        "source": "recommendation_agent",
                        "type": "recommendation",
                        "action_type": rec.get("action_type", ""),
                        "evidence_ids": ",".join(ev_ids) if ev_ids else "",
                        "case_id": str(case_id),
                    })
                    ids.append(f"case_{case_id}_rec_{doc_counter}")

                # 现金流预测
                forecast = agent_output.get("cash_gap_forecast", {})
                if forecast:
                    gap = forecast.get("gap_amount", forecast.get("predicted_gap", 0))
                    if gap:
                        doc_counter += 1
                        forecast_text = f"现金流预测: 预计{forecast.get('horizon_days', 14)}日内缺口¥{gap:,.0f}"
                        documents.append(forecast_text)
                        metadatas.append({"source": "forecast_agent", "type": "forecast", "case_id": str(case_id)})
                        ids.append(f"case_{case_id}_forecast_{doc_counter}")

            except Exception as e:
                logger.warning("解析 agent_output_json 失败: {}", e)

        # 2. 证据链
        evidence_items = db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
        for i, ev in enumerate(evidence_items):
            doc_counter += 1
            ev_text = f"[{ev.evidence_type}] {ev.summary or '无摘要'}"
            documents.append(ev_text)
            metadatas.append({
                "source": "evidence_agent",
                "type": "evidence",
                "evidence_id": f"EV-{101 + i}",
                "evidence_type": ev.evidence_type or "",
                "case_id": str(case_id),
            })
            ids.append(f"case_{case_id}_ev_{doc_counter}")

        # 3. 商家信息
        merchant = case.merchant
        if merchant:
            doc_counter += 1
            merchant_text = (
                f"商家信息: {merchant.name}, 行业: {merchant.industry}, "
                f"店铺等级: {merchant.store_level}, 结算周期: {merchant.settlement_cycle_days}天"
            )
            documents.append(merchant_text)
            metadatas.append({"source": "merchant_profile", "type": "merchant", "case_id": str(case_id)})
            ids.append(f"case_{case_id}_merchant_{doc_counter}")

        if not documents:
            return False

        # 批量写入
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info("案件 {} 向量索引完成: {} 条文档", case_id, len(documents))
        return True

    except Exception as e:
        logger.error("案件 {} 向量索引失败: {}", case_id, e)
        return False
    finally:
        if close_db:
            db.close()


def search_case_context(
    case_id: int,
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    对指定案件执行语义检索。

    Args:
        case_id: 案件 ID
        query: 用户查询文本
        top_k: 返回的最相关文档数

    Returns:
        检索结果列表，每个元素包含 document, metadata, distance
    """
    collection = _get_collection(case_id)
    if collection is None:
        return []

    try:
        # 检查 collection 是否有数据
        count = collection.count()
        if count == 0:
            logger.debug("RAG 检索跳过 | case_id={} | 原因: collection 为空（尚未索引）", case_id)
            return []

        t0 = time.time()
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        passages = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc in enumerate(docs):
                passages.append({
                    "document": doc,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": distances[i] if i < len(distances) else 0,
                })

        query_preview = query[:50] + "..." if len(query) > 50 else query
        if passages:
            top_distance = passages[0].get("distance", 0)
            logger.info(
                "✅ RAG 语义检索命中 | case_id={} | query='{}' | 命中={}条 | top_distance={:.4f} | 耗时={}ms",
                case_id, query_preview, len(passages), top_distance, elapsed_ms,
            )
        else:
            logger.info(
                "⚠️ RAG 语义检索无结果 | case_id={} | query='{}' | collection_count={} | 耗时={}ms",
                case_id, query_preview, count, elapsed_ms,
            )

        return passages
    except Exception as e:
        logger.warning("案件 {} 语义检索失败: {}", case_id, e)
        return []


def delete_case_index(case_id: int) -> bool:
    """删除案件的向量索引"""
    client = _get_client()
    if client is None:
        return False

    try:
        collection_name = f"case_{case_id}"
        client.delete_collection(name=collection_name)
        logger.info("案件 {} 向量索引已删除", case_id)
        return True
    except Exception:
        return False
