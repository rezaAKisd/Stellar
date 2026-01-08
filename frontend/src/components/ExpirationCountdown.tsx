import React, { useState, useEffect } from 'react';

interface ExpirationCountdownProps {
  expiresAt: string | null | undefined;
  isExpired?: boolean;
}

export function ExpirationCountdown({ expiresAt, isExpired }: ExpirationCountdownProps) {
  const [timeLeft, setTimeLeft] = useState<string>('');

  useEffect(() => {
    if (!expiresAt) {
      setTimeLeft('');
      return;
    }

    if (isExpired) {
      setTimeLeft('Expired');
      return;
    }

    const updateTimeLeft = () => {
      const now = new Date();
      const expiry = new Date(expiresAt);
      const diff = expiry.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeLeft('Expired');
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

      if (days > 7) {
        setTimeLeft(`${days} days remaining`);
      } else if (days > 0) {
        setTimeLeft(`${days}d ${hours}h remaining`);
      } else if (hours > 0) {
        setTimeLeft(`${hours}h ${minutes}m remaining`);
      } else {
        setTimeLeft(`${minutes}m remaining`);
      }
    };

    updateTimeLeft();
    const interval = setInterval(updateTimeLeft, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [expiresAt, isExpired]);

  if (!timeLeft) return null;

  const isWarning = timeLeft.includes('Expired') || timeLeft.startsWith('0h') || timeLeft.startsWith('1h');

  return (
    <span className={`expiration ${isWarning ? 'expiration--warning' : ''}`}>
      {timeLeft}
    </span>
  );
}
