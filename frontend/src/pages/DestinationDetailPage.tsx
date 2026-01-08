import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { destinationsApi } from '../api/destinations';
import { DestinationUsername, DestinationHighlight } from '../types/destination';
import { useToast } from '../hooks/useToast';

export function DestinationDetailPage() {
  const { usernameId } = useParams<{ usernameId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [destination, setDestination] = useState<DestinationUsername | null>(null);
  const [highlights, setHighlights] = useState<DestinationHighlight[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);

  useEffect(() => {
    loadDestinationAndHighlights();
  }, [usernameId]);

  const loadDestinationAndHighlights = async () => {
    if (!usernameId) return;

    setIsLoading(true);
    try {
      const destinations = await destinationsApi.listDestinations();
      const dest = destinations.find(d => d.id === usernameId);

      if (!dest) {
        showToast('error', 'Destination not found');
        navigate('/dashboard');
        return;
      }

      setDestination(dest);

      // Try to load cached highlights
      try {
        const cachedHighlights = await destinationsApi.getHighlights(usernameId);
        setHighlights(cachedHighlights);
      } catch (e) {
        // No cached highlights yet
      }
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to load destination');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHighlights = async () => {
    if (!usernameId) return;

    setIsFetching(true);
    try {
      const fetchedHighlights = await destinationsApi.fetchHighlights(usernameId);
      setHighlights(fetchedHighlights);
      showToast('success', `Found ${fetchedHighlights.length} highlights`);
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to fetch highlights');
    } finally {
      setIsFetching(false);
    }
  };

  const downloadHighlight = async (highlightId: string) => {
    if (!usernameId) return;

    try {
      // Auto-refresh highlights first to verify it still exists on Instagram
      showToast('info', 'Verifying highlight availability...');
      setIsFetching(true);

      const refreshedHighlights = await destinationsApi.fetchHighlights(usernameId);
      setHighlights(refreshedHighlights);

      // Check if the highlight still exists after refresh
      const highlightExists = refreshedHighlights.some(h => h.highlight_id === highlightId);

      if (!highlightExists) {
        showToast('error', 'This highlight no longer exists on Instagram. It may have been deleted or expired.');
        return;
      }

      // Proceed with download
      showToast('info', 'Starting download...');
      await destinationsApi.downloadHighlight(usernameId, highlightId);
      showToast('success', 'Download started');
      navigate('/dashboard');
    } catch (e: any) {
      showToast('error', e.response?.data?.detail || 'Failed to start download');
    } finally {
      setIsFetching(false);
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

  if (!destination) {
    return null;
  }

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
        <div className="destination-header">
          {destination.avatar_url && (
            <img
              src={destination.avatar_url}
              alt={destination.username}
              className="destination-avatar"
            />
          )}
          <div>
            <h1 className="destination-username">@{destination.username}</h1>
            {destination.display_name && (
              <p className="destination-display-name">{destination.display_name}</p>
            )}
            {destination.last_fetched_at && (
              <p className="muted">Last fetched: {new Date(destination.last_fetched_at).toLocaleString()}</p>
            )}
          </div>
        </div>

        <div className="card mt-lg">
          <div className="card-header">
            <h2>Highlights</h2>
            <button
              className="btn btn--primary"
              onClick={fetchHighlights}
              disabled={isFetching}
            >
              {isFetching ? 'Refreshing...' : highlights.length > 0 ? '🔄 Refresh Highlights' : 'Fetch Highlights'}
            </button>
          </div>

          {destination.last_fetched_at && highlights.length > 0 && (
            <div style={{ padding: '12px 16px', background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: '6px', margin: '16px' }}>
              <p style={{ margin: 0, fontSize: '14px', color: '#92400e' }}>
                ⚠️ Highlights cached from {new Date(destination.last_fetched_at).toLocaleString()}.
                Click "Refresh" to get the latest highlights from Instagram before downloading.
              </p>
            </div>
          )}

          {highlights.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state__icon">📋</div>
              <h3>No highlights yet</h3>
              <p>Click "Fetch Highlights" to load highlights from Instagram</p>
            </div>
          ) : (
            <div className="highlights-grid">
              {highlights.map((highlight) => (
                <div
                  key={highlight.id}
                  className="highlight-card"
                  onClick={() => {
                    // Navigate to detail page if downloaded, otherwise trigger download
                    if (highlight.project_id) {
                      navigate(`/highlights/${highlight.project_id}`);
                    } else {
                      downloadHighlight(highlight.highlight_id);
                    }
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  {highlight.cover_url ? (
                    <img
                      src={highlight.cover_url}
                      alt={highlight.name}
                      className="highlight-cover"
                      onError={(e) => {
                        // If image fails to load, show placeholder
                        e.currentTarget.style.display = 'none';
                        const placeholder = e.currentTarget.nextElementSibling;
                        if (placeholder && placeholder.classList.contains('highlight-cover-placeholder')) {
                          (placeholder as HTMLElement).style.display = 'flex';
                        }
                      }}
                    />
                  ) : null}
                  <div
                    className="highlight-cover-placeholder"
                    style={{ display: highlight.cover_url ? 'none' : 'flex' }}
                  >
                    📸
                  </div>
                  <div className="highlight-info">
                    <h3 className="highlight-name">{highlight.name}</h3>
                    <p className="highlight-count">{highlight.item_count} items</p>
                    {highlight.project_id ? (
                      <span className="badge badge--success">Downloaded</span>
                    ) : (
                      <button
                        className="btn btn--sm btn--primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          downloadHighlight(highlight.highlight_id);
                        }}
                      >
                        Download
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
