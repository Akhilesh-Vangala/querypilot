export interface UserMe {
  email: string;
  full_name: string;
  role: string;
}
export interface RuntimeConfig {
  data: string;
  model_mode: string;
  framework: string;
  contract_version: string;
  public_demo: boolean;
  production_runtime: boolean;
  max_rows: number;
  max_rounds: number;
  max_sql_attempts: number;
  demo_accounts: boolean;
  history_scope: string;
  live_available: boolean;
}
export interface Metric {
  id: string;
  name: string;
  unit: string;
  table: string;
  grain: string;
  expression: string;
  definition: string;
}
export interface Event {
  sequence: number;
  stage: string;
  status: string;
  elapsed_ms: number;
  tool?: string;
  [key: string]: unknown;
}
export interface AnalysisResult {
  answer: string;
  sql: string;
  chart: string;
  rows: unknown[][];
  columns: string[];
  attempts: number;
  refused: boolean;
  status: string;
  plan: {
    objective: string;
    metric_ids: string[];
    assumptions: string[];
    checks: string[];
  } | null;
  events: Event[];
  model_mode: string;
  rounds: number;
  corrections: number;
  framework: string;
  usage: Record<string, number>;
  elapsed_ms: number;
  validation?: {
    possibly_truncated: boolean;
    result_sha256: string;
    semantic_guarantee: string;
  };
}
export interface Run {
  id: string;
  question: string;
  mode: string;
  status: string;
  result?: AnalysisResult | null;
  events?: Event[];
  error_kind?: string | null;
  created_at: string;
  updated_at: string;
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
  row_count_kind: string;
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

let publicDemo = false;
function demoRuns(): Run[] {
  try {
    return JSON.parse(
      sessionStorage.getItem("querypilot-demo-runs") || "[]",
    ) as Run[];
  } catch {
    return [];
  }
}
function saveDemo(value: Run) {
  sessionStorage.setItem(
    "querypilot-demo-runs",
    JSON.stringify(
      [value, ...demoRuns().filter((r) => r.id !== value.id)].slice(0, 30),
    ),
  );
}
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    credentials: "include",
    headers: { ...(options.headers || {}) },
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      message = (await response.json()).detail || message;
    } catch {
      /* no JSON detail */
    }
    throw new Error(
      typeof message === "string" ? message : "Request could not be completed",
    );
  }
  return response.json() as Promise<T>;
}
export async function login(email: string, password: string): Promise<string> {
  const data = await request<{ access_token: string }>("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  return data.access_token;
}
export const api = {
  config: async () => {
    const value = await request<RuntimeConfig>("/api/config");
    publicDemo = value.public_demo;
    return value;
  },
  me: () => request<UserMe>("/api/auth/me"),
  logout: async () => { const result = await request("/api/auth/logout", { method: "POST" }); sessionStorage.removeItem("querypilot-demo-runs"); return result; },
  metrics: () =>
    request<{ metrics: Metric[]; contract: Record<string, string> }>(
      "/api/metrics",
    ),
  schema: () => request<{ tables: TableInfo[] }>("/api/schema"),
  analyses: async () =>
    publicDemo ? demoRuns() : request<Run[]>("/api/analyses"),
  analysis: async (id: string) => {
    const cached = publicDemo ? demoRuns().find((r) => r.id === id) : null;
    return cached && !["queued", "running"].includes(cached.status)
      ? cached
      : request<Run>("/api/analyses/" + id);
  },
  createAnalysis: async (question: string, mode: string = "baseline") => {
    const value = await request<Run>("/api/analyses", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({ question, mode }),
    });
    if (publicDemo) saveDemo(value);
    return value;
  },
  ask: (question: string) =>
    request<AskResponse>("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
  history: () => request<HistoryItem[]>("/api/ask/history"),
  evalRun: () => request<EvalReport>("/api/eval/run", { method: "POST" }),
};
