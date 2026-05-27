"use client";

import { useEffect, useState } from "react";
import { loadAuth, GmailUser } from "@/lib/auth";
import { processDocument } from "@/lib/api";
import GmailConnect from "./components/GmailConnect";
import DocumentUpload from "./components/DocumentUpload";
import AgentRequest from "./components/AgentRequest";
import ResultDownload from "./components/ResultDownload";

type Result = {
  blob: Blob;
  filename: string;
  summary: string;
  rowCount: number;
};

export default function Home() {
  const [user, setUser]       = useState<GmailUser | null>(null);
  const [file, setFile]       = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [result, setResult]   = useState<Result | null>(null);
  const [status, setStatus]   = useState("");

  // Load saved auth on mount
  useEffect(() => {
    setUser(loadAuth());
  }, []);

  async function handleRequest(request: string) {
    if (!user || !file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setStatus("Starting agent…");

    try {
      const res = await processDocument(
        file,
        request,
        user.token,
        setStatus,
      );
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
      // If token expired, clear auth so user reconnects
      if (msg.includes("session expired")) {
        setUser(null);
      }
    } finally {
      setLoading(false);
      setStatus("");
    }
  }

  function handleReset() {
    setResult(null);
    setError(null);
  }

  // Determine which step is active (for the stepper indicator)
  const step = !user ? 1 : !file ? 2 : result ? 4 : 3;

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-2xl">

        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-slate-900">Gmail Helper</h1>
          <p className="mt-2 text-slate-500">
            Extract Gmail data into your Word or Excel documents
          </p>
        </div>

        {/* Step indicator */}
        <div className="mb-8 flex items-center justify-center gap-0">
          {[
            { n: 1, label: "Connect" },
            { n: 2, label: "Upload" },
            { n: 3, label: "Request" },
            { n: 4, label: "Download" },
          ].map(({ n, label }, idx) => (
            <div key={n} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className={`
                  flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold
                  ${step === n
                    ? "bg-blue-600 text-white shadow"
                    : step > n
                    ? "bg-green-500 text-white"
                    : "bg-slate-200 text-slate-500"
                  }
                `}>
                  {step > n ? (
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : n}
                </div>
                <span className={`mt-1 text-xs ${step === n ? "font-semibold text-blue-600" : "text-slate-400"}`}>
                  {label}
                </span>
              </div>
              {idx < 3 && (
                <div className={`mb-4 h-0.5 w-12 ${step > n ? "bg-green-400" : "bg-slate-200"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Main card */}
        <div className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100 flex flex-col gap-6">

          {/* Step 1 — Connect Gmail */}
          <section>
            <SectionLabel n={1} active={step === 1} done={step > 1}>
              Connect Gmail
            </SectionLabel>
            <GmailConnect user={user} onDisconnect={() => { setUser(null); setFile(null); setResult(null); }} />
          </section>

          {/* Step 2 — Upload document */}
          <section className={step < 2 ? "opacity-40 pointer-events-none" : ""}>
            <SectionLabel n={2} active={step === 2} done={step > 2}>
              Upload Document
            </SectionLabel>
            <DocumentUpload file={file} onChange={(f) => { setFile(f); setResult(null); setError(null); }} />
          </section>

          {/* Step 3 — Request */}
          <section className={step < 3 ? "opacity-40 pointer-events-none" : ""}>
            <SectionLabel n={3} active={step === 3} done={step > 3}>
              Your Request
            </SectionLabel>

            {/* Loading status */}
            {loading && status && (
              <div className="mb-3 flex items-center gap-2 rounded-lg bg-blue-50 px-4 py-2.5 text-sm text-blue-700">
                <svg className="h-4 w-4 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {status}
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="mb-3 flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                <svg className="h-4 w-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {error}
              </div>
            )}

            <AgentRequest
              onSubmit={handleRequest}
              loading={loading}
              disabled={!user || !file}
            />
          </section>

          {/* Step 4 — Download */}
          {result && (
            <section>
              <SectionLabel n={4} active={true} done={false}>
                Download Result
              </SectionLabel>
              <ResultDownload result={result} onReset={handleReset} />
            </section>
          )}
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-slate-400">
          Gmail Helper — personal use only · read-only Gmail access
        </p>
      </div>
    </div>
  );
}

// ─── Small helper component ────────────────────────────────────────────────

function SectionLabel({
  n,
  active,
  done,
  children,
}: {
  n: number;
  active: boolean;
  done: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <span className={`
        flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold
        ${done ? "bg-green-100 text-green-700" : active ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-400"}
      `}>{n}</span>
      <span className={`text-sm font-semibold ${active ? "text-slate-800" : done ? "text-slate-500" : "text-slate-400"}`}>
        {children}
      </span>
    </div>
  );
}
