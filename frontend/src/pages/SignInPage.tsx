import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';

export function SignInPage() {
  const navigate = useNavigate();
  const { login, restoreSession } = useAuth();
  const { showToast } = useToast();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);

  const canSubmit = useMemo(() => username.trim().length > 0 && password.length > 0, [username, password]);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    const result = await login(username.trim(), password);
    setIsSubmitting(false);

    if (!result.success) {
      showToast('error', result.error || 'Login failed');
      return;
    }

    if (result.needs2FA) {
      navigate('/2fa', { state: { username: username.trim(), password } });
      return;
    }

    showToast('success', 'Signed in');
    navigate('/dashboard');
  };

  const onRestore = async () => {
    setIsRestoring(true);
    const ok = await restoreSession();
    setIsRestoring(false);

    if (ok) {
      showToast('success', 'Session restored');
      navigate('/dashboard');
      return;
    }

    showToast('error', 'No session to restore');
  };

  return (
    <div className="page page--center">
      <form className="card card--narrow" onSubmit={onSubmit}>
        <div className="card__title">Sign in</div>
        <div className="muted mt-sm">Use your Instagram credentials.</div>

        <label className="field mt-lg">
          <div className="field__label">Username</div>
          <input
            className="input"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="your_username"
          />
        </label>

        <label className="field mt-md">
          <div className="field__label">Password</div>
          <input
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>

        <button className="btn btn--primary mt-lg" type="submit" disabled={!canSubmit || isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>

        <button className="btn mt-sm" type="button" onClick={onRestore} disabled={isRestoring}>
          {isRestoring ? 'Restoring…' : 'Restore saved session'}
        </button>

        <div className="muted mt-md" style={{ fontSize: 12 }}>
          If you have 2FA enabled, you’ll be prompted for a code.
        </div>
      </form>
    </div>
  );
}

