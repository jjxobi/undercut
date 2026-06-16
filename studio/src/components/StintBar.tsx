import "./StintBar.css";

export const COMPOUND_COLOR: Record<string, string> = {
  SOFT: "var(--tire-soft)",
  MEDIUM: "var(--tire-medium)",
  HARD: "var(--tire-hard)",
};

const HARD_COMPOUND = "HARD";

interface StintBarProps {
  compounds: string[];
  stintLengths: number[];
  pitLaps: number[];
  raceLength: number;
}

function StintBar({ compounds, stintLengths, pitLaps, raceLength }: StintBarProps) {
  const segments = compounds.map((compound, index) => `${compound} for ${stintLengths[index] ?? 0} laps`);
  const pitSummary = pitLaps.length > 0 ? `pitting on lap ${pitLaps.join(" and lap ")}` : "no pit stops";
  const description = `Recommended plan: ${segments.join(", then ")}, ${pitSummary}.`;

  return (
    <div className="stint-bar" role="img" aria-label={description}>
      <div className="stint-bar-reveal">
        <div className="stint-bar-track">
          {compounds.map((compound, index) => {
            const length = stintLengths[index] ?? 0;
            const widthPercent = raceLength > 0 ? (length / raceLength) * 100 : 0;
            const isHard = compound === HARD_COMPOUND;
            return (
              <div
                key={`${compound}-${index}`}
                className="stint-bar-segment"
                data-testid={`stint-segment-${index}`}
                data-compound={compound}
                style={{
                  width: `${widthPercent}%`,
                  backgroundColor: COMPOUND_COLOR[compound] ?? "var(--ink-muted)",
                  color: isHard ? "var(--surface-0)" : "var(--ink-primary)",
                }}
              >
                <span className="stint-bar-label">
                  {compound} &middot; {length} laps
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default StintBar;
