"use client";

import { useState, useEffect } from "react";

interface Business {
  id: number;
  user_id: number;
  name: string;
  url: string;
  description: string;
  created_at: string;
  updated_at: string;
}

interface BusinessFormData {
  name: string;
  url: string;
  description: string;
}

interface BusinessInformationProps {
  authenticated: boolean;
}

export default function BusinessInformation({
  authenticated,
}: BusinessInformationProps) {
  const [business, setBusiness] = useState<Business | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<BusinessFormData>({
    name: "",
    url: "",
    description: "",
  });
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);

  useEffect(() => {
    if (authenticated) {
      fetchBusiness();
    }
  }, [authenticated]);

  const fetchBusiness = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("http://localhost:8000/business", {
        credentials: "include",
      });

      if (response.status === 401) {
        setError("Authentication required");
        return;
      }

      if (response.ok) {
        const data = await response.json();
        if (data) {
          setBusiness(data);
          setFormData({
            name: data.name,
            url: data.url,
            description: data.description,
          });
        } else {
          setBusiness(null);
          setFormData({ name: "", url: "", description: "" });
        }
      }
    } catch (err) {
      console.error("Error fetching business:", err);
      setError("Failed to fetch business information");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (
      !formData.name.trim() ||
      !formData.url.trim() ||
      !formData.description.trim()
    ) {
      setError("All fields are required");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch("http://localhost:8000/business", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || "Failed to save business information"
        );
      }

      const data = await response.json();
      setBusiness(data);
      setShowSuccessMessage(true);
      setTimeout(() => {
        setIsEditing(false);

        setTimeout(() => {
          setShowSuccessMessage(false);
        }, 3000);
      }, 400);
    } catch (err) {
      console.error("Error saving business:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to save business information"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setError(null);
    setShowSuccessMessage(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setError(null);
    if (business) {
      setFormData({
        name: business.name,
        url: business.url,
        description: business.description,
      });
    } else {
      setFormData({ name: "", url: "", description: "" });
    }
  };

  const handleDelete = async () => {
    if (
      !confirm("Are you sure you want to delete your business information?")
    ) {
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch("http://localhost:8000/business", {
        method: "DELETE",
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || "Failed to delete business information"
        );
      }

      setBusiness(null);
      setFormData({ name: "", url: "", description: "" });
      setIsEditing(false);
    } catch (err) {
      console.error("Error deleting business:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to delete business information"
      );
    } finally {
      setLoading(false);
    }
  };

  if (!authenticated) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
          <svg
            className="w-5 h-5 mr-2 text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
          Business Information
        </h2>
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
              Please log in to manage your business information.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          <svg
            className="w-5 h-5 mr-2 text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
          Business Information
        </h2>

        {business && !isEditing && (
          <div className="flex space-x-2">
            <button
              onClick={handleEdit}
              className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              disabled={loading}
            >
              <svg
                className="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
              Edit
            </button>
            <button
              onClick={handleDelete}
              className="inline-flex items-center px-3 py-1 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              disabled={loading}
            >
              <svg
                className="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
              Delete
            </button>
          </div>
        )}
      </div>

      {showSuccessMessage && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-3 animate-pulse">
          <div className="flex items-center text-sm text-green-700">
            <svg
              className="w-4 h-4 mr-2 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            Business information saved successfully!
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="text-sm text-red-700">{error}</div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        </div>
      )}

      <div
        className={`transition-all duration-500 ease-in-out overflow-hidden ${
          (!business || isEditing) && !loading
            ? "opacity-100 max-h-screen"
            : "opacity-0 max-h-0"
        }`}
      >
        {!loading && (!business || isEditing) && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="business-name"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Business Name
              </label>
              <input
                id="business-name"
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter your business name"
                required
              />
            </div>

            <div>
              <label
                htmlFor="business-url"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Business URL
              </label>
              <input
                id="business-url"
                type="url"
                value={formData.url}
                onChange={(e) =>
                  setFormData({ ...formData, url: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="https://yourwebsite.com"
                required
              />
            </div>

            <div>
              <label
                htmlFor="business-description"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Business Description
              </label>
              <textarea
                id="business-description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Describe your business, what you do, your target market, and any other relevant information that would help AI agents understand your context."
                required
              />
            </div>

            <div className="flex space-x-3">
              <button
                type="submit"
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                disabled={loading}
              >
                {loading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                ) : (
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
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                )}
                Save Business Information
              </button>

              {business && (
                <button
                  type="button"
                  onClick={handleCancel}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  disabled={loading}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        )}
      </div>
      <div
        className={`transition-all duration-500 ease-in-out overflow-hidden ${
          !loading && business && !isEditing
            ? "opacity-100 max-h-screen"
            : "opacity-0 max-h-0"
        }`}
      >
        {!loading && business && !isEditing && (
          <div className="space-y-4">
            <div>
              <span className="block text-sm font-medium text-gray-500 mb-1">
                Business Name
              </span>
              <span className="text-sm text-gray-900">{business.name}</span>
            </div>

            <div>
              <span className="block text-sm font-medium text-gray-500 mb-1">
                Website
              </span>
              <a
                href={business.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
              >
                {business.url}
              </a>
            </div>

            <div>
              <span className="block text-sm font-medium text-gray-500 mb-1">
                Description
              </span>
              <p className="text-sm text-gray-900 whitespace-pre-wrap">
                {business.description}
              </p>
            </div>

            <div className="pt-4 border-t border-gray-200">
              <div className="flex items-center text-xs text-gray-500 space-x-4">
                <span>
                  Created:{" "}
                  {new Date(business.created_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </span>
                <span>
                  Updated:{" "}
                  {new Date(business.updated_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
      <div
        className={`transition-all duration-500 ease-in-out overflow-hidden ${
          !loading && !business && !isEditing
            ? "opacity-100 max-h-screen"
            : "opacity-0 max-h-0"
        }`}
      >
        {!loading && !business && !isEditing && (
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
                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                />
              </svg>
              <p className="text-sm">No business information saved.</p>
              <p className="text-xs text-gray-400 mt-1">
                Add your business details to help AI agents provide more
                relevant assistance.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
