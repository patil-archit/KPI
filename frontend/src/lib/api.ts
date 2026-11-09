const PLANT = "";
const DEV_TOKEN_KEY = "arena_dev_token";
const EVIDENCE_TOKEN = "arena-evidence-token";

export function getToken() {
  return localStorage.getItem("arena_token") || "";
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem("arena_token", t);
  else localStorage.removeItem("arena_token");
}
export function getDevToken() {
  return localStorage.getItem(DEV_TOKEN_KEY) || "arena-dev-token";
}
export function setDevToken(t: string) {
  localStorage.setItem(DEV_TOKEN_KEY, t);
}

async function req(path: string, opts: RequestInit = {}, headers: Record<string, string> = {}) {
  const res = await fetch(PLANT + path, {
    ...opts,
    headers: { "content-type": "application/json", ...headers, ...(opts.headers || {}) },
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.detail || msg;
    } catch {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (p: string) => req(p, {}, auth()),
  post: (p: string, body?: any) => req(p, { method: "POST", body: JSON.stringify(body ?? {}) }, auth()),
};

function auth(): Record<string, string> {
  const t = getToken();
  return t ? { authorization: `Bearer ${t}` } : {};
}

export const dev = {
  get: (p: string) => req(p, {}, { "x-dev-token": getDevToken() }),
  post: (p: string, body?: any) =>
    req(p, { method: "POST", body: JSON.stringify(body ?? {}) }, { "x-dev-token": getDevToken() }),
};

export const evidence = {
  get: (p: string) => req(p, {}, { "x-evidence-token": EVIDENCE_TOKEN }),
};

// auth endpoints (no bearer needed for login)
export const authApi = {
  login: (username: string, password: string, via: string) =>
    req("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password, via }) }),
  mfa: (token: string, code: string) =>
    req("/api/auth/mfa", { method: "POST", body: JSON.stringify({ token, code }) }),
  me: () => api.get("/api/auth/me"),
  logout: () => api.post("/api/auth/logout"),
};
