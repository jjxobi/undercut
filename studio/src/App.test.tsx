import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchCircuits, fetchEvaluationSummary } from "./api/client";
import App from "./App";

vi.mock("./api/client", () => ({
  fetchCircuits: vi.fn(),
  fetchEvaluationSummary: vi.fn(),
  solveStrategy: vi.fn(),
  compareStrategies: vi.fn(),
}));

const mockedFetchCircuits = vi.mocked(fetchCircuits);
const mockedFetchEvaluationSummary = vi.mocked(fetchEvaluationSummary);

afterEach(() => {
  vi.clearAllMocks();
});

describe("App", () => {
  it("keeps a single h1 on the page and toggles between the write-up page and the studio", async () => {
    mockedFetchCircuits.mockResolvedValue({ circuits: [], eras: [] });
    mockedFetchEvaluationSummary.mockResolvedValue({
      driver_races: 652,
      mean_actual_regret_seconds: 16.77,
      median_actual_regret_seconds: 8.1,
      mean_policy_regret_seconds: 6.17,
      median_policy_regret_seconds: 3.2,
      captured_fraction: 0.629,
      mean_regret_positions_per_race: null,
    });

    render(<App />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "Methodology" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pit Strategy Tool" }));

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.queryByRole("heading", { level: 2, name: "Methodology" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Methodology" }));

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "Methodology" })).toBeInTheDocument();
  });

  it("marks the active nav link for the current page", async () => {
    mockedFetchCircuits.mockResolvedValue({ circuits: [], eras: [] });
    mockedFetchEvaluationSummary.mockResolvedValue({
      driver_races: 652,
      mean_actual_regret_seconds: 16.77,
      median_actual_regret_seconds: 8.1,
      mean_policy_regret_seconds: 6.17,
      median_policy_regret_seconds: 3.2,
      captured_fraction: 0.629,
      mean_regret_positions_per_race: null,
    });

    render(<App />);

    expect(screen.getByRole("button", { name: "Methodology" })).toHaveClass("shell-nav-link-active");
    expect(screen.getByRole("button", { name: "Pit Strategy Tool" })).not.toHaveClass("shell-nav-link-active");

    fireEvent.click(screen.getByRole("button", { name: "Pit Strategy Tool" }));

    expect(screen.getByRole("button", { name: "Pit Strategy Tool" })).toHaveClass("shell-nav-link-active");
    expect(screen.getByRole("button", { name: "Methodology" })).not.toHaveClass("shell-nav-link-active");
  });

  it("navigates to the studio from the methodology page's bottom call to action", async () => {
    mockedFetchCircuits.mockResolvedValue({ circuits: [], eras: [] });
    mockedFetchEvaluationSummary.mockResolvedValue({
      driver_races: 652,
      mean_actual_regret_seconds: 16.77,
      median_actual_regret_seconds: 8.1,
      mean_policy_regret_seconds: 6.17,
      median_policy_regret_seconds: 3.2,
      captured_fraction: 0.629,
      mean_regret_positions_per_race: null,
    });

    render(<App />);

    expect(screen.getByRole("heading", { level: 2, name: "Methodology" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /view the tool/i }));

    expect(screen.queryByRole("heading", { level: 2, name: "Methodology" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to the tool" })).not.toBeInTheDocument();
  });
});
