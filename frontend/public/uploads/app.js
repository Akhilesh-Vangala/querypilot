"use strict";
const $ = (id) => document.getElementById(id);
let config, source = "", report, controller, generation = 0;
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}
function table(headers, rows) {
  const element = node("table"), head = node("thead"), header = node("tr"), body = node("tbody");
  headers.forEach((h) => header.append(node("th", h))); head.append(header); element.append(head);
  rows.forEach((row) => { const tr = node("tr"); row.forEach((v) => tr.append(node("td", v))); body.append(tr); });
  element.append(body); return element;
}
function message(text = "") { $("error").textContent = text; $("error").hidden = !text; }
function invalidate() { report = undefined; $("output").hidden = true; $("consent").checked = false; $("approve").disabled = true; }
function busy(value, text = "") {
  $("status").textContent = text;
  document.querySelectorAll("#file, #form input, #form select, #analyze").forEach((el) => { el.disabled = value || !config; });
  $("consent").disabled = value;
  $("approve").disabled = value || !$("consent").checked;
}
async function api(path, body) {
  controller = new AbortController();
  const response = await fetch("/api/uploads/" + path, { method: body ? "POST" : "GET", credentials: "same-origin", signal: controller.signal,
    headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
  const result = await response.json();
  if (!response.ok) throw Error(typeof result.detail === "string" ? result.detail : "The file or contract is invalid. Review the selected columns and values.");
  return result;
}
function payload() {
  const mapping = {}, options = {};
  document.querySelectorAll("[data-mapping]").forEach((el) => { if (el.value) mapping[el.dataset.mapping] = el.value; });
  document.querySelectorAll("[data-option]").forEach((el) => { if (el.value) options[el.dataset.option] = el.value; });
  return { csv: source, mapping, options };
}
function mapping(profile) {
  $("mapping").replaceChildren(); $("options").replaceChildren();
  config.fields.forEach(([key, title, required]) => {
    const label = node("label", title + (required ? " *" : "")), select = node("select");
    select.dataset.mapping = key; select.required = required;
    const empty = node("option", required ? "Choose a column…" : "None"); empty.value = ""; select.append(empty);
    profile.columns.forEach((column) => { const option = node("option", column.name); option.value = column.id; select.append(option); });
    const suggestion = profile.columns.find((c) => (config.suggest[key] || []).includes(c.name.toLowerCase().trim()));
    if (suggestion) select.value = suggestion.id;
    select.addEventListener("change", invalidate); label.append(select); $("mapping").append(label);
  });
  config.options.forEach(([key, title, choices]) => {
    const label = node("label", title), field = node(choices ? "select" : "input"); field.dataset.option = key;
    if (choices) choices.forEach((value) => { const option = node("option", value); option.value = value; field.append(option); });
    else { field.maxLength = 120; field.type = "text"; }
    if (key === "eligible_status" && document.querySelector('[data-mapping="status"]').value) field.value = "completed";
    field.addEventListener("input", invalidate); label.append(field); $("options").append(label);
  });
  $("contract").hidden = false;
}
function show(result) {
  report = result; $("output").hidden = false; $("summary").replaceChildren();
  Object.entries(result.summary).forEach(([key, value]) => { if (value === null) return;
    const card = node("div", undefined, "stat"); card.append(node("span", key.replaceAll("_", " ")), node("strong", value)); $("summary").append(card); });
  $("verification").textContent = Object.values(result.checks).every(Boolean) ? "Independent checks passed" : "Results withheld";
  $("scope").textContent = result.scope; $("results").replaceChildren();
  if (config.project === "RelayOps") {
    $("results").append(table(["Order", "Outcome", "Proposed actions", "Checks"], result.results.map((r) => [r.order_id, r.plan.outcome.replaceAll("_", " "), r.plan.actions.map((a) => `${a.kind}: ${a.amount}`).join(" · ") || "No changes", r.passed ? "Passed" : "Failed"])));
  } else {
    const headers = config.project === "VerifyOps" ? ["Segment", "Verified total", "Integer cents"] : ["Segment", "Value", "Records"];
    $("results").append(table(headers, result.results.map((r) => config.project === "VerifyOps" ? [r.segment, r.total, r.total_cents] : [r.segment, r.value, r.records])));
  }
  $("approval").hidden = config.project !== "RelayOps" || result.summary.approved_export || !result.summary.resolvable;
  $("consent").checked = false; $("approve").disabled = true;
  if (config.project === "RelayOps" && !config.approval_available) { $("approval").hidden = true; message("Approval signing is unavailable. You can inspect and download the proposed plan."); }
  $("download-csv").disabled = !result.csv;
  $("evidence").replaceChildren();
  const { csv, review, ...evidence } = result;
  if (result.sql) $("evidence").append(node("pre", result.sql));
  $("evidence").append(node("pre", JSON.stringify(evidence, null, 2)));
  $("output").scrollIntoView({ behavior: "smooth", block: "start" });
}
function download(text, extension, type) {
  const url = URL.createObjectURL(new Blob([text], { type })), anchor = node("a");
  anchor.href = url; anchor.download = config.project.toLowerCase() + "-results." + extension;
  document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("file").addEventListener("change", async () => {
  const epoch = ++generation; controller?.abort(); invalidate(); message(); $("profile").replaceChildren(); $("contract").hidden = true; source = ""; $("file-info").textContent = "";
  const file = $("file").files[0]; if (!file) return;
  try {
    if (!file.name.toLowerCase().endsWith(".csv") || file.size > config.max_csv_bytes) throw Error("Choose a UTF-8 .csv file of at most 400 KB.");
    busy(true, "Inspecting your file…");
    const text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(await file.arrayBuffer());
    if (epoch !== generation) return;
    const profile = await api("profile", { csv: text }); if (epoch !== generation) return;
    source = text; $("file-info").textContent = `${file.name} · ${profile.rows} rows · SHA-256 ${profile.sha256}`;
    $("profile").append(table(["Column", "Missing values", "Preview (first 3 rows)"], profile.columns.map((c) => [c.name, c.missing, c.samples.join(" · ")])));
    mapping(profile);
  } catch (error) { if (error.name !== "AbortError" && epoch === generation) message(error.message); }
  finally { if (epoch === generation) busy(false); }
});
$("form").addEventListener("submit", async (event) => {
  event.preventDefault(); const epoch = generation; message(); invalidate();
  try { busy(true, "Processing your data and reconciling independent checks…"); const result = await api("analyze", payload()); if (epoch === generation) show(result); }
  catch (error) { if (error.name !== "AbortError" && epoch === generation) message(error.message); }
  finally { if (epoch === generation) busy(false); }
});
$("consent").addEventListener("change", () => { $("approve").disabled = !$("consent").checked; });
$("approve").addEventListener("click", async () => {
  if (!report?.review || !$("consent").checked) return; const epoch = generation; const review = report.review; message();
  try { busy(true, "Rechecking the exact reviewed source and generating verified updates…"); const result = await api("approve", { ...payload(), review }); if (epoch === generation) show(result); }
  catch (error) { if (error.name !== "AbortError" && epoch === generation) message(error.message); }
  finally { if (epoch === generation) busy(false); }
});
$("clear").addEventListener("click", () => { ++generation; controller?.abort(); source = ""; invalidate(); message(); busy(false); $("file").value = ""; $("file-info").textContent = ""; $("profile").replaceChildren(); $("contract").hidden = true; $("mapping").replaceChildren(); $("options").replaceChildren(); $("results").replaceChildren(); $("evidence").replaceChildren(); $("summary").replaceChildren(); $("scope").textContent = ""; $("verification").textContent = ""; });
$("download-json").addEventListener("click", () => { if (report) { const { csv, review, ...evidence } = report; download(JSON.stringify(evidence, null, 2), "json", "application/json"); } });
$("download-csv").addEventListener("click", () => { if (report?.csv) download(report.csv, "csv", "text/csv;charset=utf-8"); });
api("capabilities").then((value) => {
  config = value; document.title = `${config.project} · Your data`;
  $("brand").textContent = config.project; $("title").textContent = config.title; $("description").textContent = config.description;
  busy(false); $("notice").textContent = config.notice; $("retention").textContent = config.retention; $("row-limit").textContent = config.max_rows.toLocaleString();
}).catch((error) => message("Workspace unavailable: " + error.message));
