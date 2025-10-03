// Unified API base for frontend (Vite or Next.js)
export const API_BASE =
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_URL) ||
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
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
