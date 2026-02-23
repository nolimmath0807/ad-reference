import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { api } from "@/lib/api-client";
import type { User } from "@/types/user";
import type { LoginRequest, RegisterRequest, TokenResponse } from "@/types/auth";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      api
        .get<User>("/users/me")
        .then(setUser)
        .catch(() => {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (data: LoginRequest) => {
    const tokens = await api.post<TokenResponse>("/auth/login", data);
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    const me = await api.get<User>("/users/me");
    setUser(me);
  };

  const register = async (data: RegisterRequest) => {
    const result = await api.post<{ user: User; tokens: TokenResponse }>(
      "/auth/register",
      data,
    );
    localStorage.setItem("access_token", result.tokens.access_token);
    localStorage.setItem("refresh_token", result.tokens.refresh_token);
    setUser(result.user);
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      await api.post("/auth/logout", { refresh_token: refreshToken }).catch(() => {});
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated: !!user, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
