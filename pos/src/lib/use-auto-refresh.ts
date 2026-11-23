import { useEffect, useRef } from 'react';

export const AUTO_REFRESH_MS = 10_000;

/**
 * Re-runs `refresh` every `intervalMs` while the page is visible, and right away when the
 * page comes back into view (screen woken, app reopened), so orders placed on another
 * device show up without a manual refresh. A run is skipped while the previous one is
 * still in flight.
 */
export function useAutoRefresh(refresh: () => unknown, intervalMs = AUTO_REFRESH_MS, enabled = true) {
  const latest = useRef(refresh);
  latest.current = refresh;

  useEffect(() => {
    if (!enabled) return;
    let running = false;

    const run = async () => {
      if (running || document.visibilityState !== 'visible') return;
      running = true;
      try {
        await latest.current();
      } catch (err) {
        console.error('Auto refresh failed', err);
      } finally {
        running = false;
      }
    };

    const timer = window.setInterval(run, intervalMs);
    const onVisible = () => {
      if (document.visibilityState === 'visible') run();
    };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onVisible);
    };
  }, [intervalMs, enabled]);
}
