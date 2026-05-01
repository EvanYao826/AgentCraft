import { useState, useEffect } from 'react';
import './AdminDashboard.css';

const priorityColors = {
  '高': '#ff4d4f',
  '中': '#faad14',
  '低': '#52c41a'
};

const suggestionTypeLabels = {
  '紧急补库': '紧急',
  '建议补库': '建议',
  '观察': '观察'
};

export default function KnowledgeInspection() {
  const [activeTab, setActiveTab] = useState('unanswered');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    minCount: 1,
    clusterThreshold: 3
  });
  const [expandedCluster, setExpandedCluster] = useState(null);

  useEffect(() => {
    if (activeTab === 'unanswered') {
      fetchAnalysis();
    } else {
      fetchLibraryInspection();
    }
  }, [activeTab]);

  const fetchAnalysis = async () => {
    setLoading(true);
    try {
      let url = `/api/admin/knowledge-inspection/unanswered/analyze?minCount=${filters.minCount}&clusterThreshold=${filters.clusterThreshold}`;
      if (filters.startDate) url += `&startDate=${filters.startDate}`;
      if (filters.endDate) url += `&endDate=${filters.endDate}`;

      const token = localStorage.getItem('adminToken');
      const response = await fetch(url, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      const result = await response.json();

      if (result.code === 200) {
        setData(result.data);
      }
    } catch (error) {
      console.error('获取分析数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchLibraryInspection = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.minChunkLength) params.append('minChunkLength', filters.minChunkLength);
      if (filters.outdatedDays) params.append('outdatedDays', filters.outdatedDays);
      if (filters.unaccessedDays) params.append('unaccessedDays', filters.unaccessedDays);
      if (filters.similarityThreshold) params.append('similarityThreshold', filters.similarityThreshold);

      const token = localStorage.getItem('adminToken');
      const response = await fetch(`/api/admin/knowledge-inspection/library/analyze?${params.toString()}`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      const result = await response.json();

      if (result.code === 200) {
        setData(result.data);
      }
    } catch (error) {
      console.error('获取巡检数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    if (activeTab === 'unanswered') {
      fetchAnalysis();
    } else {
      fetchLibraryInspection();
    }
  };

  const handleExport = () => {
    if (!data?.exportData || data.exportData.length === 0) {
      alert('没有可导出的数据');
      return;
    }

    const headers = ['类型', '名称', '问题', '详情'];
    const rows = data.exportData.map(item => [
      item.type,
      item.name,
      item.issue,
      item.detail
    ]);

    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `知识库巡检_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const formatDate = (date) => {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('zh-CN');
  };

  return (
    <div className="admin-panel">
      <div className="panel-header">
        <h2>🔍 知识巡检</h2>
        <p>分析未命中问题，检测重复文档、低质量Chunk、过期知识和无人访问文档</p>
      </div>

      <div className="tab-bar">
        <button
          className={`tab-btn ${activeTab === 'unanswered' ? 'active' : ''}`}
          onClick={() => setActiveTab('unanswered')}
        >
          📊 未命中问题分析
        </button>
        <button
          className={`tab-btn ${activeTab === 'library' ? 'active' : ''}`}
          onClick={() => setActiveTab('library')}
        >
          📚 知识库巡检
        </button>
      </div>

      {activeTab === 'unanswered' && (
        <>
          <div className="search-bar">
            <div className="search-row">
              <div className="search-item">
                <label>开始日期:</label>
                <input
                  type="date"
                  value={filters.startDate}
                  onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
                />
              </div>
              <div className="search-item">
                <label>结束日期:</label>
                <input
                  type="date"
                  value={filters.endDate}
                  onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
                />
              </div>
              <div className="search-item">
                <label>最小出现次数:</label>
                <input
                  type="number"
                  min="1"
                  value={filters.minCount}
                  onChange={(e) => setFilters({ ...filters, minCount: parseInt(e.target.value) || 1 })}
                />
              </div>
              <div className="search-item">
                <label>聚类阈值:</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={filters.clusterThreshold}
                  onChange={(e) => setFilters({ ...filters, clusterThreshold: parseInt(e.target.value) || 3 })}
                />
              </div>
              <div className="search-actions">
                <button className="btn btn-primary" onClick={handleSearch}>分析</button>
                <button className="btn btn-default" onClick={handleExport}>导出</button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="admin-card">
              <div className="loading" style={{ textAlign: 'center', padding: '40px' }}>
                分析中...
              </div>
            </div>
          ) : data ? (
            <>
              <div className="admin-card">
                <div className="card-header">
                  <h2>📊 分析概览</h2>
                </div>
                <div className="stats-grid">
                  <div className="stat-item">
                    <div className="stat-value">{data.totalUnansweredCount}</div>
                    <div className="stat-label">未命中问题总数</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value">{data.totalUniqueQuestions}</div>
                    <div className="stat-label">独立问题数</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value">{data.clusterCount}</div>
                    <div className="stat-label">主题聚类数</div>
                  </div>
                </div>
              </div>

              <div className="admin-card">
                <div className="card-header">
                  <h2>🏷️ 高频未命中主题</h2>
                </div>
                {data.clusters && data.clusters.length > 0 ? (
                  <div className="cluster-list">
                    {data.clusters.map((cluster, index) => (
                      <div
                        key={index}
                        className="cluster-item"
                        onClick={() => setExpandedCluster(expandedCluster === index ? null : index)}
                      >
                        <div className="cluster-header">
                          <div className="cluster-info">
                            <span className="cluster-topic">{cluster.topic}</span>
                            <span className="cluster-count">出现 {cluster.totalCount} 次</span>
                          </div>
                          <div className="cluster-arrow">
                            {expandedCluster === index ? '▲' : '▼'}
                          </div>
                        </div>
                        {expandedCluster === index && (
                          <div className="cluster-details">
                            <div className="cluster-summary">
                              <strong>主题摘要:</strong> {cluster.topicSummary}
                            </div>
                            <div className="cluster-keywords">
                              <strong>关键词:</strong>
                              {cluster.suggestedKeywords?.map((kw, i) => (
                                <span key={i} className="keyword-tag">{kw}</span>
                              ))}
                            </div>
                            <div className="cluster-questions">
                              <strong>相关问题:</strong>
                              <ul>
                                {cluster.questions?.slice(0, 5).map((q, i) => (
                                  <li key={i}>{q}</li>
                                ))}
                                {cluster.questions?.length > 5 && (
                                  <li className="more-questions">... 还有 {cluster.questions.length - 5} 个问题</li>
                                )}
                              </ul>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty" style={{ textAlign: 'center', padding: '40px' }}>
                    暂无聚类数据
                  </div>
                )}
              </div>

              <div className="admin-card">
                <div className="card-header">
                  <h2>💡 补库建议</h2>
                </div>
                {data.suggestions && data.suggestions.length > 0 ? (
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>优先级</th>
                        <th>主题</th>
                        <th>建议类型</th>
                        <th>问题数量</th>
                        <th>相关分类</th>
                        <th>建议内容</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.suggestions.map((suggestion, index) => (
                        <tr key={index}>
                          <td>
                            <span
                              className="status-badge"
                              style={{
                                backgroundColor: priorityColors[suggestion.priority] + '20',
                                color: priorityColors[suggestion.priority]
                              }}
                            >
                              {suggestion.priority}
                            </span>
                          </td>
                          <td>{suggestion.topic}</td>
                          <td>{suggestion.suggestionType}</td>
                          <td>{suggestion.questionCount}</td>
                          <td>{suggestion.relatedCategory}</td>
                          <td className="ellipsis" title={suggestion.suggestion}>
                            {suggestion.suggestion}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="empty" style={{ textAlign: 'center', padding: '40px' }}>
                    暂无补库建议
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
        </>
      )}

      {activeTab === 'library' && (
        <>
          <div className="search-bar">
            <div className="search-row">
              <div className="search-item">
                <label>过期天数:</label>
                <input
                  type="number"
                  min="1"
                  placeholder="180"
                  value={filters.outdatedDays || ''}
                  onChange={(e) => setFilters({ ...filters, outdatedDays: parseInt(e.target.value) || undefined })}
                />
              </div>
              <div className="search-item">
                <label>无人访问天数:</label>
                <input
                  type="number"
                  min="1"
                  placeholder="90"
                  value={filters.unaccessedDays || ''}
                  onChange={(e) => setFilters({ ...filters, unaccessedDays: parseInt(e.target.value) || undefined })}
                />
              </div>
              <div className="search-item">
                <label>最小Chunk长度:</label>
                <input
                  type="number"
                  min="1"
                  placeholder="10"
                  value={filters.minChunkLength || ''}
                  onChange={(e) => setFilters({ ...filters, minChunkLength: parseInt(e.target.value) || undefined })}
                />
              </div>
              <div className="search-item">
                <label>相似度阈值:</label>
                <input
                  type="number"
                  min="0.1"
                  max="1"
                  step="0.1"
                  placeholder="0.8"
                  value={filters.similarityThreshold || ''}
                  onChange={(e) => setFilters({ ...filters, similarityThreshold: parseFloat(e.target.value) || undefined })}
                />
              </div>
              <div className="search-actions">
                <button className="btn btn-primary" onClick={handleSearch}>巡检</button>
                <button className="btn btn-default" onClick={handleExport}>导出</button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="admin-card">
              <div className="loading" style={{ textAlign: 'center', padding: '40px' }}>
                巡检中...
              </div>
            </div>
          ) : data && data.stats ? (
            <>
              <div className="admin-card">
                <div className="card-header">
                  <h2>📊 巡检概览</h2>
                </div>
                <div className="stats-grid">
                  <div className="stat-item">
                    <div className="stat-value">{data.stats.totalDocs || 0}</div>
                    <div className="stat-label">文档总数</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value">{data.stats.totalChunks || 0}</div>
                    <div className="stat-label">Chunk总数</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value" style={{ color: '#ff4d4f' }}>{data.stats.duplicateDocGroups || 0}</div>
                    <div className="stat-label">重复文档组</div>
                  </div>
                </div>
                <div className="stats-grid" style={{ marginTop: '16px' }}>
                  <div className="stat-item">
                    <div className="stat-value" style={{ color: '#faad14' }}>{data.stats.lowQualityChunkCount || 0}</div>
                    <div className="stat-label">低质量Chunk</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value" style={{ color: '#52c41a' }}>{data.stats.outdatedDocCount || 0}</div>
                    <div className="stat-label">过期文档</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value" style={{ color: '#722ed1' }}>{data.stats.unaccessedDocCount || 0}</div>
                    <div className="stat-label">无人访问文档</div>
                  </div>
                </div>
              </div>

              {data.duplicateDocs && data.duplicateDocs.length > 0 && (
                <div className="admin-card">
                  <div className="card-header">
                    <h2>📄 重复文档</h2>
                  </div>
                  <div className="issue-list">
                    {data.duplicateDocs.map((group, gIndex) => (
                      <div key={gIndex} className="issue-group">
                        <div className="issue-group-header">
                          <span className="issue-tag duplicate">重复组 {gIndex + 1}</span>
                          <span className="issue-count">{group.documents?.length || 0} 个文档</span>
                          <span className="issue-similarity">相似度: {(group.similarity * 100).toFixed(0)}%</span>
                        </div>
                        <table className="admin-table">
                          <thead>
                            <tr>
                              <th>文档名称</th>
                              <th>分类</th>
                              <th>创建时间</th>
                            </tr>
                          </thead>
                          <tbody>
                            {group.documents?.map((doc, dIndex) => (
                              <tr key={dIndex}>
                                <td>{doc.docName}</td>
                                <td>{doc.categoryName}</td>
                                <td>{formatDate(doc.createTime)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {data.lowQualityChunks && data.lowQualityChunks.length > 0 && (
                <div className="admin-card">
                  <div className="card-header">
                    <h2>⚠️ 低质量Chunk</h2>
                  </div>
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>文档</th>
                        <th>Chunk索引</th>
                        <th>问题类型</th>
                        <th>描述</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.lowQualityChunks.slice(0, 20).map((chunk, index) => (
                        <tr key={index}>
                          <td>{chunk.docName}</td>
                          <td>#{chunk.chunkIndex}</td>
                          <td><span className="status-badge warning">{chunk.issueType}</span></td>
                          <td className="ellipsis" title={chunk.issueDescription}>{chunk.issueDescription}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {data.lowQualityChunks.length > 20 && (
                    <div className="more-hint">还有 {data.lowQualityChunks.length - 20} 条...</div>
                  )}
                </div>
              )}

              {data.outdatedDocs && data.outdatedDocs.length > 0 && (
                <div className="admin-card">
                  <div className="card-header">
                    <h2>📅 过期文档</h2>
                  </div>
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>文档名称</th>
                        <th>分类</th>
                        <th>创建时间</th>
                        <th>距今天数</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.outdatedDocs.slice(0, 20).map((doc, index) => (
                        <tr key={index}>
                          <td>{doc.docName}</td>
                          <td>{doc.categoryName}</td>
                          <td>{formatDate(doc.createTime)}</td>
                          <td><span className="status-badge error">{doc.daySinceUpdate}天</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {data.outdatedDocs.length > 20 && (
                    <div className="more-hint">还有 {data.outdatedDocs.length - 20} 条...</div>
                  )}
                </div>
              )}

              {data.unaccessedDocs && data.unaccessedDocs.length > 0 && (
                <div className="admin-card">
                  <div className="card-header">
                    <h2>👁️ 无人访问文档</h2>
                  </div>
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>文档名称</th>
                        <th>分类</th>
                        <th>访问次数</th>
                        <th>距今未访问</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.unaccessedDocs.slice(0, 20).map((doc, index) => (
                        <tr key={index}>
                          <td>{doc.docName}</td>
                          <td>{doc.categoryName}</td>
                          <td>{doc.accessCount}</td>
                          <td><span className="status-badge purple">{doc.daySinceAccess}天</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {data.unaccessedDocs.length > 20 && (
                    <div className="more-hint">还有 {data.unaccessedDocs.length - 20} 条...</div>
                  )}
                </div>
              )}

              {(!data.duplicateDocs?.length && !data.lowQualityChunks?.length && !data.outdatedDocs?.length && !data.unaccessedDocs?.length) && (
                <div className="admin-card">
                  <div className="empty" style={{ textAlign: 'center', padding: '40px' }}>
                    🎉 知识库状态良好，未发现问题！
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="admin-card">
              <div className="empty" style={{ textAlign: 'center', padding: '40px' }}>
                暂无数据
              </div>
            </div>
          )}
        </>
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

        .tab-bar {
          display: flex;
          gap: 12px;
          margin-bottom: 20px;
          border-bottom: 2px solid #f0f0f0;
          padding-bottom: 12px;
        }

        .tab-btn {
          padding: 12px 24px;
          border: none;
          background: transparent;
          font-size: 15px;
          font-weight: 500;
          color: #666;
          cursor: pointer;
          border-radius: 8px;
          transition: all 0.3s;
        }

        .tab-btn:hover {
          background: #f5f5f5;
          color: #333;
        }

        .tab-btn.active {
          background: #1890ff;
          color: white;
        }

        .cluster-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .cluster-item {
          border: 1px solid #e8e8e8;
          border-radius: 8px;
          overflow: hidden;
          cursor: pointer;
          transition: all 0.3s;
        }

        .cluster-item:hover {
          border-color: #40a9ff;
          box-shadow: 0 2px 8px rgba(64, 169, 255, 0.15);
        }

        .cluster-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background-color: #fafafa;
        }

        .cluster-info {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .cluster-topic {
          font-weight: 600;
          color: #333;
          font-size: 15px;
        }

        .cluster-count {
          font-size: 13px;
          color: #999;
          background-color: #fff;
          padding: 4px 10px;
          border-radius: 12px;
        }

        .cluster-arrow {
          font-size: 12px;
          color: #999;
          transition: transform 0.3s;
        }

        .cluster-details {
          padding: 16px;
          background-color: #fff;
          border-top: 1px solid #e8e8e8;
        }

        .cluster-summary, .cluster-keywords, .cluster-questions {
          margin-bottom: 12px;
          font-size: 14px;
          color: #666;
        }

        .cluster-questions ul {
          margin: 8px 0 0 20px;
          padding: 0;
        }

        .cluster-questions li {
          margin-bottom: 6px;
          color: #333;
        }

        .more-questions {
          color: #999 !important;
          font-style: italic;
        }

        .keyword-tag {
          display: inline-block;
          background-color: #e6f7ff;
          color: #1890ff;
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 12px;
          margin-right: 8px;
          margin-top: 4px;
        }

        .ellipsis {
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .issue-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .issue-group {
          border: 1px solid #e8e8e8;
          border-radius: 8px;
          overflow: hidden;
        }

        .issue-group-header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: #fafafa;
          border-bottom: 1px solid #e8e8e8;
        }

        .issue-tag {
          padding: 4px 12px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
        }

        .issue-tag.duplicate {
          background: #fff1f0;
          color: #ff4d4f;
        }

        .issue-count {
          font-size: 13px;
          color: #666;
        }

        .issue-similarity {
          font-size: 13px;
          color: #999;
          margin-left: auto;
        }

        .status-badge {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }

        .status-badge.warning {
          background: #fffbe6;
          color: #faad14;
        }

        .status-badge.error {
          background: #fff1f0;
          color: #ff4d4f;
        }

        .status-badge.purple {
          background: #f9f0ff;
          color: #722ed1;
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
