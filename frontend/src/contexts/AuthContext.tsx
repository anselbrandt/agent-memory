"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { authAPI, User, AuthStatus } from "@/lib/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  authenticated: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    checkAuthStatus();

    // Check for auth success/error in URL params
    const urlParams = new URLSearchParams(window.location.search);
    const authResult = urlParams.get("auth");

    if (authResult === "success") {
      // Remove auth params from URL
      window.history.replaceState({}, document.title, window.location.pathname);
      // Refresh auth status with longer delay to ensure cookie is set
      setTimeout(checkAuthStatus, 1000);
    } else if (authResult === "error") {
      const message = urlParams.get("message") || "Authentication failed";
      console.error("Auth error:", message);
      // Remove auth params from URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      console.log("Checking auth status...");
      console.log("Current URL:", window.location.href);
      console.log("Current cookies:", document.cookie);

      const authStatus: AuthStatus = await authAPI.getAuthStatus();
      console.log("Auth status response:", authStatus);

      setAuthenticated(authStatus.authenticated);
      setUser(authStatus.user || null);

      console.log("Auth state updated:", {
        authenticated: authStatus.authenticated,
        user: authStatus.user,
      });
    } catch (error) {
      console.error("Auth check failed:", error);
      setAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async () => {
    try {
      const { auth_url } = await authAPI.getGoogleAuthUrl();
      window.location.href = auth_url;
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
      setUser(null);
      setAuthenticated(false);
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  const refreshAuth = async () => {
    await checkAuthStatus();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        authenticated,
        login,
        logout,
        refreshAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
