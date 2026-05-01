import { useState, useEffect } from 'react';
import './AdminDashboard.css';

export default function Reports() {
  const [activeTab, setActiveTab] = useState('overview');
  const [dateRange, setDateRange] = useState({
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0]
  });
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchReportData();
  }, []);

  const fetchReportData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('startDate', dateRange.startDate);
      params.append('endDate', dateRange.endDate);

      const token = localStorage.getItem('adminToken');
      const response = await fetch(`/api/admin/reports/generate?${params.toString()}`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      const result = await response.json();

      if (result.code === 200) {
        setReportData(result.data);
      }
    } catch (error) {
      console.error('获取报表数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDateRangeChange = (type, value) => {
    setDateRange(prev => ({ ...prev, [type]: value }));
  };

  const handleSearch = () => {
    fetchReportData();
  };

  const handleExport = () => {
    if (!reportData) return;

    const exportData = [];

    if (reportData.hotQuestions) {
      reportData.hotQuestions.weekly?.forEach(item => {
        exportData.push({
          type: '热门问题',
          name: item.question,
          value: item.count,
          category: item.category
        });
      });
    }

    if (reportData.agentPerformance) {
      exportData.push({
        type: 'Agent性能',
        name: '成功率',
        value: reportData.agentPerformance.successRate + '%',
        category: ''
      });
      exportData.push({
        type: 'Agent性能',
        name: '失败率',
        value: reportData.agentPerformance.failureRate + '%',
        category: ''
      });
    }

    if (reportData.toolFailures) {
      reportData.toolFailures.rankings?.forEach(item => {
        exportData.push({
          type: '工具失败',
          name: item.toolName,
          value: item.failureCount,
          category: item.lastError
        });
      });
    }

    const headers = ['类型', '名称', '数值', '详情'];
    const rows = exportData.map(item => [item.type, item.name, item.value, item.category]);
    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `自动报表_${dateRange.endDate}.csv`;
    link.click();
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('zh-CN');
  };

  return (
    <div className="admin-panel">
      <div className="panel-header">
        <h2>📊 自动报表</h2>
        <p>热门问题日报/周报、知识库增长趋势、Agent成功率与失败率趋势、工具调用失败排行</p>
      </div>

      <div className="search-bar">
        <div className="search-row">
          <div className="search-item">
            <label>开始日期:</label>
            <input
              type="date"
              value={dateRange.startDate}
              onChange={(e) => handleDateRangeChange('startDate', e.target.value)}
            />
          </div>
          <div className="search-item">
            <label>结束日期:</label>
            <input
              type="date"
              value={dateRange.endDate}
              onChange={(e) => handleDateRangeChange('endDate', e.target.value)}
            />
          </div>
          <div className="search-actions">
            <button className="btn btn-primary" onClick={handleSearch}>查询</button>
            <button className="btn btn-default" onClick={handleExport}>导出报表</button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="admin-card">
          <div className="loading" style={{ textAlign: 'center', padding: '40px' }}>
            加载中...
          </div>
        </div>
      ) : reportData ? (
        <>
          <div className="admin-card">
            <div className="card-header">
              <h2>📈 报表概览</h2>
            </div>
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-value">{reportData.knowledgeGrowth?.totalDocs || 0}</div>
                <div className="stat-label">文档总数</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{reportData.knowledgeGrowth?.totalChunks || 0}</div>
                <div className="stat-label">Chunk总数</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{reportData.agentPerformance?.totalRuns || 0}</div>
                <div className="stat-label">Agent运行次数</div>
              </div>
            </div>
            <div className="stats-grid" style={{ marginTop: '16px' }}>
              <div className="stat-item">
                <div className="stat-value" style={{ color: '#52c41a' }}>
                  {reportData.agentPerformance?.successRate || 0}%
                </div>
                <div className="stat-label">成功率</div>
              </div>
              <div className="stat-item">
                <div className="stat-value" style={{ color: '#ff4d4f' }}>
                  {reportData.agentPerformance?.failureRate || 0}%
                </div>
                <div className="stat-label">失败率</div>
              </div>
              <div className="stat-item">
                <div className="stat-value" style={{ color: '#faad14' }}>
                  {reportData.toolFailures?.totalFailures || 0}
                </div>
                <div className="stat-label">工具失败次数</div>
              </div>
            </div>
          </div>

          <div className="admin-card">
            <div className="card-header">
              <h2>🔥 热门问题 TOP 10</h2>
            </div>
            {reportData.hotQuestions?.weekly && reportData.hotQuestions.weekly.length > 0 ? (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>排名</th>
                    <th>问题</th>
                    <th>提问次数</th>
                    <th>占比</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.hotQuestions.weekly.map((item, index) => (
                    <tr key={index}>
                      <td>
                        <span className={`rank-badge rank-${index < 3 ? 'top' : 'normal'}`}>
                          {index + 1}
                        </span>
                      </td>
                      <td className="question-text" title={item.question}>
                        {item.question}
                      </td>
                      <td>{item.count}</td>
                      <td>{item.percentage || '-'}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty" style={{ textAlign: 'center', padding: '40px' }}>
                暂无数据
              </div>
            )}
          </div>

          <div className="admin-card">
            <div className="card-header">
              <h2>📚 知识库增长趋势</h2>
            </div>
            <div className="growth-stats">
              <div className="growth-item">
                <span className="growth-label">今日新增文档:</span>
                <span className="growth-value">{reportData.knowledgeGrowth?.newDocsToday || 0}</span>
              </div>
              <div className="growth-item">
                <span className="growth-label">今日新增Chunk:</span>
                <span className="growth-value">{reportData.knowledgeGrowth?.newChunksToday || 0}</span>
              </div>
              <div className="growth-item">
                <span className="growth-label">累计文档:</span>
                <span className="growth-value">{reportData.knowledgeGrowth?.totalDocs || 0}</span>
              </div>
              <div className="growth-item">
                <span className="growth-label">累计Chunk:</span>
                <span className="growth-value">{reportData.knowledgeGrowth?.totalChunks || 0}</span>
              </div>
            </div>
            {reportData.knowledgeGrowth?.docCountTrend && reportData.knowledgeGrowth.docCountTrend.length > 0 && (
              <div className="trend-chart">
                <div className="trend-title">近 {reportData.knowledgeGrowth.docCountTrend.length} 天文档增长趋势</div>
                <div className="trend-bars">
                  {reportData.knowledgeGrowth.docCountTrend.slice(-7).map((point, index) => (
                    <div key={index} className="trend-bar-container">
                      <div
                        className="trend-bar doc-bar"
                        style={{ height: `${Math.max(10, (point.value / Math.max(...reportData.knowledgeGrowth.docCountTrend.map(p => p.value || 1))) * 100)}%` }}
                        title={`${formatDate(point.date)}: ${point.value} 文档`}
                      >
                        <span className="bar-value">{point.value}</span>
                      </div>
                      <div className="trend-date">{formatDate(point.date).slice(5)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="admin-card">
            <div className="card-header">
              <h2>🤖 Agent 性能趋势</h2>
            </div>
            <div className="performance-stats">
              <div className="perf-item">
                <div className="perf-label">总运行次数</div>
                <div className="perf-value">{reportData.agentPerformance?.totalRuns || 0}</div>
              </div>
              <div className="perf-item success">
                <div className="perf-label">成功次数</div>
                <div className="perf-value">{reportData.agentPerformance?.successCount || 0}</div>
              </div>
              <div className="perf-item failure">
                <div className="perf-label">失败次数</div>
                <div className="perf-value">{reportData.agentPerformance?.failureCount || 0}</div>
              </div>
              <div className="perf-item">
                <div className="perf-label">平均耗时</div>
                <div className="perf-value">{(reportData.agentPerformance?.avgDurationMs || 0) / 1000}s</div>
              </div>
            </div>
            {reportData.agentPerformance?.successRateTrend && reportData.agentPerformance.successRateTrend.length > 0 && (
              <div className="trend-chart">
                <div className="trend-title">成功率趋势 (%)</div>
                <div className="trend-bars">
                  {reportData.agentPerformance.successRateTrend.slice(-7).map((point, index) => (
                    <div key={index} className="trend-bar-container">
                      <div
                        className="trend-bar success-bar"
                        style={{ height: `${Math.max(10, point.value)}%` }}
                        title={`${formatDate(point.date)}: ${point.value}%`}
                      >
                        <span className="bar-value">{point.value}%</span>
                      </div>
                      <div className="trend-date">{formatDate(point.date).slice(5)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="admin-card">
            <div className="card-header">
              <h2>⚠️ 工具调用失败排行</h2>
            </div>
            {reportData.toolFailures?.rankings && reportData.toolFailures.rankings.length > 0 ? (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>排名</th>
                    <th>工具名称</th>
                    <th>失败次数</th>
                    <th>失败率</th>
                    <th>最近错误</th>
                    <th>最近失败时间</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.toolFailures.rankings.map((item, index) => (
                    <tr key={index}>
                      <td>
                        <span className={`rank-badge rank-${index < 3 ? 'top' : 'normal'}`}>
                          {index + 1}
                        </span>
                      </td>
                      <td><code className="tool-name">{item.toolName}</code></td>
                      <td><span className="failure-count">{item.failureCount}</span></td>
                      <td>{item.failureRate}%</td>
                      <td className="error-text" title={item.lastError}>
                        {item.lastError || '-'}
                      </td>
                      <td>{formatDate(item.lastFailureTime)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty" style={{ textAlign: 'center', padding: '40px' }}>
                🎉 暂无工具调用失败记录
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="admin-card">
          <div className="empty" style={{ textAlign: 'center', padding: '40px' }}>
            暂无数据
          </div>
        </div>
      )}

      <style>{`
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
        }

        .stat-item {
          background: white;
          border: 1px solid #e8e8e8;
          border-radius: 12px;
          padding: 28px 24px;
          color: #333;
          text-align: center;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
          transition: all 0.3s;
        }

        .stat-item:hover {
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
          transform: translateY(-2px);
        }

        .stat-value {
          font-size: 42px;
          font-weight: 800;
          margin-bottom: 12px;
          color: #1890ff;
          letter-spacing: -0.5px;
        }

        .stat-label {
          font-size: 15px;
          color: #666;
          font-weight: 500;
        }

        .rank-badge {
          display: inline-block;
          width: 28px;
          height: 28px;
          line-height: 28px;
          text-align: center;
          border-radius: 50%;
          font-weight: 600;
          font-size: 13px;
        }

        .rank-badge.rank-top {
          background: linear-gradient(135deg, #ff9a56, #ff6b6b);
          color: white;
        }

        .rank-badge.rank-normal {
          background: #f0f0f0;
          color: #666;
        }

        .question-text {
          max-width: 300px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .growth-stats {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
          margin-bottom: 24px;
        }

        .growth-item {
          background: #f8f9fa;
          padding: 16px;
          border-radius: 8px;
          text-align: center;
        }

        .growth-label {
          display: block;
          font-size: 13px;
          color: #666;
          margin-bottom: 8px;
        }

        .growth-value {
          font-size: 24px;
          font-weight: 700;
          color: #1890ff;
        }

        .trend-chart {
          margin-top: 24px;
          padding-top: 16px;
          border-top: 1px solid #f0f0f0;
        }

        .trend-title {
          font-size: 14px;
          color: #666;
          margin-bottom: 16px;
        }

        .trend-bars {
          display: flex;
          align-items: flex-end;
          justify-content: space-around;
          height: 180px;
          gap: 8px;
        }

        .trend-bar-container {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          height: 100%;
        }

        .trend-bar {
          width: 100%;
          max-width: 40px;
          background: linear-gradient(180deg, #1890ff 0%, #40a9ff 100%);
          border-radius: 4px 4px 0 0;
          display: flex;
          align-items: flex-start;
          justify-content: center;
          transition: height 0.3s;
          position: relative;
        }

        .trend-bar.doc-bar {
          background: linear-gradient(180deg, #1890ff 0%, #40a9ff 100%);
        }

        .trend-bar.success-bar {
          background: linear-gradient(180deg, #52c41a 0%, #73d13d 100%);
        }

        .bar-value {
          font-size: 10px;
          color: white;
          padding: 4px 2px;
          white-space: nowrap;
          overflow: hidden;
        }

        .trend-date {
          font-size: 11px;
          color: #999;
          margin-top: 8px;
        }

        .performance-stats {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
          margin-bottom: 24px;
        }

        .perf-item {
          background: #f8f9fa;
          padding: 20px;
          border-radius: 8px;
          text-align: center;
          border-left: 4px solid #1890ff;
        }

        .perf-item.success {
          border-left-color: #52c41a;
        }

        .perf-item.failure {
          border-left-color: #ff4d4f;
        }

        .perf-label {
          font-size: 13px;
          color: #666;
          margin-bottom: 8px;
        }

        .perf-value {
          font-size: 28px;
          font-weight: 700;
          color: #333;
        }

        .tool-name {
          background: #f5f5f5;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 13px;
          color: #1890ff;
        }

        .failure-count {
          font-weight: 700;
          color: #ff4d4f;
        }

        .error-text {
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          color: #666;
          font-size: 13px;
        }

        .more-hint {
          text-align: center;
          padding: 12px;
          color: #999;
          font-size: 13px;
        }
      `}</style>
    </div>
  );
}
