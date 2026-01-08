import React, { useEffect, useMemo, useState } from 'react';
import { highlightsApi } from '../api/highlights';
import { destinationsApi } from '../api/destinations';
import { HighlightProjectResponse } from '../types/highlight';
import { DestinationUsername, DestinationHighlight } from '../types/destination';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { useWebSocketContext } from '../context/WebSocketContext';
import { Tabs } from '../components/Tabs';
import { StatusBadge } from '../components/StatusBadge';
import { ExpirationCountdown } from '../components/ExpirationCountdown';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function ProgressBar({ value }: { value: number }) {
  const percent = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
  return (
    <div className="progress">
      <div className="progress__bar" style={{ width: `${percent}%` }} />
    </div>
  );
}

function sanitizeTitleForFilename(title: string): string {
  const safe = title.replace(/[^a-zA-Z0-9._-]+/g, '_').replace(/^_+|_+$/g, '');
  return safe || 'highlight';
}

function exportedVideoUrl(project: HighlightProjectResponse): string | null {
  if (project.export_status !== 'exported') return null;
  const base = project.folder_path.replace(/^\.?\/*/, '');
  const rel = base.replace(/^data\//, '');
  const filename = `${sanitizeTitleForFilename(project.title)}_merged.mp4`;
  return `${API_BASE_URL}/files/${rel}/exports/${encodeURIComponent(filename)}`;
}

export function DashboardPage() {
  const { user, logout } = useAuth();
  const { showToast } = useToast();
  const { isConnected, subscribe } = useWebSocketContext();

  // Tab state
  const [activeTab, setActiveTab] = useState('direct-link');

  // Direct Link tab state
  const [link, setLink] = useState('');
  const [projects, setProjects] = useState<HighlightProjectResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);

  // Username/Playlists tab state
  const [username, setUsername] = useState('');
  const [destinations, setDestinations] = useState<DestinationUsername[]>([]);
  const [selectedDestination, setSelectedDestination] = useState<string | null>(null);
  const [highlights, setHighlights] = useState<DestinationHighlight[]>([]);
  const [isFetchingHighlights, setIsFetchingHighlights] = useState(false);
  const [isAddingDestination, setIsAddingDestination] = useState(false);

  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => b.id.localeCompare(a.id)),
    [projects]
  );

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      try {
        const response = await highlightsApi.getProjects();
        if (!cancelled) setProjects(response.projects);
      } catch (e: any) {
        showToast('error', e.response?.data?.detail || 'Failed to load projects');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [showToast]);

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
              return {
                ...p,
                download_status: msg.status === 'downloaded' ? 'downloaded' : p.download_status,
                export_status: msg.status === 'exported' ? 'exported' : p.export_status,
                download_progress: msg.status === 'downloaded' ? 1 : p.download_progress,
                export_progress: msg.status === 'exported' ? 1 : p.export_progress,
              };
            }
            if (msg.type === 'error') {
              return { ...p, error_message: msg.message || 'Task failed' };
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

  const startDownload = async (projectId: string) => {
    try {
      await highlightsApi.downloadHighlight(projectId);
      setProjects((prev) =>
        prev.map((p) =>
          p.id === projectId ? { ...p, download_status: 'queued', download_progress: p.download_progress || 0 } : p
        )
      );
      showToast('info', 'Download started');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to start download');
    }
  };

  const startBuild = async (projectId: string) => {
    try {
      await highlightsApi.buildVideo(projectId);
      setProjects((prev) =>
        prev.map((p) =>
          p.id === projectId ? { ...p, export_status: 'queued', export_progress: p.export_progress || 0 } : p
        )
      );
      showToast('info', 'Build started');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to start build');
    }
  };

  const onLogout = async () => {
    await logout();
    showToast('success', 'Signed out');
  };

  // Load destinations when switching to Username tab
  useEffect(() => {
    if (activeTab === 'username-playlists') {
      loadDestinations();
    }
  }, [activeTab]);

  const loadDestinations = async () => {
    try {
      const dests = await destinationsApi.listDestinations();
      setDestinations(dests);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to load destinations');
    }
  };

  const addDestination = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!username.trim()) return;
    setIsAddingDestination(true);
    try {
      const dest = await destinationsApi.addDestination(username.trim());
      setDestinations((prev) => [dest, ...prev]);
      setUsername('');
      showToast('success', `Destination @${dest.username} added`);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to add destination');
    } finally {
      setIsAddingDestination(false);
    }
  };

  const fetchHighlights = async (usernameId: string) => {
    setIsFetchingHighlights(true);
    setSelectedDestination(usernameId);
    try {
      const hl = await destinationsApi.fetchHighlights(usernameId);
      setHighlights(hl);
      showToast('success', `Fetched ${hl.length} highlights`);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to fetch highlights');
    } finally {
      setIsFetchingHighlights(false);
    }
  };

  const downloadDestinationHighlight = async (usernameId: string, highlightId: string) => {
    try {
      // Auto-refresh highlights first to ensure it still exists
      showToast('info', 'Verifying highlight availability...');
      const refreshedHighlights = await destinationsApi.fetchHighlights(usernameId);

      // Check if highlight still exists
      const highlightExists = refreshedHighlights.some(h => h.highlight_id === highlightId);
      if (!highlightExists) {
        showToast('error', 'Highlight no longer available. It may have been deleted or expired.');
        // Update the highlights list to remove stale ones
        setHighlights(refreshedHighlights);
        return;
      }

      // Proceed with download
      const result = await destinationsApi.downloadHighlight(usernameId, highlightId);
      showToast('success', 'Download started');

      // Reload projects to show the new one
      const response = await highlightsApi.getProjects();
      setProjects(response.projects);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to start download');
    }
  };

  const deleteDestination = async (usernameId: string) => {
    if (!window.confirm('Delete this destination?')) return;
    try {
      await destinationsApi.deleteDestination(usernameId);
      setDestinations((prev) => prev.filter((d) => d.id !== usernameId));
      if (selectedDestination === usernameId) {
        setSelectedDestination(null);
        setHighlights([]);
      }
      showToast('success', 'Destination deleted');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to delete destination');
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

  const cancelTask = async (projectId: string) => {
    try {
      await highlightsApi.cancelTask(projectId);
      showToast('success', 'Task cancelled');
      // Reload projects to update status
      const response = await highlightsApi.getProjects();
      setProjects(response.projects);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to cancel task');
    }
  };

  const deleteProject = async (projectId: string) => {
    if (!window.confirm('Delete this project? All files will be removed.')) return;
    try {
      await highlightsApi.deleteProject(projectId);
      setProjects((prev) => prev.filter((p) => p.id !== projectId));
      showToast('success', 'Project deleted');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to delete project');
    }
  };

  return (
    <div className="page">
      <div className="topbar">
        <div className="topbar__brand">Stellar</div>
        <div className="topbar__right">
          <div className="badge">{isConnected ? 'WS: connected' : 'WS: disconnected'}</div>
          <div className="muted">Signed in as {user}</div>
          <button className="btn btn--danger" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </div>

      <div className="container mt-lg">
        <Tabs
          tabs={[
            { id: 'direct-link', label: 'Direct Link / ID' },
            { id: 'username-playlists', label: 'Username / Playlists' },
          ]}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

        {activeTab === 'direct-link' && (
          <div className="mt-lg">
            <div className="card">
              <div className="card__title">Add highlight link</div>
              <form className="mt-md" onSubmit={addLink}>
                <label className="field">
                  <div className="field__label">Instagram highlight URL or ID</div>
                  <input
                    className="input"
                    value={link}
                    onChange={(e) => setLink(e.target.value)}
                    placeholder="https://www.instagram.com/stories/highlights/..."
                  />
                </label>
                <button className="btn btn--primary mt-md" type="submit" disabled={!link.trim() || isAdding}>
                  {isAdding ? 'Adding…' : 'Add'}
                </button>
              </form>
            </div>

            <div className="card mt-lg">
              <div className="card__title">Projects</div>
              {isLoading ? (
                <div className="muted mt-md">Loading…</div>
              ) : sortedProjects.length === 0 ? (
                <div className="muted mt-md">No projects yet.</div>
              ) : (
                <div className="table-container mt-md">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th>Type</th>
                        <th>Count</th>
                        <th>Download Progress</th>
                        <th>Export Progress</th>
                        <th>Status</th>
                        <th>Expiration</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedProjects.map((p) => (
                        <tr key={p.id}>
                          <td>
                            <div className="table-cell-title">{p.title || p.id}</div>
                            {p.error_message && <div className="error mt-xs">{p.error_message}</div>}
                          </td>
                          <td>Highlight</td>
                          <td>{p.item_count}</td>
                          <td>
                            <div className="progress-cell">
                              <ProgressBar value={p.download_progress * 100} />
                              <span className="progress-text">{Math.round(p.download_progress * 100)}%</span>
                            </div>
                          </td>
                          <td>
                            <div className="progress-cell">
                              <ProgressBar value={p.export_progress * 100} />
                              <span className="progress-text">{Math.round(p.export_progress * 100)}%</span>
                            </div>
                          </td>
                          <td>
                            <div className="status-cell">
                              {p.download_status === 'downloading' ? (
                                <StatusBadge status="Downloading" variant="downloading" />
                              ) : p.download_status === 'downloaded' && p.export_status === 'pending' ? (
                                <StatusBadge status="Downloaded" variant="downloaded" />
                              ) : p.export_status === 'building' ? (
                                <StatusBadge status="Building" variant="downloading" />
                              ) : p.export_status === 'exported' ? (
                                <StatusBadge status="Ready" variant="ready" />
                              ) : p.download_status === 'failed' || p.export_status === 'failed' ? (
                                <StatusBadge status="Error" variant="error" />
                              ) : (
                                <StatusBadge status="Pending" variant="idle" />
                              )}
                            </div>
                          </td>
                          <td>
                            <ExpirationCountdown expiresAt={p.expires_at} isExpired={p.is_expired === 1} />
                          </td>
                          <td>
                            <div className="action-buttons">
                              {p.download_status === 'pending' && (
                                <button
                                  className="btn btn--sm"
                                  onClick={() => startDownload(p.id)}
                                  disabled={false}
                                >
                                  Download
                                </button>
                              )}
                              {p.download_status === 'downloading' && (
                                <button className="btn btn--sm btn--danger" onClick={() => cancelTask(p.id)}>
                                  Cancel
                                </button>
                              )}
                              {p.download_status === 'failed' && (
                                <button className="btn btn--sm" onClick={() => startDownload(p.id)}>
                                  Retry
                                </button>
                              )}
                              {p.download_status === 'downloaded' && p.export_status === 'pending' && (
                                <button className="btn btn--sm" onClick={() => startBuild(p.id)}>
                                  Create Video
                                </button>
                              )}
                              {p.export_status === 'building' && (
                                <button className="btn btn--sm btn--danger" onClick={() => cancelTask(p.id)}>
                                  Cancel
                                </button>
                              )}
                              {p.export_status === 'exported' && p.merged_video_url && (
                                <a className="btn btn--sm btn--primary" href={p.merged_video_url} download>
                                  Show Video
                                </a>
                              )}
                              {p.has_downloads && (
                                <button className="btn btn--sm" onClick={() => createZip(p.id)}>
                                  Download ZIP
                                </button>
                              )}
                              <button className="btn btn--sm btn--danger" onClick={() => deleteProject(p.id)}>
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'username-playlists' && (
          <div className="mt-lg">
            <div className="card">
              <div className="card__title">Add destination username</div>
              <form className="mt-md" onSubmit={addDestination}>
                <label className="field">
                  <div className="field__label">Instagram username</div>
                  <input
                    className="input"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="username"
                  />
                </label>
                <button className="btn btn--primary mt-md" type="submit" disabled={!username.trim() || isAddingDestination}>
                  {isAddingDestination ? 'Adding…' : 'Add'}
                </button>
              </form>
            </div>

            <div className="card mt-lg">
              <div className="card__title">Destination Usernames</div>
              {destinations.length === 0 ? (
                <div className="muted mt-md">No destinations yet.</div>
              ) : (
                <div className="list mt-md">
                  {destinations.map((dest) => (
                    <div key={dest.id} className="list__item">
                      <div className="list__header">
                        <div className="list__title">@{dest.username}</div>
                        {dest.display_name && <div className="muted">{dest.display_name}</div>}
                      </div>
                      <div className="actions mt-md">
                        <button
                          className="btn"
                          onClick={() => fetchHighlights(dest.id)}
                          disabled={isFetchingHighlights && selectedDestination === dest.id}
                        >
                          {isFetchingHighlights && selectedDestination === dest.id ? 'Fetching…' : 'Fetch Highlights'}
                        </button>
                        <button className="btn btn--danger" onClick={() => deleteDestination(dest.id)}>
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedDestination && highlights.length > 0 && (
              <div className="card mt-lg">
                <div className="card__title">Highlights</div>
                <div className="list mt-md">
                  {highlights.map((hl) => (
                    <div key={hl.id} className="list__item">
                      <div className="list__header">
                        <div className="list__title">{hl.name}</div>
                        <div className="muted">{hl.item_count} items</div>
                      </div>
                      <div className="actions mt-md">
                        {hl.project_id ? (
                          <span className="badge">Already downloaded</span>
                        ) : (
                          <button
                            className="btn btn--primary"
                            onClick={() => downloadDestinationHighlight(selectedDestination, hl.highlight_id)}
                          >
                            Download
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
