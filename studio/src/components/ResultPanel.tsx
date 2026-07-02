import type { StrategyResponse } from "../api/types";
import StintBar from "./StintBar";
import "./ResultPanel.css";

interface ResultPanelProps {
  result: StrategyResponse | null;
  pitLossSeconds: number;
  isLoading: boolean;
  error: string | null;
}

function formatCost(seconds: number): string {
  return `${seconds.toFixed(1)}s`;
}

function ResultPanel({ result, pitLossSeconds, isLoading, error }: ResultPanelProps) {
  if (isLoading) {
    return (
      <div className="result-panel result-panel-loading" role="status">
        <h2 className="result-panel-heading">Recommended plan</h2>
        <div className="result-panel-sweep" aria-hidden="true" />
        <p className="result-panel-loading-text">Solving your recommended strategy&hellip;</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="result-panel" role="alert">
        <h2 className="result-panel-heading">Recommended plan</h2>
        <p className="result-panel-error-heading">Solve failed</p>
        <p className="result-panel-error-detail">{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="result-panel result-panel-empty">
        <h2 className="result-panel-heading">Recommended plan</h2>
        <div className="result-panel-ghost" aria-hidden="true">
          <div
            className="result-panel-ghost-segment"
            style={{ width: "38%", borderColor: "color-mix(in srgb, var(--tire-soft) 40%, transparent)" }}
          />
          <div
            className="result-panel-ghost-segment"
            style={{ width: "34%", borderColor: "color-mix(in srgb, var(--tire-medium) 40%, transparent)" }}
          />
          <div
            className="result-panel-ghost-segment"
            style={{ width: "28%", borderColor: "color-mix(in srgb, var(--tire-hard) 40%, transparent)" }}
          />
        </div>
        <p className="result-panel-empty-heading">No plan solved yet</p>
        <p className="result-panel-empty-body">
          Choose a circuit and race length on the left, then solve to see a recommended pit strategy here.
        </p>
      </div>
    );
  }

  const raceLength = result.stint_lengths.reduce((total, length) => total + length, 0);

  const stintBarKey = `${result.compounds.join("-")}_${result.stint_lengths.join("-")}_${result.pit_laps.join("-")}`;

  return (
    <div className="result-panel result-panel-populated">
      <h2 className="result-panel-heading">Recommended plan</h2>
      <StintBar
        key={stintBarKey}
        compounds={result.compounds}
        stintLengths={result.stint_lengths}
        pitLaps={result.pit_laps}
        raceLength={raceLength}
      />

      <dl className="result-panel-stats">
        <div className="result-panel-stat">
          <dt>Pit laps</dt>
          <dd>{result.pit_laps.length > 0 ? result.pit_laps.join(", ") : "none"}</dd>
        </div>
        <div className="result-panel-stat">
          <dt>Expected time lost to tyres and pit stops</dt>
          <dd>{formatCost(result.expected_cost_seconds)}</dd>
        </div>
        <div className="result-panel-stat">
          <dt>Pit loss estimate used</dt>
          <dd>{formatCost(pitLossSeconds)}</dd>
        </div>
      </dl>
    </div>
  );
}

export default ResultPanel;
