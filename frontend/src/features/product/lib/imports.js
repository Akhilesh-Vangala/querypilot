/** One bounded tabular file import, with an explicit accessible worksheet choice. */
export const ACCEPT =
  ".csv,.tsv,.xlsx,.json,.jsonl,text/csv,text/tab-separated-values,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
export const FORMAT_HELP =
  "CSV, TSV, Excel (.xlsx), JSON or JSONL · Up to 400 KB";
function worksheet(sheets, signal) {
  return new Promise((resolve, reject) => {
    const dialog = document.createElement("dialog");
    dialog.setAttribute("aria-labelledby", "import-sheet-title");
    dialog.id = "import-sheet-dialog";
    const title = document.createElement("h2");
    title.id = "import-sheet-title";
    title.textContent = "Choose the worksheet to inspect";
    const detail = document.createElement("p");
    detail.className = "muted spaced";
    detail.textContent =
      "Import one visible table at a time. Sheets are never combined automatically.";
    const label = document.createElement("label");
    label.className = "field spaced";
    label.textContent = "Worksheet";
    const select = document.createElement("select");
    select.id = "import-sheet";
    for (const sheet of sheets) {
      const option = document.createElement("option");
      option.value = sheet;
      option.textContent = sheet;
      select.append(option);
    }
    label.append(select);
    const form = document.createElement("form");
    form.method = "dialog";
    const actions = document.createElement("div");
    actions.className = "dialog-actions spaced";
    const cancel = document.createElement("button");
    cancel.className = "secondary";
    cancel.value = "cancel";
    cancel.textContent = "Cancel import";
    const choose = document.createElement("button");
    choose.className = "primary";
    choose.value = "choose";
    choose.id = "confirm-sheet";
    choose.textContent = "Inspect worksheet";
    actions.append(cancel, choose);
    form.append(title, detail, label, actions);
    dialog.append(form);
    const active = document.activeElement;
    const abort = () => {
      dialog.close("cancel");
    };
    dialog.addEventListener(
      "close",
      () => {
        signal?.removeEventListener("abort", abort);
        const value = select.value,
          accepted = dialog.returnValue === "choose";
        dialog.remove();
        active?.focus?.();
        if (accepted) resolve(value);
        else reject(new DOMException("Import cancelled", "AbortError"));
      },
      { once: true },
    );
    (document.querySelector(".product-root") || document.body).append(dialog);
    if (signal?.aborted) {
      dialog.remove();
      reject(new DOMException("Import cancelled", "AbortError"));
      return;
    }
    signal?.addEventListener("abort", abort, { once: true });
    dialog.showModal();
    select.focus();
  });
}
export async function importFile(file, send, signal) {
  if (
    !/\.(csv|tsv|xlsx|json|jsonl)$/i.test(file.name) ||
    !file.size ||
    file.size > 400000
  )
    throw Error(
      "Choose a non-empty CSV, TSV, Excel .xlsx, JSON or JSONL file no larger than 400 KB.",
    );
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 32768)
    binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
  const body = {
    filename: file.name.slice(0, 160),
    content_base64: btoa(binary),
  };
  let result = await send(body);
  if (result.needs_sheet) {
    body.sheet = await worksheet(result.sheets, signal);
    result = await send(body);
  }
  if (result.needs_sheet || !result.csv || !result.profile)
    throw Error("File inspection could not complete; choose the file again.");
  return result;
}
