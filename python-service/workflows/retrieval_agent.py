from typing import Dict, Any, Optional, Generator, List
from tools.question_rewrite import QuestionRewriteTool
from tools.knowledge_search import KnowledgeSearchTool
from tools.rerank import RerankTool
from tools.citation import CitationIntegrator, CitationTracker
from core.vector_store import vector_store
from core.config import config
import logging
import json

logger = logging.getLogger(__name__)


class RetrievalResult:
    """检索结果封装"""

    def __init__(
        self,
        original_query: str,
        rewritten_query: Optional[str] = None,
        retrieved_documents: Optional[List] = None,
        reranked_documents: Optional[List] = None,
        scores: Optional[List[float]] = None,
        citations: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        self.original_query = original_query
        self.rewritten_query = rewritten_query or original_query
        self.retrieved_documents = retrieved_documents or []
        self.reranked_documents = reranked_documents or []
        self.scores = scores or []
        self.citations = citations or {}
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "rewritten_query": self.rewritten_query,
            "retrieved_documents": self.retrieved_documents,
            "reranked_documents": self.reranked_documents,
            "scores": self.scores,
            "citations": self.citations,
            "success": self.success,
            "error": self.error
        }


class RetrievalAgent:
    """Retrieval Agent - 负责检索全流程：query rewrite -> recall -> rerank -> citation integration"""

    def __init__(self):
        self.question_rewrite_tool = QuestionRewriteTool()
        self.knowledge_search_tool = KnowledgeSearchTool()
        self.rerank_tool = RerankTool()
        self.citation_integrator = CitationIntegrator()
        self.citation_tracker = CitationTracker()
        self.vector_store = vector_store

        self.config = {
            "top_k": 5,
            "initial_k": 10,
            "similarity_threshold": 0.7,
            "use_rerank": False,   # 默认关闭重排序，减少开销
            "use_rewrite": False,  # 默认关闭问题重写，减少LLM调用
            "max_citations": 5
        }

    def retrieve(
        self,
        query: str,
        conversation_context: str = "",
        use_rewrite: bool = False,
        use_rerank: bool = False,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        **kwargs
    ) -> RetrievalResult:
        """
        执行完整检索流程

        Args:
            query: 用户问题
            conversation_context: 对话上下文
            use_rewrite: 是否使用问题改写
            use_rerank: 是否使用重排序
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值

        Returns:
            RetrievalResult: 检索结果
        """
        logger.info(f"[RetrievalAgent] Starting retrieval for: {query[:50]}...")

        original_query = query
        rewritten_query = query

        try:
            if use_rewrite:
                rewrite_result = self.question_rewrite_tool.execute({
                    "question": query,
                    "conversation_context": conversation_context
                })
                rewritten_query = rewrite_result.get("rewritten_question", query)
                logger.info(f"[RetrievalAgent] Query rewritten: '{query}' -> '{rewritten_query}'")

            retrieved_docs = self._retrieve_documents(
                rewritten_query,
                k=top_k * 3 if use_rerank else top_k,
                similarity_threshold=similarity_threshold
            )

            if use_rerank and retrieved_docs:
                reranked_result = self._rerank_documents(
                    rewritten_query,
                    retrieved_docs,
                    top_k=top_k
                )
                reranked_docs = reranked_result.get("reranked_documents", retrieved_docs)
                scores = reranked_result.get("scores", [])
            else:
                reranked_docs = retrieved_docs[:top_k]
                scores = [0.5] * len(reranked_docs)

            citation_result = self.citation_integrator.integrate(
                answer="",
                documents=reranked_docs,
                scores=scores,
                query=query
            )

            result = RetrievalResult(
                original_query=original_query,
                rewritten_query=rewritten_query,
                retrieved_documents=retrieved_docs,
                reranked_documents=reranked_docs,
                scores=scores,
                citations=citation_result,
                success=True
            )

            logger.info(
                f"[RetrievalAgent] Retrieval completed: "
                f"original='{original_query[:30]}...', "
                f"rewritten='{rewritten_query[:30]}...', "
                f"retrieved={len(retrieved_docs)}, "
                f"reranked={len(reranked_docs)}"
            )

            return result

        except Exception as e:
            logger.error(f"[RetrievalAgent] Retrieval failed: {e}")
            return RetrievalResult(
                original_query=original_query,
                success=False,
                error=str(e)
            )

    def retrieve_stream(
        self,
        query: str,
        conversation_context: str = "",
        use_rewrite: bool = False,
        use_rerank: bool = False,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        流式执行检索流程

        Yields:
            JSON格式的事件流
        """
        logger.info(f"[RetrievalAgent] Stream retrieval for: {query[:50]}...")

        original_query = query
        rewritten_query = query

        try:
            yield json.dumps({
                "type": "retrieval_started",
                "query": original_query
            })

            if use_rewrite:
                yield json.dumps({
                    "type": "step",
                    "step_name": "question_rewrite",
                    "status": "started"
                })

                rewrite_result = self.question_rewrite_tool.execute({
                    "question": query,
                    "conversation_context": conversation_context
                })
                rewritten_query = rewrite_result.get("rewritten_question", query)

                yield json.dumps({
                    "type": "step",
                    "step_name": "question_rewrite",
                    "status": "completed",
                    "output": {
                        "original_query": original_query,
                        "rewritten_query": rewritten_query
                    }
                })

            yield json.dumps({
                "type": "step",
                "step_name": "knowledge_search",
                "status": "started"
            })

            retrieved_docs = self._retrieve_documents(
                rewritten_query,
                k=top_k * 3 if use_rerank else top_k,
                similarity_threshold=similarity_threshold
            )

            yield json.dumps({
                "type": "step",
                "step_name": "knowledge_search",
                "status": "completed",
                "output": {
                    "retrieved_count": len(retrieved_docs)
                }
            })

            if use_rerank and retrieved_docs:
                yield json.dumps({
                    "type": "step",
                    "step_name": "rerank",
                    "status": "started"
                })

                reranked_result = self._rerank_documents(
                    rewritten_query,
                    retrieved_docs,
                    top_k=top_k
                )
                reranked_docs = reranked_result.get("reranked_documents", retrieved_docs)
                scores = reranked_result.get("scores", [])

                yield json.dumps({
                    "type": "step",
                    "step_name": "rerank",
                    "status": "completed",
                    "output": {
                        "reranked_count": len(reranked_docs),
                        "top_scores": scores[:3] if scores else []
                    }
                })
            else:
                reranked_docs = retrieved_docs[:top_k]
                scores = [0.5] * len(reranked_docs)

            yield json.dumps({
                "type": "retrieval_completed",
                "output": {
                    "original_query": original_query,
                    "rewritten_query": rewritten_query,
                    "retrieved_count": len(retrieved_docs),
                    "final_count": len(reranked_docs),
                    "documents": reranked_docs,
                    "scores": scores
                }
            })

        except Exception as e:
            logger.error(f"[RetrievalAgent] Stream retrieval failed: {e}")
            yield json.dumps({
                "type": "error",
                "error": str(e)
            })

    def _retrieve_documents(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List:
        """执行文档检索"""
        try:
            if self.knowledge_search_tool.vector_store:
                result = self.knowledge_search_tool.execute({
                    "query": query,
                    "top_k": k,
                    "similarity_threshold": similarity_threshold,
                    "use_rerank": False
                })
                return result.get("documents", [])
        except Exception as e:
            logger.warning(f"[RetrievalAgent] knowledge_search tool failed: {e}")

        docs = self.vector_store.search(
            query=query,
            k=k,
            similarity_threshold=similarity_threshold,
            use_rerank=False
        )

        return [
            {
                "content": getattr(doc, "page_content", str(doc)),
                "metadata": getattr(doc, "metadata", {}),
                "score": getattr(doc, "score", 0.5)
            }
            for doc in docs
        ]

    def _rerank_documents(
        self,
        query: str,
        documents: List,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """执行文档重排序"""
        try:
            return self.rerank_tool.execute({
                "query": query,
                "documents": documents,
                "top_k": top_k
            })
        except Exception as e:
            logger.warning(f"[RetrievalAgent] rerank failed: {e}")
            return {
                "reranked_documents": documents[:top_k],
                "scores": [0.5] * min(top_k, len(documents)),
                "original_indices": list(range(min(top_k, len(documents)))),
                "count": min(top_k, len(documents))
            }

    def integrate_citations(
        self,
        answer: str,
        documents: List[Dict[str, Any]],
        scores: Optional[List[float]] = None,
        query: str = ""
    ) -> Dict[str, Any]:
        """整合引用到答案"""
        return self.citation_integrator.integrate(
            answer=answer,
            documents=documents,
            scores=scores,
            query=query
        )

    def track_retrieval(
        self,
        query: str,
        rewritten_query: str,
        retrieved_docs: List[Dict[str, Any]],
        reranked_docs: List[Dict[str, Any]],
        final_answer: str
    ) -> Dict[str, Any]:
        """追踪检索链路"""
        return self.citation_tracker.track(
            query=query,
            rewritten_query=rewritten_query,
            retrieved_docs=retrieved_docs,
            reranked_docs=reranked_docs,
            final_answer=final_answer
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取检索统计信息"""
        return {
            "config": self.config,
            "citation_stats": self.citation_tracker.get_citation_stats()
        }


retrieval_agent = RetrievalAgent()