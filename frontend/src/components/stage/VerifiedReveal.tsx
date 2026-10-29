import React, { useEffect, useState } from 'react';
import { useReducedMotion } from '../../lib/motion';

interface VerifiedRevealProps {
  isVerified: boolean;
  replayKey?: number;
  children: React.ReactNode;
}

export const VerifiedReveal: React.FC<VerifiedRevealProps> = ({ isVerified, replayKey = 0, children }) => {
  const prefersReduced = useReducedMotion();
  const [hasRevealed, setHasRevealed] = useState(false);
  const [glowActive, setGlowActive] = useState(false);

  useEffect(() => {
    if (!isVerified) {
      setHasRevealed(false);
      setGlowActive(false);
      return;
    }

    if (prefersReduced) {
      setHasRevealed(true);
      setGlowActive(true);
      return;
    }

    // Step 1: Initial state before reveal
    setHasRevealed(false);
    setGlowActive(false);

    // Step 2: At 1180ms, switch on winner glow (first green of the view per Section 7)
    const glowTimer = setTimeout(() => {
      setGlowActive(true);
    }, 1180);

    // Step 3: At 1400ms, lock in final revealed state
    const completeTimer = setTimeout(() => {
      setHasRevealed(true);
    }, 1400);

    return () => {
      clearTimeout(glowTimer);
      clearTimeout(completeTimer);
    };
  }, [isVerified, replayKey, prefersReduced]);

  if (!isVerified) {
    return <>{children}</>;
  }

  const containerClasses = [
    'verified-reveal-container',
    hasRevealed ? 'revealed' : 'revealing',
    glowActive ? 'winner-glow' : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      key={replayKey}
      className={containerClasses}
      style={{
        position: 'relative',
        transition: prefersReduced ? 'opacity 120ms ease' : 'box-shadow 380ms var(--ease-spring), border-color 380ms ease',
      }}
    >
      {children}
    </div>
  );
};
