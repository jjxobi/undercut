import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HowItWorks from "./HowItWorks";

describe("HowItWorks", () => {
  it("renders the page title as an h2 and every section heading", () => {
    render(<HowItWorks onBack={vi.fn()} />);

    expect(screen.getByRole("heading", { level: 2, name: "Methodology" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "The problem" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "How it decides" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "What it found" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "What this doesn't claim" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Why this exists" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
  });

  it("carries the headline regret figures", () => {
    render(<HowItWorks onBack={vi.fn()} />);

    expect(screen.getByText("17 seconds")).toBeInTheDocument();
    expect(screen.getByText("63%")).toBeInTheDocument();
  });

  it("calls back to the tool when the back control is used", () => {
    const onBack = vi.fn();
    render(<HowItWorks onBack={onBack} />);

    fireEvent.click(screen.getByRole("button", { name: /back to the tool/i }));

    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
