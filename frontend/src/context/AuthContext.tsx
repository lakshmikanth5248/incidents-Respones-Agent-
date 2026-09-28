import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'ADMIN' | 'RESPONDER' | 'VIEWER' | 'ANALYST';
  roles?: string[];
  permissions?: Record<string, boolean>;
  avatar_url: string;
  created_at: string;
  last_login_at: string | null;
  is_active?: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAdmin: boolean;
  hasPermission: (moduleKey: string) => boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string, role?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('aegis_token'));
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    try {
      const res = await api.auth.me();
      setUser(res.user);
    } catch (err) {
      console.warn('[Auth] Session invalid or expired:', err);
      localStorage.removeItem('aegis_token');
      setToken(null);
      setUser(null);
    }
  };

  useEffect(() => {
    async function loadUser() {
      const storedToken = localStorage.getItem('aegis_token');
      if (!storedToken) {
        setLoading(false);
        return;
      }
      try {
        const res = await api.auth.me();
        setUser(res.user);
      } catch (err) {
        console.warn('[Auth] Session invalid or expired:', err);
        localStorage.removeItem('aegis_token');
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    loadUser();
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    const res = await api.auth.login({ email, password });
    localStorage.setItem('aegis_token', res.token);
    setToken(res.token);
    setUser(res.user);
    return res.user;
  };

  const register = async (name: string, email: string, password: string, role?: string) => {
    const res = await api.auth.register({ name, email, password, role });
    localStorage.setItem('aegis_token', res.token);
    setToken(res.token);
    setUser(res.user);
  };

  const logout = () => {
    localStorage.removeItem('aegis_token');
    setToken(null);
    setUser(null);
    api.auth.logout().catch(() => {});
  };

  const userRoles = user?.roles || (user?.role ? [user.role] : []);
  const isAdmin = Boolean(
    user?.role === 'ADMIN' ||
    userRoles.includes('ADMIN') ||
    user?.email.toLowerCase() === 'admin@aegis.corp'
  );

  const hasPermission = (moduleKey: string): boolean => {
    if (!user) return false;
    if (isAdmin) return true;
    if (user.permissions && user.permissions[moduleKey] !== undefined) {
      return Boolean(user.permissions[moduleKey]);
    }
    // Default fallback
    return true;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAdmin,
        hasPermission,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
