/* qAOP Editor (plain JS, no build step)
   - Fetches compiled form spec from GET /v1/form-spec/qaop
   - Renders all sections with field dispatch by value_type
   - Cross-entity KE reference dropdowns for KER fields
   - show_when conditional visibility
   - Help text rendering
*/

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let formSpec = null;   // compiled form spec from backend
let formData = {
  identity: {},
  structure: {
    _mie: { ke_id: null, title: "", biological_organization_level: "", role: "mie" },
    _key_events: [],
    _ao: { ke_id: null, title: "", biological_organization_level: "", role: "ao" },
    key_event_relationships: []
  },
  quantitative: {},
  applicability: {}
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function $(id) { return document.getElementById(id); }

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1600);
}

function setStatus(msg) { $("status").textContent = msg; }

function deepGet(obj, pathParts) {
  let cur = obj;
  for (const p of pathParts) {
    if (cur == null) return undefined;
    cur = cur[p];
  }
  return cur;
}

function deepSet(obj, pathParts, value) {
  let cur = obj;
  for (let i = 0; i < pathParts.length - 1; i++) {
    const p = pathParts[i];
    if (cur[p] == null) cur[p] = {};
    cur = cur[p];
  }
  cur[pathParts[pathParts.length - 1]] = value;
}

// Convert form-spec path like "/identity/title" to ["identity", "title"]
function pathToParts(path) {
  return path.replace(/^\//, "").split("/").filter(Boolean);
}

// ---------------------------------------------------------------------------
// Cross-entity KE reference options
// ---------------------------------------------------------------------------

function collectKEOptions() {
  const options = [];
  const mie = formData.structure?._mie;
  if (mie?.ke_id && mie?.title) {
    options.push({ value: mie.ke_id, label: "KE " + mie.ke_id + ": " + mie.title });
  }
  for (const ke of (formData.structure?._key_events || [])) {
    if (ke?.ke_id && ke?.title) {
      options.push({ value: ke.ke_id, label: "KE " + ke.ke_id + ": " + ke.title });
    }
  }
  const ao = formData.structure?._ao;
  if (ao?.ke_id && ao?.title) {
    options.push({ value: ao.ke_id, label: "KE " + ao.ke_id + ": " + ao.title });
  }
  return options;
}

// All ke_reference <select> elements, refreshed when KE data changes
const keSelectElements = [];

function refreshKEDropdowns() {
  const options = collectKEOptions();
  for (const { select, getCurrentValue } of keSelectElements) {
    const currentVal = getCurrentValue();
    select.innerHTML = "";
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = "-- Select KE --";
    select.appendChild(emptyOpt);
    for (const opt of options) {
      const o = document.createElement("option");
      o.value = opt.value;
      o.textContent = opt.label;
      select.appendChild(o);
    }
    if (currentVal != null) {
      select.value = String(currentVal);
    }
  }
}

// ---------------------------------------------------------------------------
// show_when conditional visibility
// ---------------------------------------------------------------------------

function shouldShowField(field, parentData) {
  if (!field.show_when) return true;
  const currentValue = parentData?.[field.show_when.field];
  return currentValue === field.show_when.equals;
}

// ---------------------------------------------------------------------------
// Field renderers
// ---------------------------------------------------------------------------

function createLabel(field) {
  const label = document.createElement("label");
  label.textContent = field.label || field.id;
  if (field.required) {
    const req = document.createElement("span");
    req.className = "req";
    req.textContent = "*";
    label.appendChild(req);
  }
  return label;
}

function createHelpText(field) {
  if (!field.help) return null;
  const small = document.createElement("small");
  small.className = "help-text";
  small.textContent = field.help;
  return small;
}

function renderStringField(field, value, onChange) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  wrap.appendChild(createLabel(field));

  const input = document.createElement("input");
  input.type = "text";
  input.value = value ?? "";
  input.addEventListener("change", () => onChange(input.value));
  wrap.appendChild(input);

  const help = createHelpText(field);
  if (help) wrap.appendChild(help);
  return wrap;
}

