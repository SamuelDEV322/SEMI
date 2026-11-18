import { useEffect, useRef, useState } from "react";
import type { Scan } from "../types/api";
export function useScanFreshness(scan: Scan | null) {
  const observed = useRef({ scan, at: performance.now() });
  const [, redraw] = useState(0);
  if (observed.current.scan !== scan)
    observed.current = { scan, at: performance.now() };
  useEffect(() => {
    const timer = setInterval(() => redraw((n) => n + 1), 250);
    return () => clearInterval(timer);
  }, []);
  const age = scan?.age_ms ?? scan?.acquisition?.reader_age_ms;
  return (
    scan?.source !== "mock" &&
    age != null &&
    age + performance.now() - observed.current.at > 2000
  );
}
