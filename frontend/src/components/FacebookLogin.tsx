"use client";

import { useState, useEffect, useCallback } from "react";

export interface FacebookPage {
  id: string;
  name: string;
  access_token: string;
  category: string;
  tasks: string[];
}

export interface InstagramAccount {
  id: string;
  username: string;
  name?: string;
  profile_picture_url?: string;
  followers_count?: number;
  media_count?: number;
}

export interface FacebookUser {
  id: string;
  name: string;
  email?: string | null;
}

export interface FacebookData {
  facebook_user: FacebookUser;
  pages: FacebookPage[];
  instagram_accounts: InstagramAccount[];
}

export interface Credentials {
  id: number;
  user_id: string;
  facebook_user_id: string;
  facebook_user_name: string;
  facebook_user_email?: string | null;
  access_token: string;
  pages_data: FacebookPage[];
  instagram_accounts_data: InstagramAccount[];
  created_at: string; // ISO date string
  updated_at: string; // ISO date string
}

interface FacebookLoginProps {
  authenticated: boolean;
}

export default function FacebookLogin({ authenticated }: FacebookLoginProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [facebookData, setFacebookData] = useState<FacebookData | null>(null);
  const [fullCredentials, setFullCredentials] = useState<Credentials | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    "checking" | "connected" | "disconnected"
  >("checking");
  const [showCredentials, setShowCredentials] = useState(false);

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      console.log(`${label} copied to clipboard`);
    } catch (err) {
      console.error("Failed to copy to clipboard:", err);
    }
  };

  const saveFacebookDataToDatabase = async (userData: FacebookData) => {
    try {
      console.log("Saving Facebook data to database...", userData);
      const response = await fetch("http://localhost:8000/facebook/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(userData),
      });

      console.log("Save response status:", response.status);
      if (response.ok) {
        console.log("Facebook data saved successfully");
      } else {
        const errorData = await response.text();
        console.error("Failed to save Facebook data to database:", errorData);
      }
    } catch (error) {
      console.error("Error saving Facebook data:", error);
    }
  };

  const loadFullCredentials = async () => {
    try {
      const response = await fetch(
        "http://localhost:8000/facebook/credentials",
        {
          credentials: "include",
        }
      );
      if (response.ok) {
        const credentials = await response.json();
        setFullCredentials(credentials);
      }
    } catch (error) {
      console.error("Error loading full credentials:", error);
    }
  };

  const loadFacebookDataFromDatabase = useCallback(async () => {
    try {
      console.log("Loading Facebook data from database...");
      const response = await fetch("http://localhost:8000/facebook/status", {
        credentials: "include",
      });

      console.log("Facebook status response status:", response.status);

      if (response.ok) {
        const data = await response.json();
        console.log("Facebook status data:", data);
        if (data.connected) {
          setIsConnected(true);
          setFacebookData(data.facebook_data);
          setConnectionStatus("connected");
          // Load full credentials including tokens
          await loadFullCredentials();
        } else {
          setConnectionStatus("disconnected");
        }
      } else {
        console.log(
          "Facebook status response not ok, status:",
          response.status
        );
        setConnectionStatus("disconnected");
      }
    } catch (error) {
      console.error("Error loading Facebook data:", error);
      setConnectionStatus("disconnected");
    }
  }, []);

  useEffect(() => {
    // Load existing Facebook data on component mount
    if (authenticated) {
      loadFacebookDataFromDatabase();
    }
  }, [authenticated, loadFacebookDataFromDatabase]);

  useEffect(() => {
    // Listen for OAuth callback messages (like the working example)
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== "http://localhost:8000") return;

      if (event.data.type === "OAUTH_SUCCESS") {
        // Store data locally first (for immediate UI update)
        setFacebookData(event.data.user);
        setIsConnected(true);
        setConnectionStatus("connected");
        setIsLoading(false);

        // Save to database in background
        saveFacebookDataToDatabase(event.data.user);

        // Load full credentials including tokens
        setTimeout(() => loadFullCredentials(), 1000);
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  const handleFacebookLogin = async () => {
    setIsLoading(true);

    try {
      // Get the auth URL from backend
      const response = await fetch("http://localhost:8000/facebook/login");
      const data = await response.json();

      // Open popup window for OAuth
      const popup = window.open(
        data.auth_url,
        "oauth",
        "width=600,height=700,scrollbars=yes,resizable=yes"
      );

      // Check if popup was closed without completing OAuth
      const checkClosed = setInterval(() => {
        if (popup && popup.closed) {
          clearInterval(checkClosed);
          setIsLoading(false);
        }
      }, 1000);
    } catch (error) {
      console.error("Login error:", error);
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      // Remove from database
      const response = await fetch(
        "http://localhost:8000/facebook/disconnect",
        {
          method: "POST",
          credentials: "include",
        }
      );

      if (response.ok) {
        // Clear local state
        setIsConnected(false);
        setFacebookData(null);
        setConnectionStatus("disconnected");
      } else {
        console.error("Failed to disconnect from database");
      }
    } catch (error) {
      console.error("Error disconnecting Facebook:", error);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
              <svg
                className="w-6 h-6 text-white"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Facebook Business
              </h3>
              <p className="text-sm text-gray-500">
                Connect your Facebook Business account
              </p>
            </div>
          </div>

          <div className="flex items-center">
            {connectionStatus === "checking" ? (
              <div className="flex items-center text-gray-500">
                <svg
                  className="animate-spin w-4 h-4 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                <span className="text-sm">Checking...</span>
              </div>
            ) : isConnected ? (
              <div className="flex items-center text-green-600">
                <svg
                  className="w-4 h-4 mr-2"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="text-sm font-medium">Connected</span>
              </div>
            ) : (
              <div className="flex items-center text-gray-400">
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
                <span className="text-sm">Not Connected</span>
              </div>
            )}
          </div>
        </div>

        {!authenticated && (
          <div className="text-center py-8">
            <div className="text-gray-500 mb-4">
              <svg
                className="w-12 h-12 mx-auto mb-4 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
              <p className="text-sm">
                Please log in to connect your Facebook Business account.
              </p>
            </div>
          </div>
        )}

        {authenticated && isConnected && facebookData ? (
          <div className="space-y-6">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center">
                  <svg
                    className="w-5 h-5 text-green-600 mr-2"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span className="text-green-800 font-medium">
                    Successfully connected to Facebook!
                  </span>
                </div>
                <button
                  onClick={() => setShowCredentials(!showCredentials)}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  {showCredentials
                    ? "Hide Credentials"
                    : "Show All Credentials"}
                </button>
              </div>

              <div className="text-sm text-green-700">
                <p>
                  <strong>User:</strong> {facebookData.facebook_user.name}
                </p>
                {facebookData.facebook_user.email && (
                  <p>
                    <strong>Email:</strong> {facebookData.facebook_user.email}
                  </p>
                )}
              </div>
            </div>

            {showCredentials && fullCredentials && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h4 className="text-md font-medium text-gray-900 mb-4">
                  Facebook API Credentials
                </h4>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Facebook User ID
                    </label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={fullCredentials.facebook_user_id || ""}
                        readOnly
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
                      />
                      <button
                        onClick={() =>
                          copyToClipboard(
                            String(fullCredentials.facebook_user_id),
                            "Facebook User ID"
                          )
                        }
                        className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                      >
                        Copy
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Main Access Token
                    </label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={fullCredentials.access_token || ""}
                        readOnly
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
                      />
                      <button
                        onClick={() =>
                          copyToClipboard(
                            String(fullCredentials.access_token),
                            "Access Token"
                          )
                        }
                        className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                      >
                        Copy
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Full Name
                    </label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={fullCredentials.facebook_user_name || ""}
                        readOnly
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                      />
                      <button
                        onClick={() =>
                          copyToClipboard(
                            String(fullCredentials.facebook_user_name),
                            "Full Name"
                          )
                        }
                        className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                      >
                        Copy
                      </button>
                    </div>
                  </div>

                  {fullCredentials.facebook_user_email && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Email Address
                      </label>
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={fullCredentials.facebook_user_email || ""}
                          readOnly
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                        />
                        <button
                          onClick={() =>
                            copyToClipboard(
                              String(fullCredentials.facebook_user_email),
                              "Email"
                            )
                          }
                          className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                        >
                          Copy
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {facebookData.pages.length > 0 && (
              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">
                  Connected Facebook Pages ({facebookData.pages.length})
                </h4>
                <div className="space-y-3">
                  {facebookData.pages.map((page) => (
                    <div
                      key={page.id}
                      className="border border-gray-200 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <p className="font-medium text-gray-900">
                            {page.name}
                          </p>
                          <p className="text-sm text-gray-500">
                            {page.category}
                          </p>
                        </div>
                        <div className="text-xs text-gray-400">
                          {page.tasks.length} permissions
                        </div>
                      </div>

                      {showCredentials && (
                        <div className="space-y-3 pt-3 border-t border-gray-100">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Page ID
                            </label>
                            <div className="flex items-center space-x-2">
                              <input
                                type="text"
                                value={page.id}
                                readOnly
                                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
                              />
                              <button
                                onClick={() =>
                                  copyToClipboard(
                                    page.id,
                                    `Page ID for ${page.name}`
                                  )
                                }
                                className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                              >
                                Copy
                              </button>
                            </div>
                          </div>

                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Page Access Token
                            </label>
                            <div className="flex items-center space-x-2">
                              <input
                                type="text"
                                value={page.access_token}
                                readOnly
                                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
                              />
                              <button
                                onClick={() =>
                                  copyToClipboard(
                                    page.access_token,
                                    `Access Token for ${page.name}`
                                  )
                                }
                                className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                              >
                                Copy
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {facebookData.instagram_accounts.length > 0 && (
              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">
                  Connected Instagram Business Accounts (
                  {facebookData.instagram_accounts.length})
                </h4>
                <div className="space-y-3">
                  {facebookData.instagram_accounts.map((account) => (
                    <div
                      key={account.id}
                      className="border border-gray-200 rounded-lg p-4"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center">
                          {account.profile_picture_url && (
                            <img
                              src={account.profile_picture_url}
                              alt={account.username}
                              className="w-8 h-8 rounded-full mr-3"
                            />
                          )}
                          <div>
                            <p className="font-medium text-gray-900">
                              @{account.username}
                            </p>
                            {account.name && (
                              <p className="text-sm text-gray-500">
                                {account.name}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="text-xs text-gray-400 text-right">
                          {account.followers_count && (
                            <p>
                              {account.followers_count.toLocaleString()}{" "}
                              followers
                            </p>
                          )}
                          {account.media_count && (
                            <p>{account.media_count} posts</p>
                          )}
                        </div>
                      </div>

                      {showCredentials && (
                        <div className="space-y-3 pt-3 border-t border-gray-100">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Instagram Account ID
                            </label>
                            <div className="flex items-center space-x-2">
                              <input
                                type="text"
                                value={account.id}
                                readOnly
                                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
                              />
                              <button
                                onClick={() =>
                                  copyToClipboard(
                                    account.id,
                                    `Instagram ID for @${account.username}`
                                  )
                                }
                                className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                              >
                                Copy
                              </button>
                            </div>
                          </div>

                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Username
                            </label>
                            <div className="flex items-center space-x-2">
                              <input
                                type="text"
                                value={account.username}
                                readOnly
                                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                              />
                              <button
                                onClick={() =>
                                  copyToClipboard(
                                    account.username,
                                    "Instagram Username"
                                  )
                                }
                                className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                              >
                                Copy
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex space-x-3">
              <button
                onClick={handleDisconnect}
                className="flex-1 flex items-center justify-center px-4 py-2 border border-red-300 rounded-lg text-sm font-medium text-red-700 bg-white hover:bg-red-50 transition-colors"
              >
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
                Disconnect Facebook
              </button>
            </div>
          </div>
        ) : authenticated && !isLoading ? (
          <div className="text-center py-8">
            <svg
              className="w-12 h-12 text-gray-400 mx-auto mb-4"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
            </svg>
            <h4 className="text-lg font-medium text-gray-900 mb-2">
              Connect Facebook Business
            </h4>
            <p className="text-gray-500 mb-6">
              Connect your Facebook Business account to manage pages and
              Instagram accounts
            </p>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left">
              <h5 className="font-medium text-blue-900 mb-2">
                What you&apos;ll get:
              </h5>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Access to your Facebook Business pages</li>
                <li>• Instagram Business account management</li>
                <li>• Post scheduling and insights</li>
                <li>• Audience analytics and engagement metrics</li>
              </ul>
            </div>

            <button
              onClick={handleFacebookLogin}
              disabled={isLoading}
              className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-3 h-4 w-4 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Connecting...
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                  </svg>
                  Connect with Facebook
                </>
              )}
            </button>
          </div>
        ) : null}

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          </div>
        )}
      </div>
    </div>
  );
}
