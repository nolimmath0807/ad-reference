import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { flushSync } from "react-dom";
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
    if (!token) {
      setIsLoading(false);
      return;
    }

    // localStorage에 저장된 user 정보가 있으면 API 호출 없이 복원
    const savedUser = localStorage.getItem("user_info");
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
        setIsLoading(false);
        return;
      } catch {
        localStorage.removeItem("user_info");
      }
    }

    // user_info가 없는 경우에만 API 호출 (하위 호환)
    api
      .get<User>("/users/me")
      .then((me) => {
        localStorage.setItem("user_info", JSON.stringify(me));
        setUser(me);
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user_info");
      })
      .finally(() => setIsLoading(false));
  }, []);

  // 세션 만료 이벤트 리스너
  useEffect(() => {
    const handleSessionExpired = () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user_info");
      setUser(null);
    };
    window.addEventListener("auth:session-expired", handleSessionExpired);
    return () => window.removeEventListener("auth:session-expired", handleSessionExpired);
  }, []);

  const login = async (data: LoginRequest) => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_info");

    const result = await api.post<{ user: User; tokens: TokenResponse }>(
      "/auth/login",
      data,
    );
    localStorage.setItem("access_token", result.tokens.access_token);
    localStorage.setItem("refresh_token", result.tokens.refresh_token);
    localStorage.setItem("user_info", JSON.stringify(result.user));
    flushSync(() => setUser(result.user));
  };

  const register = async (data: RegisterRequest) => {
    const result = await api.post<{ user: User; tokens: TokenResponse }>(
      "/auth/register",
      data,
    );
    localStorage.setItem("access_token", result.tokens.access_token);
    localStorage.setItem("refresh_token", result.tokens.refresh_token);
    localStorage.setItem("user_info", JSON.stringify(result.user));
    setUser(result.user);
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      await api.post("/auth/logout", { refresh_token: refreshToken }).catch(() => {});
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_info");
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
