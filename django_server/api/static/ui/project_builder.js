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

  /** Одна строка поля из root.config.fields[idx] */
  function buildFieldRow(f, idx) {
    const tr = document.createElement("tr");
    tr.dataset.rowIndex = String(idx);
    tr.innerHTML = `
      <td><input type="text" class="form-control form-control-sm" data-fk="field_id" value="${escapeAttr(f.field_id || "")}" autocomplete="off"></td>
      <td><input type="number" class="form-control form-control-sm" data-fk="priority" value="${Number(f.priority) || 0}"></td>
      <td><select class="form-select form-select-sm" data-fk="type">
        ${
          !FIELD_TYPES.some((t) => t.v === f.type) && f.type
            ? `<option value="${escapeAttr(f.type)}" selected>${escapeHtml(String(f.type) + " (устар./не в списке)")}</option>`
            : ""
        }
        ${FIELD_TYPES.map(
          (t) =>
            `<option value="${escapeAttr(t.v)}" ${f.type === t.v ? "selected" : ""}>${escapeHtml(t.label)}</option>`,
        ).join("")}
      </select></td>
      <td><input type="text" class="form-control form-control-sm" data-fk="title" value="${escapeAttr(f.title || "")}" autocomplete="off"></td>
      <td><textarea class="form-control form-control-sm" data-fk="instructions" rows="2" autocomplete="off"></textarea></td>
      <td><button type="button" class="btn btn-sm btn-outline-danger" data-del-field title="Удалить поле"><i class="bi bi-trash3"></i></button></td>`;
    const ins = tr.querySelector('[data-fk="instructions"]');
    if (ins) ins.value = f.instructions || "";
    return tr;
  }

  function fullRebuildFields(root) {
    const tb = document.querySelector("#builder-fields-body");
    if (!tb) return;
    tb.innerHTML = "";
    (root.config.fields || []).forEach((f, idx) => {
      tb.appendChild(buildFieldRow(f, idx));
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
          ? '<p class="small text-info mb-0 mt-2"><i class="bi bi-lightbulb me-1"></i>В таблице полей у этого id тип должен быть <strong>instruction</strong>.</p>'
          : '<p class="small text-info mb-0 mt-2"><i class="bi bi-lightbulb me-1"></i>В таблице полей — тип <strong>camera_photo</strong>.</p>';
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
    const get = (k) => tr.querySelector(`[data-fk="${k}"]`);
    const fid = get("field_id")?.value?.trim();
    if (fid) f.field_id = fid;
    f.priority = parseInt(get("priority")?.value || "0", 10) || 0;
    f.type = get("type")?.value || "text_input";
    f.title = get("title")?.value || "";
    f.instructions = get("instructions")?.value || "";
    delete f.options;
    delete f.sub_fields;
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

    const nameEl = document.getElementById("b-name");
    const verEl = document.getElementById("b-version");
    if (nameEl) nameEl.value = root.name || "";
    if (verEl) verEl.value = root.version || "1";

    let debounceTimer = null;
    function scheduleDebouncedSync() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        renderPreview(root, pid);
        syncTextarea(root, pid);
      }, 200);
    }

    function structuralSync() {
      syncAllFieldsFromDom(root);
      syncAllStepsFromDom(root);
      fullRebuildFields(root);
      fullRebuildSteps(root);
      renderPreview(root, pid);
      syncTextarea(root, pid);
    }

    /** Ввод в ячейках полей — только правим объект, DOM не трогаем */
    app.addEventListener("input", (e) => {
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
      const tr = e.target.closest("#builder-fields-body tr[data-row-index]");
      if (tr) {
        syncFieldRowFromDom(tr, root);
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
      syncRootFromMeta(root, pid);
      syncTextarea(root, pid);
    });

    fullRebuildFields(root);
    fullRebuildSteps(root);
    renderPreview(root, pid);
    syncTextarea(root, pid);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
