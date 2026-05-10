import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // 允许携带cookie
});

// 请求拦截器 - 添加Authorization header
api.interceptors.request.use(
  config => {
    const token = getCookie('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    if (response.data.code === 200) {
      // 处理登录和注册响应，存储token到cookie
      if (response.config.url.includes('/auth/login') || response.config.url.includes('/auth/register')) {
        if (response.data.data && response.data.data.accessToken) {
          setCookie('accessToken', response.data.data.accessToken, 1); // 1小时过期
          setCookie('refreshToken', response.data.data.refreshToken, 24); // 24小时过期
        }
      }
      return response.data;
    }
    return Promise.reject(new Error(response.data.message || 'Request failed'));
  },
  error => {
    // 处理401错误，尝试刷新token
    if (error.response && error.response.status === 401) {
      const refreshToken = getCookie('refreshToken');
      if (refreshToken) {
        return api.post('/auth/refresh', {}, {
          headers: {
            Authorization: `Bearer ${refreshToken}`
          }
        }).then(response => {
          if (response.data && response.data.accessToken) {
            setCookie('accessToken', response.data.accessToken, 1);
            setCookie('refreshToken', response.data.refreshToken, 24);
            // 重新发送原请求
            error.config.headers.Authorization = `Bearer ${response.data.accessToken}`;
            return api(error.config);
          }
        }).catch(() => {
          // 刷新token失败，清除cookie并跳转到登录页
          clearCookies();
          window.location.href = '/login';
        });
      } else {
        // 没有refreshToken，跳转到登录页
        clearCookies();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Cookie操作函数
function setCookie(name, value, hours) {
  const expires = new Date();
  expires.setTime(expires.getTime() + hours * 60 * 60 * 1000);
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
}

function getCookie(name) {
  const cookieName = `${name}=`;
  const decodedCookie = decodeURIComponent(document.cookie);
  const cookieArray = decodedCookie.split(';');
  for (let i = 0; i < cookieArray.length; i++) {
    let cookie = cookieArray[i];
    while (cookie.charAt(0) === ' ') {
      cookie = cookie.substring(1);
    }
    if (cookie.indexOf(cookieName) === 0) {
      return cookie.substring(cookieName.length, cookie.length);
    }
  }
  return '';
}

function clearCookies() {
  setCookie('accessToken', '', -1);
  setCookie('refreshToken', '', -1);
  localStorage.removeItem('user');
  localStorage.removeItem('userId');
}

// Auth API
export const authAPI = {
  sendCode: (phone) => api.post(`/auth/sendCode?phone=${phone}`),
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  updateUser: (data) => api.post('/auth/update', data),
};

// Chat API
export const chatAPI = {
  createConversation: (userId, title) =>
    api.post(`/chat/conversations?userId=${userId}&title=${title || ''}`),
  getConversations: (userId) =>
    api.get(`/chat/conversations?userId=${userId}`),
  sendMessage: (data, config) => api.post('/chat/messages', data, config),
  sendMessageStream: async (data, onMessage, onError, onComplete) => {
    try {
      // 获取JWT token
      const token = getCookie('accessToken');
      const headers = {
        'Content-Type': 'application/json',
      };

      // 添加Authorization header
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      console.log('Sending streaming request with token:', token ? 'present' : 'missing');
      const response = await fetch('/api/chat/stream/messages', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(data),
      });

      console.log('Streaming response status:', response.status, response.statusText);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Streaming request failed:', response.status, errorText);
        throw new Error(`HTTP error! status: ${response.status}: ${errorText}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (onComplete) onComplete();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.substring(6).trim();
            if (jsonStr) {
              try {
                const response = JSON.parse(jsonStr);
                onMessage(response);
              } catch (error) {
                console.error('Failed to parse SSE message:', error, jsonStr);
              }
            }
          }
        }
      }
    } catch (error) {
      if (onError) onError(error);
    }
  },
  getMessages: (conversationId) =>
    api.get(`/chat/messages?conversationId=${conversationId}`),
  deleteConversation: (id) => api.delete(`/chat/conversations/${id}`),
  updateConversation: (id, data) => api.put(`/chat/conversations/${id}`, data),
  // 临时图片上传
  uploadImage: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/chat/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  // 查看临时图片
  viewImage: (id) => api.get(`/chat/view/image/${id}`),
  // 提交消息反馈
  submitFeedback: (messageId, feedbackType) => 
    api.post('/chat/messages/feedback', { messageId, feedbackType }),
};

// Knowledge API
export const knowledgeAPI = {
  upload: (file, categoryId) => {
    const formData = new FormData();
    formData.append('file', file);
    if (categoryId) {
      formData.append('categoryId', categoryId);
    }
    return api.post('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  list: (categoryId) =>
    api.get(`/knowledge/list${categoryId ? `?categoryId=${categoryId}` : ''}`),
  delete: (id) => api.delete(`/knowledge/${id}`),
  view: (id, userId) => api.get(`/knowledge/view/${id}?userId=${userId}`),
};

export default api;
