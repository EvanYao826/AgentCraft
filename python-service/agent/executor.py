from typing import Dict, Any, Optional, List
from agent.state import AgentState, AgentStep, StepType, StepStatus
from agent.planner import Planner, QuestionClassification, RewriteResult, SufficiencyResult
from intent.classifier import IntentResult
from tools.registry import tool_registry
from core.llm import LLMService
from core.vector_store import vector_store
import time
import logging
import json
import os

logger = logging.getLogger(__name__)


class Executor:
    """步骤执行器 - 负责执行各个步骤"""

    def __init__(self):
        self.planner = Planner()
        self.llm_service = LLMService()
        self.vector_store = vector_store
        self._memory_agent = None

    @property
    def memory_agent(self):
        """延迟加载 MemoryAgent"""
        if self._memory_agent is None:
            from agent.memory_agent import MemoryAgent
            self._memory_agent = MemoryAgent()
        return self._memory_agent

    def execute_step(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行单个步骤"""
        step.start()
        logger.info(f"[{state.run_id}] Executing step: {step.step_name} (type: {step.step_type.value})")

        try:
            if step.step_type == StepType.INTENT_RECOGNITION:
                return self._execute_intent_recognition(state, step)
            elif step.step_type == StepType.QUESTION_CLASSIFICATION:
                return self._execute_question_classification(state, step)
            elif step.step_type == StepType.CLARIFICATION:
                return self._execute_clarification(state, step)
            elif step.step_type == StepType.QUESTION_REWRITE:
                return self._execute_question_rewrite(state, step)
            elif step.step_type == StepType.KNOWLEDGE_SEARCH:
                return self._execute_knowledge_search(state, step)
            elif step.step_type == StepType.RESULT_EVALUATION:
                return self._execute_result_evaluation(state, step)
            elif step.step_type == StepType.ANSWER_GENERATION:
                return self._execute_answer_generation(state, step)
            elif step.step_type == StepType.MEMORY_READ:
                return self._execute_memory_read(state, step)
            elif step.step_type == StepType.MEMORY_WRITE:
                return self._execute_memory_write(state, step)
            elif step.step_type == StepType.MEMORY_COMPRESS:
                return self._execute_memory_compress(state, step)
            elif step.step_type == StepType.TOOL_CALL:
                return self._execute_tool_call(state, step)
            else:
                raise ValueError(f"Unknown step type: {step.step_type}")
        except Exception as e:
            logger.error(f"[{state.run_id}] Step {step.step_name} failed: {str(e)}")
            step.fail(str(e))
            raise

    def _execute_intent_recognition(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行意图识别"""
        intent_result = self.planner.recognize_intent(state)

        state.add_intermediate_conclusion(
            step_id=step.step_id,
            conclusion_type="intent",
            content=intent_result.intent.value,
            confidence=intent_result.confidence
        )

        step.complete({
            "intent": intent_result.intent.value,
            "confidence": intent_result.confidence,
            "reasoning": intent_result.reasoning,
            "requires_clarification": intent_result.requires_clarification
        })

        return step.output_data

    def _execute_question_classification(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行问题分类"""
        question = state.original_input or ""
        classification = self.planner.classify_question(question)

        state.add_intermediate_conclusion(
            step_id=step.step_id,
            conclusion_type="question_type",
            content=classification.question_type,
            confidence=classification.confidence,
            sources=[{"keyword": kw} for kw in classification.keywords]
        )

        step.complete({
            "question_type": classification.question_type,
            "confidence": classification.confidence,
            "keywords": classification.keywords,
            "should_return_sources": classification.should_return_sources
        })

        return step.output_data

    def _execute_clarification(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行澄清判断"""
        intent = self.planner.recognize_intent(state)
        needs_clarification, prompt = self.planner.check_clarification_needed(state, intent)

        step.complete({
            "needs_clarification": needs_clarification,
            "prompt": prompt
        })

        if needs_clarification:
            state.wait()

        return step.output_data

    def _execute_question_rewrite(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行问题改写"""
        question = state.original_input or ""
        rewrite_result = self.planner.rewrite_question(question, conversation_context=state.context or "")

        state.add_intermediate_conclusion(
            step_id=step.step_id,
            conclusion_type="rewritten_question",
            content=rewrite_result.rewritten_question,
            confidence=rewrite_result.confidence
        )

        step.complete({
            "original_question": rewrite_result.original_question,
            "rewritten_question": rewrite_result.rewritten_question,
            "rewrite_type": rewrite_result.rewrite_type
        })

        return step.output_data

    def _execute_knowledge_search(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行知识检索"""
        query = state.original_input or ""

        rewritten_question = None
        for conclusion in state.intermediate_conclusions:
            if conclusion.conclusion_type == "rewritten_question":
                rewritten_question = conclusion.content
                break

        search_query = rewritten_question if rewritten_question else query

        tool_call_id = None
        if tool_registry.has_tool("knowledge_search"):
            try:
                result = tool_registry.invoke_tool(
                    "knowledge_search",
                    {"query": search_query, "top_k": 5, "similarity_threshold": 0.7},
                    run_id=state.run_id
                )
                chunks = result.get("chunks", [])
                scores = result.get("scores", [])
                tool_call_id = result.get("tool_call_id")
            except Exception as e:
                logger.warning(f"[{state.run_id}] knowledge_search tool failed: {e}")
                chunks = self.vector_store.search(search_query, k=5, similarity_threshold=0.7)
                scores = [getattr(doc, 'score', 0.5) for doc in chunks]
        else:
            chunks = self.vector_store.search(search_query, k=5, similarity_threshold=0.7)
            scores = [getattr(doc, 'score', 0.5) for doc in chunks]

        sufficiency = self.planner.evaluate_retrieval_sufficiency(chunks, query, scores)

        sources = []
        for doc in chunks:
            source_info = {
                "source": getattr(doc, 'metadata', {}).get('source', ''),
                "doc_id": getattr(doc, 'metadata', {}).get('doc_id', ''),
                "page": getattr(doc, 'metadata', {}).get('page', '')
            }
            if source_info["source"]:
                source_info["doc_name"] = os.path.basename(source_info["source"])
            sources.append(source_info)

        state.add_intermediate_conclusion(
            step_id=step.step_id,
            conclusion_type="retrieval",
            content={
                "chunk_count": len(chunks),
                "avg_score": sum(scores) / len(scores) if scores else 0,
                "is_sufficient": sufficiency.is_sufficient
            },
            confidence=sufficiency.confidence,
            sources=sources
        )

        step.tool_call_id = tool_call_id
        step.complete({
            "chunks": [{"content": getattr(doc, 'page_content', str(doc)), "score": getattr(doc, 'score', 0)} for doc in chunks],
            "scores": scores,
            "sources": sources,
            "is_sufficient": sufficiency.is_sufficient,
            "reasoning": sufficiency.reasoning
        })

        return step.output_data

    def _execute_result_evaluation(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行结果充分性判断"""
        chunks = None
        for s in state.steps:
            if s.step_type == StepType.KNOWLEDGE_SEARCH and s.output_data:
                chunks = s.output_data.get("chunks", [])
                break

        if chunks is None:
            step.complete({
                "is_sufficient": False,
                "reasoning": "未找到检索结果"
            })
            return step.output_data

        sufficiency = self.planner.evaluate_retrieval_sufficiency(
            [type('obj', (object,), {'page_content': c.get('content', '')}) for c in chunks],
            state.original_input or ""
        )

        state.add_intermediate_conclusion(
            step_id=step.step_id,
            conclusion_type="sufficiency",
            content={
                "is_sufficient": sufficiency.is_sufficient,
                "reasoning": sufficiency.reasoning
            },
            confidence=sufficiency.confidence
        )

        step.complete({
            "is_sufficient": sufficiency.is_sufficient,
            "confidence": sufficiency.confidence,
            "reasoning": sufficiency.reasoning,
            "missing_aspects": sufficiency.missing_aspects,
            "suggestions": sufficiency.suggestions
        })

        return step.output_data

    def _execute_answer_generation(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行答案生成（使用 Memory Agent 加载记忆）"""
        question = state.original_input or ""
        context = state.context or ""

        # 使用 Memory Agent 加载记忆
        memory_context = self.memory_agent.load_memory(state)
        full_context = context
        if memory_context:
            full_context = f"{context}\n\n{memory_context}" if context else memory_context

        chunks = None
        sources = []
        for s in state.steps:
            if s.step_type == StepType.KNOWLEDGE_SEARCH and s.output_data:
                chunks = s.output_data.get("chunks", [])
                sources = s.output_data.get("sources", [])
                break

        should_return_sources = True
        for s in state.steps:
            if s.step_type == StepType.QUESTION_CLASSIFICATION and s.output_data:
                should_return_sources = s.output_data.get("should_return_sources", True)
                break

        docs = []
        if chunks:
            for chunk in chunks:
                doc = type('Doc', (), {
                    'page_content': chunk.get('content', ''),
                    'metadata': {'source': '', 'doc_id': '', 'page': ''}
                })()
                docs.append(doc)

        # 如果有文档且应该返回来源，传入文档；否则传空列表
        answer = self.llm_service.get_answer(
            question, docs if (docs and should_return_sources) else [], full_context
        )

        # 2. 写入会话记忆
        if state.conversation_id and tool_registry.has_tool("conversation_memory_write"):
            try:
                # 写入用户问题
                tool_registry.invoke_tool(
                    "conversation_memory_write",
                    {
                        "conversation_id": state.conversation_id,
                        "role": "user",
                        "content": question
                    },
                    run_id=state.run_id
                )
                # 写入AI回答
                tool_registry.invoke_tool(
                    "conversation_memory_write",
                    {
                        "conversation_id": state.conversation_id,
                        "role": "assistant",
                        "content": answer
                    },
                    run_id=state.run_id
                )
                logger.info(f"[{state.run_id}] Saved conversation to memory")
            except Exception as e:
                logger.warning(f"[{state.run_id}] Failed to write conversation memory: {e}")

        step.complete({
            "answer": answer,
            "sources": sources if should_return_sources else [],
            "has_sources": len(sources) > 0 if should_return_sources else False
        })

        return step.output_data

    def _format_history(self, messages: list) -> str:
        """格式化对话历史为上下文字符串"""
        if not messages:
            return ""

        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "system":
                formatted.append(content)
            elif role == "user":
                formatted.append(f"用户: {content}")
            elif role == "assistant":
                formatted.append(f"AI: {content}")

        return "\n".join(formatted)

    def _execute_memory_write(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行记忆写入（使用 Memory Agent）"""
        answer = None
        for s in reversed(state.steps):
            if s.step_type == StepType.ANSWER_GENERATION and s.output_data:
                answer = s.output_data.get("answer", "")
                break

        # 使用 Memory Agent 保存记忆
        self.memory_agent.save_memory(state, state.original_input, answer)

        step.complete({
            "success": True,
            "message": "记忆写入完成"
        })

        return step.output_data

    def _execute_memory_read(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行记忆读取（使用 Memory Agent）"""
        context = self.memory_agent.load_memory(state)

        step.complete({
            "context": context,
            "has_history": bool(context)
        })

        # 将记忆上下文保存到 state，供后续步骤使用
        if context:
            state.context = f"{state.context}\n\n{context}" if state.context else context

        return step.output_data

    def _execute_memory_compress(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行记忆压缩"""
        # 压缩逻辑已在 conversation_memory_read 工具中实现
        # 此步骤主要用于标记和日志记录
        logger.info(f"[{state.run_id}] Memory compress step executed")

        step.complete({
            "success": True,
            "message": "记忆压缩检查完成"
        })

        return step.output_data

    def _execute_tool_call(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行通用工具调用"""
        tool_name = step.input_data.get("tool_name")
        parameters = step.input_data.get("parameters", {})

        if not tool_registry.has_tool(tool_name):
            raise ValueError(f"Tool not found: {tool_name}")

        result = tool_registry.invoke_tool(tool_name, parameters, run_id=state.run_id)

        step.complete({
            "result": result,
            "tool_name": tool_name
        })

        return step.output_data
