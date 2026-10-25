import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useProduct } from "./context";
import { cloud, download, request } from "./lib/api";
import { saved } from "./lib/storage";
import {
  fresh,
  payload,
  sameContract,
  type Draft,
  type Profile,
  type Project,
  type Storage,
} from "./types";
import { Dialog, Heading, Issue, Table } from "./components";
import ProductHome, { Brand } from "./ProductHome";
import ProductIntake from "./ProductIntake";
import ProductReport from "./ProductReport";
import StudioIcon from "../../components/layout/StudioIcon";
import "./styles.css";
import "./studio.css";
type Modal =
  | "save"
  | "project"
  | "clear"
  | "new"
  | "sample"
  | "remove"
  | "remove-project"
  | "wipe"
  | "restore"
  | "commands"
  | null;
const nav = [
  ["/workspace", "Overview"],
  ["/workspace/history", "Analyses"],
  ["/workspace/projects", "Projects"],
  ["/workspace/guide", "Quick guide"],
  ["/workspace/settings", "Settings"],
];
const date = (entry: Draft) =>
  new Date(entry.savedAt || entry.createdAt).toLocaleString();
export default function ProductApp() {
  const ctx = useProduct(),
    { draft, entries, projects } = ctx,
    location = useLocation(),
    navigate = useNavigate(),
    path = location.pathname;
  const analysis =
    path === "/uploads" ||
    path === "/uploads/" ||
    path === "/workspace/new" ||
    path.startsWith("/workspace/analyses/");
  const [modal, setModal] = useState<Modal>(null),
    [consent, setConsent] = useState(false),
    [destination, setDestination] = useState<Storage>("device"),
    [retainSource, setRetainSource] = useState(false),
    [message, setMessage] = useState(""),
    [working, setWorking] = useState(false),
    [name, setName] = useState(""),
    [search, setSearch] = useState(""),
    [status, setStatus] = useState(""),
    [target, setTarget] = useState<Draft | null>(null),
    [targetProject, setTargetProject] = useState<Project | null>(null),
    [backup, setBackup] = useState<File | null>(null),
    [candidate, setCandidate] = useState("");
  function show(value: Modal) {
    setConsent(false);
    setMessage("");
    setWorking(false);
    setDestination("device");
    setRetainSource(false);
    setName("");
    setCandidate(crypto.randomUUID());
    setModal(value);
  }
  function sample() {
    if (draft.csv && draft.dirty) {
      show("sample");
      return;
    }
    navigate("/uploads");
    ctx.sample();
  }
  function clear() {
    show("clear");
  }
  function save() {
    show("save");
  }
  useEffect(() => {
    let active = true;
    if (new URLSearchParams(location.search).has("new")) {
      if (draft.csv && draft.dirty) show("new");
      else ctx.setDraft(fresh());
      navigate("/uploads", { replace: true });
      return;
    }
    if (path.startsWith("/workspace/analyses/")) {
      const id = path.split("/").at(-1)!;
      ctx
        .open(
          id,
          new URLSearchParams(location.search).get("storage") || "device",
        )
        .catch((error) => {
          if (active) {
            ctx.setDraft(fresh());
            ctx.fail(error);
          }
        });
    }
    return () => {
      active = false;
    };
  }, [path, location.search]);
  useEffect(() => {
    document.title =
      path === "/"
        ? "QueryPilot · Questions to executed evidence"
        : analysis
          ? draft.title
          : "QueryPilot workspace";
    const timer = setTimeout(
      () =>
        document
          .querySelector<HTMLElement>(".product-root h1")
          ?.focus({ preventScroll: true }),
      0,
    );
    return () => clearTimeout(timer);
  }, [path, draft.stage]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        show("commands");
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);
  async function saveSnapshot() {
    if (!consent || !draft.csv) return;
    setWorking(true);
    setMessage("");
    const selected = projects.find((p) => p.id === draft.projectId);
    const value = {
      ...structuredClone(draft),
      id: candidate,
      storage: destination,
      dirty: false,
      savedAt: new Date().toISOString(),
      stage: draft.report ? 3 : draft.stage,
    };
    try {
      if (selected && selected.storage !== destination)
        throw Error(
          "Choose a project in the selected storage location, or select Unassigned before saving.",
        );
      if (destination === "device") await saved.put(value, true);
      else
        await cloud("/investigations", {
          id: candidate,
          title: draft.title,
          filename: draft.filename,
          project_id: draft.projectId || null,
          parent_id: draft.storage === "cloud" ? draft.id : null,
          status: draft.report ? "completed" : "draft",
          upload: payload(draft),
          retain_source: retainSource,
          consent: true,
        });
      ctx.setDraft(value);
      await ctx.refresh();
      setModal(null);
      navigate("/workspace/analyses/" + candidate + "?storage=" + destination, {
        replace: true,
      });
      ctx.notify(
        "Saved a new " +
          (draft.report ? "report" : "draft") +
          " snapshot " +
          (destination === "device" ? "on this device." : "to your account."),
      );
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setWorking(false);
    }
  }
  async function createProject() {
    if (!consent || !name.trim()) return;
    setWorking(true);
    try {
      const value = {
        id: candidate,
        name: name.trim(),
        storage: destination,
        createdAt: new Date().toISOString(),
      };
      if (destination === "device") await saved.project(value);
      else
        await cloud("/projects", {
          id: candidate,
          name: value.name,
          consent: true,
        });
      await ctx.refresh();
      setModal(null);
      ctx.notify("Project created.");
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setWorking(false);
    }
  }
  async function remove() {
    setWorking(true);
    try {
      if (modal === "remove" && target) {
        if (target.storage === "cloud")
          await cloud("/investigations/delete", { id: target.id });
        else await saved.remove(target.id);
      } else if (modal === "remove-project" && targetProject) {
        if (targetProject.storage === "cloud")
          await cloud("/projects/delete", { id: targetProject.id });
        else await saved.removeProject(targetProject.id);
      } else if (modal === "wipe" && consent) await saved.clear();
      await ctx.refresh();
      setModal(null);
      ctx.notify(
        "Selected saved data removed; the active source and connected business systems are unchanged.",
      );
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setWorking(false);
    }
  }
  async function exportBackup() {
    try {
      download(
        JSON.stringify(
          {
            format: "querypilot-device-backup-v1",
            exportedAt: new Date().toISOString(),
            entries: await saved.list(),
            projects: await saved.projects(),
          },
          null,
          2,
        ),
        "querypilot-device-backup.json",
      );
    } catch (error) {
      ctx.notify((error as Error).message);
    }
  }
  async function restore() {
    if (!consent || !backup) return;
    setWorking(true);
    let rejected = 0;
    try {
      if (
        backup.size > 24000000 ||
        !backup.name.toLowerCase().endsWith(".json")
      )
        throw Error("Choose a QueryPilot JSON backup no larger than 24 MB.");
      const value = JSON.parse(await backup.text());
      if (
        value.format !== "querypilot-device-backup-v1" ||
        !Array.isArray(value.entries) ||
        !Array.isArray(value.projects) ||
        value.entries.length > 50 ||
        value.projects.length > 20
      )
        throw Error("Unsupported backup format or device limits exceeded.");
      const ids = new Map<string, string>();
      const groups: Project[] = value.projects.map((p: Project) => {
        if (
          typeof p.id !== "string" ||
          ids.has(p.id) ||
          typeof p.name !== "string" ||
          !p.name.trim() ||
          p.name.length > 80
        )
          throw Error("A backup project is invalid.");
        const id = crypto.randomUUID();
        ids.set(p.id, id);
        return {
          id,
          name: p.name.trim(),
          storage: "device",
          createdAt: new Date().toISOString(),
        };
      });
      const rows: Draft[] = [];
      for (const [i, entry] of (value.entries as Draft[]).entries()) {
        setMessage(
          "Inspecting saved source " +
            (i + 1) +
            " of " +
            value.entries.length +
            "…",
        );
        if (
          typeof entry.csv !== "string" ||
          typeof entry.title !== "string" ||
          !entry.title.trim() ||
          entry.title.length > 100 ||
          typeof entry.filename !== "string" ||
          entry.filename.length > 160
        )
          throw Error("A saved analysis has invalid source or metadata.");
        const profile = await request<Profile>(
          "/api/uploads/profile",
          payload(entry),
        );
        let report = null;
        if (entry.report) {
          const check = await request<{ verified: boolean }>(
            "/api/uploads/check-report",
            { report: entry.report },
          );
          if (
            check.verified &&
            profile.sha256 === entry.report.source_sha256 &&
            sameContract(entry, entry.report.contract)
          )
            report = entry.report;
          else rejected++;
        }
        rows.push({
          ...fresh(),
          id: crypto.randomUUID(),
          title: entry.title.trim(),
          filename: entry.filename,
          csv: entry.csv,
          mapping: entry.mapping || {},
          options: entry.options || {},
          profile,
          report,
          stage: report ? 3 : 1,
          projectId: ids.get(entry.projectId) || "",
          storage: "device",
          dirty: false,
          savedAt: new Date().toISOString(),
          sourceKind: "restored backup",
        });
      }
      await saved.restore(rows, groups);
      await ctx.refresh();
      setModal(null);
      navigate("/workspace/history");
      ctx.notify(
        "Restored " +
          rows.length +
          " new device snapshots." +
          (rejected
            ? " " +
              rejected +
              " unverifiable reports returned to drafts; rerun their sources."
            : ""),
      );
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setWorking(false);
    }
  }
  const complete = (entry: Draft) =>
    !!entry.report || entry.status === "completed";
  const entryLink = (entry: Draft) =>
    "/workspace/analyses/" + entry.id + "?storage=" + entry.storage;
  const projectId = path.startsWith("/workspace/projects/")
    ? path.split("/").at(-1)
    : "";
  const selectedEntries = entries.filter(
    (e) =>
      (!projectId || e.projectId === projectId) &&
      (!status || (status === "completed" ? complete(e) : !complete(e))) &&
      (e.title + " " + e.filename).toLowerCase().includes(search.toLowerCase()),
  );
  function recent(rows: Draft[]) {
    return rows.length ? (
      <div className="recent-list">
        {rows.map((e) => (
          <div className="recent-item" key={e.id}>
            <div className="recent-title">
              <Link to={entryLink(e)}>
                <strong>{e.title}</strong>
              </Link>
              <p>
                {e.filename +
                  " · " +
                  date(e) +
                  " · " +
                  (e.storage === "cloud" ? "Account" : "This device")}
              </p>
            </div>
            <span className="badge">
              {complete(e) ? "Saved result" : "Draft"}
            </span>
            <Link
              className="quiet"
              to={entryLink(e)}
              aria-label={"Open " + e.title}
            >
              →
            </Link>
          </div>
        ))}
      </div>
    ) : (
      <div className="empty">
        <h2>Your first analysis starts here.</h2>
        <p>
          Bring a table export or explore the sample. Only work you explicitly
          save appears here.
        </p>
        <div className="actions">
          <Link className="primary" to="/uploads?new=1">
            Upload a data file
          </Link>
          <button className="secondary" onClick={sample}>
            Explore the sample
          </button>
        </div>
      </div>
    );
  }
  let content: ReactNode;
  if (analysis)
    content =
      draft.report && draft.stage === 3 ? (
        <ProductReport save={save} clear={clear} />
      ) : (
        <ProductIntake save={save} clear={clear} />
      );
  else if (path === "/workspace")
    content = (
      <>
        <Heading
          eyebrow="YOUR ANALYTICAL WORKSPACE"
          title="Make the definition part of the answer."
          description="Start an analysis, resume a saved draft or revisit the evidence behind a result."
          actions={
            <Link className="primary" to="/uploads?new=1">
              New analysis →
            </Link>
          }
        />
        <section
          className="workspace-launchpad"
          aria-label="Choose your next analytical task"
        >
          <Link to="/uploads?new=1" className="launch-upload">
            <StudioIcon name="upload" />
            <span className="eyebrow">ANALYZE A FILE</span>
            <h2>Your data. Your definition.</h2>
            <p>Upload, profile and reconcile a table export.</p>
            <span>Start an analysis →</span>
          </Link>
          <Link to="/compare" className="launch-compare">
            <StudioIcon name="compare" />
            <span className="eyebrow">COMPARE WAREHOUSE PERIODS</span>
            <h2>Understand what changed.</h2>
            <p>Inspect contributions across reviewed synthetic metrics.</p>
            <span>Open period comparison →</span>
          </Link>
        </section>
        <div className="stats">
          {[
            [
              "Saved analyses",
              entries.length,
              "Only work you explicitly saved",
            ],
            [
              "Completed reports",
              entries.filter(complete).length,
              "Saved results, not fresh source-system checks",
            ],
            ["Projects", projects.length, "Related analytical work"],
          ].map(([label, value, hint]) => (
            <div className="stat" key={String(label)}>
              <span className="stat-label">{label}</span>
              <strong>{value}</strong>
              <small>{hint}</small>
            </div>
          ))}
        </div>
        <section className="panel spaced">
          <div className="panel-heading">
            <h2>Recent analyses</h2>
            <Link className="quiet" to="/workspace/history">
              View all →
            </Link>
          </div>
          {recent(entries.slice(0, 5))}
        </section>
      </>
    );
  else if (path === "/workspace/history" || projectId)
    content = (
      <>
        <Heading
          eyebrow="SAVED WORK"
          title={
            projectId
              ? projects.find((p) => p.id === projectId)?.name ||
                "Project analyses"
              : "A record of the work you kept."
          }
          description="Drafts and saved results are explicit snapshots. A saved result authenticates a past calculation."
          actions={
            <Link className="primary" to="/uploads?new=1">
              New analysis →
            </Link>
          }
        />
        <div className="toolbar">
          <label className="search-field">
            Search analyses
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <label>
            Filter status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All snapshots</option>
              <option value="completed">Saved results</option>
              <option value="draft">Drafts</option>
            </select>
          </label>
        </div>
        <section className="panel">
          {selectedEntries.length ? (
            <Table
              label="Saved analyses"
              headers={["Analysis", "Status", "Saved", "Storage", "Actions"]}
              rows={selectedEntries.map((e) => [
                <Link to={entryLink(e)}>{e.title}</Link>,
                <span className="badge">
                  {complete(e) ? "Saved result" : "Draft"}
                </span>,
                date(e),
                e.storage === "cloud" ? "Account" : "This device",
                <button
                  className="quiet"
                  aria-label={"Delete " + e.title}
                  onClick={() => {
                    setTarget(e);
                    show("remove");
                  }}
                >
                  Delete
                </button>,
              ])}
            />
          ) : (
            recent([])
          )}
        </section>
      </>
    );
  else if (path === "/workspace/projects")
    content = (
      <>
        <Heading
          eyebrow="PROJECTS"
          title="Keep related questions together."
          description="Organize deliberate snapshots by dataset, reporting cycle or business question."
          actions={
            <button className="primary" onClick={() => show("project")}>
              Create project
            </button>
          }
        />
        {projects.length ? (
          <div className="project-grid">
            {projects.map((p) => (
              <section key={p.id} className="project-card">
                <h2>{p.name}</h2>
                <p className="spaced">
                  {entries.filter((e) => e.projectId === p.id).length} saved
                  analyses · {p.storage === "cloud" ? "Account" : "This device"}
                </p>
                <div className="actions">
                  <Link
                    className="secondary"
                    to={"/workspace/projects/" + p.id}
                  >
                    Open project →
                  </Link>
                  <button
                    className="quiet"
                    aria-label={"Delete project " + p.name}
                    onClick={() => {
                      setTargetProject(p);
                      show("remove-project");
                    }}
                  >
                    Delete
                  </button>
                </div>
              </section>
            ))}
          </div>
        ) : (
          <section className="panel empty">
            <h2>A project starts with a clear question.</h2>
            <p>
              Create a named group and choose its storage location deliberately.
            </p>
            <button className="primary" onClick={() => show("project")}>
              Create your first project
            </button>
          </section>
        )}
      </>
    );
  else if (path === "/workspace/settings")
    content = (
      <>
        <Heading
          eyebrow="WORKSPACE SETTINGS"
          title="Know where the data lives."
          description="Unsaved work stays in browser memory. Saving and source retention require explicit consent."
        />
        <section className="panel">
          <div className="settings-row">
            <div>
              <h3>This device</h3>
              <p>
                Explicit snapshots include source CSV, rules and reports in this
                browser’s IndexedDB. They do not sync automatically and may be
                removed by browser cleanup.
              </p>
            </div>
            <span className="badge">
              {entries.filter((e) => e.storage === "device").length} saved
            </span>
          </div>
          <div className="settings-row">
            <div>
              <h3>Cloud account</h3>
              <p>
                {ctx.user
                  ? ctx.user.email
                  : ctx.account.enabled
                    ? "A provider is configured. Sign in before choosing account storage."
                    : "Cloud accounts are not connected on this deployment. Device workflows and deliberate backup transfer are available."}
              </p>
            </div>
            <Link className="secondary" to="/workspace/login">
              Account status
            </Link>
          </div>
          <div className="settings-row">
            <div>
              <h3>Export device history</h3>
              <p>
                The JSON backup contains saved source files, rules and reports.
                Keep it somewhere appropriate for your business data.
              </p>
            </div>
            <button className="secondary" onClick={exportBackup}>
              Export device backup
            </button>
          </div>
          <div className="settings-row">
            <div>
              <h3>Restore a device backup</h3>
              <p>
                Transfer work to another browser. Sources are validated and
                reports authenticated before new copies are saved.
              </p>
            </div>
            <label className="field">
              QueryPilot JSON backup
              <input
                type="file"
                id="backup-file"
                accept=".json,application/json"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    setBackup(e.target.files[0]);
                    show("restore");
                  }
                  e.target.value = "";
                }}
              />
            </label>
          </div>
          <div className="settings-row">
            <div>
              <h3>Remove device history</h3>
              <p>
                Deletes saved investigations and projects in this browser. It
                does not delete the active unsaved file or account data.
              </p>
            </div>
            <button className="secondary" onClick={() => show("wipe")}>
              Delete device history
            </button>
          </div>
          <div className="settings-row">
            <div>
              <h3>Processing boundary</h3>
              <p>
                UTF-8 CSV, 400 KB, 5,000 records, 60 columns and 100 result
                groups. Public processing is deterministic and read-only. No raw
                source is deliberately logged; hosting metadata may remain with
                the host. Large files, confidential hosting certification, live
                model quality and monitored customer execution are separate
                gates.
              </p>
            </div>
          </div>
        </section>
      </>
    );
  else if (path === "/workspace/login") content = <Account />;
  else if (path === "/workspace/guide")
    content = (
      <>
        <Heading
          eyebrow="QUICK GUIDE"
          title="A precise question makes a useful result."
          description="Use a reviewed analytical contract, keep its assumptions visible and inspect the executed evidence."
        />
        <div className="guide-grid">
          {[
            [
              "Prepare the export",
              "Use a UTF-8 comma-separated file with a unique named header. Keep units consistent. Inspect source rows and column quality before mapping.",
            ],
            [
              "Define the metric",
              "Choose sum, count or average; sum and average require a numeric measure. Optional exact-match filtering is case-sensitive and does not silently trim source cells.",
            ],
            [
              "Interpret the result",
              "Decimal sums and actual row counts are independently reconciled with SQL. The overall average uses all included records. Duplicates remain; malformed included values and empty filter results withhold the report.",
            ],
            [
              "Keep the evidence",
              "Download exact result strings, normalized SQL and evidence. Saving creates a new device or configured-account snapshot. Reopening checks the past report signature and source/contract linkage; it is not a live warehouse check.",
            ],
          ].map(([h, p]) => (
            <section className="panel" key={h}>
              <h2>{h}</h2>
              <p>{p}</p>
            </section>
          ))}
        </div>
        <section className="panel spaced">
          <h2>Explore the separate guided analytics workbench.</h2>
          <p className="muted spaced">
            The original synthetic claims/network agent and period-comparison
            flows remain available. Their dataset, authentication and session
            history are separate from your uploaded data.
          </p>
          <div className="actions spaced">
            <Link className="secondary" to="/demo">
              Guided analytics demo →
            </Link>
            <a className="secondary" href="/uploads/recording.html">
              Watch upload demo
            </a>
          </div>
        </section>
      </>
    );
  else
    content = (
      <section className="panel empty">
        <h1>This page isn’t available.</h1>
        <Link className="primary" to="/workspace">
          Open workspace
        </Link>
      </section>
    );
  return (
    <div className="product-root">
      <a className="skip" href="#main">
        Skip to content
      </a>
      {path === "/" ? (
        <ProductHome sample={sample} />
      ) : (
        <div className="app-shell">
          <aside className="sidebar">
            <Brand />
            <Link className="rail-create" to="/uploads?new=1">
              <StudioIcon name="upload" /> New analysis <span>+</span>
            </Link>
            <p className="eyebrow">YOUR STUDIO</p>
            <nav className="app-nav" aria-label="Workspace navigation">
              {nav.map(([href, label], index) => (
                <Link
                  key={href}
                  to={href}
                  aria-current={path === href ? "page" : undefined}
                >
                  <StudioIcon
                    name={
                      ["overview", "analyses", "projects", "guide", "settings"][
                        index
                      ]
                    }
                  />
                  {label}
                </Link>
              ))}
            </nav>
            <div className="rail-lab">
              <span className="eyebrow">EXPLORE THE WAREHOUSE</span>
              <Link to="/demo">
                <StudioIcon name="query" /> Investigation studio <span>↗</span>
              </Link>
              <p>Reviewed metrics. Guarded SQL. Reconciled comparisons.</p>
            </div>
            <div className="sidebar-foot">
              <span className="badge">
                {ctx.user ? "Account connected" : "Device workspace"}
              </span>
              <p>Save deliberately. Keep the definition with the result.</p>
              <Link className="text-link" to="/demo">
                Guided analytics demo ↗
              </Link>
            </div>
          </aside>
          <div className="workspace">
            <header className="workspace-bar">
              <span>
                <span className="bar-context">QueryPilot studio</span> /{" "}
                {analysis
                  ? "Analysis"
                  : nav.find(([p]) => p === path)?.[1] || "Details"}
              </span>
              <div className="actions">
                <button
                  className="command-button"
                  onClick={() => show("commands")}
                  aria-label="Find work"
                >
                  <StudioIcon name="search" /> Find work <kbd>⌘ K</kbd>
                </button>
                <span className="badge">
                  {ctx.user ? "Account" : "This device"}
                </span>
                <Link className="quiet" to="/workspace/login">
                  {ctx.user ? "Account" : "Sign in"}
                </Link>
              </div>
            </header>
            <main id="main">
              {ctx.storageError && (
                <p className="inline-error" role="alert">
                  {ctx.storageError}
                </p>
              )}
              {!analysis && <Issue />}
              {content}
              <footer className="workspace-footer">
                <span>QueryPilot · Reviewed questions · Executed evidence</span>
                <div className="actions">
                  <Link to="/workspace/settings">Data handling</Link>
                  <a
                    href="https://github.com/Akhilesh-Vangala/querypilot/tree/main/docs"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Engineering documentation ↗
                  </a>
                </div>
              </footer>
            </main>
          </div>
        </div>
      )}
      {ctx.toast && (
        <div className="toast" role="status">
          {ctx.toast}
        </div>
      )}
      {modal && (
        <Dialog
          title={
            {
              save: "Save this analysis deliberately.",
              project: "Create a project",
              clear: "Clear active work?",
              new: "Start a new analysis?",
              sample: "Replace with the sample file?",
              remove: "Delete this saved analysis?",
              "remove-project": "Delete this project?",
              wipe: "Delete device history?",
              restore: "Restore work on this device",
              commands: "Find work",
            }[modal]
          }
          onClose={() => {
            if (!working) setModal(null);
          }}
        >
          {modal === "save" && (
            <>
              <label className="field">
                Storage destination
                <select
                  id="save-destination"
                  value={destination}
                  onChange={(e) => {
                    setDestination(e.target.value as Storage);
                    setConsent(false);
                  }}
                >
                  <option value="device">This device · browser storage</option>
                  <option value="cloud" disabled={!ctx.user || !ctx.cloudReady}>
                    My cloud account
                    {!ctx.user || !ctx.cloudReady ? " · not available" : ""}
                  </option>
                </select>
              </label>
              <p className="spaced">
                {destination === "device"
                  ? "This copy includes your source CSV, rules and completed report. It stays in this browser and may be cleared by browser cleanup."
                  : "The report and metadata are stored in your authenticated account. Source retention is a separate choice; a draft without its source requires a matching re-upload."}
              </p>
              {destination === "cloud" && (
                <label className="checkbox spaced">
                  <input
                    type="checkbox"
                    checked={retainSource}
                    onChange={(e) => setRetainSource(e.target.checked)}
                  />
                  Also retain the original CSV in my cloud account.
                </label>
              )}
              <label className="checkbox spaced">
                <input
                  type="checkbox"
                  id="save-consent"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                I consent to saving the business data described above in the
                selected location.
              </label>
              <p className="hint spaced">
                Each save is a new snapshot. Existing saved results are not
                overwritten.
              </p>
            </>
          )}
          {modal === "project" && (
            <>
              <label className="field">
                Project name
                <input
                  id="project-name"
                  maxLength={80}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <label className="field spaced">
                Storage
                <select
                  value={destination}
                  onChange={(e) => {
                    setDestination(e.target.value as Storage);
                    setConsent(false);
                  }}
                >
                  <option value="device">This device</option>
                  <option value="cloud" disabled={!ctx.cloudReady}>
                    Cloud account
                  </option>
                </select>
              </label>
              <label className="checkbox spaced">
                <input
                  type="checkbox"
                  id="project-consent"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                Save this project name in the selected location.
              </label>
            </>
          )}
          {["clear", "new", "sample"].includes(modal) && (
            <p>
              The active unsaved source and result will leave memory. Explicitly
              saved history remains available. Save or export the current work
              first if you need it.
            </p>
          )}
          {modal === "remove" && (
            <p>
              The saved snapshot will be deleted from{" "}
              {target?.storage === "cloud" ? "your account" : "this browser"}.
              Export evidence first if needed. The source system is not
              modified.
            </p>
          )}
          {modal === "remove-project" && (
            <p>
              Delete this project’s saved analyses first. The project name will
              be removed from its selected storage.
            </p>
          )}
          {modal === "wipe" && (
            <>
              <p>
                This deletes device projects and snapshots. Account data and the
                active source are separate. Export a backup first if you need
                these records.
              </p>
              <label className="checkbox spaced">
                <input
                  type="checkbox"
                  id="confirm-delete-history"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                I understand this device history will be deleted.
              </label>
            </>
          )}
          {modal === "restore" && (
            <>
              <p>
                The backup may contain business data. Its sources will be
                submitted to this deployment for bounded validation; reports
                must authenticate against their retained source and rules. New
                IDs preserve existing snapshots. Unverifiable reports return to
                drafts.
              </p>
              <label className="checkbox spaced">
                <input
                  type="checkbox"
                  id="restore-consent"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                I consent to validating these sources and storing new copies in
                this browser.
              </label>
            </>
          )}
          {modal === "commands" ? (
            <>
              <label className="field">
                Search pages and saved work
                <input
                  type="search"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoFocus
                />
              </label>
              <div className="command-results">
                {[
                  ...nav,
                  ["/uploads?new=1", "New analysis"],
                  ...entries.map((e) => [entryLink(e), e.title]),
                ]
                  .filter(([, label]) =>
                    label.toLowerCase().includes(name.toLowerCase()),
                  )
                  .map(([href, label]) => (
                    <Link key={href} to={href} onClick={() => setModal(null)}>
                      {label}
                    </Link>
                  ))}
              </div>
            </>
          ) : (
            <>
              <p className="inline-error spaced" role="status">
                {message}
              </p>
              <div className="dialog-actions">
                <button
                  className="secondary"
                  onClick={() => setModal(null)}
                  disabled={working}
                >
                  Cancel
                </button>
                {modal === "save" ? (
                  <button
                    className="primary"
                    id="confirm-save"
                    disabled={!consent || working}
                    onClick={saveSnapshot}
                  >
                    {working
                      ? "Saving…"
                      : draft.report
                        ? "Save report snapshot"
                        : "Save draft snapshot"}
                  </button>
                ) : modal === "project" ? (
                  <button
                    className="primary"
                    disabled={!consent || !name.trim() || working}
                    onClick={createProject}
                  >
                    Create project
                  </button>
                ) : modal === "restore" ? (
                  <button
                    className="primary"
                    id="confirm-restore"
                    disabled={!consent || working}
                    onClick={restore}
                  >
                    {working ? "Validating…" : "Restore device backup"}
                  </button>
                ) : ["remove", "remove-project", "wipe"].includes(modal) ? (
                  <button
                    className="danger"
                    disabled={working || (modal === "wipe" && !consent)}
                    onClick={remove}
                  >
                    Delete{" "}
                    {modal === "wipe"
                      ? "device history"
                      : modal === "remove-project"
                        ? "project"
                        : "snapshot"}
                  </button>
                ) : (
                  <button
                    className="primary"
                    id="confirm-clear"
                    onClick={() => {
                      if (ctx.busy) ctx.stop();
                      ctx.setProblem(null);
                      ctx.setDraft(fresh());
                      setModal(null);
                      navigate("/uploads");
                      if (modal === "sample") ctx.sample();
                    }}
                  >
                    {modal === "sample"
                      ? "Use sample"
                      : modal === "new"
                        ? "Start new"
                        : "Clear active work"}
                  </button>
                )}
              </div>
            </>
          )}
        </Dialog>
      )}
    </div>
  );
}
function Account() {
  const ctx = useProduct(),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [signUp, setSignUp] = useState(false),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <>
      <Heading
        eyebrow="ACCOUNT"
        title="Keep storage choices explicit."
        description="Device workflows work without an account. Cross-device cloud saving requires a genuine configured identity service."
      />
      <section className="panel auth-card">
        {!ctx.account.enabled ? (
          <>
            <h2>Cloud accounts aren’t connected yet.</h2>
            <p className="muted spaced">
              No successful login or cloud save is simulated. Use device history
              and deliberate backup transfer right now.
            </p>
            <div className="actions spaced">
              <Link className="primary" to="/workspace">
                Continue on this device
              </Link>
              <Link className="secondary" to="/workspace/settings">
                Storage settings
              </Link>
            </div>
          </>
        ) : ctx.user ? (
          <>
            <h2>You’re signed in.</h2>
            <p className="spaced">{ctx.user.email}</p>
            <button
              className="secondary spaced"
              onClick={async () => {
                try {
                  const value = await cloud<{ provider_revoked: boolean }>(
                    "/sign-out",
                    {},
                  );
                  await ctx.refreshUser();
                  if (ctx.draft.storage === "cloud") ctx.setDraft(fresh());
                  ctx.notify(
                    value.provider_revoked
                      ? "Signed out."
                      : "Browser cookies cleared. Provider revocation was unavailable; its access token may remain valid until expiry.",
                  );
                } catch (error) {
                  setMessage((error as Error).message);
                }
              }}
            >
              Sign out
            </button>
          </>
        ) : (
          <>
            <h2>{signUp ? "Create your account." : "Welcome back."}</h2>
            <form
              className="spaced"
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setMessage("");
                try {
                  const value = await cloud<{
                    confirmation_required?: boolean;
                  }>(signUp ? "/sign-up" : "/sign-in", { email, password });
                  setPassword("");
                  if (value.confirmation_required)
                    setMessage(
                      "Confirm the email from your provider, then return to sign in. No source has been saved.",
                    );
                  else {
                    await ctx.refreshUser();
                    ctx.notify(
                      "Signed in. Choose a destination when saving work.",
                    );
                  }
                } catch (error) {
                  setMessage((error as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label className="field">
                Email
                <input
                  type="email"
                  value={email}
                  required
                  maxLength={254}
                  autoComplete="email"
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              <label className="field spaced">
                Password
                <input
                  type="password"
                  value={password}
                  required
                  minLength={signUp ? 12 : 1}
                  maxLength={128}
                  autoComplete={signUp ? "new-password" : "current-password"}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <button type="submit" className="primary spaced" disabled={busy}>
                {busy ? "Connecting…" : signUp ? "Create account" : "Sign in"}
              </button>
            </form>
            {ctx.account.signup_enabled && (
              <button
                className="quiet spaced"
                onClick={() => setSignUp(!signUp)}
              >
                {signUp
                  ? "Already have an account? Sign in"
                  : "Create an account"}
              </button>
            )}
          </>
        )}
        <p className="hint spaced" role="status">
          {message}
        </p>
      </section>
    </>
  );
}
