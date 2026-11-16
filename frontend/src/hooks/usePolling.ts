import { useCallback, useEffect, useRef, useState } from "react";
export function usePolling<T>(load: () => Promise<T>, interval: number) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState<string | null>(null),
    [loading, setLoading] = useState(true);
  const refreshRef = useRef<() => void>(() => {});
  useEffect(() => {
    setLoading(true);
    setData(null);
    setError(null);
    let alive = true,
      running = false,
      rerun = false,
      timer: ReturnType<typeof setTimeout>;
    const run = async () => {
      if (running) {
        rerun = true;
        return;
      }
      running = true;
      clearTimeout(timer);
      try {
        const next = await load();
        if (alive) {
          setData(next);
          setError(null);
        }
      } catch (error) {
        if (alive) {
          setError(
            error instanceof Error ? error.message : "Error desconocido",
          );
          setData(null);
        }
      } finally {
        running = false;
        if (alive) {
          setLoading(false);
          if (rerun) {
            rerun = false;
            void run();
          } else {
            timer = setTimeout(run, interval);
          }
        }
      }
    };
    refreshRef.current = () => {
      void run();
    };
    void run();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [load, interval]);
  const refresh = useCallback(() => refreshRef.current(), []);
  return { data, error, loading, refresh };
}