function renderNumberField(field, value, onChange) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  wrap.appendChild(createLabel(field));

  const input = document.createElement("input");
  input.type = "number";
  input.value = value != null ? value : "";
  input.addEventListener("change", () => {
    const v = input.value.trim();
    onChange(v === "" ? null : Number(v));
  });
  wrap.appendChild(input);

  const help = createHelpText(field);
  if (help) wrap.appendChild(help);
  return wrap;
}

function renderTextField(field, value, onChange) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  wrap.appendChild(createLabel(field));

  const textarea = document.createElement("textarea");
  textarea.value = value ?? "";
  textarea.addEventListener("change", () => onChange(textarea.value));
  wrap.appendChild(textarea);

  const help = createHelpText(field);
  if (help) wrap.appendChild(help);
  return wrap;
}

function renderControlledTermField(field, value, onChange) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  wrap.appendChild(createLabel(field));

  const select = document.createElement("select");
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "";
  select.appendChild(emptyOpt);
  for (const v of (field.allowed_values || [])) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    select.appendChild(opt);
  }
  select.value = value ?? "";
  select.addEventListener("change", () => onChange(select.value || null));
  wrap.appendChild(select);

  const help = createHelpText(field);
  if (help) wrap.appendChild(help);
  return wrap;
}

function renderKeReferenceField(field, value, onChange) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  wrap.appendChild(createLabel(field));

  const select = document.createElement("select");
  const options = collectKEOptions();
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "-- Select KE --";
  select.appendChild(emptyOpt);
  for (const opt of options) {
    const o = document.createElement("option");
    o.value = opt.value;
    o.textContent = opt.label;
    select.appendChild(o);
  }
  if (value != null) select.value = String(value);

  select.addEventListener("change", () => {
    const val = select.value ? parseInt(select.value, 10) : null;
    onChange(val);
  });
  wrap.appendChild(select);

  // Track for refresh
  keSelectElements.push({
    select,
    getCurrentValue: () => value
  });

  const help = createHelpText(field);
  if (help) wrap.appendChild(help);
  return wrap;
}

// ---------------------------------------------------------------------------
// Dispatch field rendering
// ---------------------------------------------------------------------------

function renderField(field, dataObj, dataKey, onDataChange, parentData) {
  // Check show_when
  if (!shouldShowField(field, parentData)) return null;

  const value = dataObj?.[dataKey];

  function onChange(newVal) {
    dataObj[dataKey] = newVal;
    onDataChange();
  }

  switch (field.value_type) {
    case "string":
      return renderStringField(field, value, onChange);
    case "number":
      return renderNumberField(field, value, onChange);
    case "text":
      return renderTextField(field, value, onChange);
    case "controlled_term":
      return renderControlledTermField(field, value, onChange);
    case "ke_reference":
      return renderKeReferenceField(field, value, onChange);
    case "object":
      if (field.cardinality === "many") {
        return renderRepeatableGroup(field, dataObj, dataKey, onDataChange);
      } else {
        return renderNestedObject(field, dataObj, dataKey, onDataChange);
      }
    default:
      return renderStringField(field, value, onChange);
  }
}

// ---------------------------------------------------------------------------
// Nested object (cardinality: one)
// ---------------------------------------------------------------------------

function renderNestedObject(field, dataObj, dataKey, onDataChange) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  wrap.appendChild(createLabel(field));

  const help = createHelpText(field);
  if (help) wrap.appendChild(help);

  const inner = document.createElement("div");
  inner.className = "group";
  inner.style.marginTop = "8px";

  if (!dataObj[dataKey]) dataObj[dataKey] = {};
  const objData = dataObj[dataKey];

  for (const childField of (field.fields || [])) {
    const el = renderField(childField, objData, childField.id, onDataChange, objData);
    if (el) inner.appendChild(el);
  }

  wrap.appendChild(inner);
  return wrap;
}

