"use client";

import { useRef, useState } from "react";

interface Props {
  file: File | null;
  onChange: (file: File | null) => void;
}

const ACCEPTED = ".docx,.xlsx,.xls,.doc";
const ACCEPTED_LABELS = "Word (.docx) or Excel (.xlsx)";

export default function DocumentUpload({ file, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleFileSelect(f: File | null) {
    if (!f) return;
    const ext = f.name.toLowerCase().split(".").pop();
    if (!["docx", "xlsx", "xls", "doc"].includes(ext ?? "")) {
      alert(`Unsupported format. Please upload ${ACCEPTED_LABELS}.`);
      return;
    }
    onChange(f);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    handleFileSelect(f ?? null);
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  // ── File selected ─────────────────────────────────────────────────────────
  if (file) {
    const ext = file.name.split(".").pop()?.toLowerCase();
    const isExcel = ext === "xlsx" || ext === "xls";

    return (
      <div className="flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg text-white font-bold text-xs ${isExcel ? "bg-green-600" : "bg-blue-600"}`}>
            {isExcel ? "XLS" : "DOC"}
          </div>
          <div>
            <p className="font-medium text-slate-800">{file.name}</p>
            <p className="text-sm text-slate-500">{formatSize(file.size)}</p>
          </div>
        </div>
        <button
          onClick={() => onChange(null)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition"
        >
          Change
        </button>
      </div>
    );
  }

  // ── Drop zone ─────────────────────────────────────────────────────────────
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`
        flex cursor-pointer flex-col items-center gap-4 rounded-xl border-2 border-dashed
        px-8 py-10 transition
        ${dragging
          ? "border-blue-400 bg-blue-50"
          : "border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50"
        }
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
      />

      <svg className="h-10 w-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>

      <div className="text-center">
        <p className="font-semibold text-slate-800">
          Drop your document here
        </p>
        <p className="mt-1 text-sm text-slate-500">
          {ACCEPTED_LABELS} — click or drag & drop
        </p>
      </div>

      <p className="text-xs text-slate-400">
        The document will be returned populated with your Gmail data
      </p>
    </div>
  );
}
