export type Storage = "memory" | "device" | "cloud";
export type Column = {
  id: string;
  name: string;
  missing: number;
  numeric: number;
  distinct: number;
  samples?: string[];
};
export type SourceRow = { row: number; cells: string[] };
export type Profile = {
  rows: number;
  sha256: string;
  columns: Column[];
  preview: SourceRow[];
};
export type Contract = {
  csv: string;
  mapping: Record<string, string>;
  options: Record<string, string>;
};
export type Report = {
  source_sha256: string;
  live_ai: boolean;
  verified_at: string;
  summary: {
    source_rows: number;
    included_rows: number;
    excluded_rows: number;
    groups: number;
    operation: string;
    overall_value: string;
  };
  results: { segment: string; value: string; records: number }[];
  checks: Record<string, boolean>;
  sql: string;
  csv: string;
  scope: string;
  contract: Omit<Contract, "csv">;
  source_columns: Record<string, string>;
  column_bindings: Record<string, string>;
  attestation: { version: string; signature: string };
};
export type Draft = Contract & {
  importSource?: {
    format: string;
    sheet?: string;
    original_sha256: string;
    normalized_sha256: string;
  };
  id: string;
  title: string;
  filename: string;
  projectId: string;
  stage: number;
  profile: Profile | null;
  report: Report | null;
  storage: Storage;
  dirty: boolean;
  createdAt: string;
  savedAt?: string;
  status?: string;
  sourceKind: string;
  requiredSourceHash?: string;
};
export type Project = {
  id: string;
  name: string;
  storage: Storage;
  createdAt?: string;
};
export type Problem = {
  message: string;
  hint?: string;
  issues: { row?: number; column?: string; message: string }[];
};
export function fresh(): Draft {
  return {
    id: crypto.randomUUID(),
    title: "Untitled analysis",
    filename: "",
    csv: "",
    mapping: {},
    options: { operation: "sum" },
    profile: null,
    report: null,
    stage: 0,
    projectId: "",
    storage: "memory",
    dirty: false,
    createdAt: new Date().toISOString(),
    sourceKind: "upload",
  };
}
export function payload(draft: Draft): Contract {
  return { csv: draft.csv, mapping: draft.mapping, options: draft.options };
}
export function sameContract(
  a: Contract | Report["contract"],
  b: Report["contract"],
) {
  return ["mapping", "options"].every(
    (k) =>
      JSON.stringify(Object.entries(a[k as "mapping"] || {}).sort()) ===
      JSON.stringify(Object.entries(b[k as "mapping"] || {}).sort()),
  );
}
