import { useState } from "react";

import { solveStrategy } from "./api/client";
import type { StrategyRequest, StrategyResponse } from "./api/types";
import ControlPanel from "./components/ControlPanel";
import ResultPanel from "./components/ResultPanel";
import "./App.css";

function App() {
  const [strategyResult, setStrategyResult] = useState<StrategyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="shell">
      <header className="shell-header">
        <span className="wordmark">DISPATCH</span>
        <span className="eyebrow">Strategy Studio</span>
      </header>
      <main className="shell-main">
        <section className="panel control-panel" aria-label="Control panel">
          <ControlPanel onSolve={handleSolve} isLoading={isLoading} />
        </section>
        <section className="panel results-panel" aria-label="Recommended plan">
          <ResultPanel
            result={strategyResult}
            pitLossSeconds={strategyResult?.pit_loss_seconds ?? 0}
            isLoading={isLoading}
            error={error}
          />
        </section>
        <section className="panel headline-panel" aria-label="Headline metric"></section>
      </main>
    </div>
  );
}

export default App;
