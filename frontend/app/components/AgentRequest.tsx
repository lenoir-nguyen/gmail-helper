"use client";

import { useState } from "react";

interface Props {
  onSubmit: (request: string) => void;
  loading: boolean;
  disabled: boolean;
}

const EXAMPLE_PROMPTS = [
  "Extract all Amazon orders from last month — include date, order number, and total amount",
  "Find all emails from my bank in May 2026 and list the transaction dates and amounts",
  "Get all meeting invites from this week — include sender, subject, and date",
  "Collect all invoices from suppliers — extract vendor name, invoice number, date, and amount due",
];

export default function AgentRequest({ onSubmit, loading, disabled }: Props) {
  const [request, setRequest] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!request.trim() || loading || disabled) return;
    onSubmit(request.trim());
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Text area */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700">
          What data do you want to extract?
        </label>
        <textarea
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          disabled={disabled || loading}
          placeholder="e.g. Extract all invoices from Amazon in May 2026. Include date, order number, and total."
          rows={4}
          className={`
            w-full resize-none rounded-xl border px-4 py-3 text-sm
            focus:outline-none focus:ring-2 focus:ring-blue-500
            transition placeholder-slate-400
            ${disabled ? "cursor-not-allowed bg-slate-100 text-slate-400" : "bg-white text-slate-800 border-slate-300"}
          `}
        />
      </div>

      {/* Example prompt chips */}
      {!disabled && !loading && (
        <div>
          <p className="mb-2 text-xs font-medium text-slate-500">Examples — click to use:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => setRequest(prompt)}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 transition"
              >
                {prompt.length > 60 ? prompt.slice(0, 60) + "…" : prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Submit button */}
      <button
        type="submit"
        disabled={!request.trim() || loading || disabled}
        className={`
          flex items-center justify-center gap-2.5 rounded-xl px-6 py-3.5
          font-medium text-white shadow-sm transition
          ${!request.trim() || loading || disabled
            ? "cursor-not-allowed bg-slate-300"
            : "bg-blue-600 hover:bg-blue-700 active:bg-blue-800"
          }
        `}
      >
        {loading ? (
          <>
            <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Agent is working…
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Extract &amp; Populate Document
          </>
        )}
      </button>
    </form>
  );
}
