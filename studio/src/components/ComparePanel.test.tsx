import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CompareResponse } from "../api/types";
import ComparePanel from "./ComparePanel";

const selection = { circuit_id: "bahrain", era: "2018-2021 aero", race_length: 57 };

const planSummary = {
  status: "ok",
  compounds: ["SOFT", "HARD"],
  stint_lengths: [28, 29],
  pit_laps: [28],
  expected_cost_seconds: 5400,
};

const compareResult: CompareResponse = {
  deterministic: planSummary,
  stochastic: planSummary,
  deterministic_costs: [5390, 5400, 5410],
  stochastic_costs: [5395, 5398, 5401],
  gap_seconds: 3.2,
  gap_standard_error: 1.1,
  gap_is_significant: true,
  pit_loss_seconds: 22.5,
};

describe("ComparePanel", () => {
  it("disables the check-confidence button until a selection exists", () => {
    render(<ComparePanel selection={null} result={null} isLoading={false} error={null} onCompare={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Check confidence" })).toBeDisabled();
  });

  it("calls onCompare with the selection plus the fixed scenario count and seed", () => {
    const onCompare = vi.fn();
    render(<ComparePanel selection={selection} result={null} isLoading={false} error={null} onCompare={onCompare} />);

    const button = screen.getByRole("button", { name: "Check confidence" });
    expect(button).not.toBeDisabled();

    fireEvent.click(button);

    expect(onCompare).toHaveBeenCalledTimes(1);
    expect(onCompare).toHaveBeenCalledWith({
      circuit_id: "bahrain",
      era: "2018-2021 aero",
      race_length: 57,
      n_scenarios: 200,
      seed: 0,
    });
  });

  it("disables the button while a comparison is already running", () => {
    render(<ComparePanel selection={selection} result={null} isLoading error={null} onCompare={vi.fn()} />);

    expect(screen.getByRole("button", { name: /Comparing/ })).toBeDisabled();
  });

  it("shows the real backend error message when the comparison fails", () => {
    render(
      <ComparePanel
        selection={selection}
        result={null}
        isLoading={false}
        error="POST /strategy/compare failed (422): unknown era"
        onCompare={vi.fn()}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("unknown era");
  });

  it("frames a real significant gap in favour of the hedge when the deterministic plan cost more", () => {
    render(
      <ComparePanel selection={selection} result={compareResult} isLoading={false} error={null} onCompare={vi.fn()} />,
    );

    expect(screen.getByText(/hedge earned its keep/)).toBeInTheDocument();
    expect(screen.getByText("+3.2s ± 1.1s")).toBeInTheDocument();
  });

  it("frames a non-significant gap as no meaningful difference", () => {
    const noisyResult: CompareResponse = { ...compareResult, gap_is_significant: false };
    render(
      <ComparePanel selection={selection} result={noisyResult} isLoading={false} error={null} onCompare={vi.fn()} />,
    );

    expect(screen.getByText(/neither helped nor hurt/)).toBeInTheDocument();
  });

  it("frames a negative gap as the hedge not being worth it", () => {
    const worseHedge: CompareResponse = { ...compareResult, gap_seconds: -4.5 };
    render(
      <ComparePanel selection={selection} result={worseHedge} isLoading={false} error={null} onCompare={vi.fn()} />,
    );

    expect(screen.getByText(/wasn't worth it/)).toBeInTheDocument();
  });
});
