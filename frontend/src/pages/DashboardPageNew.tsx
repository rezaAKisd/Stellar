import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { highlightsApi } from '../api/highlights';
import { destinationsApi } from '../api/destinations';
import { HighlightProjectResponse } from '../types/highlight';
import { DestinationUsername } from '../types/destination';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { useWebSocketContext } from '../context/WebSocketContext';
import { StatusBadge } from '../components/StatusBadge';
import { ExpirationCountdown } from '../components/ExpirationCountdown';

function ProgressBar({ value }: { value: number }) {
  const percent = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  return (
    <div className="progress-bar">
      <div className="progress-bar__fill" style={{ width: `${percent}%` }} />
    </div>
  );
}

export function DashboardPageNew() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { showToast } = useToast();
  const { isConnected, subscribe } = useWebSocketContext();

  // Tab state
  const [activeTab, setActiveTab] = useState<'direct-link' | 'username-playlists'>('direct-link');

  // Direct Link tab state
  const [link, setLink] = useState('');
  const [projects, setProjects] = useState<HighlightProjectResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);

  // Username/Playlists tab state
  const [username, setUsername] = useState('');
  const [destinations, setDestinations] = useState<DestinationUsername[]>([]);
  const [isFetchingUser, setIsFetchingUser] = useState(false);

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => b.id.localeCompare(a.id)),
    [projects]
  );

  const activeDownloads = projects.filter(
    (p) => p.download_status === 'queued' || p.download_status === 'downloading' ||
           p.export_status === 'queued' || p.export_status === 'building'
  ).length;

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (activeTab === 'username-playlists') {
      loadDestinations();
    }
  }, [activeTab]);

  useEffect(() => {
    const unsubscribers = sortedProjects.map((project) =>
      subscribe(project.id, (msg) => {
        if (!msg.project_id) return;
        setProjects((prev) =>
          prev.map((p) => {
            if (p.id !== msg.project_id) return p;
            if (msg.type === 'download_progress') {
              return { ...p, download_progress: msg.progress ?? p.download_progress, download_status: msg.status ?? p.download_status };
            }
            if (msg.type === 'export_progress') {
              return { ...p, export_progress: msg.progress ?? p.export_progress, export_status: msg.status ?? p.export_status };
            }
            if (msg.type === 'task_complete') {
              // Reload projects from server to get all updated fields
              loadProjects();
              if (msg.status === 'downloaded') {
                return {
                  ...p,
                  download_status: 'downloaded',
                  download_progress: 1.0,
                  export_status: p.export_status || 'not_started', // Ensure export_status is set
                };
              }
              if (msg.status === 'exported') {
                return {
                  ...p,
                  export_status: 'exported',
                  export_progress: 1.0,
                };
              }
              return p;
            }
            if (msg.type === 'error') {
              // Only update the relevant status based on task_type
              if (msg.task_type === 'download') {
                return { ...p, error_message: msg.message || 'Task failed', download_status: 'error' };
              }
              if (msg.task_type === 'build') {
                return { ...p, error_message: msg.message || 'Task failed', export_status: 'error' };
              }
              // Fallback: if task_type is missing, set both (backwards compatibility)
              return { ...p, error_message: msg.message || 'Task failed', download_status: 'error', export_status: 'error' };
            }
            return p;
          })
        );
      })
    );
    return () => {
      unsubscribers.forEach((u) => u());
    };
  }, [sortedProjects, subscribe]);

  const loadProjects = async () => {
    setIsLoading(true);
    try {
      const response = await highlightsApi.getProjects();
      setProjects(response.projects);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDestinations = async () => {
    try {
      const dests = await destinationsApi.listDestinations();
      setDestinations(dests);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to load destinations');
    }
  };

  const addLink = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!link.trim()) return;
    setIsAdding(true);
    try {
      const project = await highlightsApi.addLink({ url: link.trim() });
      setProjects((prev) => [project, ...prev]);
      setLink('');
      showToast('success', 'Highlight added');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to add link');
    } finally {
      setIsAdding(false);
    }
  };

  const fetchUser = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!username.trim()) return;
    setIsFetchingUser(true);
    try {
      const dest = await destinationsApi.addDestination(username.trim());
      setDestinations((prev) => [dest, ...prev]);
      setUsername('');
      showToast('success', `Added @${dest.username}`);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to add destination');
    } finally {
      setIsFetchingUser(false);
    }
  };

  const startDownload = async (projectId: string) => {
    try {
      await highlightsApi.downloadHighlight(projectId);
      setProjects((prev) =>
        prev.map((p) =>
          p.id === projectId ? { ...p, download_status: 'queued', download_progress: 0, error_message: null } : p
        )
      );
      showToast('info', 'Download queued');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to start download');
    }
  };

  const startBuild = async (projectId: string) => {
    try {
      await highlightsApi.buildVideo(projectId);
      setProjects((prev) =>
        prev.map((p) =>
          p.id === projectId ? { ...p, export_status: 'queued', export_progress: 0, error_message: null } : p
        )
      );
      showToast('info', 'Video build queued');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to start build');
    }
  };

  const cancelTask = async (projectId: string) => {
    try {
      await highlightsApi.cancelTask(projectId);
      showToast('success', 'Task cancelled. Files cleaned up. Ready to retry!');
      loadProjects();
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to cancel task');
    }
  };

  const createZip = async (projectId: string) => {
    try {
      await highlightsApi.createZipBundle(projectId);
      showToast('info', 'Creating ZIP bundle...');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to create ZIP');
    }
  };

  const deleteProject = async (projectId: string) => {
    if (!window.confirm('Are you sure you want to delete this project? All files will be removed.')) {
      return;
    }

    try {
      await highlightsApi.deleteProject(projectId);
      showToast('success', 'Project deleted successfully');
      loadProjects();
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to delete project');
    }
  };

  const retryDownload = async (projectId: string) => {
    try {
      await highlightsApi.downloadHighlight(projectId);
      showToast('info', 'Retrying download...');
      loadProjects();
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to retry download');
    }
  };

  return (
    <div className="modern-page">
      {/* Header */}
      <header className="modern-header">
        <div className="modern-header__left">
          <div className="logo">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="8" fill="#3B82F6"/>
              <path d="M16 8L16 24M8 16H24" stroke="white" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <span className="logo__text">Video Downloader</span>
          </div>
        </div>
        <div className="modern-header__right">
          <button className="icon-btn" title="Settings">
            ⚙️
          </button>
          <div className="user-menu">
            <button className="user-menu__btn">
              <span className="user-icon">👤</span>
              <span>{user || 'demo_user'}</span>
              <span className="dropdown-arrow">▼</span>
            </button>
            <div className="user-menu__dropdown">
              <button onClick={logout} className="dropdown-item">
                Sign out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="modern-tabs">
        <button
          className={`modern-tab ${activeTab === 'direct-link' ? 'modern-tab--active' : ''}`}
          onClick={() => setActiveTab('direct-link')}
        >
          <span className="tab-icon">🔗</span>
          Direct Link / ID
        </button>
        <button
          className={`modern-tab ${activeTab === 'username-playlists' ? 'modern-tab--active' : ''}`}
          onClick={() => setActiveTab('username-playlists')}
        >
          <span className="tab-icon">👤</span>
          Username / Playlists
        </button>
      </div>

      {/* Content */}
      <main className="modern-content">
        {activeTab === 'direct-link' && (
          <>
            {/* Input Section */}
            <div className="input-card">
              <form onSubmit={addLink} className="input-form">
                <div className="input-wrapper">
                  <span className="input-icon">🔍</span>
                  <input
                    type="text"
                    className="modern-input"
                    placeholder="Paste direct link or enter ID..."
                    value={link}
                    onChange={(e) => setLink(e.target.value)}
                  />
                </div>
                <button
                  type="submit"
                  className="btn-fetch"
                  disabled={!link.trim() || isAdding}
                >
                  {isAdding ? 'Fetching...' : 'Fetch'}
                </button>
              </form>
              <details className="advanced-options">
                <summary>Advanced options</summary>
                <div className="advanced-content">
                  <p className="muted">Advanced options coming soon...</p>
                </div>
              </details>
            </div>

            {/* Projects Table */}
            {isLoading ? (
              <div className="loading-state">Loading...</div>
            ) : sortedProjects.length === 0 ? (
              <div className="empty-state-card">
                <div className="empty-icon">⬇️</div>
                <h3>No downloads yet</h3>
                <p>Add a link or enter an ID to start downloading videos.</p>
                <button className="btn-empty-action" onClick={() => {}}>
                  🔗 Add a link to start
                </button>
              </div>
            ) : (
              <div className="projects-table-card">
                <table className="modern-table">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Type</th>
                      <th>Count</th>
                      <th>Progress</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedProjects.map((p) => (
                      <tr
                        key={p.id}
                        className="table-row-clickable"
                        onClick={() => navigate(`/highlights/${p.id}`)}
                      >
                        <td>
                          <div className="item-cell">
                            <div className="item-icon">🎬</div>
                            <div>
                              <div className="item-title">{p.title || p.id}</div>
                              {p.error_message && (
                                <div className="item-error">{p.error_message}</div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td>Video</td>
                        <td>{p.item_count}</td>
                        <td>
                          <div className="progress-cell">
                            {p.download_status === 'queued' && (
                              <>
                                <ProgressBar value={0} />
                                <span className="progress-text">Queued</span>
                              </>
                            )}
                            {p.download_status === 'downloading' && (
                              <>
                                <ProgressBar value={p.download_progress * 100} />
                                <span className="progress-text">
                                  {Math.round(p.download_progress * 100)}%
                                </span>
                              </>
                            )}
                            {p.export_status === 'queued' && (
                              <>
                                <ProgressBar value={0} />
                                <span className="progress-text">Queued</span>
                              </>
                            )}
                            {p.export_status === 'building' && (
                              <>
                                <ProgressBar value={p.export_progress * 100} />
                                <span className="progress-text">
                                  {Math.round(p.export_progress * 100)}%
                                </span>
                              </>
                            )}
                            {p.download_status === 'downloaded' && p.export_status === 'not_started' && (
                              <span className="progress-text">—</span>
                            )}
                            {p.export_status === 'exported' && (
                              <span className="progress-text">—</span>
                            )}
                          </div>
                        </td>
                        <td>
                          {p.download_status === 'queued' && (
                            <StatusBadge status="Queued" variant="queued" />
                          )}
                          {p.download_status === 'downloading' && (
                            <StatusBadge status="Downloading" variant="downloading" />
                          )}
                          {p.download_status === 'downloaded' && p.export_status === 'not_started' && (
                            <StatusBadge status="Downloaded" variant="downloaded" />
                          )}
                          {p.export_status === 'queued' && (
                            <StatusBadge status="Queued" variant="queued" />
                          )}
                          {p.export_status === 'building' && (
                            <StatusBadge status="Building" variant="downloading" />
                          )}
                          {p.export_status === 'exported' && (
                            <StatusBadge status="Completed" variant="completed" />
                          )}
                          {p.download_status === 'idle' && (
                            <StatusBadge status="Ready" variant="ready" />
                          )}
                        </td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="action-buttons-compact">
                            {p.download_status === 'downloading' && (
                              <button
                                className="btn-action btn-action--danger"
                                onClick={() => cancelTask(p.id)}
                              >
                                ✕ Cancel
                              </button>
                            )}
                            {p.download_status === 'downloaded' && p.export_status === 'not_started' && (
                              <>
                                <button
                                  className="btn-action btn-action--primary"
                                  onClick={() => startBuild(p.id)}
                                >
                                  🎬 Merge Video
                                </button>
                                <button
                                  className="btn-action"
                                  onClick={() => createZip(p.id)}
                                >
                                  📦 Download ZIP
                                </button>
                              </>
                            )}
                            {p.export_status === 'building' && (
                              <button
                                className="btn-action btn-action--danger"
                                onClick={() => cancelTask(p.id)}
                              >
                                ✕ Cancel
                              </button>
                            )}
                            {p.export_status === 'exported' && p.merged_video_url && (
                              <button
                                className="btn-action btn-action--primary"
                                onClick={() => navigate(`/highlights/${p.id}`)}
                              >
                                ▶ Show Video
                              </button>
                            )}
                            {p.download_status === 'idle' && (
                              <button
                                className="btn-action"
                                onClick={() => startDownload(p.id)}
                              >
                                ⬇️ Download
                              </button>
                            )}
                            {p.download_status === 'error' && (
                              <button
                                className="btn-action btn-action--warning"
                                onClick={() => retryDownload(p.id)}
                              >
                                🔄 Retry
                              </button>
                            )}
                            <button
                              className="btn-action btn-action--danger-outline"
                              onClick={() => deleteProject(p.id)}
                              title="Delete project"
                            >
                              🗑️ Remove
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {activeTab === 'username-playlists' && (
          <>
            {/* Username Input */}
            <div className="input-card">
              <form onSubmit={fetchUser} className="input-form">
                <div className="input-wrapper">
                  <span className="input-icon">👤</span>
                  <input
                    type="text"
                    className="modern-input"
                    placeholder="Enter username..."
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <button
                  type="submit"
                  className="btn-fetch"
                  disabled={!username.trim() || isFetchingUser}
                >
                  {isFetchingUser ? 'Adding...' : 'Fetch Playlists'}
                </button>
              </form>
            </div>

            {/* Destinations List */}
            {destinations.length === 0 ? (
              <div className="empty-state-card">
                <div className="empty-icon">⬇️</div>
                <h3>No downloads yet</h3>
                <p>Add a link or enter an ID to start downloading videos.</p>
                <button className="btn-empty-action">
                  🔗 Add a link to start
                </button>
              </div>
            ) : (
              <div className="destinations-card">
                <h3 className="destinations-title">Saved Usernames</h3>
                <div className="destinations-list">
                  {destinations.map((dest) => (
                    <div
                      key={dest.id}
                      className="destination-row"
                      onClick={() => navigate(`/destinations/${dest.id}`)}
                    >
                      <div className="destination-avatar">
                        {dest.avatar_url ? (
                          <img src={dest.avatar_url} alt={dest.username} />
                        ) : (
                          <div className="avatar-placeholder">👤</div>
                        )}
                      </div>
                      <div className="destination-info">
                        <div className="destination-username">@{dest.username}</div>
                        {dest.display_name && (
                          <div className="destination-display-name">{dest.display_name}</div>
                        )}
                      </div>
                      <div className="destination-arrow">→</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Footer Status Bar */}
      <footer className="modern-footer">
        <div className="footer-status">
          <span className={`status-indicator ${isConnected ? 'status-indicator--online' : 'status-indicator--offline'}`}>
            {isConnected ? '🟢 Online' : '🔴 Offline'}
          </span>
          <span className="status-info">
            🔄 Active Downloads: {activeDownloads}
          </span>
        </div>
        <div className="footer-version">v1.0.0</div>
      </footer>
    </div>
  );
}
