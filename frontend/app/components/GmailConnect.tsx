"use client";

import Image from "next/image";
import { getGmailAuthUrl } from "@/lib/api";
import { clearAuth, GmailUser } from "@/lib/auth";

interface Props {
  user: GmailUser | null;
  onDisconnect: () => void;
}

export default function GmailConnect({ user, onDisconnect }: Props) {
  async function handleConnect() {
    try {
      const url = await getGmailAuthUrl();
      window.location.href = url;
    } catch {
      alert("Could not reach the backend. Is it running?");
    }
  }

  function handleDisconnect() {
    clearAuth();
    onDisconnect();
  }

  // ── Connected state ──────────────────────────────────────────────────────
  if (user) {
    return (
      <div className="flex items-center justify-between rounded-xl border border-green-200 bg-green-50 px-5 py-4">
        <div className="flex items-center gap-3">
          {user.picture ? (
            <Image
              src={user.picture}
              alt={user.name}
              width={40}
              height={40}
              className="rounded-full"
            />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-200 text-green-700 font-semibold text-sm">
              {user.name?.[0]?.toUpperCase() ?? "G"}
            </div>
          )}
          <div>
            <p className="font-medium text-slate-800">{user.name}</p>
            <p className="text-sm text-slate-500">{user.email}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
            Read-only
          </span>
          <button
            onClick={handleDisconnect}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition"
          >
            Disconnect
          </button>
        </div>
      </div>
    );
  }

  // ── Not connected state ──────────────────────────────────────────────────
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border-2 border-dashed border-slate-200 bg-white px-8 py-10">
      {/* Gmail G logo */}
      <svg className="h-10 w-10" viewBox="0 0 48 48">
        <path fill="#4CAF50" d="M45,16.2l-5,2.75l-5,4.75L35,40h7c1.657,0,3-1.343,3-3V16.2z"/>
        <path fill="#1E88E5" d="M3,16.2l3.614,1.71L13,23.7V40H6c-1.657,0-3-1.343-3-3V16.2z"/>
        <polygon fill="#E53935" points="35,11.2 24,19.45 13,11.2 12,17 13,23.7 24,31.95 35,23.7 36,17"/>
        <path fill="#C62828" d="M3,12.298V16.2l10,7.5V11.2L9.876,8.859C9.132,8.301,8.228,8,7.298,8h0C4.924,8,3,9.924,3,12.298z"/>
        <path fill="#FBC02D" d="M45,12.298V16.2l-10,7.5V11.2l3.124-2.341C38.868,8.301,39.772,8,40.702,8h0 C43.076,8,45,9.924,45,12.298z"/>
      </svg>

      <div className="text-center">
        <p className="font-semibold text-slate-800">Connect your Gmail account</p>
        <p className="mt-1 text-sm text-slate-500">
          Read-only access — the app can never send, delete, or modify emails
        </p>
      </div>

      <button
        onClick={handleConnect}
        className="flex items-center gap-2.5 rounded-xl bg-blue-600 px-6 py-3 font-medium text-white shadow-sm hover:bg-blue-700 active:bg-blue-800 transition"
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
        </svg>
        Connect Gmail
      </button>

      <p className="text-xs text-slate-400">
        You'll be redirected to Google to authorise access
      </p>
    </div>
  );
}
