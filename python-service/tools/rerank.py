from typing import Dict, Any, List, Optional
from tools.base import Tool, ToolSchema, SchemaProperty, ToolMetadata
from core.reranker import create_reranker, BaseReranker, RerankerResult
from langchain_core.documents import Document
from core.config import config


class RerankTool(Tool):
    """重排序工具 - 对检索结果进行语义重排序"""

    def __init__(self):
        input_schema = ToolSchema(
            properties={
                "query": SchemaProperty(
                    type="string",
                    description="查询文本",
                    required=True
                ),
                "documents": SchemaProperty(
                    type="array",
                    description="待重排序的文档列表",
                    required=True
                ),
                "top_k": SchemaProperty(
                    type="number",
                    description="返回前k个结果",
                    required=False,
                    default=3
                ),
                "reranker_type": SchemaProperty(
                    type="string",
                    description="重排序类型: bge, cohere, simple",
                    required=False,
                    default="bge"
                )
            },
            type="object"
        )

        output_schema = ToolSchema(
            properties={
                "reranked_documents": SchemaProperty(
                    type="array",
                    description="重排序后的文档列表",
                    required=True
                ),
                "scores": SchemaProperty(
                    type="array",
                    description="各文档的相关性分数",
                    required=True
                ),
                "original_indices": SchemaProperty(
                    type="array",
                    description="原始文档索引",
                    required=True
                ),
                "count": SchemaProperty(
                    type="number",
                    description="返回的文档数量",
                    required=True
                )
            },
            type="object"
        )

        metadata = ToolMetadata(
            timeout_ms=20000,
            max_retries=2,
            permission="user",
            description="对检索结果进行语义重排序以提高相关性"
        )

        super().__init__(
            name="rerank",
            description="对检索结果进行语义重排序",
            input_schema=input_schema,
            output_schema=output_schema,
            metadata=metadata
        )

        self.default_reranker_type = config.RERANKER_TYPE
        self.reranker = self._create_reranker(self.default_reranker_type)

    def _create_reranker(self, reranker_type: str) -> Optional[BaseReranker]:
        """创建Reranker实例"""
        try:
            return create_reranker(reranker_type)
        except Exception as e:
            config.logger.error(f"Failed to create reranker: {e}")
            return None

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行重排序"""
        query = parameters.get("query")
        documents = parameters.get("documents", [])
        top_k = int(parameters.get("top_k", 3))
        reranker_type = parameters.get("reranker_type", self.default_reranker_type)

        if not documents:
            return {
                "reranked_documents": [],
                "scores": [],
                "original_indices": [],
                "count": 0
            }

        docs = self._convert_to_documents(documents)

        reranker = self.reranker
        if reranker_type != self.default_reranker_type:
            reranker = self._create_reranker(reranker_type)

        if reranker is None:
            config.logger.warning("Reranker not available, returning original order")
            return self._format_results(docs[:top_k], list(range(len(docs[:top_k]))), list(range(len(docs[:top_k]))))

        try:
            results = reranker.rerank(query, docs, top_k=top_k)
            reranked_docs = [r.document for r in results]
            scores = [r.score for r in results]
            original_indices = [r.original_index for r in results]

            config.logger.info(f"Reranked {len(documents)} documents, returning top {len(reranked_docs)}")

            return self._format_results(reranked_docs, scores, original_indices)

        except Exception as e:
            config.logger.error(f"Rerank failed: {e}")
            return self._format_results(docs[:top_k], list(range(len(docs[:top_k]))), list(range(len(docs[:top_k]))))

    def _convert_to_documents(self, documents: List[Any]) -> List[Document]:
        """将输入转换为Document对象"""
        result = []
        for doc in documents:
            if isinstance(doc, Document):
                result.append(doc)
            elif isinstance(doc, dict):
                content = doc.get("content", doc.get("page_content", ""))
                metadata = doc.get("metadata", {})
                result.append(Document(page_content=content, metadata=metadata))
            elif isinstance(doc, str):
                result.append(Document(page_content=doc, metadata={}))
        return result

    def _format_results(self, documents: List[Document], scores: List[float], original_indices: List[int]) -> Dict[str, Any]:
        """格式化结果"""
        formatted_docs = []
        for doc in documents:
            if isinstance(doc, Document):
                formatted_docs.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
            else:
                formatted_docs.append(doc)

        return {
            "reranked_documents": formatted_docs,
            "scores": scores,
            "original_indices": original_indices,
            "count": len(formatted_docs)
        }