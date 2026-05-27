"use client";

interface Props {
  result: {
    blob: Blob;
    filename: string;
    summary: string;
    rowCount: number;
  } | null;
  onReset: () => void;
}

export default function ResultDownload({ result, onReset }: Props) {
  if (!result) return null;

  function handleDownload() {
    if (!result) return;
    const url = URL.createObjectURL(result.blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = result.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const ext = result.filename.split(".").pop()?.toLowerCase();
  const isExcel = ext === "xlsx" || ext === "xls";

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-green-200 bg-green-50 p-6">
      {/* Success header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
          <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <p className="font-semibold text-slate-800">Document ready!</p>
          <p className="text-sm text-slate-600">{result.summary}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="flex gap-4">
        <div className="rounded-lg border border-green-200 bg-white px-4 py-2.5 text-center">
          <p className="text-2xl font-bold text-slate-800">{result.rowCount}</p>
          <p className="text-xs text-slate-500">rows extracted</p>
        </div>
        <div className="rounded-lg border border-green-200 bg-white px-4 py-2.5 text-center">
          <p className={`text-2xl font-bold ${isExcel ? "text-green-700" : "text-blue-700"}`}>
            {ext?.toUpperCase()}
          </p>
          <p className="text-xs text-slate-500">format</p>
        </div>
        <div className="rounded-lg border border-green-200 bg-white px-4 py-2.5 flex-1">
          <p className="text-sm font-medium text-slate-700 truncate">{result.filename}</p>
          <p className="text-xs text-slate-500">output file</p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleDownload}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-medium text-white shadow-sm hover:bg-blue-700 transition"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download {ext?.toUpperCase()}
        </button>
        <button
          onClick={onReset}
          className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-medium text-slate-600 hover:bg-slate-50 transition"
        >
          New request
        </button>
      </div>
    </div>
  );
}
