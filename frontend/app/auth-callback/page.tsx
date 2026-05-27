"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { saveAuth } from "@/lib/auth";

/**
 * This page receives the OAuth redirect from the backend after Gmail auth.
 * It reads the token + user info from URL params, saves to localStorage, then redirects home.
 *
 * URL format from backend:
 *   /auth-callback?token=...&email=...&name=...&picture=...
 *   /auth-callback?error=...
 */
export default function AuthCallback() {
  const router = useRouter();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const params = new URLSearchParams(window.location.search);
    const error  = params.get("error");

    if (error) {
      // Show error briefly, then go back to home
      setTimeout(() => router.replace("/"), 2500);
      return;
    }

    const token   = params.get("token")   ?? "";
    const email   = params.get("email")   ?? "";
    const name    = params.get("name")    ?? "";
    const picture = params.get("picture") ?? "";

    if (token) {
      saveAuth({ token, email, name, picture });
    }

    // Redirect to main page — clean URL
    router.replace("/");
  }, [router]);

  const params =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search)
      : null;
  const hasError = params?.get("error");

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center gap-4 rounded-2xl bg-white p-10 shadow-sm border border-slate-100">
        {hasError ? (
          <>
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="font-semibold text-slate-800">Connection failed</p>
            <p className="text-sm text-slate-500">Redirecting back…</p>
          </>
        ) : (
          <>
            <svg className="h-10 w-10 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="font-semibold text-slate-800">Connecting Gmail…</p>
            <p className="text-sm text-slate-500">You'll be redirected in a moment</p>
          </>
        )}
      </div>
    </div>
  );
}
