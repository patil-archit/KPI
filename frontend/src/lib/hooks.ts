import { useCallback, useEffect, useRef, useState } from "react";

export function useApi<T>(fn: () => Promise<T>, deps: any[] = [], pollMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const reload = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try { setData(await fnRef.current()); setError(null); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    reload();
    if (pollMs > 0) {
      const id = setInterval(() => reload(true), pollMs);
      return () => clearInterval(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, reload };
}
