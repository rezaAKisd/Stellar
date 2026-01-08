import React from 'react';

export function LoadingScreen({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="page page--center">
      <div className="card card--narrow">
        <div className="card__title">{label}</div>
        <div className="muted mt-sm">Please wait.</div>
      </div>
    </div>
  );
}

