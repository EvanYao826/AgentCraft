from typing import Dict, Any, Optional, List
from agent.state import AgentState, AgentStep, StepType, StepStatus
from agent.planner import Planner, IntentResult, QuestionClassification, RewriteResult, SufficiencyResult
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
            elif step.step_type == StepType.MEMORY_WRITE:
                return self._execute_memory_write(state, step)
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
            content=intent_result.intent,
            confidence=intent_result.confidence
        )

        step.complete({
            "intent": intent_result.intent,
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
        rewrite_result = self.planner.rewrite_question(question)

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
        """执行答案生成"""
        question = state.original_input or ""
        context = state.context or ""

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

        if docs and should_return_sources:
            answer = self.llm_service.get_answer(question, docs, context)
        elif not docs:
            answer = self.llm_service.get_answer(question, [], context)
        else:
            answer = self.llm_service.get_answer(question, [], context)

        step.complete({
            "answer": answer,
            "sources": sources if should_return_sources else [],
            "has_sources": len(sources) > 0 if should_return_sources else False
        })

        return step.output_data

    def _execute_memory_write(self, state: AgentState, step: AgentStep) -> Dict[str, Any]:
        """执行记忆写入"""
        success = True
        message = "记忆写入完成"

        if tool_registry.has_tool("memory_write"):
            try:
                answer = None
                for s in reversed(state.steps):
                    if s.step_type == StepType.ANSWER_GENERATION and s.output_data:
                        answer = s.output_data.get("answer", "")
                        break

                tool_registry.invoke_tool(
                    "memory_write",
                    {
                        "conversation_id": state.conversation_id,
                        "user_id": state.user_id,
                        "question": state.original_input,
                        "answer": answer
                    },
                    run_id=state.run_id
                )
            except Exception as e:
                logger.warning(f"[{state.run_id}] memory_write tool failed: {e}")
                success = False
                message = f"记忆写入失败: {str(e)}"

        step.complete({
            "success": success,
            "message": message
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
