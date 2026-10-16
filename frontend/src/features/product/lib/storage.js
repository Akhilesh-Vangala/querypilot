/** Opt-in IndexedDB storage. A failed transaction never reports a successful save. */
const DB = "querypilot-workspace-v1";
let connection;
function open() {
  if (connection) return Promise.resolve(connection);
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore("investigations", { keyPath: "id" });
      req.result.createObjectStore("projects", { keyPath: "id" });
    };
    req.onsuccess = () => {
      connection = req.result;
      connection.onversionchange = () => {
        connection.close();
        connection = undefined;
      };
      resolve(connection);
    };
    req.onerror = () =>
      reject(
        new Error(
          "Browser storage is unavailable. Export a backup to keep this work.",
        ),
      );
    req.onblocked = () =>
      reject(new Error("Close other QueryPilot tabs, then retry saving."));
  });
}
async function transaction(store, mode, action) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, mode),
      request = action(tx.objectStore(store));
    tx.oncomplete = () => resolve(request?.result);
    tx.onabort = tx.onerror = () =>
      reject(
        new Error(
          "This work could not be saved on this device. Export a backup and free browser storage before retrying.",
        ),
      );
  });
}
export const saved = {
  list: () => transaction("investigations", "readonly", (s) => s.getAll()),
  get: (id) => transaction("investigations", "readonly", (s) => s.get(id)),
  remove: (id) =>
    transaction("investigations", "readwrite", (s) => s.delete(id)),
  projects: () => transaction("projects", "readonly", (s) => s.getAll()),
  async project(value) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("projects", "readwrite"),
        store = tx.objectStore("projects"),
        count = store.count();
      let message =
        "Project could not be saved; existing projects are unchanged.";
      count.onsuccess = () => {
        if (count.result >= 20) {
          message =
            "This device already has 20 projects. Remove an unused project first.";
          tx.abort();
        } else store.add(structuredClone(value));
      };
      tx.oncomplete = resolve;
      tx.onerror = tx.onabort = () => reject(new Error(message));
    });
  },
  async put(value, consent) {
    if (!consent)
      throw new Error(
        "Choose a storage destination and confirm before saving.",
      );
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("investigations", "readwrite");
      const store = tx.objectStore("investigations");
      let reason =
        "This snapshot could not be saved. Existing saved work has not changed.";
      const count = store.count();
      count.onsuccess = () => {
        if (count.result >= 50) {
          reason =
            "This device already has 50 saved investigations. Export and remove older work first.";
          tx.abort();
        } else
          store.add({
            ...structuredClone(value),
            storage: "device",
            savedAt: new Date().toISOString(),
          });
      };
      tx.oncomplete = resolve;
      tx.onabort = tx.onerror = () => reject(new Error(reason));
    });
  },
  async removeProject(id) {
    const all = await this.list();
    if (all.some((r) => r.projectId === id))
      throw new Error("Move or delete this project’s investigations first.");
    return transaction("projects", "readwrite", (s) => s.delete(id));
  },
  async restore(entries, projects) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(["projects", "investigations"], "readwrite");
      const a = tx.objectStore("investigations"),
        b = tx.objectStore("projects");
      const countA = a.count(),
        countB = b.count();
      let ready = 0,
        reason =
          "The backup could not be restored. No partial import was saved.";
      const check = () => {
        if (++ready !== 2) return;
        if (
          countA.result + entries.length > 50 ||
          countB.result + projects.length > 20
        ) {
          reason =
            "Restoring this backup would exceed 50 device investigations or 20 projects. Export and remove older work first.";
          tx.abort();
          return;
        }
        projects.forEach((p) => b.add(p));
        entries.forEach((e) => a.add(e));
      };
      countA.onsuccess = countB.onsuccess = check;
      tx.oncomplete = resolve;
      tx.onabort = tx.onerror = () => reject(new Error(reason));
    });
  },
  async clear() {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(["projects", "investigations"], "readwrite");
      tx.objectStore("projects").clear();
      tx.objectStore("investigations").clear();
      tx.oncomplete = resolve;
      tx.onerror = tx.onabort = () =>
        reject(
          new Error(
            "Browser data could not be removed. Retry or use your browser’s site-data settings.",
          ),
        );
    });
  },
};
