/* PBPK form UI renderer v1 (plain JS)
   - Renders from POST /v1/form-ui/pbpk
   - Saves via:
     POST /v1/drafts/{id}/apply-edits
     POST /v1/drafts/{id}/apply-array
*/

const API = {
  drafts: "/v1/drafts",
  formUI: "/v1/form-ui/pbpk",
  validateDraft: (id) => `/v1/drafts/${id}/validate`,
  buildDraft: (id) => `/v1/drafts/${id}/build`,
  applyEdits: (id) => `/v1/drafts/${id}/apply-edits`,
  applyArray: (id) => `/v1/drafts/${id}/apply-array`,
  crateDownload: (crateId) => `/v1/rocrate/${crateId}/download`,
};

let state = {
  draftId: null,
  crateId: null,
  lastSaved: null,
  formUI: null,
};

function $(id) { return document.getElementById(id); }

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1600);
}

function setStatus(msg) {
  $("status").textContent = msg;
}

async function httpJson(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    method: opts.method || "GET",
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText}: ${text}`);
  }
  if (!text) return null;
  return JSON.parse(text);
}

function updateHeader() {
  $("draftId").textContent = state.draftId || "—";
  $("lastSaved").textContent = state.lastSaved || "—";
  $("btnRefreshUI").disabled = !state.draftId;
  $("btnDownload").disabled = !state.crateId;
}

function pointerReplaceStar(path, index) {
  // convert "/section/arr/*/field" -> "/section/arr/<index>/field"
  return path.replace("/*/", `/${index}/`);
}

function renderScalarField(field, value, onSave) {
  const wrap = document.createElement("div");
  wrap.className = "field";

  const label = document.createElement("label");
  label.textContent = field.label || field.id || field.path;
  if (field.required) {
    const req = document.createElement("span");
    req.className = "req";
    req.textContent = "*";
    label.appendChild(req);
  }
  wrap.appendChild(label);

  let input;

  const vt = field.value_type;
  const allowed = field.allowed_values || null;

  if (vt === "text") {
    input = document.createElement("textarea");
    input.value = (value ?? "");
  } else if (vt === "controlled_term" && Array.isArray(allowed) && allowed.length > 0) {
    // single select
    input = document.createElement("select");
    const optEmpty = document.createElement("option");
    optEmpty.value = "";
    optEmpty.textContent = "";
    input.appendChild(optEmpty);
    for (const v of allowed) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      input.appendChild(opt);
    }
    input.value = (value ?? "");
  } else {
    input = document.createElement("input");
    input.type = "text";
    input.value = (value ?? "");
  }

  input.addEventListener("change", async () => {
    await onSave(input.value);
  });

  wrap.appendChild(input);

  const hint = document.createElement("p");
  hint.className = "hint";
  hint.innerHTML = `<span class="mono">${field.path}</span>`;
  wrap.appendChild(hint);

  return wrap;
}

function renderArrayOfScalars(field, valueArr, onSave) {
  const wrap = document.createElement("div");
  wrap.className = "field";

  const label = document.createElement("label");
  label.textContent = field.label || field.id || field.path;
  if (field.required) {
    const req = document.createElement("span");
    req.className = "req";
    req.textContent = "*";
    label.appendChild(req);
  }
  wrap.appendChild(label);

  const allowed = field.allowed_values || null;

  if (Array.isArray(allowed) && allowed.length > 0) {
    // multi-select
    const sel = document.createElement("select");
    sel.multiple = true;
    for (const v of allowed) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    }
    const cur = Array.isArray(valueArr) ? valueArr : [];
    for (const opt of sel.options) {
      opt.selected = cur.includes(opt.value);
    }
    sel.addEventListener("change", async () => {
      const out = Array.from(sel.selectedOptions).map(o => o.value);
      await onSave(out);
    });
    wrap.appendChild(sel);
  } else {
    // fallback: comma-separated input
    const inp = document.createElement("input");
    inp.type = "text";
    inp.value = Array.isArray(valueArr) ? valueArr.join(", ") : "";
    inp.addEventListener("change", async () => {
      const out = inp.value.split(",").map(s => s.trim()).filter(Boolean);
      await onSave(out);
    });
    wrap.appendChild(inp);
    const hint2 = document.createElement("p");
    hint2.className = "hint";
    hint2.textContent = "Enter comma-separated values.";
    wrap.appendChild(hint2);
  }

  const hint = document.createElement("p");
  hint.className = "hint";
  hint.innerHTML = `<span class="mono">${field.path}</span>`;
  wrap.appendChild(hint);

  return wrap;
}

function buildEmptyObjectFromFields(fields) {
  const obj = {};
  for (const f of fields || []) {
    if (!f || !f.id) continue;
    if (f.value_type === "object") {
      obj[f.id] = (f.cardinality === "many") ? [] : {};
    } else if (f.cardinality === "many") {
      obj[f.id] = [];
    } else {
      obj[f.id] = "";
    }
  }
  return obj;
}

function renderGroupField(sectionId, field, items, onAppend, onRemoveIndex, onSaveNested) {
  const wrap = document.createElement("div");
  wrap.className = "field";

  const label = document.createElement("label");
  label.textContent = field.label || field.id || field.path;
  if (field.required) {
    const req = document.createElement("span");
    req.className = "req";
    req.textContent = "*";
    label.appendChild(req);
  }
  wrap.appendChild(label);

  const group = document.createElement("div");
  group.className = "group";

  const toolbar = document.createElement("div");
  toolbar.className = "row";
  const addBtn = document.createElement("button");
  addBtn.className = "smallbtn gray";
  addBtn.textContent = "Add item";
  addBtn.addEventListener("click", async () => { await onAppend(); });

  toolbar.appendChild(addBtn);

  const badge = document.createElement("span");
  badge.className = "pill";
  badge.textContent = `many`;
  toolbar.appendChild(badge);

  group.appendChild(toolbar);

  const cur = Array.isArray(items) ? items : [];
  cur.forEach((obj, idx) => {
    const item = document.createElement("div");
    item.className = "group-item";

    const itBar = document.createElement("div");
    itBar.className = "toolbar";

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = `${field.id} [${idx}]`;
    itBar.appendChild(title);

    const delBtn = document.createElement("button");
    delBtn.className = "smallbtn red";
    delBtn.textContent = "Remove";
    delBtn.addEventListener("click", async () => {
      await onRemoveIndex(idx);
    });
    itBar.appendChild(delBtn);

    item.appendChild(itBar);

    // render nested fields
    const inner = document.createElement("div");
    inner.className = "fields";

    for (const nf of (field.fields || [])) {
      // nf.path includes wildcard; replace with index
      const concretePath = pointerReplaceStar(nf.path, idx);
      const v = (obj && typeof obj === "object") ? obj[nf.id] : undefined;

      // nested arrays-of-scalars
      if (nf.cardinality === "many" && nf.value_type !== "object") {
        inner.appendChild(
          renderArrayOfScalars(nf, v, async (newVal) => {
            await onSaveNested(concretePath, newVal);
          })
        );
        continue;
      }

      inner.appendChild(
        renderScalarField(nf, v, async (newVal) => {
          await onSaveNested(concretePath, newVal);
        })
      );
    }

    item.appendChild(inner);
    group.appendChild(item);
  });

  wrap.appendChild(group);

  const hint = document.createElement("p");
  hint.className = "hint";
  hint.innerHTML = `<span class="mono">${field.path}</span>`;
  wrap.appendChild(hint);

  return wrap;
}

async function refreshFormUI() {
  if (!state.draftId) return;
  setStatus("Loading form UI…");
  const out = await httpJson(API.formUI, { method: "POST", body: { draft_id: state.draftId, include_helptexts: false, include_vocabularies: true } });
  state.formUI = out;
  renderForm(out);
  setStatus("Ready");
}

function renderForm(formUI) {
  const root = $("formRoot");
  root.innerHTML = "";

  if (!formUI || !Array.isArray(formUI.sections)) {
    root.textContent = "No form UI available.";
    return;
  }

  for (const section of formUI.sections) {
    const card = document.createElement("div");
    card.className = "card";

    const h2 = document.createElement("h2");
    h2.textContent = section.title || section.id;
    card.appendChild(h2);

    const desc = document.createElement("div");
    desc.className = "desc";
    desc.textContent = section.description || "";
    card.appendChild(desc);

    const fieldsWrap = document.createElement("div");
    fieldsWrap.className = "fields";

    for (const f of (section.fields || [])) {
      // group / object many
      if (f.widget === "group" && f.cardinality === "many") {
        const arrayPath = f.path; // like "/biological_system_description/biological_systems"
        const items = f.value || [];

        fieldsWrap.appendChild(
          renderGroupField(
            section.id,
            f,
            items,
            async () => {
              const empty = buildEmptyObjectFromFields(f.fields || []);
              await applyArray(arrayPath, "append", empty);
              await refreshFormUI();
            },
            async (index) => {
              await applyArray(arrayPath, "remove_index", null, index);
              await refreshFormUI();
            },
            async (concretePath, val) => {
              await applyEdits({ [concretePath]: val });
              await refreshFormUI();
            }
          )
        );
        continue;
      }

      // arrays of scalars
      if (f.cardinality === "many" && f.value_type !== "object") {
        fieldsWrap.appendChild(
          renderArrayOfScalars(f, f.value, async (newVal) => {
            await applyEdits({ [f.path]: newVal });
            await refreshFormUI();
          })
        );
        continue;
      }

      // scalar
      fieldsWrap.appendChild(
        renderScalarField(f, f.value, async (newVal) => {
          await applyEdits({ [f.path]: newVal });
          await refreshFormUI();
        })
      );
    }

    card.appendChild(fieldsWrap);
    root.appendChild(card);
  }
}

async function applyEdits(edits) {
  if (!state.draftId) throw new Error("No draft");
  setStatus("Saving…");
  const out = await httpJson(API.applyEdits(state.draftId), { method: "POST", body: { edits } });
  // out.kind: pbpk.draft.apply_result
  state.lastSaved = new Date().toISOString();
  updateHeader();
  toast("Saved");
  setStatus("Ready");
  return out;
}

async function applyArray(array_path, action, value = null, index = null) {
  if (!state.draftId) throw new Error("No draft");
  setStatus("Saving array…");
  const body = { array_path, action };
  if (value !== null) body.value = value;
  if (index !== null) body.index = index;
  const out = await httpJson(API.applyArray(state.draftId), { method: "POST", body });
  state.lastSaved = new Date().toISOString();
  updateHeader();
  toast("Saved");
  setStatus("Ready");
  return out;
}

async function createDraftFromTextarea(replaceExisting = false) {
  const txt = $("metadataJson").value.trim();
  if (!txt) throw new Error("Metadata JSON is empty");
  let md;
  try { md = JSON.parse(txt); } catch (e) { throw new Error(`Invalid JSON: ${e}`); }

  setStatus("Creating draft…");
  const out = await httpJson(API.drafts, { method: "POST", body: md });
  state.draftId = out.draft_id;
  state.crateId = null;
  state.lastSaved = out.audit?.updated_at || new Date().toISOString();
  updateHeader();
  toast(`Draft created: ${state.draftId}`);
  setStatus("Ready");

  await refreshFormUI();
}

async function validateDraft() {
  if (!state.draftId) throw new Error("No draft");
  setStatus("Validating…");
  const out = await httpJson(API.validateDraft(state.draftId), { method: "POST" });

  const card = $("validationCard");
  card.style.display = "block";
  const ok = !!out.validation?.ok;
  const w = out.validation?.warnings || [];
  const e = out.validation?.errors || [];
  $("validationSummary").textContent = ok
    ? `OK (warnings: ${w.length}, errors: ${e.length})`
    : `FAILED (warnings: ${w.length}, errors: ${e.length})`;

  $("validationDetails").textContent = JSON.stringify(out.validation, null, 2);
  state.lastSaved = out.audit?.updated_at || state.lastSaved;
  updateHeader();
  toast(ok ? "Validation OK" : "Validation failed");
  setStatus("Ready");
}

async function buildDraft() {
  if (!state.draftId) throw new Error("No draft");
  setStatus("Building RO-Crate…");
  const out = await httpJson(API.buildDraft(state.draftId), { method: "POST" });

  $("buildOut").textContent = JSON.stringify(out, null, 2);
  state.crateId = out.build?.crate_id || null;
  updateHeader();
  toast(state.crateId ? `Built: ${state.crateId}` : "Built (no crate_id?)");
  setStatus("Ready");
}

async function downloadCrate() {
  if (!state.crateId) return;
  window.location.href = API.crateDownload(state.crateId);
}

async function loadExample() {
  // Uses your existing example file path in repo; served by backend UI route (see ui.py below)
  setStatus("Loading example…");
  const res = await fetch("/ui/example/pbpk-metadata.json");
  const txt = await res.text();
  $("metadataJson").value = txt;
  toast("Example loaded");
  setStatus("Ready");
}

function wire() {
  $("btnLoadExample").addEventListener("click", () => loadExample().catch(e => toast(e.message)));
  $("btnCreateDraft").addEventListener("click", () => createDraftFromTextarea().catch(e => toast(e.message)));
  $("btnRefreshUI").addEventListener("click", () => refreshFormUI().catch(e => toast(e.message)));
  $("btnValidate").addEventListener("click", () => validateDraft().catch(e => toast(e.message)));
  $("btnBuild").addEventListener("click", () => buildDraft().catch(e => toast(e.message)));
  $("btnDownload").addEventListener("click", () => downloadCrate());

  updateHeader();
  $("buildOut").textContent = "";
  setStatus("Ready");
}

wire();