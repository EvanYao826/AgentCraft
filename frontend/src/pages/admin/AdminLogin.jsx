import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminAuthAPI } from '../../api/admin';
import '../Auth.css';

export default function AdminLogin() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await adminAuthAPI.login(formData.username, formData.password);
      localStorage.setItem('adminToken', response.data.accessToken);
      localStorage.setItem('adminInfo', JSON.stringify(response.data.admin));
      if (response.data.admin && response.data.admin.id) {
        localStorage.setItem('adminId', response.data.admin.id);
      }
      // 使用replace选项，避免登录页面留在历史堆栈中
      navigate('/admin', { replace: true }); // 修正跳转路径
      
      // 替换整个历史记录，使后退按钮不可用
      setTimeout(() => {
        window.history.replaceState(null, null, window.location.href);
      }, 100);
    } catch (err) {
      setError(err.message || '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="particle"></div>
      <div className="particle"></div>
      <div className="particle"></div>
      <div className="particle"></div>
      <div className="particle"></div>
      <div className="particle"></div>
      <div className="particle"></div>
      <div className="particle"></div>
      <div className="particle-line"></div>
      <div className="particle-line"></div>
      <div className="particle-line"></div>
      <div className="particle-line"></div>
      <div className="auth-card">
        <h1 className="auth-title">AI 知识管理系统</h1>
        <h2 className="auth-subtitle">管理员登录</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>用户名</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="请输入管理员用户名"
              required
            />
          </div>

          <div className="form-group">
            <label>密码</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="请输入密码"
              required
            />
          </div>

          {error && <div className="error">{error}</div>}

          <button type="submit" className="btn btn-primary auth-btn" disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        <div className="auth-footer">
          <a href="/login" style={{ textDecoration: 'none', color: '#666' }}>
            返回普通用户登录
          </a>
        </div>
      </div>
    </div>
  );
}
