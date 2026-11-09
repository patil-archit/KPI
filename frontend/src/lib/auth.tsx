import React, { createContext, useContext, useEffect, useState } from "react";
import { authApi, setToken, getToken } from "./api";

export type User = { username: string; full_name: string; role: string; via?: string; session_host?: string };
type AuthState = {
  user: User | null;
  loading: boolean;
  login: (u: string, p: string, via: string) => Promise<{ mfa: boolean; token: string }>;
  mfa: (token: string, code: string) => Promise<void>;
  logout: () => void;
};
const Ctx = createContext<AuthState>(null as any);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) { setLoading(false); return; }
    authApi.me().then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);

  const login = async (u: string, p: string, via: string) => {
    const r = await authApi.login(u, p, via);
    if (r.mfa_required) { setToken(r.token); return { mfa: true, token: r.token }; }
    setToken(r.token);
    setUser(await authApi.me());
    return { mfa: false, token: r.token };
  };
  const mfa = async (token: string, code: string) => {
    await authApi.mfa(token, code);
    setUser(await authApi.me());
  };
  const logout = () => { authApi.logout().catch(() => {}); setToken(null); setUser(null); };

  return <Ctx.Provider value={{ user, loading, login, mfa, logout }}>{children}</Ctx.Provider>;
}
