import type { Contract, Report } from "../types";
export class RequestProblem extends Error {
  issues: { row?: number; column?: string; message: string }[];
  hint: string;
  constructor(
    body: {
      detail?: unknown;
      issues?: RequestProblem["issues"];
      hint?: string;
    },
    public status = 0,
  ) {
    super(
      typeof body.detail === "string"
        ? body.detail
        : "The request could not complete. Review the source and retry.",
    );
    this.issues = body.issues || [];
    this.hint = body.hint || "";
  }
}
export async function request<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new RequestProblem({
      detail:
        "Connection interrupted. Your current source and rules are still available.",
      hint: "Check your connection and retry. No result was published.",
    });
  }
  const value = await response.json().catch(() => {
    throw new RequestProblem(
      { detail: "The server response was incomplete. Please retry." },
      response.status,
    );
  });
  if (!response.ok) throw new RequestProblem(value, response.status);
  return value as T;
}
export async function verify(
  body: Contract,
  stage: (value: { stage: string; state: string }) => void,
  signal: AbortSignal,
): Promise<Report> {
  let response: Response;
  try {
    response = await fetch("/api/uploads/analyze-stream", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new RequestProblem({
      detail:
        "Connection interrupted. Retry with the retained source and rules.",
    });
  }
  if (!response.ok)
    throw new RequestProblem(
      await response.json().catch(() => ({})),
      response.status,
    );
  const reader = response.body?.getReader();
  if (!reader)
    throw Error("Streaming is unavailable; retry in a supported browser.");
  const decoder = new TextDecoder();
  let buffer = "",
    result: Report | undefined;
  try {
    while (true) {
      const chunk = await reader.read();
      buffer += decoder
        .decode(chunk.value || new Uint8Array(), { stream: !chunk.done })
        .replaceAll("\r\n", "\n");
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const lines = block.split("\n"),
          event = lines.find((l) => l.startsWith("event: "))?.slice(7),
          data = lines
            .filter((l) => l.startsWith("data: "))
            .map((l) => l.slice(6))
            .join("\n");
        if (!data) continue;
        const value = JSON.parse(data);
        if (event === "stage") stage(value);
        if (event === "problem") throw new RequestProblem(value, 422);
        if (event === "result") result = value;
      }
      if (chunk.done) break;
    }
  } finally {
    reader.releaseLock();
  }
  if (!result)
    throw new RequestProblem({
      detail:
        "Verification ended without a complete result. Retry to run every check.",
    });
  return result;
}
let refreshing: Promise<unknown> | undefined;
export async function cloud<T>(path: string, body?: unknown): Promise<T> {
  try {
    return await request<T>("/api/account" + path, body);
  } catch (error) {
    if (
      !(error instanceof RequestProblem) ||
      error.status !== 401 ||
      ["/sign-in", "/refresh"].includes(path)
    )
      throw error;
    refreshing ||= request("/api/account/refresh", {}).finally(() => {
      refreshing = undefined;
    });
    await refreshing;
    return request<T>("/api/account" + path, body);
  }
}
export function download(
  value: string,
  name: string,
  type = "application/json",
) {
  const url = URL.createObjectURL(new Blob([value], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
