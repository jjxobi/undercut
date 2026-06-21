import type {
  CircuitsResponse,
  CompareRequest,
  CompareResponse,
  EvaluationSummaryResponse,
  StrategyRequest,
  StrategyResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body?.detail)) {
      return body.detail.map((entry: { msg?: string }) => entry.msg ?? JSON.stringify(entry)).join("; ");
    }
  } catch {
    // body wasn't JSON -- fall back to the status text below
  }
  return response.statusText || `status ${response.status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    // Panels show this message to the user as-is, so it stays in the
    // backend's own plain words rather than a route/status prefix meant
    // for a terminal.
    throw new Error(await readErrorDetail(response));
  }
  return (await response.json()) as T;
}

export function fetchCircuits(): Promise<CircuitsResponse> {
  return request<CircuitsResponse>("/circuits");
}

export function solveStrategy(payload: StrategyRequest): Promise<StrategyResponse> {
  return request<StrategyResponse>("/strategy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function compareStrategies(payload: CompareRequest): Promise<CompareResponse> {
  return request<CompareResponse>("/strategy/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function fetchEvaluationSummary(): Promise<EvaluationSummaryResponse> {
  return request<EvaluationSummaryResponse>("/evaluation/summary");
}
