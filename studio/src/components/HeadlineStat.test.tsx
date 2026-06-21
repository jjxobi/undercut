import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { EvaluationSummaryResponse } from "../api/types";
import HeadlineStat from "./HeadlineStat";

const summaryWithPositions: EvaluationSummaryResponse = {
  driver_races: 652,
  mean_actual_regret_seconds: 12.4,
  median_actual_regret_seconds: 8.1,
  mean_policy_regret_seconds: 4.6,
  median_policy_regret_seconds: 3.2,
  captured_fraction: 0.629,
  mean_regret_positions_per_race: 4.6,
};

describe("HeadlineStat", () => {
  it("shows a spinner while the baseline is loading", () => {
    render(<HeadlineStat summary={null} isLoading error={null} />);

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows the backend's real detail message when the baseline fails to load", () => {
    render(
      <HeadlineStat summary={null} isLoading={false} error="regret_report.csv not found -- run scripts/run_evaluation.py first" />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("regret_report.csv not found");
  });

  it("renders the real percentage and positions figure computed from the response", () => {
    render(<HeadlineStat summary={summaryWithPositions} isLoading={false} error={null} />);

    // jsdom has no matchMedia, so the roll animation is skipped and the
    // component renders straight at its resting value.
    expect(screen.getByText("4.6")).toBeInTheDocument();
    expect(screen.getByText("positions / race")).toBeInTheDocument();
    expect(screen.getByText("63%")).toBeInTheDocument();
    expect(screen.getByText(/652 real driver-races/)).toBeInTheDocument();
  });

  it("falls back to the seconds framing when no positions figure is available", () => {
    const summaryWithoutPositions: EvaluationSummaryResponse = {
      ...summaryWithPositions,
      mean_regret_positions_per_race: null,
    };

    render(<HeadlineStat summary={summaryWithoutPositions} isLoading={false} error={null} />);

    expect(screen.getByText("12.4")).toBeInTheDocument();
    expect(screen.getByText("seconds / race")).toBeInTheDocument();
    expect(screen.queryByText("positions / race")).not.toBeInTheDocument();
  });

  it("renders nothing once loading has finished with no error and no summary yet", () => {
    const { container } = render(<HeadlineStat summary={null} isLoading={false} error={null} />);

    expect(container).toBeEmptyDOMElement();
  });
});
