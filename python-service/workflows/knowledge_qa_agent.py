from typing import Dict, Any, Optional, Generator
from agent.orchestrator import Orchestrator
from agent.state import AgentState
from agent.events import EventBus, event_bus
from workflows.retrieval_agent import RetrievalAgent
from core.vector_store import vector_store
from core.llm import LLMService
import logging
import json

logger = logging.getLogger(__name__)


class KnowledgeQAAgent:
    """知识问答Agent - 精简RAG链路：直接检索 → LLM生成 → 返回"""

    def __init__(self):
        self.orchestrator = Orchestrator()
        self.event_bus = event_bus
        self.retrieval_agent = RetrievalAgent()
        self.vector_store = vector_store
        self.llm_service = LLMService()

    def ask(self, question: str, conversation_id: Optional[str] = None,
            user_id: Optional[str] = None, context: str = "",
            **kwargs) -> Dict[str, Any]:
        """
        处理知识问答 - 精简RAG链路

        直接走：向量检索 → LLM生成 → 返回（带引用）
        去掉 Orchestrator fallback、问题重写、重排序等开销
        """
        logger.info(f"[KnowledgeQAAgent] Processing question: {question[:50]}...")

        try:
            # 1. 直接向量检索（不经过 RetrievalAgent 的额外工具链）
            docs = self.vector_store.search(
                query=question,
                k=5,
                similarity_threshold=0.7,
                use_rerank=False  # 跳过重排序，减少开销
            )

            logger.info(f"[KnowledgeQAAgent] Retrieved {len(docs)} documents")

            # 2. 无文档 → 直接返回
            if not docs:
                return {
                    "answer": "抱歉，知识库中没有找到与您问题相关的内容。",
                    "sources": [],
                    "has_sources": False,
                    "task_type": "knowledge_qa"
                }

            # 3. LLM 生成回答
            answer = self.llm_service.get_answer(
                question=question,
                context_docs=docs,
                conversation_context=context
            )

            # 4. 构建引用来源（按 doc_id 去重）
            seen_doc_ids = set()
            sources = []
            for doc in docs:
                metadata = getattr(doc, 'metadata', {})
                doc_id = metadata.get("doc_id")
                if doc_id and doc_id in seen_doc_ids:
                    continue
                if doc_id:
                    seen_doc_ids.add(doc_id)
                sources.append({
                    "doc_id": doc_id,
                    "doc": metadata.get("source", "未知文档"),
                    "page": metadata.get("page"),
                    "chunk_index": metadata.get("chunk_index"),
                    "score": metadata.get("score", 0)
                })

            return {
                "answer": answer,
                "sources": sources,
                "has_sources": len(sources) > 0,
                "task_type": "knowledge_qa"
            }

        except Exception as e:
            logger.error(f"[KnowledgeQAAgent] QA failed: {e}", exc_info=True)
            return {
                "answer": "抱歉，处理您的问题时遇到了错误，请稍后再试。",
                "sources": [],
                "has_sources": False,
                "task_type": "knowledge_qa",
                "error": True
            }

    def ask_stream(self, question: str, conversation_id: Optional[str] = None,
                   user_id: Optional[str] = None, context: str = "",
                   **kwargs) -> Generator[str, None, None]:
        """
        流式处理知识问答 - 精简RAG链路

        直接走：向量检索 → LLM流式生成 → 返回
        """
        logger.info(f"[KnowledgeQAAgent] Stream processing question: {question[:50]}...")

        try:
            # 1. 直接向量检索
            docs = self.vector_store.search(
                query=question,
                k=5,
                similarity_threshold=0.7,
                use_rerank=False
            )

            logger.info(f"[KnowledgeQAAgent] Retrieved {len(docs)} documents")

            # 2. 构建引用来源（按 doc_id 去重）
            seen_doc_ids = set()
            sources = []
            for doc in docs:
                metadata = getattr(doc, 'metadata', {})
                doc_id = metadata.get("doc_id")
                if doc_id and doc_id in seen_doc_ids:
                    continue
                if doc_id:
                    seen_doc_ids.add(doc_id)
                sources.append({
                    "doc_id": doc_id,
                    "doc": metadata.get("source", "未知文档"),
                    "page": metadata.get("page"),
                    "chunk_index": metadata.get("chunk_index"),
                })

            # 3. 流式 LLM 生成
            for chunk in self.llm_service.get_answer_stream(
                question=question,
                context_docs=docs,
                conversation_context=context
            ):
                yield chunk

            # 4. 发送来源信息
            yield json.dumps({
                "type": "sources",
                "sources": sources,
                "task_type": "knowledge_qa"
            })

        except Exception as e:
            logger.error(f"[KnowledgeQAAgent] Stream QA failed: {e}", exc_info=True)
            yield json.dumps({
                "type": "error",
                "content": "处理问题时遇到错误，请稍后再试。"
            })

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
