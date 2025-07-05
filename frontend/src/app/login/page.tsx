"use client";

import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import LoginButton from "@/components/LoginButton";
import Link from "next/link";

export default function LoginPage() {
  const { authenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (authenticated) {
      router.push("/");
    }
  }, [authenticated, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border border-blue-600"></div>
      </div>
    );
  }

  if (authenticated) {
    return null; // Will redirect via useEffect
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-lg w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <Link
            href="/"
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            ← Back to Home
          </Link>
          <h2 className="mt-6 font-serif font-bold text-3xl text-gray-900">
            Everything Your Business Needs. In One Place.
          </h2>
          <p className="mt-2 font-serif text-lg text-gray-800">
            Simplify, grow, and manage your business.
          </p>
        </div>

        <div className="bg-white py-8 px-6 shadow-lg rounded-xl">
          <div className="space-y-6">
            {/* Google Sign In Button */}
            <LoginButton className="w-full" />
          </div>
        </div>

        {/* Footer */}
        <div className="text-center">
          <p className="text-xs text-gray-500">
            By signing in, you agree to our terms of service and privacy policy.
          </p>
        </div>
      </div>
    </div>
  );
}
