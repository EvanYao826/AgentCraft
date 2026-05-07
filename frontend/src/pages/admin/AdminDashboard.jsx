import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import './AdminDashboard.css';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const location = useLocation();
  const [adminInfo, setAdminInfo] = useState(null);
  const [activeMenu, setActiveMenu] = useState('users');

  useEffect(() => {
    document.title = 'AI 知识系统-管理后台';
    return () => {
      document.title = 'AI 知识系统';
    };
  }, []);

  useEffect(() => {
    const info = localStorage.getItem('adminInfo');
    if (!info) {
      navigate('/admin/login');
      return;
    }
    setAdminInfo(JSON.parse(info));

    const path = location.pathname;
    if (path.includes('/dashboard')) setActiveMenu('dashboard');
    else if (path.includes('/users')) setActiveMenu('users');
    else if (path.includes('/knowledge')) setActiveMenu('knowledge');
    else if (path.includes('/logs')) setActiveMenu('logs');
    else if (path.includes('/agent-runs')) setActiveMenu('agent-runs');
    else if (path.includes('/inspection')) setActiveMenu('inspection');
    else if (path.includes('/reports')) setActiveMenu('reports');
    else if (path.includes('/chat')) setActiveMenu('chat');
  }, [navigate, location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminInfo');
    navigate('/admin/login');
  };

  const menuItems = [
    { id: 'chat', label: '管理助手', icon: '⚙️', path: '/admin/chat' },
    { id: 'dashboard', label: '仪表盘', icon: '📊', path: '/admin/dashboard' },
    { id: 'users', label: '用户管理', icon: '👥', path: '/admin/users' },
    { id: 'knowledge', label: '知识库管理', icon: '📚', path: '/admin/knowledge' },
    { id: 'logs', label: '问答日志', icon: '📝', path: '/admin/logs' },
    { id: 'agent-runs', label: 'Agent执行记录', icon: '🔄', path: '/admin/agent-runs' },
    { id: 'inspection', label: '知识巡检', icon: '🔍', path: '/admin/inspection' },
    { id: 'reports', label: '自动报表', icon: '📈', path: '/admin/reports' },
  ];

  const handleMenuClick = (path) => {
    navigate(path);
  };

  return (
    <div className="admin-layout">
      <div className="admin-sidebar">
        <div className="sidebar-header">
          <h2>🤖 AI知识管理系统</h2>
        </div>

        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            <div
              key={item.id}
              className={`nav-item ${activeMenu === item.id ? 'active' : ''}`}
              onClick={() => handleMenuClick(item.path)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="admin-info">
            <div className="admin-name">{adminInfo?.username}</div>
            <div className="admin-role">{adminInfo?.role}</div>
          </div>
          <button className="btn btn-danger logout-btn" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </div>

      <div className="admin-main">
        <Outlet />
      </div>
    </div>
  );
}
