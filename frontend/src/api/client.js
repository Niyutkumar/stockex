/* The single place the front end talks to the API.
 *
 * Every request goes through here, so the token header, error handling
 * and the base URL are defined once. Components call named functions
 * like `getPortfolio()` and never touch fetch directly.
 */

const BASE = "/api";
const TOKEN_KEY = "stockex.token";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    // Private windows and blocked site data make this throw. Treat it as
    // "not logged in" rather than crashing the whole app.
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore: the session still works, it just will not survive a reload */
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, { method = "GET", body, form, auth = true } = {}) {
  const headers = {};
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    // The login endpoint follows the OAuth2 password flow, which is
    // form-encoded rather than JSON.
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(BASE + path, { method, headers, body: payload });
  } catch {
    throw new ApiError("Could not reach the server. Is the API running?", 0);
  }

  if (response.status === 204) return null;

  const text = await response.text();
  const data = text ? safeJson(text) : null;

  if (!response.ok) {
    throw new ApiError(describe(data, response.status), response.status);
  }
  return data;
}

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

/** Turn FastAPI's error shapes into one readable sentence. */
function describe(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // Validation errors arrive as a list of field problems.
    const first = detail[0];
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "";
    return field ? `${field}: ${first.msg}` : first.msg;
  }
  return `Request failed (${status})`;
}

export const api = {
  register: (payload) =>
    request("/auth/register", { method: "POST", body: payload, auth: false }),

  login: (email, password) =>
    request("/auth/login", {
      method: "POST",
      form: { username: email, password },
      auth: false,
    }),

  me: () => request("/auth/me"),

  searchStocks: (q, limit = 20) =>
    request(`/stocks/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  quote: (stockId) => request(`/stocks/${stockId}/quote`),

  portfolio: () => request("/portfolio"),

  portfolioHistory: (months = 12) =>
    request(`/portfolio/history?months=${months}`),

  transactions: (stockId) =>
    request("/transactions" + (stockId ? `?stock_id=${stockId}` : "")),

  createTransaction: (payload) =>
    request("/transactions", { method: "POST", body: payload }),

  deleteTransaction: (id) =>
    request(`/transactions/${id}`, { method: "DELETE" }),

  watchlist: () => request("/watchlist"),
  addToWatchlist: (stockId) =>
    request(`/watchlist/${stockId}`, { method: "POST" }),
  removeFromWatchlist: (stockId) =>
    request(`/watchlist/${stockId}`, { method: "DELETE" }),
};
