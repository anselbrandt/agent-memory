"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import Header from "@/components/Header";
import BusinessInformation from "@/components/BusinessInformation";

interface BackendUser {
  id: string;
  username: string;
  created_at: string;
  updated_at: string;
}

export default function MePage() {
  const { user: authUser, authenticated, loading: authLoading } = useAuth();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBackendUser();
  }, [authenticated]);

  const fetchBackendUser = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("http://localhost:8000/me", {
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const userData = await response.json();
      setBackendUser(userData);
    } catch (err) {
      console.error("Error fetching user data:", err);
      setError(
        err instanceof Error ? err.message : "Failed to fetch user data"
      );
    } finally {
      setLoading(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />

      <div className="flex-1 px-10 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              My Profile
            </h1>
            <p className="text-gray-600">
              Your account information and preferences
            </p>
          </div>

          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <div className="mt-2 text-sm text-red-700">{error}</div>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Authentication Information */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                  />
                </svg>
                Authentication Status
              </h2>

              <div className="space-y-4">
                <div className="flex items-center">
                  <span className="text-sm font-medium text-gray-500 w-24">
                    Status:
                  </span>
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      authenticated
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {authenticated ? "Authenticated" : "Not Authenticated"}
                  </span>
                </div>

                {authUser && (
                  <>
                    <div className="flex items-center space-x-3">
                      <span className="text-sm font-medium text-gray-500 w-24">
                        Profile:
                      </span>
                      <div className="flex items-center space-x-3">
                        {authUser.picture ? (
                          <img
                            src={authUser.picture}
                            alt={authUser.name}
                            className="w-10 h-10 rounded-full"
                            loading="lazy"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center">
                            <span className="text-white font-semibold text-sm">
                              {authUser.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {authUser.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {authUser.email}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center">
                      <span className="text-sm font-medium text-gray-500 w-24">
                        Provider:
                      </span>
                      <span className="text-sm text-gray-900 capitalize">
                        {authUser.provider}
                      </span>
                    </div>

                    <div className="flex items-center">
                      <span className="text-sm font-medium text-gray-500 w-24">
                        User ID:
                      </span>
                      <span className="text-sm text-gray-900 font-mono">
                        {authUser.id}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Backend User Information */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-purple-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                System Profile
              </h2>

              {backendUser ? (
                <div className="space-y-4">
                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-500 w-24">
                      Username:
                    </span>
                    <span className="text-sm text-gray-900">
                      {backendUser.username}
                    </span>
                  </div>

                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-500 w-24">
                      User ID:
                    </span>
                    <span className="text-sm text-gray-900 font-mono">
                      {backendUser.id}
                    </span>
                  </div>

                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-500 w-24">
                      Created:
                    </span>
                    <span className="text-sm text-gray-900">
                      {new Date(backendUser.created_at).toLocaleDateString(
                        "en-US",
                        {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        }
                      )}
                    </span>
                  </div>

                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-500 w-24">
                      Updated:
                    </span>
                    <span className="text-sm text-gray-900">
                      {new Date(backendUser.updated_at).toLocaleDateString(
                        "en-US",
                        {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        }
                      )}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500">
                  {error
                    ? "Failed to load system profile"
                    : "Loading system profile..."}
                </div>
              )}
            </div>
          </div>

          {/* Business Information */}
          <div className="mt-8">
            <BusinessInformation authenticated={authenticated} />
          </div>

          {/* Actions */}
          <div className="mt-8">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                Actions
              </h2>

              <div className="flex space-x-4">
                <button
                  onClick={fetchBackendUser}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:cursor-pointer hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transform hover:scale-105 active:scale-95"
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
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Refresh Data
                </button>

                <a
                  href="/"
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-400 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transform hover:scale-105 active:scale-95"
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
                      d="M7 16l-4-4m0 0l4-4m-4 4h18"
                    />
                  </svg>
                  Back to Chat
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
