import { useEffect, useState } from "react";

import { compareStrategies, fetchEvaluationSummary, solveStrategy } from "./api/client";
import type {
  CompareRequest,
  CompareResponse,
  EvaluationSummaryResponse,
  StrategyRequest,
  StrategyResponse,
  StrategySelection,
} from "./api/types";
import ComparePanel from "./components/ComparePanel";
import ControlPanel from "./components/ControlPanel";
import HeadlineStat from "./components/HeadlineStat";
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

  const [evaluationSummary, setEvaluationSummary] = useState<EvaluationSummaryResponse | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchEvaluationSummary()
      .then((result) => {
        if (cancelled) return;
        setEvaluationSummary(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setSummaryError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (cancelled) return;
        setIsSummaryLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

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
        <h1 className="wordmark">DISPATCH</h1>
        <span className="eyebrow">Strategy Studio</span>
      </header>
      <main className="shell-main">
        <details className="panel control-panel" open>
          <summary className="control-panel-summary">Control panel</summary>
          <ControlPanel onSolve={handleSolve} isLoading={isLoading} onSelectionChange={setCurrentSelection} />
        </details>
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
      </main>
      <section className="panel headline-panel" aria-label="Headline metric">
        <HeadlineStat summary={evaluationSummary} isLoading={isSummaryLoading} error={summaryError} />
      </section>
    </div>
  );
}

export default App;
