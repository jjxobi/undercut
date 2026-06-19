import { useState } from "react";

import "./DistributionChart.css";

// A histogram needs enough bins to show shape without turning into noise.
// Fixed at 12 rather than derived from sample size -- the bin *width* still
// adapts to whatever range the real costs span, which is the part that
// actually matters for two arrays this size.
export const BIN_COUNT = 12;

const SVG_WIDTH = 640;
const SVG_HEIGHT = 320;
const MARGIN = { top: 16, right: 16, bottom: 44, left: 48 };
const BAR_GAP = 2;

interface DistributionChartProps {
  deterministicCosts: number[];
  stochasticCosts: number[];
}

export interface HistogramBins {
  edges: number[];
  deterministicCounts: number[];
  stochasticCounts: number[];
  maxCount: number;
}

export function computeHistogramBins(
  deterministicCosts: number[],
  stochasticCosts: number[],
  binCount: number = BIN_COUNT,
): HistogramBins {
  const all = [...deterministicCosts, ...stochasticCosts];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const range = max - min;
  const width = range > 0 ? range / binCount : 1;

  const edges = Array.from({ length: binCount + 1 }, (_, index) => min + index * width);

  function countInto(values: number[]): number[] {
    const counts = new Array(binCount).fill(0);
    for (const value of values) {
      let index = range > 0 ? Math.floor((value - min) / width) : 0;
      if (index >= binCount) index = binCount - 1;
      if (index < 0) index = 0;
      counts[index] += 1;
    }
    return counts;
  }

  const deterministicCounts = countInto(deterministicCosts);
  const stochasticCounts = countInto(stochasticCosts);
  const maxCount = Math.max(1, ...deterministicCounts, ...stochasticCounts);

  return { edges, deterministicCounts, stochasticCounts, maxCount };
}

function formatCost(value: number): string {
  return `${value.toFixed(1)}s`;
}

function niceYTicks(maxCount: number): number[] {
  const step = Math.max(1, Math.ceil(maxCount / 4));
  const ticks: number[] = [];
  for (let value = 0; value <= maxCount + step && ticks.length <= 6; value += step) {
    ticks.push(value);
  }
  return ticks;
}

