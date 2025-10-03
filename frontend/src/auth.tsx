import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, getToken, setToken, clearToken } from './api/client';
import type { User } from './types/api';

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
};

const AuthCtx = createContext<AuthState | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = async () => {
    if (!getToken()) { setUser(null); return; }
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      clearToken();
      setUser(null);
    }
  };

  useEffect(() => {
    (async () => { setLoading(true); await refreshMe(); setLoading(false); })();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    setToken(res.access_token);
    setUser(res.user);
  };

  const logout = () => {
    const t = getToken();
    // încearcă să anunți backendul; dacă eșuează, ignorăm
    (async () => { try { if (t) await api.logout(); } catch {} finally {
      clearToken();
      setUser(null);
    }})();
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, logout, refreshMe }}>
      {children}
    </AuthCtx.Provider>
  );
};

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
