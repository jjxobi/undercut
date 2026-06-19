import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DistributionChart, { BIN_COUNT, computeHistogramBins } from "./DistributionChart";

// Combined range is 80..104 (24), split into BIN_COUNT (12) bins of width 2,
// so every edge lands on a whole number and every value's bin is easy to
// check by hand: bin index = floor((value - 80) / 2).
const deterministicCosts = [80, 81, 83, 90, 90, 90, 104];
const stochasticCosts = [80, 86, 86, 92, 98, 104, 104, 104];

describe("computeHistogramBins", () => {
  it("bins both arrays against one shared set of edges", () => {
    const { edges, deterministicCounts, stochasticCounts } = computeHistogramBins(
      deterministicCosts,
      stochasticCosts,
    );

    expect(edges).toEqual([80, 82, 84, 86, 88, 90, 92, 94, 96, 98, 100, 102, 104]);
    expect(deterministicCounts).toEqual([2, 1, 0, 0, 0, 3, 0, 0, 0, 0, 0, 1]);
    expect(stochasticCounts).toEqual([1, 0, 0, 2, 0, 0, 1, 0, 0, 1, 0, 3]);
  });
});

describe("DistributionChart", () => {
  it("renders one bar per bin for each series", () => {
    const { container } = render(
      <DistributionChart deterministicCosts={deterministicCosts} stochasticCosts={stochasticCosts} />,
    );

    expect(container.querySelectorAll('[data-testid^="distribution-bar-deterministic-"]')).toHaveLength(BIN_COUNT);
    expect(container.querySelectorAll('[data-testid^="distribution-bar-stochastic-"]')).toHaveLength(BIN_COUNT);
  });

  it("scales bar heights from the real per-bin counts, on a shared count axis", () => {
    const { getByTestId } = render(
      <DistributionChart deterministicCosts={deterministicCosts} stochasticCosts={stochasticCosts} />,
    );

    // maxCount across both series is 3 (deterministic bin 5, stochastic bin 11),
    // so the y-axis tops out at 4 and each unit of count is plotHeight/4 = 65px.
    expect(getByTestId("distribution-bar-deterministic-5").getAttribute("height")).toBe("195");
    expect(getByTestId("distribution-bar-deterministic-11").getAttribute("height")).toBe("65");
    expect(getByTestId("distribution-bar-stochastic-11").getAttribute("height")).toBe("195");
    expect(getByTestId("distribution-bar-stochastic-0").getAttribute("height")).toBe("65");
    expect(getByTestId("distribution-bar-deterministic-2").getAttribute("height")).toBe("0");
  });

  it("shows a legend naming both series", () => {
    render(<DistributionChart deterministicCosts={deterministicCosts} stochasticCosts={stochasticCosts} />);

    expect(screen.getByText("Deterministic plan")).toBeInTheDocument();
    expect(screen.getByText("Stochastic plan")).toBeInTheDocument();
  });

  it("reveals a tooltip with the hovered bin's real range and counts", () => {
    const { getByTestId, getByRole } = render(
      <DistributionChart deterministicCosts={deterministicCosts} stochasticCosts={stochasticCosts} />,
    );

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    fireEvent.mouseEnter(getByTestId("distribution-bin-5"));

    const tooltip = getByRole("tooltip");
    expect(tooltip).toHaveTextContent("90.0s");
    expect(tooltip).toHaveTextContent("92.0s");
    expect(tooltip).toHaveTextContent("Deterministic");
    expect(tooltip).toHaveTextContent("3");
    expect(tooltip).toHaveTextContent("Stochastic");

    fireEvent.mouseLeave(getByTestId("distribution-bin-5"));
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("also reveals the tooltip on keyboard focus, not just hover", () => {
    const { getByTestId, getByRole } = render(
      <DistributionChart deterministicCosts={deterministicCosts} stochasticCosts={stochasticCosts} />,
    );

    fireEvent.focus(getByTestId("distribution-bin-11"));
    const tooltip = getByRole("tooltip");
    expect(tooltip).toHaveTextContent("104.0s");

    fireEvent.blur(getByTestId("distribution-bin-11"));
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("rings the shorter bar when both series land at nearly the same count in a bin", () => {
    // Every value is identical (55) in both arrays, so the whole sample collapses
    // into bin 0 with counts 30 and 29 -- the same near-tie shape that gets lost
    // under plain translucent fill. Stochastic is the shorter one here, so it's
    // the bar that needs the separator ring; deterministic (taller, behind) doesn't.
    const closeCallDeterministic = Array(30).fill(55);
    const closeCallStochastic = Array(29).fill(55);

    const { getByTestId } = render(
      <DistributionChart deterministicCosts={closeCallDeterministic} stochasticCosts={closeCallStochastic} />,
    );

    expect(getByTestId("distribution-bar-stochastic-0")).toHaveClass("distribution-chart-bar-separated");
    expect(getByTestId("distribution-bar-deterministic-0")).not.toHaveClass("distribution-chart-bar-separated");
  });
});
