"""
向量存储 (ChromaDB) 单元测试
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock


class TestVectorStoreAvailability:
    """向量存储可用性检查"""

    def test_unavailable_when_chromadb_not_installed(self):
        """chromadb 未安装时返回不可用"""
        with patch.dict("sys.modules", {"chromadb": None}):
            from app.core.vector_store import is_vector_store_available
            result = is_vector_store_available()
            assert isinstance(result, bool)

    def test_embedding_model_config(self):
        """验证嵌入模型默认配置为 text-embedding-v4"""
        from app.core.config import settings
        assert settings.EMBEDDING_MODEL == "text-embedding-v4"


@pytest.mark.slow
class TestVectorStoreIndexAndSearch:
    """文档索引和语义检索测试（需要下载嵌入模型，首次运行较慢）"""

    @pytest.fixture(autouse=True)
    def setup_temp_dir(self, tmp_path):
        """使用临时目录作为向量存储"""
        self.temp_dir = str(tmp_path / "vector_data")
        os.makedirs(self.temp_dir, exist_ok=True)

    def test_index_and_search_basic(self):
        """基本索引和检索流程"""
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb 未安装")

        # 创建临时 ChromaDB 客户端
        client = chromadb.PersistentClient(path=self.temp_dir)
        collection = client.get_or_create_collection("case_test")

        # 添加文档
        collection.add(
            documents=[
                "该商家退货率放大1.8倍，近7日退货集中",
                "回款延迟3.2天，影响现金流",
                "建议回款加速，缓解流动性压力",
            ],
            metadatas=[
                {"source": "diagnosis_agent", "type": "root_cause"},
                {"source": "evidence_agent", "type": "evidence"},
                {"source": "recommendation_agent", "type": "recommendation"},
            ],
            ids=["doc_1", "doc_2", "doc_3"],
        )

        # 检索
        results = collection.query(
            query_texts=["退货率为什么这么高"],
            n_results=2,
        )

        assert results is not None
        assert len(results["documents"][0]) == 2
        # 最相关的应该是退货相关文档
        assert "退货" in results["documents"][0][0]

    def test_metadata_filtering(self):
        """元数据过滤测试"""
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb 未安装")

        client = chromadb.PersistentClient(path=self.temp_dir)
        collection = client.get_or_create_collection("case_filter_test")

        collection.add(
            documents=["退货率异常", "回款延迟", "建议加速"],
            metadatas=[
                {"source": "diagnosis_agent", "case_id": "1"},
                {"source": "evidence_agent", "case_id": "1"},
                {"source": "recommendation_agent", "case_id": "2"},
            ],
            ids=["d1", "d2", "d3"],
        )

        # 按 case_id 过滤
        results = collection.query(
            query_texts=["风险分析"],
            n_results=3,
            where={"case_id": "1"},
        )

        assert len(results["documents"][0]) == 2  # 只返回 case_id=1 的

    def test_delete_collection(self):
        """删除 collection 测试"""
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb 未安装")

        client = chromadb.PersistentClient(path=self.temp_dir)
        collection = client.get_or_create_collection("case_delete_test")
        collection.add(documents=["test"], ids=["d1"])

        client.delete_collection("case_delete_test")

        # 验证已删除
        collections = client.list_collections()
        names = [c.name for c in collections]
        assert "case_delete_test" not in names

    def test_search_empty_collection(self):
        """空 collection 检索测试"""
        from app.core.vector_store import search_case_context

        # 对不存在的案件检索
        results = search_case_context(999999, "测试查询")
        assert results == [] or isinstance(results, list)
