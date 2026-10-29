/**
 * Motion primitives & reduced motion hook
 * Aligned with AGENTS.md § 4.5: transitions <= 220ms, support prefers-reduced-motion.
 */

import { useState, useEffect } from 'react';

export const MOTION = {
  spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
  fast: '140ms cubic-bezier(0.16, 1, 0.3, 1)',
  normal: '220ms cubic-bezier(0.16, 1, 0.3, 1)',
  reveal: '1400ms cubic-bezier(0.16, 1, 0.3, 1)',
};

export function useReducedMotion(): boolean {
  const [prefersReduced, setPrefersReduced] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const listener = (event: MediaQueryListEvent) => {
      setPrefersReduced(event.matches);
    };

    mediaQuery.addEventListener('change', listener);
    return () => mediaQuery.removeEventListener('change', listener);
  }, []);

  return prefersReduced;
}

/**
 * Safely executes a state update inside the browser's View Transitions API
 * with automatic fallback and strict prefers-reduced-motion compliance.
 */
export function runWithViewTransition(updateDom: () => void | Promise<void>): Promise<void> {
  if (typeof document === 'undefined') {
    updateDom();
    return Promise.resolve();
  }

  // If user requests reduced motion, bypass transitions immediately
  const prefersReduced = typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const doc = document as Document & {
    startViewTransition?: (cb: () => void | Promise<void>) => { finished: Promise<void> };
  };

  if (!prefersReduced && typeof doc.startViewTransition === 'function') {
    try {
      return doc.startViewTransition(updateDom).finished;
    } catch {
      updateDom();
      return Promise.resolve();
    }
  }

  updateDom();
  return Promise.resolve();
}
