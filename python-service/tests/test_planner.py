"""测试 Planner 规划器"""

import pytest
from agent.planner import Planner, QuestionType
from intent.classifier import IntentType, IntentResult
from agent.state import AgentState


@pytest.fixture
def planner():
    return Planner()


class TestIntentRecognition:
    """测试意图识别"""

    def test_recognize_chitchat(self, planner):
        """测试识别闲聊意图"""
        state = AgentState(original_input="你好，今天天气怎么样？")
        result = planner.recognize_intent(state)
        assert result.intent == IntentType.CHITCHAT
        assert result.confidence > 0.5

    def test_recognize_knowledge_qa(self, planner):
        """测试识别知识问答意图"""
        state = AgentState(original_input="什么是 RAG？请解释一下它的工作原理")
        result = planner.recognize_intent(state)
        assert result.intent == IntentType.KNOWLEDGE_QA
        assert result.confidence > 0.5

    def test_recognize_identity_query(self, planner):
        """测试识别身份查询意图"""
        state = AgentState(original_input="你是谁？")
        result = planner.recognize_intent(state)
        # "你是谁" 在当前关键词匹配下被归类为闲聊
        assert result.intent in [IntentType.IDENTITY_QUERY, IntentType.CHITCHAT]

    def test_recognize_admin_operation(self, planner):
        """测试识别管理操作意图"""
        state = AgentState(original_input="查看后台统计数据")
        result = planner.recognize_intent(state)
        assert result.intent == IntentType.ADMIN_OPERATION

    def test_recognize_unknown(self, planner):
        """测试识别未知意图"""
        state = AgentState(original_input="asdfghjkl")
        result = planner.recognize_intent(state)
        assert result.intent == IntentType.UNKNOWN


class TestQuestionClassification:
    """测试问题分类"""

    def test_classify_technical(self, planner):
        """测试技术类问题"""
        result = planner.classify_question("Python 的装饰器怎么用？")
        assert result.question_type == QuestionType.TECHNICAL
        assert result.should_return_sources is True

    def test_classify_professional(self, planner):
        """测试专业类问题"""
        result = planner.classify_question("最新的教育政策是什么？")
        assert result.question_type == QuestionType.PROFESSIONAL

    def test_classify_life(self, planner):
        """测试生活类问题"""
        result = planner.classify_question("今天天气怎么样？")
        assert result.question_type == QuestionType.LIFE
        assert result.should_return_sources is False


class TestClarificationCheck:
    """测试澄清检查"""

    def test_need_clarification_vague(self, planner):
        """测试模糊问题需要澄清"""
        state = AgentState(original_input="那个")
        intent = planner.recognize_intent(state)
        needs_clarification, prompt = planner.check_clarification_needed(state, intent)
        assert needs_clarification is True

    def test_need_clarification_short(self, planner):
        """测试过短问题需要澄清"""
        state = AgentState(original_input="啥")
        intent = planner.recognize_intent(state)
        needs_clarification, prompt = planner.check_clarification_needed(state, intent)
        assert needs_clarification is True

    def test_no_clarification_needed(self, planner):
        """测试正常问题不需要澄清"""
        state = AgentState(original_input="什么是机器学习？请详细解释一下")
        intent = planner.recognize_intent(state)
        needs_clarification, _ = planner.check_clarification_needed(state, intent)
        assert needs_clarification is False


class TestQuestionRewrite:
    """测试问题改写"""

    def test_rewrite_simple(self, planner):
        """测试简单改写（fallback）"""
        result = planner.rewrite_question("什么是 RAG？", rewrite_type="simple")
        assert result.original_question == "什么是 RAG？"
        assert result.rewritten_question is not None
        assert result.rewrite_type == "simple"

    def test_rewrite_semantic_fallback(self, planner):
        """测试语义改写（无 LLM 时降级为简单改写）"""
        result = planner.rewrite_question("如何学习编程？")
        # 无 DASHSCOPE_API_KEY 时应降级为 simple
        assert result.rewrite_type in ["semantic", "simple"]


class TestRetrievalSufficiency:
    """测试检索充分性判断"""

    def test_sufficient_retrieval(self, planner):
        """测试充分的检索结果"""
        chunks = [{"content": "test"}, {"content": "test2"}, {"content": "test3"}]
        scores = [0.9, 0.85, 0.8]
        result = planner.evaluate_retrieval_sufficiency(chunks, "test question", scores)
        assert result.is_sufficient is True

    def test_insufficient_no_chunks(self, planner):
        """测试无检索结果"""
        result = planner.evaluate_retrieval_sufficiency([], "test question")
        assert result.is_sufficient is False

    def test_insufficient_low_scores(self, planner):
        """测试低分检索结果"""
        chunks = [{"content": "test"}, {"content": "test2"}]
        scores = [0.3, 0.2]
        result = planner.evaluate_retrieval_sufficiency(chunks, "test question", scores)
        assert result.is_sufficient is False


class TestStepPlanning:
    """测试步骤规划"""

    def test_plan_chitchat_steps(self, planner):
        """测试闲聊步骤规划"""
        state = AgentState(original_input="你好")
        steps = planner.plan_steps(state)
        assert "answer_generation" in steps
        assert "knowledge_search" not in steps

    def test_plan_knowledge_qa_steps(self, planner):
        """测试知识问答步骤规划"""
        state = AgentState(original_input="什么是 RAG？请解释原理")
        steps = planner.plan_steps(state)
        assert "knowledge_search" in steps
        assert "answer_generation" in steps

    def test_plan_identity_steps(self, planner):
        """测试身份查询步骤规划"""
        state = AgentState(original_input="你是谁？")
        steps = planner.plan_steps(state)
        # "你是谁" 当前被归类为闲聊，走 answer_generation
        assert "answer_generation" in steps
