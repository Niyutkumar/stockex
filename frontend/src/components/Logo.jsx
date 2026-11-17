/* The Lot Stack mark.
 *
 * Three bars of different lengths — the FIFO lots the position engine
 * replays. The fills come from CSS variables rather than fixed hex, so
 * the mark re-colours itself with the theme: a mint green that reads on
 * near-black washes out completely on white.
 */

export default function Logo({ size = 24 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      role="img"
      aria-label="StockEx"
    >
      <rect x="4" y="6" width="24" height="5.2" rx="2.6" fill="var(--logo-1)" />
      <rect x="4" y="13.4" width="16" height="5.2" rx="2.6" fill="var(--logo-2)" />
      <rect x="4" y="20.8" width="21" height="5.2" rx="2.6" fill="var(--logo-3)" />
    </svg>
  );
}

export function Wordmark({ size = 24, fontSize = 16 }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 9 }}>
      <Logo size={size} />
      <span style={{ fontSize, fontWeight: 800, letterSpacing: "-0.01em" }}>
        Stock<span style={{ color: "var(--accent)" }}>Ex</span>
      </span>
    </span>
  );
}
