import { useState } from "react";

import { compareStrategies, solveStrategy } from "./api/client";
import type { CompareRequest, CompareResponse, StrategyRequest, StrategyResponse, StrategySelection } from "./api/types";
import ComparePanel from "./components/ComparePanel";
import ControlPanel from "./components/ControlPanel";
import ResultPanel from "./components/ResultPanel";
import "./App.css";

function App() {
  const [strategyResult, setStrategyResult] = useState<StrategyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [currentSelection, setCurrentSelection] = useState<StrategySelection | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  async function handleSolve(request: StrategyRequest) {
    setIsLoading(true);
    setError(null);
    try {
      const result = await solveStrategy(request);
      setStrategyResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCompare(request: CompareRequest) {
    setIsComparing(true);
    setCompareError(null);
    try {
      const result = await compareStrategies(request);
      setCompareResult(result);
    } catch (err) {
      setCompareError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsComparing(false);
    }
  }

  return (
    <div className="shell">
      <header className="shell-header">
        <span className="wordmark">DISPATCH</span>
        <span className="eyebrow">Strategy Studio</span>
      </header>
      <main className="shell-main">
        <section className="panel control-panel" aria-label="Control panel">
          <ControlPanel onSolve={handleSolve} isLoading={isLoading} onSelectionChange={setCurrentSelection} />
        </section>
        <section className="panel results-panel" aria-label="Recommended plan">
          <ResultPanel
            result={strategyResult}
            pitLossSeconds={strategyResult?.pit_loss_seconds ?? 0}
            isLoading={isLoading}
            error={error}
          />
          <ComparePanel
            selection={currentSelection}
            result={compareResult}
            isLoading={isComparing}
            error={compareError}
            onCompare={handleCompare}
          />
        </section>
        <section className="panel headline-panel" aria-label="Headline metric"></section>
      </main>
    </div>
  );
}

export default App;
