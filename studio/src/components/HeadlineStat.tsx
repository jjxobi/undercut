import { useEffect, useState } from "react";

import type { EvaluationSummaryResponse } from "../api/types";
import "./HeadlineStat.css";

const ROLL_DURATION_MS = 900;

interface HeadlineStatProps {
  summary: EvaluationSummaryResponse | null;
  isLoading: boolean;
  error: string | null;
}

// jsdom (and presumably some older browsers) don't implement matchMedia at
// all. Treat that the same as a reduced-motion preference rather than risk
// animating somewhere that has no way of telling us the user opted out.
function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return true;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function useRolledValue(target: number): number {
  const [value, setValue] = useState(() => (prefersReducedMotion() ? target : 0));

  useEffect(() => {
    if (prefersReducedMotion()) {
      setValue(target);
      return;
    }

    let frame = 0;
    const start = performance.now();

    function step(now: number) {
      const progress = Math.min(1, (now - start) / ROLL_DURATION_MS);
      const eased = 1 - (1 - progress) ** 3;
      setValue(target * eased);
      if (progress < 1) {
        frame = requestAnimationFrame(step);
      }
    }

    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  return value;
}

function HeadlineStat({ summary, isLoading, error }: HeadlineStatProps) {
  const hasPositions = summary?.mean_regret_positions_per_race != null;
  const positionsValue = summary?.mean_regret_positions_per_race;
  const target = summary ? (hasPositions ? (positionsValue as number) : summary.mean_actual_regret_seconds) : 0;
  const rolled = useRolledValue(target);

  if (isLoading) {
    return (
      <div className="headline-stat headline-stat-loading" role="status">
        <span className="headline-stat-spinner" aria-hidden="true" />
        <p>Loading the regret baseline&hellip;</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="headline-stat headline-stat-error" role="alert">
        <p className="headline-stat-error-heading">Baseline unavailable</p>
        <p className="headline-stat-error-detail">{error}</p>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  const unitLabel = hasPositions ? "positions / race" : "seconds / race";
  const displayValue = rolled.toFixed(1);
  const finalValue = target.toFixed(1);
  const capturedPercent = Math.round(summary.captured_fraction * 100);
  const capturedIsReadable = Number.isFinite(capturedPercent);

  return (
    <div className="headline-stat headline-stat-populated">
      <p className="headline-stat-eyebrow">Perfect information was worth</p>

      <div className="headline-stat-readout">
        <span className="headline-stat-number" aria-hidden="true">
          {displayValue}
        </span>
        <span className="headline-stat-unit" aria-hidden="true">
          {unitLabel}
        </span>
        <span className="headline-stat-sr-value">
          {finalValue} {unitLabel}
        </span>
      </div>

      <p className="headline-stat-caption">
        {capturedIsReadable ? (
          <>
            the policy captured <strong>{capturedPercent}%</strong> of that value
          </>
        ) : (
          "the policy's captured share isn't well defined against this baseline"
        )}
      </p>

      <p className="headline-stat-footnote">{summary.driver_races.toLocaleString()} real driver-races</p>
    </div>
  );
}

export default HeadlineStat;
