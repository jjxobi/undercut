import type { CompareRequest, CompareResponse, StrategySelection } from "../api/types";
import DistributionChart from "./DistributionChart";
import "./ComparePanel.css";

// A deeper, slower check than the main solve -- it runs two solves and draws
// its own held-out scenario set, so it gets a fixed scenario count rather
// than reusing whatever ControlPanel's input happens to be set to.
const DEFAULT_N_SCENARIOS = 200;

interface ComparePanelProps {
  selection: StrategySelection | null;
  result: CompareResponse | null;
  isLoading: boolean;
  error: string | null;
  onCompare: (request: CompareRequest) => void;
}

function formatSeconds(value: number): string {
  return `${value.toFixed(1)}s`;
}

function describeGap(result: CompareResponse): string {
  const gap = result.gap_seconds;
  const se = result.gap_standard_error;

  if (!result.gap_is_significant) {
    return `The gap between the two plans is smaller than the noise in these scenarios (± ${formatSeconds(se)}) -- hedging against the safety car neither helped nor hurt here.`;
  }

  if (gap > 0) {
    return `Committing to the no-safety-car plan runs ${formatSeconds(gap)} slower on average than the plan that hedged -- the hedge earned its keep here.`;
  }

  return `Hedging against the safety car runs ${formatSeconds(-gap)} slower on average than just committing to the no-safety-car plan -- the caution wasn't worth it here.`;
}

function ComparePanel({ selection, result, isLoading, error, onCompare }: ComparePanelProps) {
  function handleCheckConfidence() {
    if (!selection) return;
    onCompare({
      circuit_id: selection.circuit_id,
      era: selection.era,
      race_length: selection.race_length,
      n_scenarios: DEFAULT_N_SCENARIOS,
      seed: 0,
    });
  }

  return (
    <div className="compare-panel">
      <div className="compare-panel-header">
        <div className="compare-panel-heading-group">
          <h2 className="compare-panel-heading">How confident should you be?</h2>
          <p className="compare-panel-subheading">
            Solves the plan again assuming no safety car, hedges a second plan across{" "}
            {DEFAULT_N_SCENARIOS} sampled scenarios, then prices both on a held-out set neither ever saw.
          </p>
        </div>
        <button
          type="button"
          className="compare-panel-button"
          onClick={handleCheckConfidence}
          disabled={!selection || isLoading}
        >
          {isLoading ? (
            <>
              <span className="compare-panel-spinner" aria-hidden="true" />
              Comparing&hellip;
            </>
          ) : (
            "Check confidence"
          )}
        </button>
      </div>

      {error && (
        <p className="compare-panel-error" role="alert">
          {error}
        </p>
      )}

      {!error && !isLoading && !result && (
        <p className="compare-panel-empty">
          {selection
            ? "Run a comparison to see how the recommended plan holds up against a genuinely uncertain race."
            : "Choose a circuit and race length on the left to unlock a confidence check."}
        </p>
      )}

      {!error && result && (
        <div className="compare-panel-result">
          <DistributionChart
            deterministicCosts={result.deterministic_costs}
            stochasticCosts={result.stochastic_costs}
          />

          <dl className="compare-panel-stats">
            <div className="compare-panel-stat">
              <dt>Gap on held-out scenarios</dt>
              <dd>
                {result.gap_seconds >= 0 ? "+" : ""}
                {formatSeconds(result.gap_seconds)} &plusmn; {formatSeconds(result.gap_standard_error)}
              </dd>
            </div>
          </dl>

          <p className="compare-panel-gap">{describeGap(result)}</p>
        </div>
      )}
    </div>
  );
}

export default ComparePanel;
