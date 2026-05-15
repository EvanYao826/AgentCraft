"""测试 Memory Agent"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agent.memory_agent import MemoryAgent
from agent.state import AgentState


@pytest.fixture
def memory_agent():
    return MemoryAgent()


@pytest.fixture
def state_with_conversation():
    return AgentState(
        run_id="test-run-001",
        conversation_id="conv-001",
        user_id="user-001",
        original_input="什么是RAG？"
    )


@pytest.fixture
def state_without_conversation():
    return AgentState(
        run_id="test-run-002",
        original_input="什么是RAG？"
    )


class TestMemoryAgentInit:
    """测试 Memory Agent 初始化"""

    def test_init(self, memory_agent):
        """测试初始化"""
        assert memory_agent is not None
        assert memory_agent.llm_service is not None

    def test_compress_threshold(self, memory_agent):
        """测试压缩阈值配置"""
        assert memory_agent.COMPRESS_THRESHOLD == 10
        assert memory_agent.KEEP_RECENT == 5


class TestLoadMemory:
    """测试记忆加载"""

    def test_load_memory_without_conversation(self, memory_agent, state_without_conversation):
        """测试没有会话ID时加载记忆"""
        context = memory_agent.load_memory(state_without_conversation)
        assert context == ""

    @patch('agent.memory_agent.tool_registry')
    def test_load_memory_with_empty_history(self, mock_registry, memory_agent, state_with_conversation):
        """测试加载空历史"""
        mock_registry.has_tool.return_value = True
        mock_registry.invoke_tool.return_value = {
            "messages": [],
            "compressed": False
        }

        context = memory_agent.load_memory(state_with_conversation)
        assert context == ""

    @patch('agent.memory_agent.tool_registry')
    def test_load_memory_with_messages(self, mock_registry, memory_agent, state_with_conversation):
        """测试加载有消息的历史"""
        mock_registry.has_tool.return_value = True
        mock_registry.invoke_tool.return_value = {
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"}
            ],
            "compressed": False
        }

        context = memory_agent.load_memory(state_with_conversation)
        assert "用户: 你好" in context
        assert "AI: 你好！有什么可以帮助你的吗？" in context

    @patch('agent.memory_agent.tool_registry')
    def test_load_memory_with_system_message(self, mock_registry, memory_agent, state_with_conversation):
        """测试加载包含系统消息的历史"""
        mock_registry.has_tool.return_value = True
        mock_registry.invoke_tool.return_value = {
            "messages": [
                {"role": "system", "content": "[历史对话摘要] 用户询问了RAG相关问题"},
                {"role": "user", "content": "它有什么优点？"},
                {"role": "assistant", "content": "RAG的优点包括..."}
            ],
            "compressed": True
        }

        context = memory_agent.load_memory(state_with_conversation)
        assert "[历史对话摘要]" in context
        assert "用户: 它有什么优点？" in context

    @patch('agent.memory_agent.tool_registry')
    def test_load_memory_tool_not_found(self, mock_registry, memory_agent, state_with_conversation):
        """测试工具不存在时的处理"""
        mock_registry.has_tool.return_value = False

        context = memory_agent.load_memory(state_with_conversation)
        assert context == ""

    @patch('agent.memory_agent.tool_registry')
    def test_load_memory_tool_error(self, mock_registry, memory_agent, state_with_conversation):
        """测试工具调用出错时的处理"""
        mock_registry.has_tool.return_value = True
        mock_registry.invoke_tool.side_effect = Exception("Redis connection error")

        context = memory_agent.load_memory(state_with_conversation)
        assert context == ""


class TestSaveMemory:
    """测试记忆保存"""

    def test_save_memory_without_conversation(self, memory_agent, state_without_conversation):
        """测试没有会话ID时保存记忆"""
        # 应该直接返回，不抛异常
        memory_agent.save_memory(state_without_conversation, "问题", "回答")

    @patch('agent.memory_agent.tool_registry')
    def test_save_memory_success(self, mock_registry, memory_agent, state_with_conversation):
        """测试成功保存记忆"""
        mock_registry.has_tool.return_value = True
        mock_registry.invoke_tool.return_value = {"success": True}

        memory_agent.save_memory(state_with_conversation, "什么是RAG？", "RAG是...")

        # 验证调用了两次写入（用户问题 + AI回答）
        assert mock_registry.invoke_tool.call_count >= 2

        # 验证第一次调用是写入用户问题
        first_call = mock_registry.invoke_tool.call_args_list[0]
        assert first_call[0][0] == "conversation_memory_write"
        assert first_call[0][1]["role"] == "user"
        assert first_call[0][1]["content"] == "什么是RAG？"

        # 验证第二次调用是写入AI回答
        second_call = mock_registry.invoke_tool.call_args_list[1]
        assert second_call[0][0] == "conversation_memory_write"
        assert second_call[0][1]["role"] == "assistant"
        assert second_call[0][1]["content"] == "RAG是..."

    @patch('agent.memory_agent.tool_registry')
    def test_save_memory_write_user_fail(self, mock_registry, memory_agent, state_with_conversation):
        """测试写入用户问题失败时的处理"""
        mock_registry.has_tool.return_value = True
        mock_registry.invoke_tool.side_effect = [
            Exception("Write failed"),  # 用户问题写入失败
            {"success": True}  # AI回答写入成功
        ]

        # 应该不抛异常
        memory_agent.save_memory(state_with_conversation, "问题", "回答")


class TestFormatHistory:
    """测试历史格式化"""

    def test_format_history_empty(self, memory_agent):
        """测试格式化空历史"""
        result = memory_agent._format_history([])
        assert result == ""

    def test_format_history_single_message(self, memory_agent):
        """测试格式化单条消息"""
        messages = [{"role": "user", "content": "你好"}]
        result = memory_agent._format_history(messages)
        assert result == "用户: 你好"

    def test_format_history_multiple_messages(self, memory_agent):
        """测试格式化多条消息"""
        messages = [
            {"role": "user", "content": "什么是RAG？"},
            {"role": "assistant", "content": "RAG是检索增强生成的缩写。"},
            {"role": "user", "content": "它有什么优点？"},
            {"role": "assistant", "content": "RAG的优点包括..."}
        ]
        result = memory_agent._format_history(messages)
        assert "用户: 什么是RAG？" in result
        assert "AI: RAG是检索增强生成的缩写。" in result
        assert "用户: 它有什么优点？" in result
        assert "AI: RAG的优点包括..." in result

    def test_format_history_with_system_message(self, memory_agent):
        """测试格式化包含系统消息的历史"""
        messages = [
            {"role": "system", "content": "系统消息"},
            {"role": "user", "content": "用户问题"}
        ]
        result = memory_agent._format_history(messages)
        assert "系统消息" in result
        assert "用户: 用户问题" in result

    def test_format_history_unknown_role(self, memory_agent):
        """测试格式化未知角色的消息"""
        messages = [{"role": "unknown", "content": "未知角色消息"}]
        result = memory_agent._format_history(messages)
        assert "未知角色消息" in result


class TestExtractUserPreference:
    """测试用户偏好提取"""

    @patch('core.mysql_client.user_memory_client')
    @patch('agent.memory_agent.tool_registry')
    def test_extract_preference_with_user_id(self, mock_registry, mock_mysql, memory_agent, state_with_conversation):
        """测试有用户ID时提取偏好"""
        mock_registry.has_tool.return_value = True
        mock_mysql.update_user_memory = Mock()

        # Mock LLM 返回
        memory_agent.llm_service.chat = Mock(return_value='{"preference_style": "简洁", "topics": ["RAG"]}')

        memory_agent._extract_user_preference(
            state_with_conversation,
            "什么是RAG？",
            "RAG是检索增强生成的缩写。"
        )

        # 验证调用了更新用户记忆
        mock_mysql.update_user_memory.assert_called_once()

    def test_extract_preference_without_user_id(self, memory_agent, state_without_conversation):
        """测试没有用户ID时提取偏好"""
        # 应该直接返回，不抛异常
        memory_agent._extract_user_preference(
            state_without_conversation,
            "什么是RAG？",
            "RAG是检索增强生成的缩写。"
        )

    @patch('core.mysql_client.user_memory_client')
    @patch('agent.memory_agent.tool_registry')
    def test_extract_preference_llm_returns_null(self, mock_registry, mock_mysql, memory_agent, state_with_conversation):
        """测试LLM返回null时的处理"""
        mock_registry.has_tool.return_value = True

        # Mock LLM 返回 null
        memory_agent.llm_service.chat = Mock(return_value='null')

        memory_agent._extract_user_preference(
            state_with_conversation,
            "什么是RAG？",
            "RAG是检索增强生成的缩写。"
        )

        mock_mysql.update_user_memory.assert_not_called()

    @patch('agent.memory_agent.tool_registry')
    def test_extract_preference_llm_error(self, mock_registry, memory_agent, state_with_conversation):
        """测试LLM调用出错时的处理"""
        mock_registry.has_tool.return_value = True

        # Mock LLM 抛出异常
        memory_agent.llm_service.chat = Mock(side_effect=Exception("LLM error"))

        # 应该不抛异常
        memory_agent._extract_user_preference(
            state_with_conversation,
            "什么是RAG？",
            "RAG是检索增强生成的缩写。"
        )


class TestLoadUserProfile:
    """测试用户画像加载"""

    @patch('core.mysql_client.user_memory_client')
    def test_load_user_profile_success(self, mock_mysql, memory_agent):
        """测试成功加载用户画像"""
        mock_mysql.get_user_memory.return_value = {
            "preference_style": {"value": "简洁"},
            "high_freq_topics": {"topics": ["RAG", "LLM"]}
        }

        profile = memory_agent._load_user_profile("user-001")
        assert profile is not None
        assert "preference_style" in profile
        assert "high_freq_topics" in profile

    @patch('core.mysql_client.user_memory_client')
    def test_load_user_profile_error(self, mock_mysql, memory_agent):
        """测试加载用户画像出错时的处理"""
        mock_mysql.get_user_memory.side_effect = Exception("DB error")

        profile = memory_agent._load_user_profile("user-001")
        assert profile is None


class TestMemoryAgentIntegration:
    """测试 Memory Agent 集成"""

    @patch('agent.memory_agent.tool_registry')
    def test_full_workflow(self, mock_registry, memory_agent, state_with_conversation):
        """测试完整工作流程"""
        # 设置 mock
        mock_registry.has_tool.return_value = True

        # 第一次调用：保存记忆
        mock_registry.invoke_tool.return_value = {"success": True}
        memory_agent.save_memory(state_with_conversation, "什么是RAG？", "RAG是...")

        # 第二次调用：加载记忆
        mock_registry.invoke_tool.return_value = {
            "messages": [
                {"role": "user", "content": "什么是RAG？"},
                {"role": "assistant", "content": "RAG是..."}
            ],
            "compressed": False
        }

        context = memory_agent.load_memory(state_with_conversation)
        assert "用户: 什么是RAG？" in context
        assert "AI: RAG是..." in context
