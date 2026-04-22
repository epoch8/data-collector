/**
 * Визуальный редактор конфига: поля и flow.
 * Полный пересбор таблицы/карточек только при структурных изменениях — иначе не теряется фокус ввода.
 */
(function () {
  "use strict";

  /** value → подпись в селекте (в JSON уходит только value). */
  const FIELD_TYPES = [
    { v: "text_input", label: "text_input — однострочный текст" },
    { v: "datetime", label: "datetime — дата и время" },
    { v: "instruction", label: "instruction — экран подсказки (без ввода)" },
    { v: "camera_photo", label: "camera_photo — снимок с камеры" },
  ];
  const SCREENS = [
    { v: "form", label: "Форма" },
    { v: "instruction", label: "Инструкция (экран текста)" },
    { v: "camera_pose", label: "Камера / ракурс" },
    { v: "review", label: "Проверка перед отправкой" },
    { v: "scroll_form", label: "Одна длинная форма (все поля)" },
  ];

  function getCookie(name) {
    const v = document.cookie.match("(^|;) ?" + name + "=([^;]*)(;|$)");
    return v ? decodeURIComponent(v[2]) : null;
  }

  /** Путь на диске сервера (relative_path) → значение для JSON (Flutter: `assets/` → URL API). */
  function assetsPathForUploadedRel(rel) {
    const r = String(rel || "")
      .trim()
      .replace(/^\/+/, "")
      .replace(/\\/g, "/");
    if (!r) return "";
    if (r.startsWith("assets/")) return r;
    return "assets/" + r;
  }

  function normalizePathKey(s) {
    return String(s || "")
      .trim()
      .replace(/^\/+/, "")
      .replace(/\\/g, "/");
  }

  function formatBytes(n) {
    const x = Number(n);
    if (!Number.isFinite(x) || x < 0) return "";
    if (x < 1024) return `${x} B`;
    if (x < 1024 * 1024) return `${(x / 1024).toFixed(1)} KB`;
    return `${(x / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function fetchMediaFileList(listUrl) {
    const res = await fetch(listUrl, { credentials: "same-origin" });
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      /* ignore */
    }
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    if (!Array.isArray(data.files)) return [];
    return data.files;
  }

  /** Сопоставить значение из JSON с `asset_path` из списка медиа (в т.ч. путь без префикса `assets/`). */
  function resolveExampleAssetToListValue(files, raw) {
    const cur = normalizePathKey(raw);
    if (!cur) return "";
    if (/^https?:\/\//i.test(cur)) return cur;
    for (const f of files) {
      const rel = normalizePathKey(f.relative_path || "");
      if (!rel) continue;
      const ap = normalizePathKey(f.asset_path || assetsPathForUploadedRel(rel));
      if (cur === ap || cur === rel) return ap;
      const noAssets = cur.replace(/^assets\//i, "");
      if (noAssets === rel) return ap;
    }
    return cur;
  }

  function fillPoseCardAssetSelect(card, files, currentValue) {
    const sel = card.querySelector("[data-pc-asset-select]");
    if (!sel) return;
    const current = normalizePathKey(currentValue);
    const makeAp = (f) => normalizePathKey(f.asset_path || assetsPathForUploadedRel(f.relative_path));
    const known = new Set();
    const addOpt = (val, label) => {
      const o = document.createElement("option");
      o.value = val;
      o.textContent = label;
      sel.appendChild(o);
      if (val) known.add(normalizePathKey(val));
    };
    sel.textContent = "";
    addOpt("", "— без картинки —");
    for (const f of files) {
      const rel = normalizePathKey(f.relative_path || "");
      if (!rel) continue;
      const ap = makeAp(f);
      const sz = formatBytes(f.size);
      addOpt(ap, rel + (sz ? ` (${sz})` : ""));
    }
    if (current && !known.has(current)) {
      const lab = current.length > 72 ? `${current.slice(0, 69)}…` : current;
      addOpt(current, `${lab} (нет в медиа проекта)`);
    }
    sel.value = current;
    if (current && sel.value !== current) sel.selectedIndex = 0;
  }

  function applyMediaListToPoseCards(files, root) {
    let mutated = false;
    const appNode = document.getElementById("builder-app");
    const pid = appNode?.getAttribute("data-project-id");
    document.querySelectorAll("#builder-ui-panel .builder-pose-card").forEach((card) => {
      const hid = card.querySelector('[data-pc="example_asset_path"]');
      const raw = (hid?.value || "").trim();
      const resolved = resolveExampleAssetToListValue(files, raw);
      if (
        hid &&
        resolved &&
        normalizePathKey(resolved) !== normalizePathKey(raw) &&
        !/^https?:\/\//i.test(raw)
      ) {
        hid.value = resolved;
        mutated = true;
      }
      fillPoseCardAssetSelect(card, files, (hid?.value || "").trim());
    });
    if (mutated && root && pid) {
      syncUiFromDom(root);
      renderPreview(root, pid);
      syncTextarea(root, pid);
    }
  }

  async function ensureMediaSelectsFilled(app, root) {
    const listUrl = app.getAttribute("data-media-list-url");
    if (!listUrl) return;
    try {
      const files = await fetchMediaFileList(listUrl);
      applyMediaListToPoseCards(files, root);
    } catch (e) {
      console.warn("media list", e);
      document.querySelectorAll("#builder-ui-panel .builder-pose-card").forEach((card) => {
        const hid = card.querySelector('[data-pc="example_asset_path"]');
        fillPoseCardAssetSelect(card, [], (hid?.value || "").trim());
      });
    }
  }

  function deepClone(o) {
    return JSON.parse(JSON.stringify(o));
  }

  function fieldById(root, id) {
    return root.config.fields.find((f) => f.field_id === id);
  }

  function fieldTitle(root, id) {
    const f = fieldById(root, id);
    return f ? f.title || f.field_id : id;
  }

  function syncRootFromMeta(root, pid) {
    root.id = pid;
    const nm = document.getElementById("b-name");
    const vr = document.getElementById("b-version");
    if (nm) root.name = nm.value.trim() || pid;
    if (vr) root.version = vr.value.trim() || "1";
  }

  function buildPayload(root, pid) {
    const out = deepClone(root);
    syncRootFromMeta(out, pid);
    out.config = out.config || {};
    out.config.fields = out.config.fields || [];
    out.config.flow = out.config.flow || { steps: [] };
    out.config.flow.steps = out.config.flow.steps || [];
    if (!out.config.ui) delete out.config.ui;
    (out.config.fields || []).forEach((f) => {
      if (f && typeof f === "object") {
        delete f.options;
        delete f.sub_fields;
      }
    });
    return out;
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function linesFromArray(arr) {
    if (!Array.isArray(arr)) return "";
    return arr.map((x) => String(x)).join("\n");
  }

  function arrayFromLines(text) {
    return String(text || "")
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function syncTextarea(root, pid) {
    const ta = document.getElementById("id_raw_json");
    if (!ta) return;
    const payload = buildPayload(root, pid);
    const text = JSON.stringify(payload, null, 2);
    ta.value = text;
    const ro = document.getElementById("builder-json-readonly");
    if (ro) ro.value = text;
  }

  function renderPreview(root, pid) {
    const el = document.getElementById("builder-preview-steps");
    if (!el) return;
    syncRootFromMeta(root, pid);
    const steps = root.config.flow?.steps || [];
    if (!steps.length) {
      el.innerHTML = '<p class="small ui-muted mb-0">Нет шагов — вкладка «Сценарий» → «Добавить шаг».</p>';
      return;
    }
    const icons = {
      form: "bi-ui-checks-grid",
      instruction: "bi-info-circle",
      camera_pose: "bi-camera",
      cameraphoto: "bi-camera",
      review: "bi-eye",
      scroll_form: "bi-list-columns-reverse",
      scrollform: "bi-list-columns-reverse",
    };
    el.innerHTML = steps
      .map((st, i) => {
        const sc = (st.screen || "").toLowerCase().replace(/-/g, "_");
        const ic = icons[sc] || "bi-square";
        let detail = "";
        if (sc === "form" || sc === "scroll_form" || sc === "scrollform") {
          const ids =
            st.field_ids && st.field_ids.length ? st.field_ids : (root.config.fields || []).map((f) => f.field_id);
          detail = (ids || [])
            .map((id) => `<span class="preview-chip">${escapeHtml(fieldTitle(root, id))}</span>`)
            .join(" ");
        } else if (st.field_id) {
          detail = `<span class="preview-chip">${escapeHtml(fieldTitle(root, st.field_id))}</span>`;
        }
        return `<div class="preview-step">
          <div class="preview-step-idx">${i + 1}</div>
          <div class="preview-step-body">
            <div class="preview-step-title"><i class="bi ${ic} me-2"></i>${escapeHtml(st.id || "?")} <span class="ui-muted small">· ${escapeHtml(sc)}</span></div>
            <div class="preview-step-fields">${detail || '<span class="ui-muted small">—</span>'}</div>
          </div></div>`;
      })
      .join("");
    const ph = document.getElementById("builder-preview-title");
    if (ph) ph.textContent = root.name || pid;
  }

  function applyFieldRowMeta(tr, type, f) {
    const mult = tr.querySelector('[data-fk="multiple"]');
    const minEl = tr.querySelector('[data-fk="min_items"]');
    const cam = type === "camera_photo";
    if (mult) {
      mult.disabled = !cam;
      mult.checked = f.multiple === true;
    }
    if (minEl) {
      const mi = f.validation && f.validation.min_items != null ? Number(f.validation.min_items) : "";
      minEl.value = mi === "" || Number.isNaN(mi) ? "" : String(mi);
      minEl.disabled = !cam || !mult?.checked;
    }
    const req = tr.querySelector('[data-fk="val_required"]');
    if (req) req.checked = !!(f.validation && f.validation.required === true);
  }

  function instructionDetailTr(idx) {
    return document.querySelector(`#builder-fields-body tr.builder-instruction-detail[data-detail-for="${idx}"]`);
  }

  /** Развёрнутая форма для type=instruction (title, instructions, required) — под основной строкой. */
  function buildInstructionDetailRow(f, idx) {
    const tr = document.createElement("tr");
    tr.className = "builder-instruction-detail";
    tr.dataset.detailFor = String(idx);
    const req = f.validation && f.validation.required ? "checked" : "";
    tr.innerHTML = `
      <td colspan="9" class="p-0 border-secondary">
        <div class="px-3 py-3" style="background: rgba(45, 212, 191, 0.07); border-left: 3px solid var(--ui-accent, #2dd4bf);">
          <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
            <i class="bi bi-journal-text text-info"></i>
            <strong class="small text-white">Поле instruction</strong>
            <span class="small ui-muted">— всё, что в JSON у этого объекта <code>fields[]</code> (кроме <code>field_id</code> / <code>priority</code> / <code>type</code> — они в строке выше)</span>
          </div>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label small ui-muted mb-0">title</label>
              <input type="text" class="form-control form-control-sm" data-fk="title" value="${escapeAttr(f.title || "")}" autocomplete="off" placeholder="Заголовок на экране инструкции">
            </div>
            <div class="col-md-6 d-flex align-items-end">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" data-fk="val_required" id="ixreq${idx}" ${req}>
                <label class="form-check-label small" for="ixreq${idx}">validation.required</label>
              </div>
            </div>
            <div class="col-12">
              <label class="form-label small ui-muted mb-0">instructions <span class="fw-normal text-secondary">— основной текст; новая строка = новый абзац в приложении</span></label>
              <textarea class="form-control form-control-sm" data-fk="instructions" rows="14" autocomplete="off" placeholder="Длинный текст инструкции…"></textarea>
            </div>
            <div class="col-12">
              <p class="small ui-muted mb-0"><strong>Картинки, чек-лист ракурсов, общие советы</strong> — это не поля одного <code>instruction</code>, а общий блок проекта <code>config.ui.shooting_guide</code>. Редактируйте на вкладке <strong>«UI / гайд»</strong> (как в Korovas / витрина).</p>
            </div>
          </div>
        </div>
      </td>`;
    const ta = tr.querySelector('[data-fk="instructions"]');
    if (ta) ta.value = f.instructions || "";
    return tr;
  }

  /** Одна строка поля из root.config.fields[idx] */
  function buildFieldRow(f, idx) {
    const tr = document.createElement("tr");
    tr.dataset.rowIndex = String(idx);
    const isIx = f.type === "instruction";
    const typeSelect = `
      <select class="form-select form-select-sm" data-fk="type">
        ${
          !FIELD_TYPES.some((t) => t.v === f.type) && f.type
            ? `<option value="${escapeAttr(f.type)}" selected>${escapeHtml(String(f.type) + " (устар./не в списке)")}</option>`
            : ""
        }
        ${FIELD_TYPES.map(
          (t) =>
            `<option value="${escapeAttr(t.v)}" ${f.type === t.v ? "selected" : ""}>${escapeHtml(t.label)}</option>`,
        ).join("")}
      </select>`;
    if (isIx) {
      tr.innerHTML = `
      <td><input type="text" class="form-control form-control-sm" data-fk="field_id" value="${escapeAttr(f.field_id || "")}" autocomplete="off"></td>
      <td><input type="number" class="form-control form-control-sm" data-fk="priority" value="${Number(f.priority) || 0}"></td>
      <td>${typeSelect}</td>
      <td colspan="2" class="align-middle small ui-muted bg-dark bg-opacity-25"><i class="bi bi-arrow-down-circle me-1"></i>Содержимое поля — в форме <strong>под этой строкой</strong> (title, instructions, required).</td>
      <td class="text-center align-middle text-muted">—</td>
      <td class="text-center align-middle text-muted">—</td>
      <td class="text-center align-middle text-muted">—</td>
      <td><button type="button" class="btn btn-sm btn-outline-danger" data-del-field title="Удалить поле"><i class="bi bi-trash3"></i></button></td>`;
    } else {
      tr.innerHTML = `
      <td><input type="text" class="form-control form-control-sm" data-fk="field_id" value="${escapeAttr(f.field_id || "")}" autocomplete="off"></td>
      <td><input type="number" class="form-control form-control-sm" data-fk="priority" value="${Number(f.priority) || 0}"></td>
      <td>${typeSelect}</td>
      <td><input type="text" class="form-control form-control-sm" data-fk="title" value="${escapeAttr(f.title || "")}" autocomplete="off"></td>
      <td style="min-width:14rem"><textarea class="form-control form-control-sm" data-fk="instructions" rows="6" autocomplete="off" placeholder="Длинный текст, абзацы с новой строки — как в JSON"></textarea></td>
      <td class="text-center align-middle" title="validation.required">
        <input class="form-check-input" type="checkbox" data-fk="val_required" ${f.validation && f.validation.required ? "checked" : ""}>
      </td>
      <td class="text-center align-middle" title="Несколько фото (только camera_photo)">
        <input class="form-check-input" type="checkbox" data-fk="multiple" ${f.multiple === true ? "checked" : ""}>
      </td>
      <td style="width:4.5rem"><input type="number" min="0" class="form-control form-control-sm" data-fk="min_items" placeholder="мин." title="validation.min_items при нескольких фото"></td>
      <td><button type="button" class="btn btn-sm btn-outline-danger" data-del-field title="Удалить поле"><i class="bi bi-trash3"></i></button></td>`;
      const ins = tr.querySelector('[data-fk="instructions"]');
      if (ins) ins.value = f.instructions || "";
    }
    applyFieldRowMeta(tr, f.type || "text_input", f);
    return tr;
  }

  function fullRebuildFields(root) {
    const tb = document.querySelector("#builder-fields-body");
    if (!tb) return;
    tb.innerHTML = "";
    (root.config.fields || []).forEach((f, idx) => {
      tb.appendChild(buildFieldRow(f, idx));
      if (f.type === "instruction") tb.appendChild(buildInstructionDetailRow(f, idx));
    });
  }

  function buildStepCard(st, idx, root) {
    const screen = (st.screen || "form").toLowerCase().replace(/-/g, "_");
    const opts = SCREENS.map(
      (s) => `<option value="${s.v}" ${screen === s.v ? "selected" : ""}>${s.label}</option>`,
    ).join("");
    const allIds = (root.config.fields || []).map((f) => f.field_id).filter(Boolean);
    let extra = "";
    let hint = "";
    if (screen === "form" || screen === "scroll_form") {
      const ids = (st.field_ids || []).join(", ");
      extra = `<label class="form-label small ui-muted mt-2 mb-0">Поля на этом экране (id через запятую, как в таблице слева)</label>
        <input type="text" class="form-control form-control-sm" data-sk="field_ids" value="${escapeAttr(ids)}" placeholder="например: cow_id, scan_time" autocomplete="off">`;
      if (screen === "form") {
        extra += `<div class="form-check mt-2">
            <input class="form-check-input" type="checkbox" data-sk="cow_id_hints" ${st.cow_id_hints ? "checked" : ""} id="cowh${idx}">
            <label class="form-check-label small" for="cowh${idx}">Подсказки из истории по ID (коровы)</label></div>
          <input type="text" class="form-control form-control-sm mt-1" data-sk="cow_id_field_id" value="${escapeAttr(st.cow_id_field_id || "")}" placeholder="Какое поле — ID (например cow_identifier)" autocomplete="off">`;
      }
      hint =
        screen === "scroll_form"
          ? '<p class="small text-info mb-0 mt-2"><i class="bi bi-lightbulb me-1"></i>Оставьте список пустым — на экран попадут все поля по priority (поддерживаются <strong>text_input</strong> и <strong>camera_photo</strong>).</p>'
          : '<p class="small text-info mb-0 mt-2"><i class="bi bi-lightbulb me-1"></i>Только типы <strong>text_input</strong> и <strong>datetime</strong>.</p>';
    } else if (screen === "instruction" || screen === "camera_pose") {
      extra = `<label class="form-label small ui-muted mt-2 mb-0">Одно поле этого шага</label>
        <select class="form-select form-select-sm" data-sk="field_id">
          <option value="">— выберите —</option>
          ${allIds.map((id) => `<option value="${escapeAttr(id)}" ${st.field_id === id ? "selected" : ""}>${escapeAttr(id)}</option>`).join("")}
        </select>`;
      hint =
        screen === "instruction"
          ? '<p class="small text-info mb-0 mt-2"><i class="bi bi-lightbulb me-1"></i>Тип <strong>instruction</strong>: в таблице полей под строкой поля открывается форма <code>title</code> / <code>instructions</code> / <code>required</code>. Картинки и ракурсы — вкладка <strong>«UI / гайд»</strong>.</p>'
          : '<p class="small text-info mb-0 mt-2"><i class="bi bi-lightbulb me-1"></i>Тип <strong>camera_photo</strong>: подсказки у поля + пример кадра в <strong>«UI / гайд»</strong> (карточка ракурса по порядку шага).</p>';
    } else if (screen === "review") {
      hint =
        '<p class="small text-info mb-0 mt-2"><i class="bi bi-lightbulb me-1"></i>Отдельных полей нет. Если есть шаги камеры, клиент сам добавит проверку, если вы не указали review.</p>';
    }
    const card = document.createElement("div");
    card.className = "card mb-3 p-3 border-secondary builder-step-card";
    card.dataset.stepIndex = String(idx);
    card.innerHTML = `
      <div class="d-flex justify-content-between align-items-start gap-2">
        <div class="flex-grow-1">
          <div class="row g-2">
            <div class="col-md-4">
              <label class="form-label small ui-muted mb-0">Код шага (латиница)</label>
              <input class="form-control form-control-sm" data-sk="id" value="${escapeAttr(st.id || "")}" autocomplete="off">
            </div>
            <div class="col-md-8">
              <label class="form-label small ui-muted mb-0">Тип экрана</label>
              <select class="form-select form-select-sm" data-sk="screen">${opts}</select>
            </div>
          </div>
          ${extra}
          ${hint}
        </div>
        <button type="button" class="btn btn-sm btn-outline-danger flex-shrink-0" data-del-step="${idx}" title="Удалить шаг"><i class="bi bi-trash3"></i></button>
      </div>`;
    return card;
  }

  function fullRebuildSteps(root) {
    const wrap = document.getElementById("builder-steps");
    if (!wrap) return;
    wrap.innerHTML = "";
    (root.config.flow.steps || []).forEach((st, idx) => {
      wrap.appendChild(buildStepCard(st, idx, root));
    });
  }

  function syncFieldRowFromDom(tr, root) {
    const idx = parseInt(tr.dataset.rowIndex, 10);
    const f = root.config.fields[idx];
    if (!f) return;
    const detail = instructionDetailTr(idx);
    const get = (k) => tr.querySelector(`[data-fk="${k}"]`) || detail?.querySelector(`[data-fk="${k}"]`);
    const fid = get("field_id")?.value?.trim();
    if (fid) f.field_id = fid;
    f.priority = parseInt(get("priority")?.value || "0", 10) || 0;
    f.type = get("type")?.value || "text_input";
    f.title = get("title")?.value || "";
    f.instructions = get("instructions")?.value || "";
    delete f.options;
    delete f.sub_fields;

    const req = get("val_required")?.checked === true;
    const mult = get("multiple")?.checked === true;
    const minRaw = get("min_items")?.value;
    const ft = f.type;
    const nextVal = {};
    if (req) nextVal.required = true;
    if (ft === "camera_photo") {
      if (mult) f.multiple = true;
      else delete f.multiple;
      const mi = parseInt(String(minRaw || "").trim(), 10);
      if (mult && !Number.isNaN(mi) && mi > 0) nextVal.min_items = mi;
    } else {
      delete f.multiple;
    }
    if (Object.keys(nextVal).length) f.validation = nextVal;
    else delete f.validation;
  }

  function syncStepCardFromDom(card, root) {
    const idx = parseInt(card.dataset.stepIndex, 10);
    const st = root.config.flow.steps[idx];
    if (!st) return;
    const idInp = card.querySelector('[data-sk="id"]');
    const scr = card.querySelector('[data-sk="screen"]');
    if (idInp) st.id = idInp.value.trim() || `step_${idx}`;
    if (scr) st.screen = scr.value;
    const screen = (st.screen || "").toLowerCase().replace(/-/g, "_");
    delete st.field_ids;
    delete st.field_id;
    delete st.cow_id_hints;
    delete st.cow_id_field_id;
    if (screen === "form" || screen === "scroll_form") {
      const raw = card.querySelector('[data-sk="field_ids"]')?.value || "";
      const ids = raw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      if (ids.length) st.field_ids = ids;
      else if (screen === "form") st.field_ids = [];
      const ch = card.querySelector('[data-sk="cow_id_hints"]');
      if (ch && ch.checked) st.cow_id_hints = true;
      const cf = card.querySelector('[data-sk="cow_id_field_id"]')?.value?.trim();
      if (cf) st.cow_id_field_id = cf;
    } else if (screen === "instruction" || screen === "camera_pose") {
      const fid = card.querySelector('[data-sk="field_id"]')?.value;
      if (fid) st.field_id = fid;
    }
  }

  function syncAllFieldsFromDom(root) {
    document.querySelectorAll("#builder-fields-body tr[data-row-index]").forEach((tr) => {
      syncFieldRowFromDom(tr, root);
    });
  }

  function syncAllStepsFromDom(root) {
    document.querySelectorAll("#builder-steps .builder-step-card").forEach((card) => {
      syncStepCardFromDom(card, root);
    });
  }

  function ensureShootingGuide(root) {
    root.config = root.config || {};
    root.config.ui = root.config.ui || {};
    const ui = root.config.ui;
    if (!ui.shooting_guide) ui.shooting_guide = {};
    const sg = ui.shooting_guide;
    if (!Array.isArray(sg.general_tips)) sg.general_tips = [];
    if (!Array.isArray(sg.pose_cards)) sg.pose_cards = [];
  }

  function syncUiFromDom(root) {
    const panel = document.getElementById("builder-ui-panel");
    if (!panel) return;
    ensureShootingGuide(root);
    const sg = root.config.ui.shooting_guide;
    const pick = (name) => panel.querySelector(`[data-ug="${name}"]`)?.value ?? "";
    sg.section_overline = pick("section_overline").trim();
    sg.section_title = pick("section_title").trim();
    sg.section_subtitle = pick("section_subtitle").trim();
    sg.general_tips_heading = pick("general_tips_heading").trim();
    sg.general_tips = arrayFromLines(pick("general_tips"));
    sg.asset_missing_hint = pick("asset_missing_hint").trim();
    sg.no_asset_placeholder = pick("no_asset_placeholder").trim();
    sg.start_button = pick("start_button").trim();
    const cards = [];
    panel.querySelectorAll(".builder-pose-card").forEach((card) => {
      const idx = parseInt(card.querySelector('[data-pc="index_1based"]')?.value || "1", 10) || 1;
      const title = card.querySelector('[data-pc="title"]')?.value?.trim() ?? "";
      const shortLabel = card.querySelector('[data-pc="short_label"]')?.value?.trim() ?? "";
      const lines = arrayFromLines(card.querySelector('[data-pc="description_lines"]')?.value ?? "");
      const asset = card.querySelector('[data-pc="example_asset_path"]')?.value?.trim() ?? "";
      cards.push({
        index_1based: idx,
        title,
        short_label: shortLabel || title,
        description_lines: lines.length ? lines : ["Опишите ракурс по строкам."],
        example_asset_path: asset,
      });
    });
    sg.pose_cards = cards;
  }

  function fullRebuildUi(root) {
    const panel = document.getElementById("builder-ui-panel");
    if (!panel) return;
    const appEl = document.getElementById("builder-app");
    const mediaPageUrl = appEl?.getAttribute("data-media-page-url") || "#";
    ensureShootingGuide(root);
    const sg = root.config.ui.shooting_guide;
    const val = (k, d = "") => escapeAttr(sg[k] != null && sg[k] !== "" ? String(sg[k]) : d);
    const tips = linesFromArray(sg.general_tips);
    const cardsHtml = (sg.pose_cards || [])
      .map((pc, i) => {
        const idx = pc.index_1based != null ? Number(pc.index_1based) : i + 1;
        const lines = linesFromArray(pc.description_lines);
        const title = escapeAttr(pc.title || "");
        const shortL = escapeAttr(pc.short_label || "");
        const asset = escapeAttr(pc.example_asset_path || "");
        return `<div class="card mb-3 p-3 border-secondary builder-pose-card" data-pose-idx="${i}">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="small ui-muted">Карточка ракурса ${i + 1} (порядок = порядок шагов camera_pose)</span>
            <button type="button" class="btn btn-sm btn-outline-danger" data-remove-pose title="Удалить карточку"><i class="bi bi-trash3"></i></button>
          </div>
          <div class="row g-2">
            <div class="col-md-2">
              <label class="form-label small ui-muted mb-0">index_1based</label>
              <input type="number" min="1" class="form-control form-control-sm" data-pc="index_1based" value="${Number.isFinite(idx) ? idx : i + 1}">
            </div>
            <div class="col-md-5">
              <label class="form-label small ui-muted mb-0">title</label>
              <input type="text" class="form-control form-control-sm" data-pc="title" value="${title}" autocomplete="off">
            </div>
            <div class="col-md-5">
              <label class="form-label small ui-muted mb-0">short_label</label>
              <input type="text" class="form-control form-control-sm" data-pc="short_label" value="${shortL}" autocomplete="off">
            </div>
            <div class="col-12">
              <label class="form-label small ui-muted mb-0">description_lines (каждая строка = пункт списка)</label>
              <textarea class="form-control form-control-sm" data-pc="description_lines" rows="4" autocomplete="off">${escapeHtml(lines)}</textarea>
            </div>
            <div class="col-12">
              <label class="form-label small ui-muted mb-0">Картинка-пример (только файлы медиа этого проекта)</label>
              <input type="hidden" data-pc="example_asset_path" value="${asset}">
              <select class="form-select form-select-sm mt-1" data-pc-asset-select aria-label="Файл примера"></select>
              <p class="small ui-muted mb-0 mt-1">Новые файлы загружайте на странице <a href="${escapeAttr(mediaPageUrl)}" target="_blank" rel="noopener">медиа проекта</a>, затем нажмите «Обновить список файлов» выше.</p>
            </div>
          </div>
        </div>`;
      })
      .join("");
    panel.innerHTML = `
      <div class="row g-3">
        <div class="col-md-4">
          <label class="form-label small ui-muted mb-0">section_overline</label>
          <input type="text" class="form-control form-control-sm" data-ug="section_overline" value="${val("section_overline", "Обучение")}" autocomplete="off">
        </div>
        <div class="col-md-4">
          <label class="form-label small ui-muted mb-0">section_title</label>
          <input type="text" class="form-control form-control-sm" data-ug="section_title" value="${val("section_title", "Съёмка")}" autocomplete="off">
        </div>
        <div class="col-md-4">
          <label class="form-label small ui-muted mb-0">start_button</label>
          <input type="text" class="form-control form-control-sm" data-ug="start_button" value="${val("start_button", "Понятно, начать")}" autocomplete="off">
        </div>
        <div class="col-12">
          <label class="form-label small ui-muted mb-0">section_subtitle</label>
          <textarea class="form-control form-control-sm" data-ug="section_subtitle" rows="2" autocomplete="off">${escapeHtml(sg.section_subtitle != null ? String(sg.section_subtitle) : "")}</textarea>
        </div>
        <div class="col-md-6">
          <label class="form-label small ui-muted mb-0">general_tips_heading</label>
          <input type="text" class="form-control form-control-sm" data-ug="general_tips_heading" value="${val("general_tips_heading", "Общие рекомендации")}" autocomplete="off">
        </div>
        <div class="col-md-6">
          <label class="form-label small ui-muted mb-0">asset_missing_hint / no_asset_placeholder</label>
          <div class="d-flex gap-2">
            <input type="text" class="form-control form-control-sm" data-ug="asset_missing_hint" value="${val("asset_missing_hint", "")}" placeholder="asset_missing_hint" autocomplete="off">
            <input type="text" class="form-control form-control-sm" data-ug="no_asset_placeholder" value="${val("no_asset_placeholder", "—")}" placeholder="no_asset_placeholder" autocomplete="off">
          </div>
        </div>
        <div class="col-12">
          <label class="form-label small ui-muted mb-0">general_tips (одна строка = один пункт)</label>
          <textarea class="form-control form-control-sm" data-ug="general_tips" rows="5" autocomplete="off">${escapeHtml(tips)}</textarea>
        </div>
      </div>
      <hr class="border-secondary opacity-50 my-3">
      <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
        <p class="small ui-muted mb-0">Карточки <code>pose_cards</code> — пример кадра и текст для экранов камеры. Картинка выбирается только из <a href="${escapeAttr(mediaPageUrl)}" target="_blank" rel="noopener">медиа проекта</a> (список ниже).</p>
        <button type="button" class="btn btn-sm btn-outline-secondary flex-shrink-0" data-pc-refresh-media title="Подтянуть список файлов с сервера"><i class="bi bi-arrow-clockwise me-1"></i>Обновить список файлов</button>
      </div>
      <div id="builder-pose-cards-wrap">${cardsHtml}</div>
      <button type="button" class="btn btn-outline-light btn-sm mt-2" id="builder-ui-add-pose"><i class="bi bi-plus-lg me-1"></i>Добавить карточку ракурса</button>`;
    if (appEl && root) void ensureMediaSelectsFilled(appEl, root);
  }

  function init() {
    const app = document.getElementById("builder-app");
    const seed = document.getElementById("builder-initial");
    if (!app || !seed) return;
    const pid = app.getAttribute("data-project-id");
    const validateUrl = app.getAttribute("data-validate-url");
    let root;
    try {
      root = JSON.parse(seed.textContent);
    } catch (e) {
      console.error(e);
      return;
    }
    if (!root.config) root.config = { fields: [], flow: { steps: [] }, ui: {} };
    if (!root.config.fields) root.config.fields = [];
    if (!root.config.flow) root.config.flow = { steps: [] };
    if (!root.config.flow.steps) root.config.flow.steps = [];
    if (!root.config.ui) root.config.ui = {};

    const nameEl = document.getElementById("b-name");
    const verEl = document.getElementById("b-version");
    if (nameEl) nameEl.value = root.name || "";
    if (verEl) verEl.value = root.version || "1";

    let debounceTimer = null;
    function scheduleDebouncedSync() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        syncUiFromDom(root);
        renderPreview(root, pid);
        syncTextarea(root, pid);
      }, 200);
    }

    function structuralSync() {
      syncAllFieldsFromDom(root);
      syncAllStepsFromDom(root);
      syncUiFromDom(root);
      fullRebuildFields(root);
      fullRebuildSteps(root);
      fullRebuildUi(root);
      renderPreview(root, pid);
      syncTextarea(root, pid);
    }

    /** Ввод в ячейках полей — только правим объект, DOM не трогаем */
    app.addEventListener("input", (e) => {
      if (e.target.closest("#builder-ui-panel")) {
        syncUiFromDom(root);
        scheduleDebouncedSync();
        return;
      }
      const det = e.target.closest("#builder-fields-body tr.builder-instruction-detail");
      if (det) {
        const idx = parseInt(det.dataset.detailFor, 10);
        const main = document.querySelector(`#builder-fields-body tr[data-row-index="${idx}"]`);
        if (main) syncFieldRowFromDom(main, root);
        scheduleDebouncedSync();
        return;
      }
      const tr = e.target.closest("#builder-fields-body tr[data-row-index]");
      if (tr) {
        syncFieldRowFromDom(tr, root);
        scheduleDebouncedSync();
        return;
      }
      const card = e.target.closest("#builder-steps .builder-step-card");
      if (card && e.target.matches("input,textarea") && !e.target.matches('[data-sk="screen"]')) {
        syncStepCardFromDom(card, root);
        scheduleDebouncedSync();
      }
    });

    app.addEventListener("change", (e) => {
      if (e.target.matches("[data-pc-asset-select]")) {
        const card = e.target.closest(".builder-pose-card");
        const hid = card?.querySelector('[data-pc="example_asset_path"]');
        if (hid) hid.value = e.target.value;
        syncUiFromDom(root);
        renderPreview(root, pid);
        syncTextarea(root, pid);
        return;
      }
      if (e.target.closest("#builder-ui-panel")) {
        syncUiFromDom(root);
        renderPreview(root, pid);
        syncTextarea(root, pid);
        return;
      }
      const detCh = e.target.closest("#builder-fields-body tr.builder-instruction-detail");
      if (detCh) {
        const idx = parseInt(detCh.dataset.detailFor, 10);
        const main = document.querySelector(`#builder-fields-body tr[data-row-index="${idx}"]`);
        if (main) syncFieldRowFromDom(main, root);
        renderPreview(root, pid);
        syncTextarea(root, pid);
        return;
      }
      const tr = e.target.closest("#builder-fields-body tr[data-row-index]");
      if (tr) {
        if (e.target.matches('[data-fk="multiple"]')) {
          const type = tr.querySelector('[data-fk="type"]')?.value;
          const minEl = tr.querySelector('[data-fk="min_items"]');
          if (minEl) minEl.disabled = type !== "camera_photo" || !e.target.checked;
        }
        syncFieldRowFromDom(tr, root);
        if (e.target.matches('select[data-fk="type"]')) {
          structuralSync();
          return;
        }
        renderPreview(root, pid);
        syncTextarea(root, pid);
        return;
      }
      const stepCard = e.target.closest("#builder-steps .builder-step-card");
      if (stepCard) {
        if (e.target.matches('select[data-sk="screen"]')) {
          syncStepCardFromDom(stepCard, root);
          syncAllStepsFromDom(root);
          fullRebuildSteps(root);
          renderPreview(root, pid);
          syncTextarea(root, pid);
          return;
        }
        syncStepCardFromDom(stepCard, root);
        renderPreview(root, pid);
        syncTextarea(root, pid);
      }
    });

    app.addEventListener("click", (e) => {
      const refBtn = e.target.closest("[data-pc-refresh-media]");
      if (refBtn) {
        e.preventDefault();
        const listUrl = app.getAttribute("data-media-list-url");
        if (!listUrl) return;
        refBtn.disabled = true;
        fetchMediaFileList(listUrl)
          .then((files) => {
            applyMediaListToPoseCards(files, root);
          })
          .catch((err) => window.alert(String(err.message || err)))
          .finally(() => {
            refBtn.disabled = false;
          });
        return;
      }
      if (e.target.closest("#builder-ui-add-pose")) {
        e.preventDefault();
        syncAllFieldsFromDom(root);
        syncAllStepsFromDom(root);
        syncUiFromDom(root);
        ensureShootingGuide(root);
        const pcs = root.config.ui.shooting_guide.pose_cards;
        pcs.push({
          index_1based: pcs.length + 1,
          title: "",
          short_label: "",
          description_lines: ["Первая строка описания кадра.", "Вторая строка при необходимости."],
          example_asset_path: "",
        });
        fullRebuildUi(root);
        renderPreview(root, pid);
        syncTextarea(root, pid);
        return;
      }
      const delP = e.target.closest("[data-remove-pose]");
      if (delP) {
        e.preventDefault();
        syncAllFieldsFromDom(root);
        syncAllStepsFromDom(root);
        syncUiFromDom(root);
        const card = delP.closest(".builder-pose-card");
        const wrap = document.getElementById("builder-pose-cards-wrap");
        if (card && wrap) {
          const idx = Array.prototype.indexOf.call(wrap.children, card);
          if (idx >= 0) root.config.ui.shooting_guide.pose_cards.splice(idx, 1);
        }
        fullRebuildUi(root);
        renderPreview(root, pid);
        syncTextarea(root, pid);
        return;
      }
      const delF = e.target.closest("#builder-fields-body [data-del-field]");
      if (delF) {
        e.preventDefault();
        const tr = delF.closest("tr[data-row-index]");
        if (!tr) return;
        syncAllFieldsFromDom(root);
        const idx = parseInt(tr.dataset.rowIndex, 10);
        root.config.fields.splice(idx, 1);
        structuralSync();
        return;
      }
      const delS = e.target.closest("#builder-steps [data-del-step]");
      if (delS) {
        e.preventDefault();
        const card = delS.closest(".builder-step-card");
        if (!card) return;
        syncAllStepsFromDom(root);
        const idx = parseInt(card.dataset.stepIndex, 10);
        root.config.flow.steps.splice(idx, 1);
        structuralSync();
      }
    });

    document.getElementById("builder-add-field")?.addEventListener("click", () => {
      syncAllFieldsFromDom(root);
      root.config.fields.push({
        field_id: "field_" + Date.now().toString(36).slice(-6),
        priority: (root.config.fields.length || 0) + 1,
        type: "text_input",
        title: "Новое поле",
        instructions: "",
        validation: {},
      });
      structuralSync();
    });

    document.getElementById("builder-add-step")?.addEventListener("click", () => {
      syncAllStepsFromDom(root);
      root.config.flow.steps.push({
        id: "step_" + Date.now().toString(36).slice(-6),
        screen: "form",
        field_ids: [],
      });
      structuralSync();
    });

    document.getElementById("builder-btn-validate")?.addEventListener("click", async () => {
      syncAllFieldsFromDom(root);
      syncAllStepsFromDom(root);
      syncUiFromDom(root);
      syncRootFromMeta(root, pid);
      const box = document.getElementById("builder-errors");
      if (!box) return;
      box.innerHTML = '<span class="ui-muted">Проверка…</span>';
      try {
        const res = await fetch(validateUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken") || "",
          },
          body: JSON.stringify(buildPayload(root, pid)),
        });
        const data = await res.json();
        if (data.ok) {
          box.innerHTML =
            '<div class="alert alert-success py-2 mb-0"><i class="bi bi-check-circle me-2"></i>Ошибок не найдено.</div>';
        } else {
          box.innerHTML =
            '<div class="alert alert-danger py-2 mb-0"><strong>Проблемы:</strong><ul class="mb-0 mt-1 small">' +
            (data.errors || ["Неизвестная ошибка"])
              .map((err) => "<li>" + escapeHtml(err) + "</li>")
              .join("") +
            "</ul></div>";
        }
      } catch (err) {
        box.innerHTML =
          '<div class="alert alert-danger py-2 mb-0">Запрос не удался: ' + escapeHtml(String(err)) + "</div>";
      }
    });

    ["b-name", "b-version"].forEach((id) => {
      document.getElementById(id)?.addEventListener("input", () => {
        renderPreview(root, pid);
        syncTextarea(root, pid);
      });
    });

    document.getElementById("builder-form")?.addEventListener("submit", () => {
      clearTimeout(debounceTimer);
      syncAllFieldsFromDom(root);
      syncAllStepsFromDom(root);
      syncUiFromDom(root);
      syncRootFromMeta(root, pid);
      syncTextarea(root, pid);
    });

    document.getElementById("tab-ui-btn")?.addEventListener("shown.bs.tab", () => {
      syncAllFieldsFromDom(root);
      syncAllStepsFromDom(root);
      syncUiFromDom(root);
      fullRebuildUi(root);
    });

    fullRebuildFields(root);
    fullRebuildSteps(root);
    fullRebuildUi(root);
    renderPreview(root, pid);
    syncTextarea(root, pid);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
