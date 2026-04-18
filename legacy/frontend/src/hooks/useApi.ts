import { useEffect, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Fetch JSON from the backend API.
 * @param path   API path (e.g. '/earth-now/fires')
 * @param enabled  When false, skip the fetch entirely (lazy loading).
 */
export function useApi<T>(path: string, enabled = true): UseApiState<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: enabled,
    error: null,
  });

  useEffect(() => {
    if (!enabled) {
      // Don't clear existing data — keep it cached if we had it before
      setState((prev) => prev.data ? prev : { data: null, loading: false, error: null });
      return;
    }
    // If we already have data for this path, don't show loading flash
    setState((prev) => ({ data: prev.data, loading: !prev.data, error: null }));

    let cancelled = false;
    fetch(`${API_BASE}${path}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<T>;
      })
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error) => {
        if (!cancelled) setState((prev) => ({ data: prev.data, loading: false, error }));
      });
    return () => {
      cancelled = true;
    };
  }, [path, enabled]);

  return state;
}
