import type { Profile } from "../types";
export const ACCEPT: string;
export const FORMAT_HELP: string;
export type ImportSource = {
  format: string;
  sheet?: string;
  original_sha256: string;
  normalized_sha256: string;
};
export type Imported = {
  csv: string;
  profile: Profile;
  source: ImportSource;
  needs_sheet?: boolean;
  sheets?: string[];
};
export function importFile(
  file: File,
  send: (body: Record<string, unknown>) => Promise<Imported>,
  signal?: AbortSignal,
): Promise<Imported>;
