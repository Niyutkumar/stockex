/* Number and date formatting.
 *
 * Indian grouping throughout: 9,99,684 rather than 999,684. Getting this
 * wrong is the fastest way to make a product for this market feel
 * foreign, and the browser does it for free with the en-IN locale.
 */

const RUPEES = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const RUPEES_PAISE = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const PLAIN = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

const PLAIN_PAISE = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function money(value, { paise = false } = {}) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return paise ? RUPEES_PAISE.format(n) : RUPEES.format(n);
}

export function plain(value, { paise = false } = {}) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return paise ? PLAIN_PAISE.format(n) : PLAIN.format(n);
}

/** Signed amount, e.g. "+₹26,384". The sign carries the meaning when
 *  colour cannot — for anyone who does not distinguish red from green. */
export function signedMoney(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return (n >= 0 ? "+" : "−") + money(Math.abs(n));
}

export function signedPercent(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return (n >= 0 ? "+" : "−") + Math.abs(n).toFixed(digits) + "%";
}

/** Quantities may be fractional but usually are not; don't show ".0000". */
export function quantity(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return Number.isInteger(n) ? PLAIN.format(n) : PLAIN_PAISE.format(n);
}

export function shortDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function todayISO() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

export const isUp = (v) => Number(v) >= 0;
