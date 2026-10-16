import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cloud, request, RequestProblem, verify } from "./lib/api";
import { saved } from "./lib/storage";
import {
  fresh,
  payload,
  sameContract,
  type Draft,
  type Profile,
  type Project,
  type Problem,
} from "./types";
type Cap = {
  suggest: Record<string, string[]>;
  max_csv_bytes: number;
  max_rows: number;
};
type Account = { enabled: boolean; signup_enabled?: boolean };
type User = { id: string; email: string };
function useController() {
  const [draft, setDraft] = useState<Draft>(fresh),
    [entries, setEntries] = useState<Draft[]>([]),
    [projects, setProjects] = useState<Project[]>([]),
    [cap, setCap] = useState<Cap | null>(null),
    [account, setAccount] = useState<Account>({ enabled: false }),
    [user, setUser] = useState<User | null>(null),
    [cloudReady, setCloudReady] = useState(false),
    [problem, setProblem] = useState<Problem | null>(null),
    [busy, setBusy] = useState(false),
    [stages, setStages] = useState<Record<string, string>>({}),
    [toast, setToast] = useState(""),
    [storageError, setStorageError] = useState("");
  const controller = useRef<AbortController | null>(null),
    epoch = useRef(0);
  const notify = (message: string) => setToast(message);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 4500);
    return () => window.clearTimeout(timer);
  }, [toast]);
  function fail(error: unknown) {
    if ((error as Error).name === "AbortError") return;
    const e = error as RequestProblem;
    setProblem({ message: e.message, issues: e.issues || [], hint: e.hint });
  }
  async function refresh(currentUser = user) {
    setStorageError("");
    let rows: Draft[] = [],
      groups: Project[] = [];
    try {
      rows = (await saved.list()).map((r) => ({ ...r, storage: "device" }));
      groups = (await saved.projects()).map((p) => ({
        ...p,
        storage: "device",
      }));
    } catch (error) {
      setStorageError((error as Error).message);
    }
    setCloudReady(false);
    if (currentUser)
      try {
        const [remote, remoteProjects] = await Promise.all([
          cloud<Record<string, unknown>[]>("/investigations"),
          cloud<Record<string, unknown>[]>("/projects"),
        ]);
        rows.push(
          ...remote.map((r) => ({
            ...fresh(),
            ...r,
            storage: "cloud" as const,
            projectId: r.project_id as string,
            createdAt: r.created_at as string,
            savedAt: r.created_at as string,
            status: r.status as string,
          })),
        );
        groups.push(
          ...remoteProjects.map((p) => ({
            id: p.id as string,
            name: p.name as string,
            storage: "cloud" as const,
          })),
        );
        setCloudReady(true);
      } catch {
        setStorageError(
          "Account history could not be loaded. Device work remains available; retry after checking the connection.",
        );
      }
    rows.sort((a, b) =>
      String(b.savedAt || b.createdAt).localeCompare(
        String(a.savedAt || a.createdAt),
      ),
    );
    setEntries(rows);
    setProjects(groups);
  }
  async function refreshUser() {
    let current: User | null = null;
    try {
      current = account.enabled ? await cloud<User>("/me") : null;
    } catch {
      /* no simulated login */
    }
    setUser(current);
    await refresh(current);
  }
  useEffect(() => {
    let active = true;
    Promise.allSettled([
      request<Cap>("/api/uploads/capabilities"),
      request<Account>("/api/account/config"),
    ]).then(async (values) => {
      if (!active) return;
      if (values[0].status === "fulfilled") setCap(values[0].value);
      let current: User | null = null;
      if (values[1].status === "fulfilled") {
        setAccount(values[1].value);
        if (values[1].value.enabled)
          try {
            current = await cloud<User>("/me");
          } catch {
            /* signed out */
          }
      }
      if (active) {
        setUser(current);
        await refresh(current);
      }
    });
    return () => {
      active = false;
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (draft.csv && draft.dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [draft.csv, draft.dirty]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 5500);
    return () => clearTimeout(timer);
  }, [toast]);
  function update(value: Partial<Draft>) {
    setDraft((d) => ({ ...d, ...value, dirty: true, report: null }));
    setProblem(null);
  }
  async function loadFile(file: File, kind = "upload") {
    if (file.size > 400000 || !file.name.toLowerCase().endsWith(".csv")) {
      fail(Error("Choose a UTF-8 .csv no larger than 400 KB."));
      return;
    }
    const base = kind === "sample" ? fresh() : draft;
    const current = ++epoch.current;
    controller.current?.abort();
    controller.current = new AbortController();
    setBusy(true);
    setProblem(null);
    try {
      const csv = new TextDecoder("utf-8", {
        fatal: true,
        ignoreBOM: true,
      }).decode(await file.arrayBuffer());
      const profile = await request<Profile>(
        "/api/uploads/profile",
        { csv },
        controller.current.signal,
      );
      if (current !== epoch.current) return;
      if (base.requiredSourceHash && profile.sha256 !== base.requiredSourceHash)
        throw Error(
          "This file differs from the saved source. Upload the matching original or start a new analysis.",
        );
      const mapping: Record<string, string> = {};
      for (const key of ["measure", "group", "filter"]) {
        const suggestion = profile.columns.find((c) =>
          (cap?.suggest[key] || []).includes(c.name.trim().toLowerCase()),
        );
        if (suggestion) mapping[key] = suggestion.id;
      }
      const restore = !!base.requiredSourceHash;
      setDraft({
        ...base,
        id: crypto.randomUUID(),
        csv,
        profile,
        filename: file.name.slice(0, 160),
        report: null,
        storage: "memory",
        dirty: true,
        stage: restore ? 1 : 0,
        mapping: restore ? base.mapping : mapping,
        options: restore ? base.options : { operation: "sum" },
        requiredSourceHash: undefined,
        sourceKind: kind,
        title: restore
          ? base.title
          : kind === "sample"
            ? "Sample · Revenue by region"
            : file.name.replace(/\.csv$/i, "").slice(0, 100),
      });
    } catch (error) {
      if (current === epoch.current) fail(error);
    } finally {
      if (current === epoch.current) setBusy(false);
    }
  }
  async function sample() {
    try {
      const response = await fetch("/api/uploads/template");
      if (!response.ok) throw Error("Sample could not be loaded; retry.");
      await loadFile(
        new File([await response.text()], "querypilot-sample.csv", {
          type: "text/csv",
        }),
        "sample",
      );
    } catch (error) {
      fail(error);
    }
  }
  async function run() {
    if (busy) return;
    const current = ++epoch.current;
    controller.current?.abort();
    controller.current = new AbortController();
    setBusy(true);
    setProblem(null);
    setStages({});
    setDraft((d) => ({ ...d, report: null, stage: 3, dirty: true }));
    try {
      const result = await verify(
        payload(draft),
        (v) => {
          if (current === epoch.current)
            setStages((s) => ({ ...s, [v.stage]: v.state }));
        },
        controller.current.signal,
      );
      if (current !== epoch.current) return;
      if (
        !result.checks ||
        !Object.values(result.checks).every((v) => v === true)
      )
        throw Error(
          "Independent checks did not pass; no result was published.",
        );
      setDraft((d) => ({ ...d, report: result, stage: 3, dirty: true }));
    } catch (error) {
      if (current === epoch.current) {
        fail(error);
        setDraft((d) => ({ ...d, stage: 1, report: null }));
      }
    } finally {
      if (current === epoch.current) setBusy(false);
    }
  }
  function stop() {
    epoch.current++;
    controller.current?.abort();
    setBusy(false);
    setDraft((d) => ({ ...d, stage: 2, report: null }));
    notify(
      "Stopped waiting. The bounded read-only server calculation may finish; your source and rules remain available.",
    );
  }
  async function open(id: string, storage = "device") {
    if (!/^[0-9a-f-]{36}$/.test(id)) throw Error("Invalid saved analysis ID.");
    const current = ++epoch.current;
    controller.current?.abort();
    setBusy(false);
    setProblem(null);
    setDraft(fresh());
    const value =
      storage === "cloud"
        ? await cloud<Record<string, unknown>>("/investigations/" + id)
        : await saved.get(id);
    if (!value)
      throw Error(
        "This snapshot is not available in the selected storage location.",
      );
    const row = value as unknown as Record<string, unknown>;
    const upload = row.upload as Draft | undefined;
    const restored = {
      ...fresh(),
      ...value,
      ...(upload
        ? {
            csv: upload.csv,
            mapping: upload.mapping,
            options: upload.options,
            projectId: row.project_id,
            createdAt: row.created_at,
          }
        : {}),
      storage,
      dirty: false,
    } as Draft;
    if (restored.csv)
      restored.profile = await request<Profile>("/api/uploads/profile", {
        csv: restored.csv,
      });
    if (restored.report) {
      const checked = await request<{ verified: boolean }>(
        "/api/uploads/check-report",
        { report: restored.report },
      );
      if (current !== epoch.current) return;
      if (
        !checked.verified ||
        (restored.csv &&
          restored.profile?.sha256 !== restored.report.source_sha256) ||
        !sameContract(restored, restored.report.contract)
      ) {
        restored.report = null;
        setProblem({
          message:
            "The saved report could not be authenticated for this source and contract.",
          hint: "Re-run the original source. No changed report is presented as verified.",
          issues: [],
        });
      }
    }
    if (current !== epoch.current) return;
    restored.stage = restored.report ? 3 : restored.csv ? 1 : 0;
    if (!restored.csv) {
      restored.requiredSourceHash =
        restored.report?.source_sha256 || (row.source_sha256 as string);
      if (!restored.report)
        setProblem({
          message: "Re-upload the original matching file to continue.",
          hint: "Source retention was not enabled for this snapshot.",
          issues: [],
        });
    }
    if (current === epoch.current) setDraft(restored);
  }
  return {
    draft,
    setDraft,
    entries,
    projects,
    cap,
    account,
    user,
    cloudReady,
    problem,
    setProblem,
    busy,
    stages,
    toast,
    storageError,
    notify,
    fail,
    refresh,
    refreshUser,
    update,
    loadFile,
    sample,
    run,
    stop,
    open,
  };
}
type Controller = ReturnType<typeof useController>;
const Context = createContext<Controller | null>(null);
export function ProductProvider({ children }: { children: ReactNode }) {
  const value = useController();
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useProduct() {
  const value = useContext(Context);
  if (!value) throw Error("Product context is unavailable");
  return value;
}
