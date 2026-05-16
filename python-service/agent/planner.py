from typing import Dict, Any, List, Optional, Tuple
from agent.state import AgentState, AgentStep, StepType, TerminationCondition, IntermediateConclusion
from intent.classifier import IntentClassifier, IntentType, IntentResult
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


class QuestionType:
    """问题类型枚举"""
    TECHNICAL = "technical"
    PROFESSIONAL = "professional"
    LIFE = "life"
    OPINION = "opinion"
    GREETING = "greeting"
    UNKNOWN = "unknown"


@dataclass
class QuestionClassification:
    """问题分类结果"""
    question_type: str
    confidence: float
    keywords: List[str]
    should_return_sources: bool


@dataclass
class RewriteResult:
    """问题改写结果"""
    original_question: str
    rewritten_question: str
    rewrite_type: str
    confidence: float


@dataclass
class RetrievalResult:
    """检索结果"""
    chunks: List[Any]
    scores: List[float]
    is_sufficient: bool
    reasoning: str
    coverage: float


@dataclass
class SufficiencyResult:
    """结果充分性判断"""
    is_sufficient: bool
    confidence: float
    reasoning: str
    missing_aspects: List[str]
    suggestions: List[str]


class Planner:
    """任务规划器 - 负责分析任务、规划步骤、判断状态"""

    def __init__(self):
        self.classifier = IntentClassifier()

    def recognize_intent(self, state: AgentState) -> IntentResult:
        """意图识别 - 委托给统一分类器"""
        question = state.original_input or ""
        return self.classifier.classify(question)

    def classify_question(self, question: str) -> QuestionClassification:
        """问题分类"""
        lower_question = question.lower()

        technical_keywords = ["编程", "代码", "算法", "数据库", "网络", "安全", "加密", "协议", "人工智能", "机器学习", "深度学习"]
        professional_keywords = ["法律", "法规", "政策", "制度", "经济", "金融", "商业", "管理", "营销", "教育", "培训", "课程"]
        life_keywords = ["天气", "美食", "旅游", "电影", "音乐", "健康", "健身", "感情", "购物"]

        found_technical = [kw for kw in technical_keywords if kw in lower_question]
        found_professional = [kw for kw in professional_keywords if kw in lower_question]
        found_life = [kw for kw in life_keywords if kw in lower_question]

        if found_technical:
            return QuestionClassification(
                question_type=QuestionType.TECHNICAL,
                confidence=0.85,
                keywords=found_technical,
                should_return_sources=True
            )

        if found_professional:
            return QuestionClassification(
                question_type=QuestionType.PROFESSIONAL,
                confidence=0.80,
                keywords=found_professional,
                should_return_sources=True
            )

        if found_life:
            return QuestionClassification(
                question_type=QuestionType.LIFE,
                confidence=0.75,
                keywords=found_life,
                should_return_sources=False
            )

        if any(kw in lower_question for kw in ["怎么", "如何", "为什么", "什么"]):
            return QuestionClassification(
                question_type=QuestionType.TECHNICAL,
                confidence=0.60,
                keywords=["疑问词"],
                should_return_sources=True
            )

        return QuestionClassification(
            question_type=QuestionType.UNKNOWN,
            confidence=0.5,
            keywords=[],
            should_return_sources=False
        )

    def check_clarification_needed(self, state: AgentState, intent: IntentResult) -> Tuple[bool, Optional[str]]:
        """判断是否需要澄清"""
        question = state.original_input or ""

        if intent.requires_clarification:
            return True, intent.clarification_prompt

        vague_indicators = ["那个", "它", "这个", "他", "她", "这事", "那事"]
        if any(ind in question for ind in vague_indicators) and len(question) < 15:
            return True, "您是指什么？请提供更多具体信息。"

        if len(question) < 5:
            return True, "您的问题太简略了，请详细描述一下您想了解的内容。"

        return False, None

    def rewrite_question(self, question: str, conversation_context: str = "",
                         rewrite_type: str = "semantic") -> RewriteResult:
        """问题改写 - LLM 语义改写，失败时 fallback 到简单替换"""
        if rewrite_type == "simple":
            return self._rewrite_simple(question)

        # 尝试 LLM 语义改写
        llm = self._get_llm()
        if llm:
            try:
                return self._rewrite_with_llm(question, conversation_context, llm)
            except Exception as e:
                logger.warning(f"LLM rewrite failed, falling back to simple: {e}")

        return self._rewrite_simple(question)

    def _get_llm(self):
        """延迟获取 LLM 实例"""
        if not hasattr(self, '_llm'):
            try:
                from core.llm import llm_service
                self._llm = llm_service.llm
            except Exception:
                self._llm = None
        return self._llm

    def _rewrite_with_llm(self, question: str, conversation_context: str, llm) -> RewriteResult:
        """LLM 语义改写"""
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt = PromptTemplate.from_template(
            """请对以下用户问题进行改写，目标是提升知识库检索的召回率。

改写规则：
1. 补全省略的主语/宾语
2. 将口语化表达转为书面化
3. 将代词替换为具体指代（结合上下文）
4. 保留原始意图，不要改变问题含义

对话上下文：{conversation_context}

用户问题：{question}

请直接输出改写后的问题，不要解释。"""
        )

        chain = prompt | llm | StrOutputParser()
        rewritten = chain.invoke({
            "question": question,
            "conversation_context": conversation_context or "无"
        }).strip()

        return RewriteResult(
            original_question=question,
            rewritten_question=rewritten,
            rewrite_type="semantic",
            confidence=0.85
        )

    def _rewrite_simple(self, question: str) -> RewriteResult:
        """简单替换（fallback）"""
        rewritten = question.strip()
        if "？" in rewritten:
            rewritten = rewritten.replace("？", "?")
        if "!" in rewritten:
            rewritten = rewritten.replace("!", "。")
        return RewriteResult(
            original_question=question,
            rewritten_question=rewritten,
            rewrite_type="simple",
            confidence=0.6
        )

    def evaluate_retrieval_sufficiency(self, chunks: List[Any], question: str, scores: List[float] = None) -> SufficiencyResult:
        """评估检索结果充分性"""
        if not chunks:
            return SufficiencyResult(
                is_sufficient=False,
                confidence=1.0,
                reasoning="未检索到任何相关文档",
                missing_aspects=["相关知识文档"],
                suggestions=["建议补充相关知识文档", "尝试使用不同的关键词检索"]
            )

        if scores is None:
            scores = [0.5] * len(chunks)

        low_score_count = sum(1 for s in scores if s < 0.6)
        if low_score_count > len(scores) * 0.5:
            return SufficiencyResult(
                is_sufficient=False,
                confidence=0.8,
                reasoning=f"大部分检索结果相似度较低（{low_score_count}/{len(chunks)}低于阈值）",
                missing_aspects=["高质量检索结果"],
                suggestions=["优化检索query", "增加同义词扩展"]
            )

        coverage = min(1.0, len(chunks) * 0.3)
        if coverage < 0.5:
            return SufficiencyResult(
                is_sufficient=False,
                confidence=0.7,
                reasoning=f"检索结果覆盖度较低（{coverage:.2f}）",
                missing_aspects=["相关文档数量"],
                suggestions=["增加知识库内容", "调整相似度阈值"]
            )

        return SufficiencyResult(
            is_sufficient=True,
            confidence=0.85,
            reasoning=f"检索到{len(chunks)}个相关结果，置信度良好",
            missing_aspects=[],
            suggestions=[]
        )

    def plan_steps(self, state: AgentState) -> List[str]:
        """规划执行步骤"""
        intent = self.recognize_intent(state)

        # 如果有会话ID，在开始时读取记忆
        has_conversation = bool(state.conversation_id)

        if intent.intent == IntentType.CHITCHAT:
            steps = []
            if has_conversation:
                steps.append("memory_read")
            steps.append("answer_generation")
            if has_conversation:
                steps.append("memory_write")
            return steps

        if intent.intent == IntentType.IDENTITY_QUERY:
            return ["identity_answer"]

        if intent.intent == IntentType.KNOWLEDGE_QA:
            steps = []
            if has_conversation:
                steps.append("memory_read")
            steps.append("question_rewrite")
            if len(state.original_input or "") < 10:
                steps.append("clarification")
            steps.extend([
                "knowledge_search",
                "result_evaluation",
                "answer_generation"
            ])
            if has_conversation:
                steps.append("memory_write")
            return steps

        if intent.intent == IntentType.ADMIN_OPERATION:
            steps = ["admin_operation"]
            if has_conversation:
                steps.append("memory_write")
            return steps

        steps = []
        if has_conversation:
            steps.append("memory_read")
        steps.extend(["question_rewrite", "knowledge_search", "answer_generation"])
        if has_conversation:
            steps.append("memory_write")
        return steps

    def should_terminate(self, state: AgentState) -> Tuple[bool, str]:
        """判断是否应该终止"""
        reason = TerminationCondition.get_termination_reason(state)
        return TerminationCondition.should_terminate(state), reason
