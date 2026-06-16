import { useEffect, useState } from "react";

import { fetchCircuits } from "../api/client";
import type { CircuitInfo, StrategyRequest } from "../api/types";
import "./ControlPanel.css";

const MIN_RACE_LENGTH = 1;
const MAX_RACE_LENGTH = 100;
const MIN_SCENARIOS = 1;
const MAX_SCENARIOS = 2000;
const DEFAULT_SCENARIOS = 200;
const FALLBACK_RACE_LENGTH = 57;

interface ControlPanelProps {
  onSolve: (request: StrategyRequest) => void;
  isLoading: boolean;
}

function formatCircuitLabel(circuitId: string): string {
  return circuitId
    .split("_")
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

type LoadState = "loading" | "ready" | "error";

function ControlPanel({ onSolve, isLoading }: ControlPanelProps) {
  const [circuits, setCircuits] = useState<CircuitInfo[]>([]);
  const [eras, setEras] = useState<string[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null);

  const [circuitId, setCircuitId] = useState("");
  const [era, setEra] = useState("");
  const [raceLength, setRaceLength] = useState(FALLBACK_RACE_LENGTH);
  const [nScenarios, setNScenarios] = useState(DEFAULT_SCENARIOS);

  useEffect(() => {
    let cancelled = false;

    fetchCircuits()
      .then((response) => {
        if (cancelled) return;
        setCircuits(response.circuits);
        setEras(response.eras);
        const firstCircuit = response.circuits[0];
        if (firstCircuit) {
          setCircuitId(firstCircuit.circuit_id);
          setRaceLength(firstCircuit.default_race_length);
        }
        if (response.eras[0]) {
          setEra(response.eras[0]);
        }
        setLoadState("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadErrorMessage(err instanceof Error ? err.message : String(err));
        setLoadState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function handleCircuitChange(nextCircuitId: string) {
    setCircuitId(nextCircuitId);
    const match = circuits.find((circuit) => circuit.circuit_id === nextCircuitId);
    if (match) {
      setRaceLength(match.default_race_length);
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!circuitId || !era) return;
    onSolve({
      circuit_id: circuitId,
      era,
      race_length: raceLength,
      n_scenarios: nScenarios,
    });
  }

  const formDisabled = loadState !== "ready";

  return (
    <form className="control-panel-form" onSubmit={handleSubmit}>
      <div className="control-panel-field">
        <label htmlFor="circuit-select">Circuit</label>
        <select
          id="circuit-select"
          value={circuitId}
          onChange={(event) => handleCircuitChange(event.target.value)}
          disabled={formDisabled}
          required
        >
          {circuits.length === 0 && <option value="">Loading circuits&hellip;</option>}
          {circuits.map((circuit) => (
            <option key={circuit.circuit_id} value={circuit.circuit_id}>
              {formatCircuitLabel(circuit.circuit_id)}
            </option>
          ))}
        </select>
      </div>

      <div className="control-panel-field">
        <label htmlFor="era-select">Regulation era</label>
        <select
          id="era-select"
          value={era}
          onChange={(event) => setEra(event.target.value)}
          disabled={formDisabled}
          required
        >
          {eras.length === 0 && <option value="">Loading eras&hellip;</option>}
          {eras.map((eraOption) => (
            <option key={eraOption} value={eraOption}>
              {eraOption}
            </option>
          ))}
        </select>
      </div>

      <div className="control-panel-field">
        <label htmlFor="race-length-input">Race length (laps)</label>
        <input
          id="race-length-input"
          type="number"
          min={MIN_RACE_LENGTH}
          max={MAX_RACE_LENGTH}
          value={raceLength}
          onChange={(event) => setRaceLength(Number(event.target.value))}
          disabled={formDisabled}
          required
        />
      </div>

      <div className="control-panel-field">
        <label htmlFor="scenario-count-input">Safety-car scenarios to hedge against</label>
        <input
          id="scenario-count-input"
          type="number"
          min={MIN_SCENARIOS}
          max={MAX_SCENARIOS}
          value={nScenarios}
          onChange={(event) => setNScenarios(Number(event.target.value))}
          disabled={formDisabled}
          required
        />
      </div>

      {loadState === "error" && (
        <p className="control-panel-load-error" role="alert">
          Couldn&rsquo;t load circuits: {loadErrorMessage}
        </p>
      )}

      <button type="submit" className="control-panel-submit" disabled={formDisabled || isLoading}>
        {isLoading ? (
          <>
            <span className="control-panel-spinner" aria-hidden="true" />
            Solving&hellip;
          </>
        ) : (
          "Solve"
        )}
      </button>
    </form>
  );
}

export default ControlPanel;
