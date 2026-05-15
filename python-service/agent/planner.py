from typing import Dict, Any, List, Optional, Tuple
from agent.state import AgentState, AgentStep, StepType, TerminationCondition, IntermediateConclusion
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


class IntentType:
    """意图类型枚举"""
    KNOWLEDGE_QA = "knowledge_qa"
    CHITCHAT = "chitchat"
    IDENTITY_QUERY = "identity_query"
    ADMIN_OPERATION = "admin_operation"
    UNKNOWN = "unknown"


class QuestionType:
    """问题类型枚举"""
    TECHNICAL = "technical"
    PROFESSIONAL = "professional"
    LIFE = "life"
    OPINION = "opinion"
    GREETING = "greeting"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: str
    confidence: float
    reasoning: str
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None


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
        self.life_chat_keywords = [
            "你好", "您好", "hello", "hi", "早上好", "下午好", "晚上好",
            "最近好吗", "最近怎么样", "在干嘛", "在做什么",
            "谢谢", "感谢", "再见", "拜拜",
            "知道", "了解", "认识", "听说过", "听过",
            "你觉得", "你认为", "你怎么看", "你怎么想",
            "今天天气", "天气预报", "天气怎么样",
            "现在几点", "现在时间", "今天日期", "今天是",
            "有什么好吃的", "好吃", "美食", "餐厅", "饭店",
            "好玩", "旅游", "景点", "去哪里玩",
            "电影", "电视剧", "音乐", "歌曲", "娱乐",
            "购物", "买什么", "哪里买",
            "健康", "健身", "运动", "减肥",
            "感情", "恋爱", "爱情", "婚姻", "家庭",
            "你叫什么", "你是谁", "你是什么", "你的名字",
            "讲个笑话", "说个故事", "唱首歌", "猜谜语",
            "星座", "运势", "算命", "占卜",
            "可以吗", "行吗", "好吗", "对不对", "是不是",
            "能不能", "会不会", "要不要", "该不该",
            "在哪里", "是什么地方", "哪个城市", "哪个国家",
            "多少钱", "价格", "贵不贵",
            "怎么去", "路线", "交通",
        ]

        self.knowledge_keywords = [
            "什么是", "如何", "怎么", "为什么", "原理", "机制", "工作",
            "定义", "概念", "术语", "解释", "说明",
            "步骤", "流程", "方法", "技巧", "策略",
            "优势", "缺点", "优缺点", "特点", "特性",
            "比较", "对比", "区别", "差异",
            "应用", "用途", "使用场景", "案例",
            "发展", "历史", "趋势", "未来",
            "标准", "规范", "协议", "框架",
            "编程", "代码", "算法", "数据结构", "数据库",
            "网络", "安全", "加密", "协议",
            "人工智能", "机器学习", "深度学习", "神经网络",
            "大数据", "云计算", "物联网", "区块链",
            "文档", "资料", "文件", "报告", "论文", "研究",
            "根据", "参考", "依据", "来源",
        ]

    def recognize_intent(self, state: AgentState) -> IntentResult:
        """意图识别"""
        question = state.original_input or ""
        lower_question = question.lower()

        if any(keyword in lower_question for keyword in ["我是谁", "我叫什么", "我的名字", "我的身份"]):
            return IntentResult(
                intent=IntentType.IDENTITY_QUERY,
                confidence=0.95,
                reasoning="用户询问身份相关问题"
            )

        life_score = sum(1 for kw in self.life_chat_keywords if kw in lower_question)
        knowledge_score = sum(1 for kw in self.knowledge_keywords if kw in lower_question)

        if life_score > knowledge_score:
            return IntentResult(
                intent=IntentType.CHITCHAT,
                confidence=min(0.9, 0.5 + life_score * 0.1),
                reasoning=f"闲聊类问题（命中{life_score}个生活关键词）"
            )

        if any(kw in lower_question for kw in ["管理", "后台", "运营", "统计", "报表"]):
            return IntentResult(
                intent=IntentType.ADMIN_OPERATION,
                confidence=0.85,
                reasoning="疑似管理端操作请求"
            )

        if knowledge_score > 0:
            return IntentResult(
                intent=IntentType.KNOWLEDGE_QA,
                confidence=min(0.95, 0.5 + knowledge_score * 0.15),
                reasoning=f"知识问答类问题（命中{knowledge_score}个知识关键词）"
            )

        return IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.5,
            reasoning="无法确定意图类型"
        )

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

    def rewrite_question(self, question: str, rewrite_type: str = "standard") -> RewriteResult:
        """问题改写"""
        rewritten = question.strip()

        if "？" in question:
            rewritten = rewritten.replace("？", "?")

        if "!" in question:
            rewritten = rewritten.replace("!", "。")

        if rewrite_type == "expand":
            expanded = question
            if "如何" in question:
                expanded = question.replace("如何", "怎样才能")
            elif "怎么" in question:
                expanded = question.replace("怎么", "怎样才能")
            rewritten = expanded

        return RewriteResult(
            original_question=question,
            rewritten_question=rewritten,
            rewrite_type=rewrite_type,
            confidence=0.85
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
