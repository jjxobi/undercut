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

function buildRulerTicks(raceLength: number): { lap: number; isMajor: boolean }[] {
  if (raceLength <= 0) return [];
  const major = raceLength < 20 ? 5 : 10;
  const minorStep = raceLength < 20 ? 5 : 5;
  const ticks: { lap: number; isMajor: boolean }[] = [];
  for (let lap = 0; lap <= raceLength; lap += minorStep) {
    ticks.push({ lap, isMajor: lap % major === 0 || lap === raceLength });
  }
  if (ticks[ticks.length - 1]?.lap !== raceLength) {
    ticks.push({ lap: raceLength, isMajor: true });
  }
  return ticks;
}

function StintBar({ compounds, stintLengths, pitLaps, raceLength }: StintBarProps) {
  const segments = compounds.map((compound, index) => `${compound} for ${stintLengths[index] ?? 0} laps`);
  const pitSummary = pitLaps.length > 0 ? `pitting on lap ${pitLaps.join(" and lap ")}` : "no pit stops";
  const description = `Recommended plan: ${segments.join(", then ")}, ${pitSummary}.`;

  const ticks = buildRulerTicks(raceLength);
  const majorGap = raceLength < 20 ? 5 : 10;

  return (
    <div className="stint-bar" role="img" aria-label={description}>
      <div className="stint-bar-pits">
        {pitLaps.map((lap) => (
          <span key={lap} className="stint-bar-pit" style={{ left: `${(lap / raceLength) * 100}%` }}>
            <span className="stint-bar-pit-label">L{lap}</span>
            <span className="stint-bar-pit-notch" />
          </span>
        ))}
      </div>
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
                  ["--segment-index" as string]: index,
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
      <div className="stint-bar-ruler">
        {ticks.map(({ lap, isMajor }) => {
          const showLabel = isMajor && !(raceLength - lap < majorGap * 0.6 && lap !== raceLength);
          return (
            <span key={lap} className="stint-bar-tick" data-major={isMajor} style={{ left: `${(lap / raceLength) * 100}%` }}>
              {showLabel && <span className="stint-bar-tick-label">{lap}</span>}
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default StintBar;
