import { useEffect, useRef, useState } from "react";
import { subscribe } from "@/lib/loading-bar";

export function GlobalProgressBar() {
  const [loading, setLoading] = useState(false);
  const [width, setWidth] = useState(0);
  const [visible, setVisible] = useState(false);
  const trickleRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    return subscribe(setLoading);
  }, []);

  useEffect(() => {
    if (loading) {
      // Start: show bar and quickly move to 70%
      setVisible(true);
      setWidth(0);
      // Force a reflow so the initial 0% is painted before transitioning
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setWidth(70);
        });
      });

      // Trickle: slowly creep toward 90%
      trickleRef.current = setInterval(() => {
        setWidth((prev) => {
          if (prev >= 90) return prev;
          return prev + (90 - prev) * 0.1;
        });
      }, 500);
    } else if (visible) {
      // Stop: jump to 100% then fade out
      clearInterval(trickleRef.current);
      setWidth(100);
      const fadeTimer = setTimeout(() => {
        setVisible(false);
        setWidth(0);
      }, 400);
      return () => clearTimeout(fadeTimer);
    }

    return () => clearInterval(trickleRef.current);
  }, [loading]);

  if (!visible) return null;

  const isComplete = !loading && width === 100;

  return (
    <div
      className="fixed top-0 left-0 right-0 z-[100] h-[2px] pointer-events-none"
      style={{ opacity: isComplete ? 0 : 1, transition: "opacity 300ms ease-out 100ms" }}
    >
      <div
        className="h-full"
        style={{
          width: `${width}%`,
          backgroundColor: "var(--brand-primary)",
          transition: loading
            ? width <= 70
              ? "width 300ms ease-out"
              : "width 500ms linear"
            : "width 200ms ease-in",
        }}
      />
    </div>
  );
}
