/* Portfolio value over time.
 *
 * Hand-drawn SVG rather than a charting library: one chart does not
 * justify a dependency, and every coordinate here is one we control.
 */

import { money } from "../utils/format";

const W = 560;
const H = 206;
const LEFT = 48;
const RIGHT = 540;
const TOP = 24;
const BOTTOM = 180;

/** Catmull-Rom through the points, emitted as cubic beziers. A polyline
 *  of twelve months looks jagged; this reads as a price curve. */
function smoothPath(points) {
  if (points.length < 2) return "";
  let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || points[i + 1];
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }
  return d;
}

/** 9,99,684 -> "10.0L". Lakhs are how amounts of this size are spoken
 *  about in India; "999.7K" would read as a translation. */
function lakhs(value) {
  return (value / 100000).toFixed(1) + "L";
}

export default function ValueChart({ series, investedLine }) {
  if (!series || series.length < 2) {
    return (
      <p className="muted" style={{ fontSize: 13, margin: "28px 0", textAlign: "center" }}>
        Not enough history yet. Record a few trades and run the price fetch.
      </p>
    );
  }

  const values = series.map((p) => p.value);
  const candidates = investedLine ? [...values, investedLine] : values;
  const rawMin = Math.min(...candidates);
  const rawMax = Math.max(...candidates);
  // A little padding so the line never touches the frame, and a floor of
  // zero span so a flat series does not divide by zero.
  const pad = Math.max((rawMax - rawMin) * 0.12, 1);
  const min = rawMin - pad;
  const max = rawMax + pad;

  const x = (i) => LEFT + (i * (RIGHT - LEFT)) / (series.length - 1);
  const y = (v) => BOTTOM - ((v - min) / (max - min)) * (BOTTOM - TOP);

  const points = series.map((p, i) => ({ x: x(i), y: y(p.value) }));
  const line = smoothPath(points);
  const area = `${line} L ${RIGHT} ${BOTTOM} L ${LEFT} ${BOTTOM} Z`;
  const last = points[points.length - 1];

  const ticks = [max, (max + min) / 2, min];
  const labelEvery = Math.max(1, Math.round(series.length / 4));

  return (
    <figure style={{ margin: 0 }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block", width: "100%", height: "auto" }}
        role="img"
        aria-label={`Portfolio value from ${money(series[0].value)} to ${money(
          series[series.length - 1].value
        )}`}
      >
        <defs>
          <linearGradient id="valueFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--series-fill-top)" />
            <stop offset="100%" stopColor="transparent" />
          </linearGradient>
        </defs>

        {ticks.map((value, i) => {
          const ty = y(value);
          return (
            <g key={i}>
              <line x1={LEFT} y1={ty} x2={RIGHT} y2={ty} stroke="var(--rule)" />
              <text
                x={LEFT - 8}
                y={ty + 4}
                textAnchor="end"
                fontSize="11"
                fill="var(--ink-2)"
                fontFamily="inherit"
              >
                {lakhs(value)}
              </text>
            </g>
          );
        })}

        <path d={area} fill="url(#valueFill)" />
        <path
          d={line}
          fill="none"
          stroke="var(--series)"
          strokeWidth="2.25"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {investedLine ? (
          <>
            <line
              x1={LEFT}
              y1={y(investedLine)}
              x2={RIGHT}
              y2={y(investedLine)}
              stroke="var(--ink-3)"
              strokeWidth="1"
              strokeDasharray="3 5"
            />
            {/* Right-aligned: at the left edge this label sat on top of
                the y-axis tick and the start of the curve. */}
            <text
              x={RIGHT}
              y={y(investedLine) - 6}
              textAnchor="end"
              fontSize="10.5"
              fill="var(--ink-2)"
              fontFamily="inherit"
            >
              {money(investedLine)} invested
            </text>
          </>
        ) : null}

        {/* Invisible hit targets, so every point has a native tooltip. */}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="10" fill="transparent">
            <title>{`${series[i].label} — ${money(series[i].value)}`}</title>
          </circle>
        ))}

        <circle cx={last.x} cy={last.y} r="4.5" fill="var(--series)" stroke="var(--card)" strokeWidth="2.5" />

        {series.map((p, i) =>
          i % labelEvery === 0 || i === series.length - 1 ? (
            <text
              key={i}
              x={x(i)}
              y={H - 7}
              textAnchor={i === 0 ? "start" : i === series.length - 1 ? "end" : "middle"}
              fontSize="10.5"
              fill="var(--ink-3)"
              fontFamily="inherit"
            >
              {p.short}
            </text>
          ) : null
        )}
      </svg>
    </figure>
  );
}
