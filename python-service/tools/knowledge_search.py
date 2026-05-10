from typing import Dict, Any
from tools.base import Tool, ToolSchema, SchemaProperty, ToolMetadata
from core.vector_store import vector_store
from core.config import config


class KnowledgeSearchTool(Tool):
    """知识库检索工具"""
    
    def __init__(self):
        input_schema = ToolSchema(
            properties={
                "query": SchemaProperty(
                    type="string",
                    description="检索查询语句",
                    required=True
                ),
                "top_k": SchemaProperty(
                    type="number",
                    description="返回结果数量",
                    required=False,
                    default=3
                ),
                "similarity_threshold": SchemaProperty(
                    type="number",
                    description="相似度阈值",
                    required=False,
                    default=0.75
                ),
                "use_rerank": SchemaProperty(
                    type="boolean",
                    description="是否使用重排序",
                    required=False,
                    default=True
                )
            },
            type="object"
        )
        
        output_schema = ToolSchema(
            properties={
                "documents": SchemaProperty(
                    type="array",
                    description="检索到的文档列表",
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
            timeout_ms=10000,
            max_retries=2,
            permission="user",
            description="检索知识库中的相关文档"
        )
        
        super().__init__(
            name="knowledge_search",
            description="检索知识库中的相关文档",
            input_schema=input_schema,
            output_schema=output_schema,
            metadata=metadata
        )
        
        # 使用共享的向量存储管理器单例
        self.vector_store = vector_store
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行知识库检索"""
        query = parameters.get("query")
        top_k = int(parameters.get("top_k", 3))
        similarity_threshold = parameters.get("similarity_threshold", 0.75)
        use_rerank = parameters.get("use_rerank", True)
        
        # 执行检索
        docs = self.vector_store.search(
            query=query,
            k=top_k,
            similarity_threshold=similarity_threshold,
            use_rerank=use_rerank
        )
        
        # 格式化结果
        formatted_docs = []
        for doc in docs:
            formatted_docs.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return {
            "documents": formatted_docs,
            "count": len(formatted_docs)
        }
