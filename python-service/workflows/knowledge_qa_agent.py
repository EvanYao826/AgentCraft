from typing import Dict, Any, Optional, Generator
from agent.orchestrator import Orchestrator
from agent.state import AgentState
from agent.events import EventBus, event_bus
from workflows.retrieval_agent import RetrievalAgent
from core.llm import LLMService
import logging
import json

logger = logging.getLogger(__name__)


class KnowledgeQAAgent:
    """知识问答Agent - 专门处理知识库问答的工作流"""

    def __init__(self):
        self.orchestrator = Orchestrator()
        self.event_bus = event_bus
        self.retrieval_agent = RetrievalAgent()
        self.llm_service = LLMService()

    def ask(self, question: str, conversation_id: Optional[str] = None,
            user_id: Optional[str] = None, context: str = "",
            **kwargs) -> Dict[str, Any]:
        """
        处理知识问答 - 使用RetrievalAgent进行检索

        Args:
            question: 用户问题
            conversation_id: 会话ID
            user_id: 用户ID
            context: 对话上下文
            **kwargs: 其他参数

        Returns:
            包含answer和sources的字典
        """
        logger.info(f"[KnowledgeQAAgent] Processing question: {question[:50]}...")

        try:
            # 使用RetrievalAgent进行检索
            retrieval_result = self.retrieval_agent.retrieve(
                question,
                conversation_context=context,
                use_rewrite=True,
                use_rerank=True,
                top_k=5,
                similarity_threshold=0.7
            )

            logger.info(
                f"[KnowledgeQAAgent] Retrieval completed: "
                f"original={retrieval_result.original_query[:30]}... "
                f"rewritten={retrieval_result.rewritten_query[:30]}... "
                f"docs={len(retrieval_result.reranked_documents)}"
            )

            # 获取检索到的文档内容
            docs_for_llm = []
            for doc in retrieval_result.reranked_documents:
                if isinstance(doc, dict) and 'content' in doc:
                    docs_for_llm.append(doc['content'])
                elif hasattr(doc, 'page_content'):
                    docs_for_llm.append(doc.page_content)

            # 使用LLM生成最终回答
            answer = self.llm_service.get_answer(
                question=question,
                context_docs=docs_for_llm,
                conversation_context=context
            )

            # 整合引用
            citation_result = self.retrieval_agent.integrate_citations(
                answer=answer,
                documents=retrieval_result.reranked_documents,
                scores=retrieval_result.scores,
                query=question
            )

            # 构建最终响应
            return {
                "answer": answer,
                "sources": citation_result.get('sources', []),
                "has_sources": citation_result.get('has_sources', False),
                "task_type": "knowledge_qa",
                "retrieval_info": {
                    "original_query": retrieval_result.original_query,
                    "rewritten_query": retrieval_result.rewritten_query,
                    "doc_count": len(retrieval_result.reranked_documents),
                    "citation_count": citation_result.get('citation_count', 0)
                }
            }

        except Exception as e:
            logger.error(f"[KnowledgeQAAgent] Retrieval-based QA failed: {e}", exc_info=True)
            logger.info("[KnowledgeQAAgent] Falling back to orchestrator...")

            # 回退到原有的Orchestrator方式
            return self._ask_with_orchestrator(
                question, conversation_id, user_id, context, **kwargs
            )

    def ask_stream(self, question: str, conversation_id: Optional[str] = None,
                   user_id: Optional[str] = None, context: str = "",
                   **kwargs) -> Generator[str, None, None]:
        """
        流式处理知识问答 - 使用RetrievalAgent进行检索

        Args:
            question: 用户问题
            conversation_id: 会话ID
            user_id: 用户ID
            context: 对话上下文
            **kwargs: 其他参数

        Yields:
            JSON格式的事件流
        """
        logger.info(f"[KnowledgeQAAgent] Stream processing question: {question[:50]}...")

        try:
            # 使用RetrievalAgent进行流式检索
            yield from self.retrieval_agent.retrieve_stream(
                question,
                conversation_context=context,
                use_rewrite=True,
                use_rerank=True,
                top_k=5,
                similarity_threshold=0.7
            )

        except Exception as e:
            logger.error(f"[KnowledgeQAAgent] Stream QA failed: {e}", exc_info=True)
            logger.info("[KnowledgeQAAgent] Falling back to orchestrator stream...")

            # 回退到原有的Orchestrator方式
            yield from self._ask_stream_with_orchestrator(
                question, conversation_id, user_id, context, **kwargs
            )

    def _ask_with_orchestrator(self, question: str, conversation_id: Optional[str] = None,
                               user_id: Optional[str] = None, context: str = "",
                               **kwargs) -> Dict[str, Any]:
        """
        使用原有的Orchestrator方式进行知识问答（回退方案）
        """
        logger.info(f"[KnowledgeQAAgent] Using orchestrator fallback...")
        result = self.orchestrator.run(
            input_text=question,
            conversation_id=conversation_id,
            user_id=user_id,
            context=context,
            goal=f"回答知识问题: {question[:50]}...",
            **kwargs
        )
        return result

    def _ask_stream_with_orchestrator(self, question: str, conversation_id: Optional[str] = None,
                                      user_id: Optional[str] = None, context: str = "",
                                      **kwargs) -> Generator[str, None, None]:
        """
        使用原有的Orchestrator方式进行流式知识问答（回退方案）
        """
        logger.info(f"[KnowledgeQAAgent] Using orchestrator stream fallback...")
        for event in self.orchestrator.run_stream(
            input_text=question,
            conversation_id=conversation_id,
            user_id=user_id,
            context=context,
            goal=f"流式回答知识问题: {question[:50]}...",
            **kwargs
        ):
            yield event

    def register_callback(self, event_type: str, callback):
        """注册事件回调"""
        self.event_bus.subscribe(event_type, callback)

    def unregister_callback(self, event_type: str, callback):
        """取消事件回调"""
        self.event_bus.unsubscribe(event_type, callback)
