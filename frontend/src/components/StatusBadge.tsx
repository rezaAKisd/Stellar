import React from 'react';

type BadgeVariant = 'downloading' | 'downloaded' | 'completed' | 'ready' | 'error' | 'idle' | 'queued';

interface StatusBadgeProps {
  status: string;
  variant?: BadgeVariant;
}

function getVariantFromStatus(status: string): BadgeVariant {
  const statusLower = status.toLowerCase();

  if (statusLower === 'downloading' || statusLower === 'building') return 'downloading';
  if (statusLower === 'downloaded') return 'downloaded';
  if (statusLower === 'exported' || statusLower === 'completed') return 'completed';
  if (statusLower === 'idle' || statusLower === 'not_started') return 'idle';
  if (statusLower === 'queued') return 'queued';
  if (statusLower === 'error') return 'error';

  return 'idle';
}

export function StatusBadge({ status, variant }: StatusBadgeProps) {
  const badgeVariant = variant || getVariantFromStatus(status);
  const displayStatus = status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <span className={`badge badge--${badgeVariant}`}>
      {displayStatus}
    </span>
  );
}
