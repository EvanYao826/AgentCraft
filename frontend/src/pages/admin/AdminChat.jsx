import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../Chat.css';

const adminApi = axios.create({
  baseURL: '/api/admin-chat',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

adminApi.interceptors.request.use(
  config => {
    const token = localStorage.getItem('adminToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

const TASK_TYPE_INFO = {
  chitchat: { icon: '💬', label: '闲聊', color: '#10b981' },
  knowledge_qa: { icon: '📚', label: '知识问答', color: '#3b82f6' },
  admin_copilot: { icon: '⚙️', label: '管理助手', color: '#8b5cf6' },
  knowledge_inspection: { icon: '🔍', label: '知识巡检', color: '#f59e0b' },
  unknown: { icon: '🤖', label: 'AI助手', color: '#6b7280' }
};

const adminChatAPI = {
  createConversation: (adminId, title) =>
    adminApi.post(`/conversations?adminId=${adminId}&title=${title || ''}`),
  getConversations: (adminId) =>
    adminApi.get(`/conversations?adminId=${adminId}`),
  sendMessage: (adminId, conversationId, content) =>
    adminApi.post(`/messages?adminId=${adminId}&conversationId=${conversationId}`, { content }),
  getMessages: (conversationId) =>
    adminApi.get(`/messages?conversationId=${conversationId}`),
  deleteConversation: (id) => adminApi.delete(`/conversations/${id}`),
  updateConversation: (id, data) => adminApi.put(`/conversations/${id}`, data),
  submitFeedback: (messageId, feedbackType) =>
    adminApi.post('/messages/feedback', { messageId, feedbackType }),
};

export default function AdminChat() {
  const navigate = useNavigate();
  const adminId = parseInt(localStorage.getItem('adminId'));
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [processingStep, setProcessingStep] = useState(null);
  const [currentTaskType, setCurrentTaskType] = useState(null);
  const [menuOpenId, setMenuOpenId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConversationId, setDeleteConversationId] = useState(null);
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    document.title = 'AI 知识系统-管理助手';
    return () => {
      document.title = 'AI 知识系统';
    };
  }, []);

  useEffect(() => {
    const adminToken = localStorage.getItem('adminToken');
    if (!adminToken) {
      navigate('/admin/login');
      return;
    }
    if (!adminId) {
      navigate('/admin/login');
      return;
    }
    loadConversations();
  }, [adminId, navigate]);

  useEffect(() => {
    if (currentConversation) {
      loadMessages(currentConversation.id);
    }
  }, [currentConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const getFileInfo = (fullName) => {
    if (!fullName) return { icon: '📄', name: '相关文档' };

    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_/i;
    const cleanName = fullName.replace(uuidRegex, '');

    const ext = cleanName.split('.').pop().toLowerCase();
    let icon = '📄';
    switch (ext) {
      case 'pdf': icon = '📕'; break;
      case 'doc':
      case 'docx': icon = '📘'; break;
      case 'txt': icon = '📄'; break;
      case 'md': icon = '📝'; break;
      case 'xlsx':
      case 'xls': icon = '📗'; break;
      case 'ppt':
      case 'pptx': icon = '📙'; break;
      case 'zip':
      case 'rar': icon = '📦'; break;
      default: icon = '📄';
    }

    return { icon, name: cleanName };
  };

  const renderSources = (sourcesJson) => {
    if (!sourcesJson) return null;
    try {
      const sources = JSON.parse(sourcesJson);
      if (!Array.isArray(sources) || sources.length === 0) return null;
      return (
        <div className="message-sources">
          <h4>参考来源:</h4>
          <ul>
            {sources.map((s, i) => {
              const { icon, name } = getFileInfo(s.doc || s.doc_name);
              return (
                <li key={i}>
                  {s.source && (s.source.startsWith('http://') || s.source.startsWith('https://')) ? (
                      <span className="source-link" onClick={() => window.open(s.source, '_blank')}>
                        {icon} {name}
                      </span>
                  ) : (
                      <span className="source-link" onClick={() => window.open(`/knowledge?docId=${s.doc_id || s.docId}&page=${s.page}`, '_blank')}>
                        {icon} {name}
                      </span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      );
    } catch (e) {
      console.error("Parse sources failed", e);
      return null;
    }
  };

  const getTaskTypeBadge = (taskType) => {
    const info = TASK_TYPE_INFO[taskType] || TASK_TYPE_INFO.unknown;
    return (
      <span
        className="task-type-badge"
        style={{ backgroundColor: info.color + '20', color: info.color }}
        title={`任务类型: ${info.label}`}
      >
        {info.icon} {info.label}
      </span>
    );
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpenId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleMenuClick = (id, e) => {
    e.stopPropagation();
    setMenuOpenId(menuOpenId === id ? null : id);
  };

  const handlePin = async (conv, e) => {
    e.stopPropagation();
    setMenuOpenId(null);
    try {
      await adminChatAPI.updateConversation(conv.id, { isPinned: !conv.isPinned });
      loadConversations();
    } catch (err) {
      console.error('更新置顶失败', err);
    }
  };

  const handleRenameStart = (conv, e) => {
    e.stopPropagation();
    setMenuOpenId(null);
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleRenameSave = async (id) => {
    try {
      await adminChatAPI.updateConversation(id, { title: editTitle });
      setEditingId(null);
      loadConversations();
    } catch (err) {
      console.error('重命名失败', err);
    }
  };

  const handleRenameKeyDown = (e, id) => {
    if (e.key === 'Enter') {
      handleRenameSave(id);
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  const handleDelete = (id, e) => {
    e.stopPropagation();
    setMenuOpenId(null);
    setDeleteConversationId(id);
    setShowDeleteConfirm(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConversationId) return;

    try {
      await adminChatAPI.deleteConversation(deleteConversationId);
      setConversations(conversations.filter(c => c.id !== deleteConversationId));
      if (currentConversation?.id === deleteConversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('删除会话失败:', err);
    } finally {
      setShowDeleteConfirm(false);
      setDeleteConversationId(null);
    }
  };

  const handleDeleteCancel = () => {
    setShowDeleteConfirm(false);
    setDeleteConversationId(null);
  };

  const loadConversations = async () => {
    try {
      const response = await adminChatAPI.getConversations(adminId);
      setConversations(response.data.data || []);
    } catch (err) {
      console.error('加载会话失败:', err);
    }
  };

  const loadMessages = async (conversationId) => {
    try {
      console.log('=== AdminChat: Loading messages for conversationId:', conversationId);
      const response = await adminChatAPI.getMessages(conversationId);
      console.log('=== AdminChat: Messages response:', response);
      const messages = response.data.data || [];
      const messagesWithFeedback = messages.map(msg => ({
        ...msg,
        feedbackType: msg.feedbackType || msg.feedback || null
      }));
      messagesWithFeedback.sort((a, b) => new Date(a.createTime) - new Date(b.createTime));
      setMessages(messagesWithFeedback);
    } catch (err) {
      console.error('加载消息失败:', err);
    }
  };

  const handleCreateConversation = async () => {
    try {
      const response = await adminChatAPI.createConversation(adminId, '新对话');
      setConversations([response.data.data, ...conversations]);
      setCurrentConversation(response.data.data);
    } catch (err) {
      console.error('创建会话失败:', err);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;
    if (!currentConversation) return;

    const userMessage = {
      id: Date.now(),
      conversationId: currentConversation.id,
      role: 'user',
      content: inputMessage,
      createTime: new Date().toISOString()
    };

    const thinkingMessageId = Date.now() + 1;
    const thinkingMessage = {
      id: thinkingMessageId,
      conversationId: currentConversation.id,
      role: 'assistant',
      content: '',
      isStreaming: true,
      processingStep: null,
      taskType: null,
      createTime: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage, thinkingMessage]);
    setInputMessage('');
    setLoading(true);
    setProcessingStep('understanding');
    setCurrentTaskType(null);

    try {
      const response = await adminChatAPI.sendMessage(adminId, currentConversation.id, inputMessage);

      setProcessingStep('retrieving');

      setTimeout(() => {
        setProcessingStep('generating');
      }, 300);

      setTimeout(() => {
        const aiMessage = {
          id: response.data.data.id || thinkingMessageId,
          conversationId: currentConversation.id,
          role: 'assistant',
          content: response.data.data.content,
          sources: response.data.data.sources,
          feedbackType: response.data.data.feedbackType || null,
          taskType: response.data.data.taskType || null,
          createTime: response.data.data.createTime || new Date().toISOString()
        };

        setMessages(prev => prev.map(msg => msg.id === thinkingMessageId ? aiMessage : msg));
        setLoading(false);
        setProcessingStep(null);

        loadConversations();
      }, 500);

    } catch (err) {
      console.error('发送消息失败:', err);
      const errorMessage = {
        id: thinkingMessageId,
        conversationId: currentConversation.id,
        role: 'assistant',
        content: '抱歉，我暂时无法回答这个问题，请稍后再试。',
        createTime: new Date().toISOString()
      };
      setMessages(prev => prev.map(msg => msg.id === thinkingMessageId ? errorMessage : msg));
      setLoading(false);
      setProcessingStep(null);
    }
  };

  const handleFeedback = async (messageId, type) => {
    try {
      await adminChatAPI.submitFeedback(messageId, type);

      setMessages(prev => prev.map(msg =>
        msg.id === messageId
          ? { ...msg, feedbackType: type }
          : msg
      ));

      console.log(`Feedback ${type} recorded for message ${messageId}`);
    } catch (err) {
      console.error('提交反馈失败:', err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminInfo');
    localStorage.removeItem('adminId');
    navigate('/admin/login');
  };

  const getProcessingMessage = () => {
    const steps = {
      understanding: { icon: '🧠', text: '正在理解您的问题...' },
      retrieving: { icon: '🔍', text: '正在检索知识库...' },
      generating: { icon: '✍️', text: '正在生成回答...' }
    };
    return steps[processingStep] || null;
  };

  return (
    <div className="chat-layout">
      <div className="chat-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo" onClick={() => navigate('/admin')}>
            <h2>⚙️ 管理助手</h2>
          </div>
          <button className="new-chat-btn" onClick={handleCreateConversation}>
            <span className="new-chat-icon">+</span> 开启新对话
          </button>
        </div>

        <div className="conversation-list">
          {conversations.map(conv => (
            <div
              key={conv.id}
              className={`conversation-item ${currentConversation?.id === conv.id ? 'active' : ''} ${conv.isPinned ? 'pinned' : ''}`}
              onClick={() => setCurrentConversation(conv)}
            >
              {editingId === conv.id ? (
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={() => handleRenameSave(conv.id)}
                  onKeyDown={(e) => handleRenameKeyDown(e, conv.id)}
                  autoFocus
                  className="rename-input"
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span className="conversation-title">
                  {conv.title || '新对话'}
                </span>
              )}

              <button
                className="menu-btn"
                onClick={(e) => handleMenuClick(conv.id, e)}
              >
                •••
              </button>

              {menuOpenId === conv.id && (
                <div className="context-menu" ref={menuRef}>
                  <div className="menu-item" onClick={(e) => handleRenameStart(conv, e)}>
                    ✏️ 重命名
                  </div>
                  <div className="menu-item" onClick={(e) => handlePin(conv, e)}>
                    {conv.isPinned ? '🚫 取消置顶' : '📌 置顶'}
                  </div>
                  <div className="menu-item delete" onClick={(e) => handleDelete(conv.id, e)}>
                    🗑️ 删除
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="user-profile" onClick={handleLogout} title="点击退出登录">
            <div className="user-avatar">👤</div>
            <span>退出登录</span>
          </div>
        </div>
      </div>

      <div className="chat-main">
        {currentConversation ? (
          <>
            <div className="chat-header">
              <div className="chat-header-left">
                <h3>{currentConversation.title || '新对话'}</h3>
              </div>
            </div>

            <div className="messages-container">
              {messages.length === 0 ? (
                <div className="welcome-screen">
                  <div className="welcome-avatar">⚙️</div>
                  <h1>管理助手</h1>
                  <p className="welcome-hint">我可以帮你进行知识巡检、用户分析、运营统计等管理操作</p>
                </div>
              ) : (
                messages.map((msg, index) => (
                  <div key={msg.id || index} className={`message-row ${msg.role}`}>
                    <div className="message-content-wrapper">
                      <div className="message-avatar">
                        {msg.role === 'user' ? '👤' : '⚙️'}
                      </div>
                      <div className="message-body">
                        {msg.role === 'assistant' && msg.isStreaming && processingStep ? (
                          <div className="processing-indicator">
                            <div className="processing-icon">{getProcessingMessage()?.icon}</div>
                            <div className="processing-text">{getProcessingMessage()?.text}</div>
                            <div className="processing-dots">
                              <span className="dot"></span>
                              <span className="dot"></span>
                              <span className="dot"></span>
                            </div>
                          </div>
                        ) : (
                          <>
                            {msg.role === 'assistant' && msg.taskType && (
                              <div className="message-task-type">
                                {getTaskTypeBadge(msg.taskType)}
                              </div>
                            )}
                            {msg.content}
                            {msg.role === 'assistant' && msg.sources && renderSources(msg.sources)}
                          </>
                        )}
                      </div>
                      {msg.role === 'assistant' && !msg.isStreaming && !msg.processingStep && (
                        <div className="message-feedback">
                          <button
                            className={`feedback-btn like ${msg.feedbackType === 'like' ? 'active' : ''}`}
                            onClick={() => handleFeedback(msg.id, 'like')}
                            title="点赞"
                          >
                            👍
                          </button>
                          <button
                            className={`feedback-btn dislike ${msg.feedbackType === 'dislike' ? 'active' : ''}`}
                            onClick={() => handleFeedback(msg.id, 'dislike')}
                            title="点踩"
                          >
                            👎
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-container">
              <div className="input-wrapper">
                <form className="chat-input-area" onSubmit={handleSendMessage}>
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage(e);
                      }
                    }}
                    placeholder="给管理助手发送消息..."
                    rows={1}
                  />
                  <div className="input-buttons">
                    {loading && (
                      <button
                        type="button"
                        className="stop-btn"
                        onClick={() => setLoading(false)}
                        title="停止生成"
                      >
                        ⏹️
                      </button>
                    )}
                    <button type="submit" className="send-btn" disabled={!inputMessage.trim()}>
                      ➤
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </>
        ) : (
          <div className="welcome-screen">
            <div className="welcome-avatar">⚙️</div>
            <h1>欢迎使用管理助手</h1>
            <p>基于 AI 技术，为您提供智能化的管理操作支持</p>
            <button className="start-btn" onClick={handleCreateConversation}>
              开始新对话
            </button>
          </div>
        )}
      </div>

      {showDeleteConfirm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>确认删除</h3>
            </div>
            <div className="modal-body">
              <p>确定删除此对话吗？</p>
            </div>
            <div className="modal-footer">
              <button className="modal-btn cancel" onClick={handleDeleteCancel}>
                取消
              </button>
              <button className="modal-btn confirm" onClick={handleDeleteConfirm}>
                确定
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}