// ---------------------------------------------------------------------------
// Repeatable group (cardinality: many)
// ---------------------------------------------------------------------------

function renderRepeatableGroup(field, dataObj, dataKey, onDataChange) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  wrap.appendChild(createLabel(field));

  const help = createHelpText(field);
  if (help) wrap.appendChild(help);

  const group = document.createElement("div");
  group.className = "group";
  group.style.marginTop = "8px";

  if (!Array.isArray(dataObj[dataKey])) dataObj[dataKey] = [];
  const arr = dataObj[dataKey];

  function rerender() {
    // Clear ke selects that belong to this group
    group.innerHTML = "";
    renderItems();
    refreshKEDropdowns();
  }

  function renderItems() {
    for (let i = 0; i < arr.length; i++) {
      const item = document.createElement("div");
      item.className = "group-item";

      const toolbar = document.createElement("div");
      toolbar.className = "toolbar";

      const title = document.createElement("div");
      title.className = "title";
      title.textContent = (field.label || field.id) + " [" + (i + 1) + "]";
      toolbar.appendChild(title);

      const delBtn = document.createElement("button");
      delBtn.className = "smallbtn red";
      delBtn.textContent = "Remove";
      delBtn.addEventListener("click", () => {
        arr.splice(i, 1);
        rerenderAll();
      });
      toolbar.appendChild(delBtn);
      item.appendChild(toolbar);

      const inner = document.createElement("div");
      inner.className = "fields";

      for (const childField of (field.fields || [])) {
        const el = renderField(childField, arr[i], childField.id, () => {
          onDataChange();
          // Re-render if this is a KE-related field (refreshes dropdowns)
          if (childField.id === "ke_id" || childField.id === "title") {
            refreshKEDropdowns();
          }
          // Re-render KER group for show_when re-evaluation
          if (dataKey === "key_event_relationships" && childField.id === "function_type") {
            rerenderAll();
          }
        }, arr[i]);
        if (el) inner.appendChild(el);
      }

      item.appendChild(inner);
      group.appendChild(item);
    }

    // Add button
    const addBtn = document.createElement("button");
    addBtn.className = "smallbtn gray";
    addBtn.textContent = "Add " + (field.label || field.id);
    addBtn.style.marginTop = "8px";
    addBtn.addEventListener("click", () => {
      const empty = buildEmptyItem(field.fields || []);
      // Auto-set role for KE items
      if (dataKey === "_key_events") {
        empty.role = "ke";
      }
      arr.push(empty);
      rerenderAll();
    });
    group.appendChild(addBtn);
  }

  renderItems();
  wrap.appendChild(group);
  return wrap;
}

function buildEmptyItem(fields) {
  const obj = {};
  for (const f of fields) {
    if (f.value_type === "object") {
      obj[f.id] = f.cardinality === "many" ? [] : {};
    } else if (f.value_type === "number") {
      obj[f.id] = null;
    } else {
      obj[f.id] = "";
    }
  }
  return obj;
}

// ---------------------------------------------------------------------------
// Section rendering
// ---------------------------------------------------------------------------

function getSectionClass(sectionId, fieldId) {
  if (fieldId === "mie") return "mie-section";
  if (fieldId === "ao") return "ao-section";
  if (fieldId === "key_events") return "ke-section";
  if (fieldId === "key_event_relationships") return "ker-section";
  return "";
}

