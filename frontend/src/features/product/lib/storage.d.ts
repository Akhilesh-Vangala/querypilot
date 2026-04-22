import type { Draft, Project } from "../types";
export const saved: {
  list(): Promise<Draft[]>;
  get(id: string): Promise<Draft | undefined>;
  remove(id: string): Promise<void>;
  projects(): Promise<Project[]>;
  project(value: Project): Promise<void>;
  put(value: Draft, consent: boolean): Promise<void>;
  removeProject(id: string): Promise<void>;
  clear(): Promise<void>;
  restore(entries: Draft[], projects: Project[]): Promise<void>;
};
