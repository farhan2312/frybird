import { useEffect, useState } from 'react';

/** Minutes after which an open order's elapsed time turns amber, then red. */
export const ELAPSED_WARN_MINUTES = 15;
export const ELAPSED_LATE_MINUTES = 30;

const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})/;
const TIME_RE = /(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?/;

/**
 * When an order was placed, from the server's date and time strings. Accepts a full
 * datetime ("2026-11-23 22:35:19.8"), a date plus a time, or a time alone
 * (URY Table.latest_invoice_time), which is taken as the most recent such time.
 */
export function parseOrderTime(dateOrDatetime?: string | null, time?: string | null): Date | null {
  const dateMatch = dateOrDatetime ? DATE_RE.exec(dateOrDatetime) : null;
  const timeSource = time || (dateMatch ? dateOrDatetime!.slice(10) : dateOrDatetime) || '';
  const timeMatch = TIME_RE.exec(timeSource);
  if (!timeMatch) return null;
  const [h, m, s] = [Number(timeMatch[1]), Number(timeMatch[2]), Number(timeMatch[3] || 0)];

  if (dateMatch) {
    return new Date(Number(dateMatch[1]), Number(dateMatch[2]) - 1, Number(dateMatch[3]), h, m, s);
  }
  const at = new Date();
  at.setHours(h, m, s, 0);
  if (at.getTime() - Date.now() > 60_000) at.setDate(at.getDate() - 1); // a time later than now was yesterday
  return at;
}

export function elapsedMinutes(start: Date | null, now = Date.now()): number | null {
  if (!start) return null;
  return Math.max(0, Math.floor((now - start.getTime()) / 60000));
}

/** "just now", "12 min", "1h 05m". */
export function elapsedLabel(start: Date | null, now = Date.now()): string | null {
  const minutes = elapsedMinutes(start, now);
  if (minutes === null) return null;
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`;
}

/** "10:35 PM". */
export function clockLabel(start: Date | null): string {
  return start ? start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '';
}

/** Text colour for an open order's elapsed time: normal, amber after 15 min, red after 30. */
export function elapsedTone(start: Date | null, now = Date.now()): string {
  const minutes = elapsedMinutes(start, now) ?? 0;
  if (minutes >= ELAPSED_LATE_MINUTES) return 'text-red-600 font-semibold';
  if (minutes >= ELAPSED_WARN_MINUTES) return 'text-amber-600 font-semibold';
  return '';
}

/** Current time, updated every `intervalMs`, so elapsed labels keep counting. */
export function useNow(intervalMs = 30_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}
