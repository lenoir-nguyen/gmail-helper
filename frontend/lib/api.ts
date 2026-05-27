/**
 * Backend API helpers.
 */

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8001";

/** Fetch the Google OAuth consent URL from the backend. */
export async function getGmailAuthUrl(): Promise<string> {
  const res = await fetch(`${BACKEND}/auth/google/url`);
  if (!res.ok) throw new Error("Failed to get auth URL");
  const data = await res.json();
  return data.url as string;
}

export interface ProcessResult {
  blob: Blob;
  filename: string;
  summary: string;
  rowCount: number;
}

/**
 * Send the document + request to the backend for processing.
 * Returns the populated document as a Blob.
 */
export async function processDocument(
  file: File,
  request: string,
  accessToken: string,
  onProgress?: (msg: string) => void,
): Promise<ProcessResult> {
  onProgress?.("Sending document to agent…");

  const form = new FormData();
  form.append("file", file);
  form.append("request", request);

  const res = await fetch(`${BACKEND}/process`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: form,
  });

  if (res.status === 401) {
    throw new Error("Gmail session expired. Please reconnect your Gmail account.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail ?? "Processing failed");
  }

  onProgress?.("Downloading result…");

  const blob = await res.blob();
  const summary = res.headers.get("X-Summary") ?? "";
  const rowCount = parseInt(res.headers.get("X-Row-Count") ?? "0", 10);

  // Extract filename from Content-Disposition header
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? `result_${Date.now()}.xlsx`;

  return { blob, filename, summary, rowCount };
}