function DistributionChart({ deterministicCosts, stochasticCosts }: DistributionChartProps) {
  const [hoveredBin, setHoveredBin] = useState<number | null>(null);

  if (deterministicCosts.length === 0 && stochasticCosts.length === 0) {
    return null;
  }

  const { edges, deterministicCounts, stochasticCounts, maxCount } = computeHistogramBins(
    deterministicCosts,
    stochasticCosts,
  );

  const plotWidth = SVG_WIDTH - MARGIN.left - MARGIN.right;
  const plotHeight = SVG_HEIGHT - MARGIN.top - MARGIN.bottom;
  const binCount = deterministicCounts.length;
  const slotWidth = plotWidth / binCount;
  const barWidth = Math.max(1, slotWidth - BAR_GAP);
  const yTicks = niceYTicks(maxCount);
  const yScaleMax = yTicks[yTicks.length - 1];
  const yScale = (count: number) => (count / yScaleMax) * plotHeight;
  const labelStep = Math.max(1, Math.ceil(edges.length / 6));

  return (
    <div className="distribution-chart">
      <div className="distribution-chart-legend">
        <span className="distribution-chart-legend-item">
          <span
            className="distribution-chart-swatch distribution-chart-swatch-deterministic"
            aria-hidden="true"
          />
          Deterministic plan
        </span>
        <span className="distribution-chart-legend-item">
          <span className="distribution-chart-swatch distribution-chart-swatch-stochastic" aria-hidden="true" />
          Stochastic plan
        </span>
      </div>

      <div className="distribution-chart-canvas">
        <svg
          className="distribution-chart-svg"
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
          role="img"
          aria-label="Overlaid histogram comparing the deterministic and stochastic plans' held-out cost distributions"
        >
          <g transform={`translate(${MARGIN.left}, ${MARGIN.top})`}>
            {yTicks.map((tick) => {
              const y = plotHeight - yScale(tick);
              return (
                <g key={tick}>
                  <line x1={0} x2={plotWidth} y1={y} y2={y} className="distribution-chart-gridline" />
                  <text x={-10} y={y} className="distribution-chart-axis-label" textAnchor="end" dy="0.32em">
                    {tick}
                  </text>
                </g>
              );
            })}

            {deterministicCounts.map((count, index) => {
              const x = index * slotWidth;
              const detHeight = yScale(count);
              const stoHeight = yScale(stochasticCounts[index]);
              const isHovered = hoveredBin === index;

              // Translucent fill alone can't separate two bars that land at close to the
              // same height -- their overlap just reads as one blob. So whichever bar is
              // shorter gets drawn last (on top) with a solid ring around it, cutting a
              // clean edge out of the taller one behind it instead of blending into it.
              const bothPresent = detHeight > 0 && stoHeight > 0;
              const deterministicInFront = detHeight <= stoHeight;
              const separatedClass = bothPresent ? " distribution-chart-bar-separated" : "";

              const deterministicBar = (
                <rect
                  key="deterministic"
                  data-testid={`distribution-bar-deterministic-${index}`}
                  x={x}
                  y={plotHeight - detHeight}
                  width={barWidth}
                  height={detHeight}
                  rx={2}
                  className={
                    "distribution-chart-bar distribution-chart-bar-deterministic" +
                    (isHovered ? " distribution-chart-bar-hovered" : "") +
                    (deterministicInFront ? separatedClass : "")
                  }
                />
              );
              const stochasticBar = (
                <rect
                  key="stochastic"
                  data-testid={`distribution-bar-stochastic-${index}`}
                  x={x}
                  y={plotHeight - stoHeight}
                  width={barWidth}
                  height={stoHeight}
                  rx={2}
                  className={
                    "distribution-chart-bar distribution-chart-bar-stochastic" +
                    (isHovered ? " distribution-chart-bar-hovered" : "") +
                    (deterministicInFront ? "" : separatedClass)
                  }
                />
              );

              return (
                <g
                  key={index}
                  className="distribution-chart-bin"
                  data-testid={`distribution-bin-${index}`}
                  tabIndex={0}
                  onMouseEnter={() => setHoveredBin(index)}
                  onMouseLeave={() => setHoveredBin(null)}
                  onFocus={() => setHoveredBin(index)}
                  onBlur={() => setHoveredBin(null)}
                >
                  <rect x={x} y={0} width={slotWidth} height={plotHeight} className="distribution-chart-hit-area" />
                  {deterministicInFront ? (
                    <>
                      {stochasticBar}
                      {deterministicBar}
                    </>
                  ) : (
                    <>
                      {deterministicBar}
                      {stochasticBar}
                    </>
                  )}
                </g>
              );
            })}

            <line x1={0} x2={plotWidth} y1={plotHeight} y2={plotHeight} className="distribution-chart-axis-line" />

            {edges.map((edge, index) =>
              index % labelStep === 0 ? (
                <text
                  key={edge}
                  x={index * slotWidth}
                  y={plotHeight + 20}
                  className="distribution-chart-axis-label"
                  textAnchor="middle"
                >
                  {formatCost(edge)}
                </text>
              ) : null,
            )}

            <text
              x={plotWidth / 2}
              y={plotHeight + 38}
              className="distribution-chart-axis-title"
              textAnchor="middle"
            >
              Held-out cost per scenario
            </text>
          </g>
        </svg>

        {hoveredBin !== null && (
          <div
            className="distribution-chart-tooltip"
            role="tooltip"
            style={{ left: `${((MARGIN.left + hoveredBin * slotWidth + slotWidth / 2) / SVG_WIDTH) * 100}%` }}
          >
            <p className="distribution-chart-tooltip-range">
              {formatCost(edges[hoveredBin])}&ndash;{formatCost(edges[hoveredBin + 1])}
            </p>
            <p className="distribution-chart-tooltip-row">
              <span
                className="distribution-chart-tooltip-key distribution-chart-tooltip-key-deterministic"
                aria-hidden="true"
              />
              Deterministic <strong>{deterministicCounts[hoveredBin]}</strong>
            </p>
            <p className="distribution-chart-tooltip-row">
              <span
                className="distribution-chart-tooltip-key distribution-chart-tooltip-key-stochastic"
                aria-hidden="true"
              />
              Stochastic <strong>{stochasticCounts[hoveredBin]}</strong>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DistributionChart;
