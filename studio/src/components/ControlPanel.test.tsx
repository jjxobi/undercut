import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchCircuits } from "../api/client";
import ControlPanel from "./ControlPanel";

vi.mock("../api/client", () => ({
  fetchCircuits: vi.fn(),
}));

const mockedFetchCircuits = vi.mocked(fetchCircuits);

const circuitsResponse = {
  circuits: [
    { circuit_id: "bahrain", default_race_length: 57 },
    { circuit_id: "spa_francorchamps", default_race_length: 44 },
  ],
  eras: ["2018-2021 aero", "2022-2025 ground-effect"],
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("ControlPanel", () => {
  it("populates the circuit and era selects from the real fetched list", async () => {
    mockedFetchCircuits.mockResolvedValue(circuitsResponse);
    render(<ControlPanel onSolve={vi.fn()} isLoading={false} onSelectionChange={vi.fn()} />);

    const circuitSelect = await screen.findByLabelText("Circuit");
    expect(within(circuitSelect).getAllByRole("option").map((option) => (option as HTMLOptionElement).value)).toEqual(
      ["bahrain", "spa_francorchamps"],
    );

    const eraSelect = screen.getByLabelText("Regulation era");
    expect(within(eraSelect).getAllByRole("option").map((option) => (option as HTMLOptionElement).value)).toEqual(
      circuitsResponse.eras,
    );
  });

  it("prefills race length from the selected circuit's real default", async () => {
    mockedFetchCircuits.mockResolvedValue(circuitsResponse);
    render(<ControlPanel onSolve={vi.fn()} isLoading={false} onSelectionChange={vi.fn()} />);

    await screen.findByLabelText("Circuit");
    expect(screen.getByLabelText("Race length (laps)")).toHaveValue(57);

    fireEvent.change(screen.getByLabelText("Circuit"), { target: { value: "spa_francorchamps" } });
    expect(screen.getByLabelText("Race length (laps)")).toHaveValue(44);
  });

  it("calls onSolve with the exact assembled request on submit", async () => {
    mockedFetchCircuits.mockResolvedValue(circuitsResponse);
    const onSolve = vi.fn();
    render(<ControlPanel onSolve={onSolve} isLoading={false} onSelectionChange={vi.fn()} />);

    await screen.findByLabelText("Circuit");
    fireEvent.change(screen.getByLabelText("Circuit"), { target: { value: "spa_francorchamps" } });
    fireEvent.change(screen.getByLabelText("Regulation era"), { target: { value: "2022-2025 ground-effect" } });
    fireEvent.change(screen.getByLabelText("Safety-car scenarios to hedge against"), { target: { value: "500" } });
    fireEvent.click(screen.getByRole("button", { name: "Solve" }));

    expect(onSolve).toHaveBeenCalledTimes(1);
    expect(onSolve).toHaveBeenCalledWith({
      circuit_id: "spa_francorchamps",
      era: "2022-2025 ground-effect",
      race_length: 44,
      n_scenarios: 500,
    });
  });

  it("shows a real loading state and disables the button while solving", async () => {
    mockedFetchCircuits.mockResolvedValue(circuitsResponse);
    render(<ControlPanel onSolve={vi.fn()} isLoading onSelectionChange={vi.fn()} />);

    await screen.findByLabelText("Circuit");
    const button = screen.getByRole("button", { name: /Solving/ });
    expect(button).toBeDisabled();
  });

  it("tells its parent the current selection on mount and again after changing the circuit", async () => {
    mockedFetchCircuits.mockResolvedValue(circuitsResponse);
    const onSelectionChange = vi.fn();
    render(<ControlPanel onSolve={vi.fn()} isLoading={false} onSelectionChange={onSelectionChange} />);

    await screen.findByLabelText("Circuit");
    expect(onSelectionChange).toHaveBeenCalledWith({
      circuit_id: "bahrain",
      era: "2018-2021 aero",
      race_length: 57,
    });

    onSelectionChange.mockClear();
    fireEvent.change(screen.getByLabelText("Circuit"), { target: { value: "spa_francorchamps" } });
    expect(onSelectionChange).toHaveBeenCalledWith({
      circuit_id: "spa_francorchamps",
      era: "2018-2021 aero",
      race_length: 44,
    });
  });

  it("shows the country next to the circuit name but skips it when redundant", async () => {
    mockedFetchCircuits.mockResolvedValue({
      circuits: [
        { circuit_id: "silverstone", default_race_length: 52 },
        { circuit_id: "bahrain", default_race_length: 57 },
      ],
      eras: circuitsResponse.eras,
    });
    render(<ControlPanel onSolve={vi.fn()} isLoading={false} onSelectionChange={vi.fn()} />);

    const circuitSelect = await screen.findByLabelText("Circuit");
    const options = within(circuitSelect).getAllByRole("option") as HTMLOptionElement[];
    expect(options.map((option) => option.textContent)).toEqual([
      "Silverstone (United Kingdom)",
      "Bahrain",
    ]);
  });

  it("surfaces the backend's real error message when circuits fail to load", async () => {
    mockedFetchCircuits.mockRejectedValue(new Error("GET /circuits failed (503): degradation_coefficients.csv not found"));
    render(<ControlPanel onSolve={vi.fn()} isLoading={false} onSelectionChange={vi.fn()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("degradation_coefficients.csv not found");
    expect(screen.getByRole("button", { name: "Solve" })).toBeDisabled();
  });
});
