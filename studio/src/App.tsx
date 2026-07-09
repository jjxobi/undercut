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
import HowItWorks from "./components/HowItWorks";
import ResultPanel from "./components/ResultPanel";
import "./App.css";

type View = "studio" | "how-it-works";

function App() {
  const [view, setView] = useState<View>("studio");
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

  const sessionStatus =
    error || compareError || summaryError ? "fault" : isLoading || isComparing ? "solving" : "ready";

  return (
    <div className="shell">
      <header className="shell-header">
        <h1 className="wordmark">DISPATCH</h1>
        <span className="eyebrow">Strategy Studio</span>
        <nav className="shell-nav" aria-label="Page">
          <button
            type="button"
            className="shell-nav-link"
            onClick={() => setView(view === "studio" ? "how-it-works" : "studio")}
          >
            {view === "studio" ? "Methodology" : "Back to the tool"}
          </button>
        </nav>
        <span className={`session-status session-status-${sessionStatus}`}>
          <span className="session-status-dot" aria-hidden="true" />
          {sessionStatus === "fault" ? "Fault" : sessionStatus === "solving" ? "Solving" : "Ready"}
        </span>
      </header>

      {view === "how-it-works" ? (
        <HowItWorks onBack={() => setView("studio")} />
      ) : (
        <>
          <section className="headline-band" aria-label="Headline metric">
            <HeadlineStat summary={evaluationSummary} isLoading={isSummaryLoading} error={summaryError} />
          </section>

          <main className="shell-main">
            <details className="control-rail" open>
              <summary className="control-panel-summary blade-label">Race setup</summary>
              <ControlPanel onSolve={handleSolve} isLoading={isLoading} onSelectionChange={setCurrentSelection} />
            </details>
            <section className="results-zone" aria-label="Recommended plan">
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
        </>
      )}

      <footer className="shell-footer">
        <span>Dispatch -- a race-strategy portfolio project</span>
        <span className="shell-footer-mono">CP-SAT solver · real circuit data</span>
      </footer>
    </div>
  );
}

export default App;
