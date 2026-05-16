from typing import Dict, Any, Optional, List
from core.llm import LLMService
from core.vector_store import vector_store
from tools.registry import tool_registry
import logging
import json

logger = logging.getLogger(__name__)


class ReasoningAgent:
    """Reasoning Agent - 处理复杂问题的分步推理（Chain-of-Thought）"""

    def __init__(self):
        self.llm_service = LLMService()
        self.vector_store = vector_store

    def reason(self, question: str, context: str = "",
               conversation_id: str = None) -> Dict[str, Any]:
        """执行推理流程：分解 → 逐个检索+推理 → 汇总"""
        logger.info(f"[ReasoningAgent] Starting reasoning for: {question[:50]}...")

        try:
            # Step 1：问题分解
            sub_questions = self._decompose_question(question)
            logger.info(f"[ReasoningAgent] Decomposed into {len(sub_questions)} sub-questions")

            # Step 2：逐个子问题检索 + 推理
            reasoning_steps = []
            for sub_q in sub_questions:
                docs = self.vector_store.search(sub_q, k=3, similarity_threshold=0.6)
                sub_answer = self._reason_sub_question(sub_q, docs, context)
                reasoning_steps.append({
                    "sub_question": sub_q,
                    "sources": [
                        {"doc_id": getattr(doc, 'metadata', {}).get("doc_id"),
                         "doc": getattr(doc, 'metadata', {}).get("source", "未知文档")}
                        for doc in docs
                    ],
                    "reasoning": sub_answer
                })

            # Step 3：汇总生成最终答案
            final_answer = self._synthesize_answer(question, reasoning_steps)

            # 合并所有来源
            all_sources = []
            seen_ids = set()
            for step in reasoning_steps:
                for src in step["sources"]:
                    doc_id = src.get("doc_id")
                    if doc_id and doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        all_sources.append(src)

            # 写入会话记忆
            if conversation_id and tool_registry.has_tool("conversation_memory_write"):
                try:
                    tool_registry.invoke_tool(
                        "conversation_memory_write",
                        {"conversation_id": conversation_id, "role": "user", "content": question}
                    )
                    tool_registry.invoke_tool(
                        "conversation_memory_write",
                        {"conversation_id": conversation_id, "role": "assistant", "content": final_answer}
                    )
                except Exception as e:
                    logger.warning(f"[ReasoningAgent] Failed to write memory: {e}")

            return {
                "answer": final_answer,
                "reasoning_steps": reasoning_steps,
                "sources": all_sources,
                "has_sources": len(all_sources) > 0,
                "task_type": "reasoning"
            }

        except Exception as e:
            logger.error(f"[ReasoningAgent] Reasoning failed: {e}", exc_info=True)
            return {
                "answer": "抱歉，处理您的复杂问题时遇到了错误，请稍后再试。",
                "reasoning_steps": [],
                "sources": [],
                "has_sources": False,
                "task_type": "reasoning",
                "error": True
            }

    def _decompose_question(self, question: str) -> List[str]:
        """将复杂问题分解为子问题"""
        if not self.llm_service.llm:
            return [question]

        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt = PromptTemplate.from_template(
            """请将以下复杂问题分解为 2-4 个简单的子问题，便于逐个检索和推理。

问题：{question}

请以 JSON 数组格式输出子问题列表，例如：["子问题1", "子问题2"]
只输出 JSON 数组，不要其他内容。"""
        )

        try:
            chain = prompt | self.llm_service.llm | StrOutputParser()
            response = chain.invoke({"question": question}).strip()

            # 处理可能的 markdown 代码块
            if response.startswith("```"):
                response = response.split("\n", 1)[1] if "\n" in response else response[3:]
                response = response.rsplit("```", 1)[0]

            sub_questions = json.loads(response.strip())
            if isinstance(sub_questions, list) and len(sub_questions) > 0:
                return sub_questions[:4]
        except Exception as e:
            logger.warning(f"[ReasoningAgent] Failed to decompose question: {e}")

        return [question]

    def _reason_sub_question(self, question: str, docs: list, context: str) -> str:
        """对单个子问题进行推理"""
        if not self.llm_service.llm:
            return "无法推理（LLM 不可用）"

        doc_text = "\n".join([
            getattr(doc, 'page_content', str(doc)) if hasattr(doc, 'page_content')
            else doc.get('content', str(doc)) if isinstance(doc, dict) else str(doc)
            for doc in docs
        ]) if docs else "（无相关文档）"

        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt = PromptTemplate.from_template(
            """基于以下参考资料，回答子问题。

参考资料：
{doc_text}

对话上下文：{context}

子问题：{question}

请给出简洁准确的回答。"""
        )

        chain = prompt | self.llm_service.llm | StrOutputParser()
        return chain.invoke({
            "doc_text": doc_text,
            "context": context or "无",
            "question": question
        }).strip()

    def _synthesize_answer(self, original_question: str, reasoning_steps: list) -> str:
        """汇总推理结果，生成最终答案"""
        if not self.llm_service.llm:
            return "\n\n".join([step["reasoning"] for step in reasoning_steps])

        steps_text = "\n".join([
            f"Q: {step['sub_question']}\nA: {step['reasoning']}"
            for step in reasoning_steps
        ])

        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt = PromptTemplate.from_template(
            """基于以下分步推理结果，回答用户的原始问题。

分步推理：
{steps_text}

原始问题：{original_question}

请给出完整、准确、结构化的回答。"""
        )

        chain = prompt | self.llm_service.llm | StrOutputParser()
        return chain.invoke({
            "steps_text": steps_text,
            "original_question": original_question
        }).strip()
