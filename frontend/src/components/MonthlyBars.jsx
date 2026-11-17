/* Month-on-month percentage change.
 *
 * Green up, red down. The reference design this is based on paints each
 * bar a different colour for decoration; here the colour means something,
 * which matters in an app where green and red already mean profit and
 * loss everywhere else.
 */

import { signedPercent } from "../utils/format";

const W = 560;
const H = 206;
const LEFT = 42;
const RIGHT = 548;
const TOP = 22;
const BOTTOM = 172;

export default function MonthlyBars({ changes }) {
  if (!changes || changes.length === 0) {
    return (
      <p className="muted" style={{ fontSize: 13, margin: "28px 0", textAlign: "center" }}>
        Needs at least two months of history.
      </p>
    );
  }

  const values = changes.map((c) => c.pct);
  const high = Math.max(...values, 0);
  const low = Math.min(...values, 0);
  const span = Math.max(high - low, 0.5);
  const zero = TOP + (high / span) * (BOTTOM - TOP);
  const scale = (BOTTOM - TOP) / span;

  const step = (RIGHT - LEFT) / changes.length;
  const barWidth = Math.max(Math.min(step - 14, 32), 6);

  return (
    <figure style={{ margin: 0 }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block", width: "100%", height: "auto" }}
        role="img"
        aria-label={`Monthly change, ${changes.filter((c) => c.pct >= 0).length} months up and ${
          changes.filter((c) => c.pct < 0).length
        } down`}
      >
        <line x1={LEFT} y1={TOP} x2={RIGHT} y2={TOP} stroke="var(--rule)" />
        <line x1={LEFT} y1={zero} x2={RIGHT} y2={zero} stroke="var(--ink-3)" />
        <text x={LEFT - 6} y={TOP + 4} textAnchor="end" fontSize="10.5" fill="var(--ink-2)" fontFamily="inherit">
          {high.toFixed(0)}%
        </text>
        <text x={LEFT - 6} y={zero + 4} textAnchor="end" fontSize="10.5" fill="var(--ink-2)" fontFamily="inherit">
          0
        </text>

        {changes.map((c, i) => {
          const height = Math.max(Math.abs(c.pct) * scale, 2);
          const up = c.pct >= 0;
          const bx = LEFT + i * step + (step - barWidth) / 2;
          const by = up ? zero - height : zero;
          return (
            <g key={i}>
              <rect
                x={bx}
                y={by}
                width={barWidth}
                height={height}
                rx="4"
                fill={up ? "var(--gain)" : "var(--loss)"}
              >
                <title>{`${c.label} — ${signedPercent(c.pct)}`}</title>
              </rect>
              <text
                x={bx + barWidth / 2}
                y={H - 7}
                textAnchor="middle"
                fontSize="9.5"
                fill="var(--ink-3)"
                fontFamily="inherit"
              >
                {c.short}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
