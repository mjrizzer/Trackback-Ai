export type Row = Record<string, any>;
export async function api(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  headers.set("X-CSRF-Protection", "1");
  const response = await fetch(`/api${path}`, {
    ...options,
    credentials: "same-origin",
    headers,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Please check your input and try again.",
    );
  }
  return response.json();
}
export async function download(path: string, name: string) {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
  });
  if (!response.ok)
    throw new Error("Download unavailable. Check investigation status.");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
export function exportJson(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
