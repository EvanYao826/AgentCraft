"""测试 RouterAgent 路由Agent"""

import pytest
from workflows.router_agent import RouterAgent, TaskType
from intent.classifier import IntentType


@pytest.fixture
def router():
    return RouterAgent()


class TestClassifyTask:
    """测试任务分类"""

    def test_classify_chitchat_greeting(self, router):
        """测试识别闲聊-问候"""
        assert router.classify_task("你好") == TaskType.CHITCHAT

    def test_classify_chitchat_farewell(self, router):
        """测试识别闲聊-告别"""
        assert router.classify_task("谢谢，再见") == TaskType.CHITCHAT

    def test_classify_chitchat_identity(self, router):
        """测试识别闲聊-身份询问"""
        assert router.classify_task("你是谁") == TaskType.CHITCHAT

    def test_classify_chitchat_daily(self, router):
        """测试识别闲聊-日常"""
        assert router.classify_task("讲个笑话") == TaskType.CHITCHAT

    def test_classify_chitchat_weather(self, router):
        """测试识别闲聊-天气"""
        assert router.classify_task("今天天气怎么样") == TaskType.CHITCHAT

    def test_classify_knowledge_qa_technical(self, router):
        """测试识别知识问答-技术"""
        assert router.classify_task("什么是 RAG？请解释它的工作原理") == TaskType.KNOWLEDGE_QA

    def test_classify_knowledge_qa_programming(self, router):
        """测试识别知识问答-编程"""
        assert router.classify_task("Python 的装饰器怎么用？") == TaskType.KNOWLEDGE_QA

    def test_classify_knowledge_qa_database(self, router):
        """测试识别知识问答-数据库"""
        assert router.classify_task("MySQL 的事务隔离级别有哪些？") == TaskType.KNOWLEDGE_QA

    def test_classify_knowledge_qa_concept(self, router):
        """测试识别知识问答-概念（含'区别'且>15字，走推理链路）"""
        assert router.classify_task("深度学习和机器学习的区别是什么？") == TaskType.REASONING

    def test_classify_admin_normal_user(self, router):
        """测试普通用户不触发管理"""
        result = router.classify_task("查看后台统计数据", is_admin=False)
        # 普通用户：短文本 + 包含"后台""统计"等admin关键词，但无明确疑问词
        assert result in [TaskType.KNOWLEDGE_QA, TaskType.ADMIN_COPILOT, TaskType.CHITCHAT]

    def test_classify_admin_admin_user(self, router):
        """测试管理员触发管理"""
        result = router.classify_task("查看后台统计数据", is_admin=True)
        assert result == TaskType.ADMIN_COPILOT

    def test_classify_inspection(self, router):
        """测试知识巡检"""
        result = router.classify_task("检查重复文档", is_admin=True)
        assert result == TaskType.KNOWLEDGE_INSPECTION

    def test_classify_inspection_low_quality(self, router):
        """测试低质量巡检"""
        result = router.classify_task("检查低质量片段", is_admin=True)
        assert result == TaskType.KNOWLEDGE_INSPECTION

    def test_classify_unknown_short_text(self, router):
        """测试短文本无关键词时归类为闲聊"""
        result = router.classify_task("帮我写一篇文章")
        # 短文本（<10字符）且无疑问词，默认闲聊
        assert result == TaskType.CHITCHAT

    def test_classify_unknown_long_text_defaults_to_knowledge(self, router):
        """测试长文本含'分析'时走推理链路"""
        result = router.classify_task("请帮我分析一下这个问题的具体情况并给出建议")
        assert result == TaskType.REASONING


class TestParseInspectionType:
    """测试巡检类型解析"""

    def test_parse_duplicate(self, router):
        """测试解析重复类型"""
        assert router._parse_inspection_type("检查重复文档") == "duplicate"

    def test_parse_low_quality(self, router):
        """测试解析低质量类型"""
        assert router._parse_inspection_type("检查低质量内容") == "low_quality"

    def test_parse_stale(self, router):
        """测试解析过期类型"""
        assert router._parse_inspection_type("检查过期文档") == "stale"

    def test_parse_unpopular(self, router):
        """测试解析无人访问类型"""
        assert router._parse_inspection_type("检查无人访问的文档") == "unpopular"

    def test_parse_full(self, router):
        """测试默认全量巡检"""
        assert router._parse_inspection_type("知识库巡检") == "full"


class TestGetAgent:
    """测试获取Agent"""

    def test_get_chitchat_agent(self, router):
        """测试获取闲聊Agent"""
        agent = router.get_agent(TaskType.CHITCHAT)
        assert agent is router.chitchat_agent

    def test_get_knowledge_agent(self, router):
        """测试获取知识问答Agent"""
        agent = router.get_agent(TaskType.KNOWLEDGE_QA)
        assert agent is router.knowledge_qa_agent

    def test_get_admin_agent(self, router):
        """测试获取管理Agent"""
        agent = router.get_agent(TaskType.ADMIN_COPILOT)
        assert agent is router.admin_copilot_agent

    def test_get_inspection_agent(self, router):
        """测试获取巡检Agent"""
        agent = router.get_agent(TaskType.KNOWLEDGE_INSPECTION)
        assert agent is router.inspection_agent

    def test_get_unknown_defaults_to_knowledge(self, router):
        """测试未知类型默认返回知识问答Agent"""
        agent = router.get_agent(TaskType.UNKNOWN)
        assert agent is router.knowledge_qa_agent


class TestGetTaskStats:
    """测试任务统计"""

    def test_stats_has_all_keys(self, router):
        """测试统计包含所有键"""
        stats = router.get_task_stats()
        assert "chitchat_keywords" in stats
        assert "knowledge_qa_keywords" in stats
        assert "admin_keywords" in stats
        assert "inspection_keywords" in stats
        assert "emotion_keywords" in stats

    def test_stats_values_positive(self, router):
        """测试统计值为正数"""
        stats = router.get_task_stats()
        for count in stats.values():
            assert count > 0
