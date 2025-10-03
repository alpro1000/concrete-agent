// Unified API base for Vite (primary) or Next.js (fallback).
// Важно: НЕ использовать process.env в Vite-сборке, чтобы не ловить TS2591.
export const API_BASE =
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_URL) ||
  (typeof window !== "undefined" && (window as any).__API_BASE__) ||
  "";

// Generic fetch wrapper
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed with ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// Example usage: upload endpoint
export async function postUpload(formData: FormData, token?: string) {
  return apiFetch("/api/v1/upload", { method: "POST", body: formData }, token);
}
