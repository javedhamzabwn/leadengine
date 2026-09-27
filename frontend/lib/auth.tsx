"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { login as apiLogin, me as apiMe, setTokenProvider, signup as apiSignup } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const STORAGE_KEY = "leadengine_token";

function readStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Token lives in memory; localStorage is a persistence mirror only.
  useEffect(() => {
    setTokenProvider(() => token);
  }, [token]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const stored = readStoredToken();
      if (!stored) {
        setLoading(false);
        return;
      }
      setToken(stored);
      try {
        const { user } = await apiMe();
        if (!cancelled) setUser(user);
      } catch {
        if (!cancelled) {
          setToken(null);
          window.localStorage.removeItem(STORAGE_KEY);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { token: t, user: u } = await apiLogin({ email, password });
    window.localStorage.setItem(STORAGE_KEY, t);
    setToken(t);
    setUser(u);
  }, []);

  const signup = useCallback(
    async (email: string, password: string, name: string) => {
      const { user: u } = await apiSignup({ email, password, name });
      // Contract returns only the user on signup; log in right after.
      await login(email, password).catch(() => {
        setUser(u);
      });
    },
    [login]
  );

  const logout = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, token, loading, login, signup, logout }),
    [user, token, loading, login, signup, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
