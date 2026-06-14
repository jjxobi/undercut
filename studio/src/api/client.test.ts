import { afterEach, describe, expect, it, vi } from "vitest";

import { compareStrategies, fetchCircuits, fetchEvaluationSummary, solveStrategy } from "./client";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchCircuits", () => {
  it("calls GET /circuits and returns the parsed body", async () => {
    const body = { circuits: [{ circuit_id: "bahrain", default_race_length: 57 }], eras: ["2018-2021 aero"] };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(body));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchCircuits();

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/circuits", undefined);
    expect(result).toEqual(body);
  });

  it("throws with the backend's detail message on a non-OK response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: "regret_report.csv not found" }, 503));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchCircuits()).rejects.toThrow("regret_report.csv not found");
  });
});

describe("solveStrategy", () => {
  const request = { circuit_id: "bahrain", era: "2018-2021 aero", race_length: 57, n_scenarios: 200, seed: 0 };

  it("posts to /strategy with the request body and returns the parsed plan", async () => {
    const body = {
      status: "optimal",
      compounds: ["SOFT", "MEDIUM"],
      stint_lengths: [20, 37],
      pit_laps: [20],
      expected_cost_seconds: 5123.4,
      pit_loss_seconds: 22.1,
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(body));
    vi.stubGlobal("fetch", fetchMock);

    const result = await solveStrategy(request);

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/strategy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    expect(result).toEqual(body);
  });

  it("throws with the backend's detail message when the race length is infeasible", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ detail: "no feasible strategy for a 1-lap race" }, 422));
    vi.stubGlobal("fetch", fetchMock);

    await expect(solveStrategy({ ...request, race_length: 1 })).rejects.toThrow(
      "no feasible strategy for a 1-lap race",
    );
  });
});

describe("compareStrategies", () => {
  const request = { circuit_id: "bahrain", era: "2018-2021 aero", race_length: 20, n_scenarios: 5, seed: 1 };

  it("posts to /strategy/compare and returns both plans and cost distributions", async () => {
    const plan = { status: "optimal", compounds: ["SOFT"], stint_lengths: [20], pit_laps: [] };
    const body = {
      deterministic: { ...plan, expected_cost_seconds: 5000 },
      stochastic: { ...plan, expected_cost_seconds: 5050 },
      deterministic_costs: [5000, 5010, 4990, 5005, 4995],
      stochastic_costs: [5040, 5060, 5045, 5055, 5050],
      gap_seconds: -50,
      gap_standard_error: 12.5,
      gap_is_significant: true,
      pit_loss_seconds: 22.1,
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(body));
    vi.stubGlobal("fetch", fetchMock);

    const result = await compareStrategies(request);

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/strategy/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    expect(result).toEqual(body);
  });

  it("throws with the backend's detail message on an unknown circuit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: "unknown circuit_id: nowhere" }, 404));
    vi.stubGlobal("fetch", fetchMock);

    await expect(compareStrategies({ ...request, circuit_id: "nowhere" })).rejects.toThrow(
      "unknown circuit_id: nowhere",
    );
  });
});

describe("fetchEvaluationSummary", () => {
  it("calls GET /evaluation/summary and returns the parsed body", async () => {
    const body = {
      driver_races: 652,
      mean_actual_regret_seconds: 12.4,
      median_actual_regret_seconds: 8.1,
      mean_policy_regret_seconds: 4.6,
      median_policy_regret_seconds: 3.2,
      captured_fraction: 0.629,
      mean_regret_positions_per_race: 4.6,
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(body));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchEvaluationSummary();

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/evaluation/summary", undefined);
    expect(result).toEqual(body);
  });

  it("throws a descriptive error when the response body has no detail field", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("internal error", { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchEvaluationSummary()).rejects.toThrow(/500/);
  });
});
