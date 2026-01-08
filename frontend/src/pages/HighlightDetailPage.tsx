import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { highlightsApi } from '../api/highlights';
import { HighlightProjectResponse } from '../types/highlight';
import { useToast } from '../hooks/useToast';
import { useWebSocketContext } from '../context/WebSocketContext';
import { StatusBadge } from '../components/StatusBadge';
import { ExpirationCountdown } from '../components/ExpirationCountdown';

export function HighlightDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { subscribe } = useWebSocketContext();

  const [project, setProject] = useState<HighlightProjectResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadProject();
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;

    const unsubscribe = subscribe(projectId, (msg) => {
      if (!msg.project_id) return;

      setProject((prev) => {
        if (!prev) return prev;

        if (msg.type === 'download_progress') {
          return {
            ...prev,
            download_progress: msg.progress ?? prev.download_progress,
            download_status: msg.status ?? prev.download_status,
          };
        }
        if (msg.type === 'export_progress') {
          return {
            ...prev,
            export_progress: msg.progress ?? prev.export_progress,
            export_status: msg.status ?? prev.export_status,
          };
        }
        if (msg.type === 'task_complete') {
          // Reload project to get updated URLs
          loadProject();

          if (msg.status === 'downloaded') {
            return {
              ...prev,
              download_status: 'downloaded',
              download_progress: 1.0,
            };
          }
          if (msg.status === 'exported') {
            return {
              ...prev,
              export_status: 'exported',
              export_progress: 1.0,
            };
          }
          if (msg.status === 'zip_created') {
            // ZIP bundle created, reload to get URL
            return prev;
          }
          return prev;
        }
        if (msg.type === 'error') {
          // Only update the relevant status based on task_type
          if (msg.task_type === 'download') {
            return { ...prev, error_message: msg.message || 'Task failed', download_status: 'error' };
          }
          if (msg.task_type === 'build') {
            return { ...prev, error_message: msg.message || 'Task failed', export_status: 'error' };
          }
          // Fallback: if task_type is missing, just set error_message
          return { ...prev, error_message: msg.message || 'Task failed' };
        }
        return prev;
      });
    });

    return () => unsubscribe();
  }, [projectId, subscribe]);

  const loadProject = async () => {
    if (!projectId) return;

    setIsLoading(true);
    try {
      const response = await highlightsApi.getProjects();
      const proj = response.projects.find((p) => p.id === projectId);

      if (!proj) {
        showToast('error', 'Project not found');
        navigate('/dashboard');
        return;
      }

      setProject(proj);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to load project');
    } finally {
      setIsLoading(false);
    }
  };

  const startDownload = async () => {
    if (!projectId) return;

    try {
      await highlightsApi.downloadHighlight(projectId);
      showToast('info', 'Download started');
      loadProject();
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to start download');
    }
  };

  const startBuild = async () => {
    if (!projectId) return;

    try {
      await highlightsApi.buildVideo(projectId);
      showToast('info', 'Building video...');
      loadProject();
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to start build');
    }
  };

  const createZip = async () => {
    if (!projectId) return;

    try {
      await highlightsApi.createZipBundle(projectId);
      showToast('info', 'Creating ZIP bundle...');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to create ZIP');
    }
  };

  const cancelTask = async () => {
    if (!projectId) return;

    try {
      await highlightsApi.cancelTask(projectId);
      showToast('success', 'Task cancelled. Files cleaned up. You can retry by clicking the button below.');
      loadProject();
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to cancel task');
    }
  };

  if (isLoading) {
    return (
      <div className="page">
        <div className="container mt-lg">
          <div className="muted">Loading...</div>
        </div>
      </div>
    );
  }

  if (!project) {
    return null;
  }

  const videoUrls = project.video_urls ? JSON.parse(project.video_urls) : [];
  const photoUrls = project.photo_urls ? JSON.parse(project.photo_urls) : [];

  return (
    <div className="page">
      <div className="topbar">
        <div className="topbar__brand">
          <button className="btn-back" onClick={() => navigate(-1)}>
            ← Back
          </button>
        </div>
      </div>

      <div className="container mt-lg">
        <div className="project-header">
          <div>
            <h1>{project.title}</h1>
            <p className="muted">Source: {project.source}</p>
            <p className="muted">{project.item_count} items</p>
          </div>
          <div className="project-status">
            <ExpirationCountdown expiresAt={project.expires_at} isExpired={project.is_expired === 1} />
          </div>
        </div>

        <div className="card mt-lg">
          <div className="card-header">
            <h2>Download Status</h2>
            <StatusBadge
              status={
                project.download_status === 'downloaded' ? 'Downloaded' :
                project.download_status === 'downloading' ? 'Downloading' :
                project.download_status === 'queued' ? 'Queued' :
                project.download_status === 'error' ? 'Error' :
                'Pending'
              }
              variant={
                project.download_status === 'downloaded' ? 'downloaded' :
                project.download_status === 'downloading' ? 'downloading' :
                project.download_status === 'queued' ? 'queued' :
                project.download_status === 'error' ? 'error' :
                'idle'
              }
            />
          </div>

          <div className="progress-section">
            <div className="progress-label">
              Download Progress: {Math.round(project.download_progress * 100)}%
            </div>
            <div className="progress">
              <div
                className="progress__bar"
                style={{ width: `${project.download_progress * 100}%` }}
              />
            </div>

            {/* Inline error with retry button for download errors */}
            {project.error_message && project.download_status === 'error' && (
              <div className="error-inline mt-sm">
                <div className="error-inline__message">
                  <strong>Download failed at {Math.round(project.download_progress * 100)}%:</strong> {project.error_message}
                  {project.download_progress > 0 && (
                    <div className="resume-badge mt-xs">
                      💾 Resumable - Retry will continue from {Math.round(project.download_progress * 100)}%
                    </div>
                  )}
                </div>
                <button className="btn btn--primary btn--sm" onClick={startDownload}>
                  {project.download_progress > 0 ? '🔄 Resume Download' : '🔄 Retry Download'}
                </button>
              </div>
            )}
          </div>

          <div className="actions mt-md">
            {project.download_status === 'idle' && (
              <button className="btn btn--primary" onClick={startDownload}>
                Start Download
              </button>
            )}
            {project.download_status === 'queued' && (
              <button className="btn btn--danger" onClick={cancelTask}>
                Cancel Download
              </button>
            )}
            {project.download_status === 'downloading' && (
              <button className="btn btn--danger" onClick={cancelTask}>
                Cancel Download
              </button>
            )}
            {project.download_status === 'downloaded' && (
              <>
                {project.export_status === 'not_started' && (
                  <button className="btn btn--primary" onClick={startBuild}>
                    Merge Video
                  </button>
                )}
                {!project.zip_bundle_url ? (
                  <button className="btn" onClick={createZip}>
                    Create ZIP Bundle
                  </button>
                ) : (
                  <a
                    className="btn"
                    href={project.zip_bundle_url}
                    download
                  >
                    📦 Download ZIP Bundle
                  </a>
                )}
              </>
            )}
          </div>
        </div>

        {/* Video Merge Status */}
        {(project.export_status === 'queued' || project.export_status === 'building' || project.export_status === 'exported' || project.export_status === 'error') && (
          <div className="card mt-lg">
            <div className="card-header">
              <h2>Video Merge Status</h2>
              <StatusBadge
                status={
                  project.export_status === 'exported' ? 'Completed' :
                  project.export_status === 'error' ? 'Failed' :
                  project.export_status === 'queued' ? 'Queued' :
                  'Building'
                }
                variant={
                  project.export_status === 'exported' ? 'completed' :
                  project.export_status === 'error' ? 'error' :
                  project.export_status === 'queued' ? 'queued' :
                  'downloading'
                }
              />
            </div>

            <div className="progress-section">
              <div className="progress-label">
                Merge Progress: {Math.round(project.export_progress * 100)}%
              </div>
              <div className="progress">
                <div
                  className="progress__bar"
                  style={{ width: `${project.export_progress * 100}%` }}
                />
              </div>

              {/* Inline error with retry button for merge errors */}
              {project.error_message && project.export_status === 'error' && (
                <div className="error-inline mt-sm">
                  <div className="error-inline__message">
                    <strong>Export failed:</strong> {project.error_message}
                  </div>
                  <button className="btn btn--primary btn--sm" onClick={startBuild}>
                    🔄 Retry Merge
                  </button>
                </div>
              )}
            </div>

            {(project.export_status === 'queued' || project.export_status === 'building') && (
              <div className="actions mt-md">
                <button className="btn btn--danger" onClick={cancelTask}>
                  Cancel Build
                </button>
              </div>
            )}

            {project.export_status === 'exported' && (
              <div className="actions mt-md">
                {project.merged_video_url ? (
                  <a
                    className="btn btn--primary"
                    href={project.merged_video_url}
                    download
                  >
                    🎬 Download Final Video
                  </a>
                ) : (
                  <button className="btn btn--primary" onClick={loadProject}>
                    🔄 Refresh to Get Download Link
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {(videoUrls.length > 0 || photoUrls.length > 0) && (
          <div className="card mt-lg">
            <div className="card-header">
              <h2>Items</h2>
              <p className="muted">{videoUrls.length + photoUrls.length} files</p>
            </div>

            <div className="items-grid">
              {photoUrls.map((url: string, index: number) => (
                <div key={`photo-${index}`} className="item-card">
                  <img src={url} alt={`Photo ${index + 1}`} className="item-preview" />
                  <div className="item-type">📷 Photo {index + 1}</div>
                </div>
              ))}
              {videoUrls.map((url: string, index: number) => (
                <div key={`video-${index}`} className="item-card">
                  <video src={url} className="item-preview" />
                  <div className="item-type">🎥 Video {index + 1}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {project.zip_bundle_url && (
          <div className="card mt-lg">
            <div className="card-header">
              <h2>Download Bundle</h2>
            </div>
            <div className="mt-md">
              <a className="btn btn--primary" href={project.zip_bundle_url} download>
                Download ZIP Bundle
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
