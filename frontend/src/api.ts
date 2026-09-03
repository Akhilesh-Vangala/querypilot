export interface UserMe {
  email: string;
  full_name: string;
  role: string;
}

export interface AskResponse {
  answer: string;
  sql: string;
  chart: string;
  rows: unknown[][];
  columns: string[];
  attempts: number;
  refused: boolean;
}

export interface HistoryItem {
  id: number;
  question: string;
  sql: string;
  answer: string;
  refused: boolean;
  created_at: string;
}

export interface TableInfo {
  name: string;
  row_count: number;
  columns: { name: string; type: string }[];
}

export interface EvalReport {
  score: number;
  n: number;
  passed: number;
  results: {
    id: string;
    question: string;
    passed: boolean;
    refused: boolean;
    predicted_sql: string;
    detail: string;
  }[];
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  if (response.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) throw new Error("Invalid credentials");
  const data = await response.json();
  return data.access_token as string;
}

export const api = {
  me: () => request<UserMe>("/api/auth/me"),
  schema: () => request<{ tables: TableInfo[] }>("/api/schema"),
  ask: (question: string) =>
    request<AskResponse>("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
  history: () => request<HistoryItem[]>("/api/ask/history"),
  evalRun: () =>
    request<EvalReport>("/api/eval/run", {
      method: "POST",
    }),
};
