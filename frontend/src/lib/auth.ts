const API_BASE_URL = "http://localhost:8000";

export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  provider: string;
}

export interface AuthStatus {
  authenticated: boolean;
  user?: User;
}

export const authAPI = {
  // Get Google OAuth URL
  getGoogleAuthUrl: async (): Promise<{ auth_url: string }> => {
    const response = await fetch(`${API_BASE_URL}/auth/google`, {
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Failed to get auth URL");
    }

    return response.json();
  },

  // Check authentication status
  getAuthStatus: async (): Promise<AuthStatus> => {
    try {
      console.log("Fetching auth status from:", `${API_BASE_URL}/auth/status`);
      console.log("Document cookies:", document.cookie);

      const response = await fetch(`${API_BASE_URL}/auth/status`, {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      console.log("Auth status response status:", response.status);
      console.log(
        "Auth status response headers:",
        Object.fromEntries(response.headers.entries())
      );

      if (!response.ok) {
        console.log("Auth status response not ok, returning false");
        return { authenticated: false };
      }

      const data = await response.json();
      console.log("Auth status data:", data);
      return data;
    } catch (error) {
      console.error("Auth status check failed:", error);
      return { authenticated: false };
    }
  },

  // Get current user (throws if not authenticated)
  getCurrentUser: async (): Promise<User> => {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Not authenticated");
    }

    return response.json();
  },

  // Logout
  logout: async (): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Logout failed");
    }
  },

  // Migrate conversations
  migrateConversations: async (): Promise<{
    migrated_conversations: number;
    user_id: string;
    anonymous_user_id?: string;
  }> => {
    const response = await fetch(`${API_BASE_URL}/chat/migrate-conversations`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error("Migration failed");
    }

    return response.json();
  },
};
