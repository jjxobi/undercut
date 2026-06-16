import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import StintBar, { COMPOUND_COLOR } from "./StintBar";

describe("StintBar", () => {
  const compounds = ["SOFT", "MEDIUM", "HARD"];
  const stintLengths = [15, 20, 22];
  const pitLaps = [15, 35];
  const raceLength = 57;

  it("sizes each segment proportionally to its share of the race", () => {
    const { getByTestId } = render(
      <StintBar compounds={compounds} stintLengths={stintLengths} pitLaps={pitLaps} raceLength={raceLength} />,
    );

    stintLengths.forEach((length, index) => {
      const expectedWidth = `${(length / raceLength) * 100}%`;
      expect(getByTestId(`stint-segment-${index}`).style.width).toBe(expectedWidth);
    });
  });

  it("fills each segment with its compound's real design-token color", () => {
    const { getByTestId } = render(
      <StintBar compounds={compounds} stintLengths={stintLengths} pitLaps={pitLaps} raceLength={raceLength} />,
    );

    compounds.forEach((compound, index) => {
      expect(getByTestId(`stint-segment-${index}`).style.backgroundColor).toBe(COMPOUND_COLOR[compound]);
    });
  });

  it("uses a dark-ink label on the HARD segment only, since its fill is near-white", () => {
    const { getByTestId } = render(
      <StintBar compounds={compounds} stintLengths={stintLengths} pitLaps={pitLaps} raceLength={raceLength} />,
    );

    expect(getByTestId("stint-segment-0").style.color).toBe("var(--ink-primary)");
    expect(getByTestId("stint-segment-1").style.color).toBe("var(--ink-primary)");
    expect(getByTestId("stint-segment-2").style.color).toBe("var(--surface-0)");
  });

  it("labels each segment with the compound name and lap count", () => {
    const { getByTestId } = render(
      <StintBar compounds={compounds} stintLengths={stintLengths} pitLaps={pitLaps} raceLength={raceLength} />,
    );

    expect(getByTestId("stint-segment-0").textContent).toContain("SOFT");
    expect(getByTestId("stint-segment-0").textContent).toContain("15 laps");
    expect(getByTestId("stint-segment-2").textContent).toContain("HARD");
    expect(getByTestId("stint-segment-2").textContent).toContain("22 laps");
  });

  it("describes the plan and pit laps for assistive technology", () => {
    const { getByRole } = render(
      <StintBar compounds={compounds} stintLengths={stintLengths} pitLaps={pitLaps} raceLength={raceLength} />,
    );

    const label = getByRole("img").getAttribute("aria-label") ?? "";
    expect(label).toContain("SOFT for 15 laps");
    expect(label).toContain("lap 15 and lap 35");
  });
});
