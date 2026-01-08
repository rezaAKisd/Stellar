import React, { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';

type LocationState = { username?: string; password?: string } | null;

export function TwoFactorPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LocationState) || null;

  const { verify2FA } = useAuth();
  const { showToast } = useToast();

  const [username, setUsername] = useState(state?.username || '');
  const [password, setPassword] = useState(state?.password || '');
  const [code, setCode] = useState('');
  const [trustDevice, setTrustDevice] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = useMemo(() => {
    const normalizedCode = code.replace(/\s+/g, '');
    return username.trim().length > 0 && password.length > 0 && normalizedCode.length === 6;
  }, [username, password, code]);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    const result = await verify2FA(username.trim(), password, code.replace(/\s+/g, ''), trustDevice);
    setIsSubmitting(false);

    if (!result.success) {
      showToast('error', result.error || '2FA verification failed');
      return;
    }

    showToast('success', 'Signed in');
    navigate('/dashboard');
  };

  return (
    <div className="page page--center">
      <form className="card card--narrow" onSubmit={onSubmit}>
        <div className="card__title">Two‑factor authentication</div>
        <div className="muted mt-sm">Enter the 6‑digit code from your authenticator app.</div>

        <label className="field mt-lg">
          <div className="field__label">Username</div>
          <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>

        <label className="field mt-md">
          <div className="field__label">Password</div>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <label className="field mt-md">
          <div className="field__label">2FA code</div>
          <input
            className="input"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="123456"
          />
        </label>

        <label className="checkbox mt-md">
          <input type="checkbox" checked={trustDevice} onChange={(e) => setTrustDevice(e.target.checked)} />
          <span>Trust this device</span>
        </label>

        <button className="btn btn--primary mt-lg" type="submit" disabled={!canSubmit || isSubmitting}>
          {isSubmitting ? 'Verifying…' : 'Verify'}
        </button>

        <button className="btn mt-sm" type="button" onClick={() => navigate('/signin')}>
          Back to sign in
        </button>
      </form>
    </div>
  );
}

