import { BrowserRouter, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Chat from './pages/Chat';
import Knowledge from './pages/Knowledge';
import Header from './components/Header';
import AdminLogin from './pages/admin/AdminLogin';
import AdminDashboard from './pages/admin/AdminDashboard';
import UserManagement from './pages/admin/UserManagement';
import KnowledgeManagement from './pages/admin/KnowledgeManagement';
import QaLogManagement from './pages/admin/QaLogManagement';
import Dashboard from './pages/admin/Dashboard';
import AgentRunManagement from './pages/admin/AgentRunManagement';
import KnowledgeInspection from './pages/admin/KnowledgeInspection';
import Reports from './pages/admin/Reports';
import AdminChat from './pages/admin/AdminChat';

const Layout = () => {
  const location = useLocation();
  const showHeader = !['/login', '/register'].includes(location.pathname) && !location.pathname.startsWith('/admin');

  return (
    <>
      {showHeader && <Header />}
      <div className={showHeader ? 'main-content-with-header' : ''}>
        <Outlet />
      </div>
    </>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/knowledge" element={<Knowledge />} />
        </Route>

        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminDashboard />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="users" element={<UserManagement />} />
          <Route path="knowledge" element={<KnowledgeManagement />} />
          <Route path="logs" element={<QaLogManagement />} />
          <Route path="agent-runs" element={<AgentRunManagement />} />
          <Route path="inspection" element={<KnowledgeInspection />} />
          <Route path="reports" element={<Reports />} />
          <Route path="chat" element={<AdminChat />} />
        </Route>

        <Route path="/" element={<Navigate to="/chat" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
