import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HowItWorks from "./HowItWorks";

describe("HowItWorks", () => {
  it("renders the page title as an h2 and every section heading", () => {
    render(<HowItWorks onViewTool={vi.fn()} />);

    expect(screen.getByRole("heading", { level: 2, name: "Methodology" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "The problem" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "How it decides" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "What it found" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "What this doesn't claim" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Why this exists" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
  });

  it("carries the headline regret figures", () => {
    render(<HowItWorks onViewTool={vi.fn()} />);

    expect(screen.getByText("17 seconds")).toBeInTheDocument();
    expect(screen.getByText("63%")).toBeInTheDocument();
  });

  it("has no leftover back-to-the-tool control", () => {
    render(<HowItWorks onViewTool={vi.fn()} />);

    expect(screen.queryByRole("button", { name: /back to the tool/i })).not.toBeInTheDocument();
  });

  it("calls through to the tool when the bottom call to action is used", () => {
    const onViewTool = vi.fn();
    render(<HowItWorks onViewTool={onViewTool} />);

    fireEvent.click(screen.getByRole("button", { name: /view the tool/i }));

    expect(onViewTool).toHaveBeenCalledTimes(1);
  });
});