function renderStructureSection(section) {
  const container = document.createElement("div");

  // For structure, render each top-level field as its own card
  for (const field of (section.fields || [])) {
    const card = document.createElement("div");
    const extraClass = getSectionClass(section.id, field.id);
    card.className = "card" + (extraClass ? " " + extraClass : "");

    const h2 = document.createElement("h2");
    h2.textContent = field.label || field.id;
    card.appendChild(h2);

    if (field.help) {
      const desc = document.createElement("div");
      desc.className = "desc";
      desc.textContent = field.help;
      card.appendChild(desc);
    }

    const fieldsWrap = document.createElement("div");
    fieldsWrap.className = "fields";

    // Determine the data key in formData.structure
    const dataKey = field.id === "mie" ? "_mie"
                  : field.id === "key_events" ? "_key_events"
                  : field.id === "ao" ? "_ao"
                  : field.id;

    if (field.cardinality === "many") {
      // Repeatable (KEs, KERs)
      const el = renderRepeatableGroup(field, formData.structure, dataKey, () => {});
      if (el) fieldsWrap.appendChild(el);
    } else if (field.value_type === "object") {
      // Single object (MIE, AO)
      if (!formData.structure[dataKey]) {
        formData.structure[dataKey] = {};
      }
      const objData = formData.structure[dataKey];
      // Auto-set role
      if (field.id === "mie") objData.role = "mie";
      if (field.id === "ao") objData.role = "ao";

      for (const childField of (field.fields || [])) {
        // Skip role field - it's locked
        if (childField.id === "role") continue;
        const el = renderField(childField, objData, childField.id, () => {
          if (childField.id === "ke_id" || childField.id === "title") {
            refreshKEDropdowns();
          }
        }, objData);
        if (el) fieldsWrap.appendChild(el);
      }
    }

    card.appendChild(fieldsWrap);
    container.appendChild(card);
  }

  return container;
}

function renderGenericSection(section) {
  const card = document.createElement("div");
  card.className = "card";

  const h2 = document.createElement("h2");
  h2.textContent = section.title || section.id;
  card.appendChild(h2);

  if (section.description) {
    const desc = document.createElement("div");
    desc.className = "desc";
    desc.textContent = section.description;
    card.appendChild(desc);
  }

  const fieldsWrap = document.createElement("div");
  fieldsWrap.className = "fields";

  // Ensure section data exists
  if (!formData[section.id]) formData[section.id] = {};
  const sectionData = formData[section.id];

  for (const field of (section.fields || [])) {
    const el = renderField(field, sectionData, field.id, () => {}, sectionData);
    if (el) fieldsWrap.appendChild(el);
  }

  card.appendChild(fieldsWrap);
  return card;
}

// ---------------------------------------------------------------------------
// Full form render
// ---------------------------------------------------------------------------

let rerenderAll;

function renderForm() {
  const root = $("formRoot");
  root.innerHTML = "";
  keSelectElements.length = 0;

  if (!formSpec || !Array.isArray(formSpec.sections)) {
    root.textContent = "No form spec loaded.";
    return;
  }

  for (const section of formSpec.sections) {
    if (section.id === "structure") {
      root.appendChild(renderStructureSection(section));
    } else {
      root.appendChild(renderGenericSection(section));
    }
  }

  // Populate KE dropdowns after full render
  refreshKEDropdowns();
}

rerenderAll = function() {
  renderForm();
};

// ---------------------------------------------------------------------------
// Show JSON
// ---------------------------------------------------------------------------

function showJson() {
  const card = $("jsonCard");
  const pre = $("jsonOutput");
  if (card.style.display === "none") {
    card.style.display = "";
    pre.textContent = JSON.stringify(formData, null, 2);
  } else {
    card.style.display = "none";
  }
}

// ---------------------------------------------------------------------------
// Load form spec and initialize
// ---------------------------------------------------------------------------

async function loadFormSpec() {
  const resp = await fetch("/v1/form-spec/qaop");
  if (!resp.ok) throw new Error("Failed to load form spec: " + resp.status);
  return resp.json();
}

async function init() {
  try {
    setStatus("Loading form spec...");
    formSpec = await loadFormSpec();
    renderForm();
    setStatus("Ready");
    toast("qAOP form loaded");
  } catch (e) {
    setStatus("Error: " + e.message);
    $("formRoot").textContent = "Failed to load form spec. Ensure the server is running and /v1/form-spec/qaop is available.";
  }
}

// Wire up
$("btnShowJson").addEventListener("click", () => {
  showJson();
});

init();
