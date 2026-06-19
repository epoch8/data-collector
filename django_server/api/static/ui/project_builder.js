/**
 * Визуальный редактор конфига — сценарий из карточек-экранов с drag-and-drop.
 *
 * Модель: сценарий = список шагов (экранов). Шаг scroll_form содержит блоки полей.
 * Последний шаг — review (отправка пакета): он обязателен, всегда в конце и неудаляем —
 * без него мобильный клиент не может отправить данные.
 *
 * Источник истины для значений и порядка — DOM. Модель пересобирается из DOM
 * (readModelFromDom) при сериализации; структурные изменения (добавить/удалить/сменить тип,
 * перетаскивание) перерисовывают карточки и переинициализируют Sortable.
 */
(function () {
  "use strict";

  const FIELD_TYPES = [
    { v: "text_input", label: "Текст", icon: "bi-input-cursor-text", hint: "однострочный ввод" },
    { v: "datetime", label: "Дата и время", icon: "bi-calendar-event", hint: "выбор даты/времени" },
    { v: "camera_photo", label: "Фото", icon: "bi-camera", hint: "снимок с камеры" },
    { v: "instruction", label: "Инструкция", icon: "bi-journal-text", hint: "Markdown-текст" },
  ];

  function typeMeta(v) {
    return FIELD_TYPES.find((t) => t.v === v) || { v, label: v, icon: "bi-question-circle", hint: "" };
  }

  let _uid = 0;
  function uid() {
    _uid += 1;
    return "u" + _uid + Date.now().toString(36).slice(-3);
  }

  function getCookie(name) {
    const v = document.cookie.match("(^|;) ?" + name + "=([^;]*)(;|$)");
    return v ? decodeURIComponent(v[2]) : null;
  }

  function escapeAttr(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : s;
    return d.innerHTML;
  }

  function slugify(s) {
    return String(s || "")
      .toLowerCase()
      .replace(/[^a-z0-9_]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 48);
  }

  function mediaPageUrl() {
    const app = document.getElementById("builder-app");
    const u = app?.getAttribute("data-media-url");
    return u && u.trim() ? u.trim() : "";
  }

  // ——— Загрузка модели из project JSON ———

  function loadModel(root) {
    const cfg = (root && root.config) || {};
    const byId = {};
    (Array.isArray(cfg.fields) ? cfg.fields : []).forEach((f) => {
      if (f && typeof f === "object" && typeof f.field_id === "string") byId[f.field_id] = f;
    });

    const rawSteps = Array.isArray(cfg.flow && cfg.flow.steps) ? cfg.flow.steps : [];
    const steps = [];
    const usedIds = new Set();

    rawSteps.forEach((st) => {
      if (!st || typeof st !== "object") return;
      const screen = String(st.screen || "scroll_form").toLowerCase().replace(/-/g, "_");
      if (screen === "review") {
        steps.push({ uid: uid(), kind: "review", id: st.id || "review", form_title: st.form_title || "" });
        return;
      }
      // всё, что не review — трактуем как scroll_form (form/instruction/camera_pose устарели)
      const ids = Array.isArray(st.field_ids) ? st.field_ids : [];
      const fields = [];
      ids.forEach((fid) => {
        if (usedIds.has(fid)) return;
        const f = byId[fid];
        if (!f) return;
        usedIds.add(fid);
        fields.push(fieldFromConfig(f));
      });
      steps.push({
        uid: uid(),
        kind: "scroll_form",
        id: st.id || "",
        form_title: st.form_title || "",
        cow_id_hints: st.cow_id_hints === true,
        cow_id_field_id: st.cow_id_field_id || "",
        fields,
      });
    });

    // Поля, не попавшие ни в один шаг — добавим в первый scroll_form, чтобы не потерять.
    const orphan = [];
    Object.keys(byId).forEach((fid) => {
      if (!usedIds.has(fid)) orphan.push(fieldFromConfig(byId[fid]));
    });

    let firstScroll = steps.find((s) => s.kind === "scroll_form");
    if (!firstScroll) {
      firstScroll = { uid: uid(), kind: "scroll_form", id: "form1", form_title: "", fields: [] };
      steps.unshift(firstScroll);
    }
    orphan.forEach((f) => firstScroll.fields.push(f));

    // Ровно один review, в самом конце.
    const reviews = steps.filter((s) => s.kind === "review");
    const nonReview = steps.filter((s) => s.kind !== "review");
    const review = reviews[0] || { uid: uid(), kind: "review", id: "review", form_title: "" };
    const ordered = nonReview.concat([review]);

    return {
      name: typeof root.name === "string" ? root.name : "",
      version: typeof root.version === "string" ? root.version : "1",
      ui: cfg.ui && typeof cfg.ui === "object" ? cfg.ui : {},
      extraRoot: extractExtraRoot(root),
      steps: ordered,
    };
  }

  function extractExtraRoot(root) {
    const out = {};
    Object.keys(root || {}).forEach((k) => {
      if (["id", "name", "version", "config"].includes(k)) return;
      out[k] = root[k];
    });
    return out;
  }

  function fieldFromConfig(f) {
    const validation = f.validation && typeof f.validation === "object" ? { ...f.validation } : {};
    const required = validation.required === true;
    delete validation.required;
    return {
      uid: uid(),
      field_id: f.field_id || "",
      type: typeof f.type === "string" ? f.type : "text_input",
      title: typeof f.title === "string" ? f.title : "",
      instructions: typeof f.instructions === "string" ? f.instructions : "",
      required,
      validationExtra: validation,
    };
  }

  // ——— Чтение модели из DOM (источник истины) ———

  function readModelFromDom(model) {
    const steps = [];
    document.querySelectorAll("#builder-steps .builder-step-card").forEach((card) => {
      if (card.classList.contains("is-review")) {
        steps.push({
          uid: card.dataset.uid,
          kind: "review",
          id: (card.querySelector('[data-sk="id"]')?.value || "review").trim() || "review",
          form_title: card.querySelector('[data-sk="form_title"]')?.value?.trim() || "",
        });
        return;
      }
      const fields = [];
      card.querySelectorAll(".builder-field-block").forEach((blk) => {
        const get = (k) => blk.querySelector(`[data-fk="${k}"]`);
        const type = get("type")?.value || "text_input";
        fields.push({
          uid: blk.dataset.uid,
          field_id: get("field_id")?.value?.trim() || "",
          type,
          title: type === "instruction" ? "" : get("title")?.value || "",
          instructions: get("instructions")?.value || "",
          required: type !== "instruction" && get("required")?.checked === true,
          validationExtra: blockExtra(blk),
        });
      });
      steps.push({
        uid: card.dataset.uid,
        kind: "scroll_form",
        id: card.querySelector('[data-sk="id"]')?.value?.trim() || "",
        form_title: card.querySelector('[data-sk="form_title"]')?.value?.trim() || "",
        cow_id_hints: card.querySelector('[data-sk="cow_id_hints"]')?.checked === true,
        cow_id_field_id: card.querySelector('[data-sk="cow_id_field_id"]')?.value?.trim() || "",
        fields,
      });
    });
    model.steps = steps;
    const nm = document.getElementById("b-name");
    const vr = document.getElementById("b-version");
    if (nm) model.name = nm.value.trim();
    if (vr) model.version = vr.value.trim() || "1";
    return model;
  }

  const _extraStore = new WeakMap();
  function blockExtra(blk) {
    return _extraStore.get(blk) || {};
  }

  // ——— Сериализация модели в project JSON ———

  function serialize(model, pid) {
    const fields = [];
    const steps = [];
    model.steps.forEach((st, i) => {
      if (st.kind === "review") {
        const s = { id: slugify(st.id) || "review", screen: "review" };
        if (st.form_title) s.form_title = st.form_title;
        steps.push(s);
        return;
      }
      const sid = slugify(st.id) || `form${i + 1}`;
      const ids = [];
      (st.fields || []).forEach((f) => {
        const fid = slugify(f.field_id);
        if (!fid) return;
        ids.push(fid);
        const out = {
          field_id: fid,
          type: f.type || "text_input",
          title: f.type === "instruction" ? "" : f.title || "",
          instructions: f.instructions || "",
        };
        const validation = { ...(f.validationExtra || {}) };
        if (f.type !== "instruction" && f.required) validation.required = true;
        if (Object.keys(validation).length) out.validation = validation;
        fields.push(out);
      });
      const s = { id: sid, screen: "scroll_form", field_ids: ids };
      if (st.form_title) s.form_title = st.form_title;
      if (st.cow_id_hints) {
        s.cow_id_hints = true;
        if (st.cow_id_field_id) s.cow_id_field_id = slugify(st.cow_id_field_id);
      }
      steps.push(s);
    });

    const config = { fields, flow: { steps } };
    if (model.ui && typeof model.ui === "object" && Object.keys(model.ui).length) {
      config.ui = model.ui;
    }
    return {
      ...(model.extraRoot || {}),
      id: pid,
      name: model.name || pid,
      version: model.version || "1",
      config,
    };
  }

  // ——— Рендер ———

  function buildFieldBlock(f) {
    const blk = document.createElement("div");
    blk.className = "builder-field-block";
    blk.dataset.uid = f.uid;
    const isIx = f.type === "instruction";
    const tm = typeMeta(f.type);
    const typeOpts = FIELD_TYPES.map(
      (t) => `<option value="${t.v}" ${f.type === t.v ? "selected" : ""}>${escapeHtml(t.label)}</option>`,
    ).join("");
    blk.innerHTML = `
      <div class="builder-field-head">
        <span class="builder-drag" data-drag title="Перетащить"><i class="bi bi-grip-vertical"></i></span>
        <span class="builder-field-icon ${isIx ? "is-ix" : ""}"><i class="bi ${tm.icon}"></i></span>
        <select class="form-select form-select-sm builder-field-type" data-fk="type" title="Тип поля">${typeOpts}</select>
        <input type="text" class="form-control form-control-sm builder-field-id" data-fk="field_id"
               value="${escapeAttr(f.field_id)}" placeholder="field_id (латиница)" autocomplete="off" title="Идентификатор поля"
               ${f.field_id ? 'data-touched="1"' : ""}>
        <button type="button" class="btn btn-sm btn-icon-danger" data-del-field title="Удалить поле"><i class="bi bi-trash3"></i></button>
      </div>
      <div class="builder-field-body">
        <div class="builder-field-title-row ${isIx ? "d-none" : ""}">
          <input type="text" class="form-control form-control-sm" data-fk="title"
                 value="${escapeAttr(f.title)}" placeholder="Подпись (видна пользователю)" autocomplete="off">
          <label class="builder-required-toggle" title="Обязательное поле">
            <input class="form-check-input" type="checkbox" data-fk="required" ${f.required ? "checked" : ""}>
            <span>обяз.</span>
          </label>
        </div>
        <textarea class="form-control form-control-sm builder-field-instr" data-fk="instructions"
                  rows="${isIx ? 6 : 2}" autocomplete="off"
                  placeholder="${isIx ? "Markdown-текст инструкции (абзацы — с новой строки, картинки ![](collector/media/…))" : "Подсказка под полем (необязательно)"}"></textarea>
      </div>`;
    blk.querySelector('[data-fk="instructions"]').value = f.instructions || "";
    if (f.validationExtra && Object.keys(f.validationExtra).length) {
      _extraStore.set(blk, { ...f.validationExtra });
    }
    return blk;
  }

  function buildStepCard(st, index, scrollOrdinal) {
    const card = document.createElement("div");
    card.dataset.uid = st.uid;

    if (st.kind === "review") {
      card.className = "card builder-step-card is-review";
      card.innerHTML = `
        <div class="builder-step-head">
          <span class="builder-step-grip is-locked" title="Финальный экран"><i class="bi bi-lock-fill"></i></span>
          <span class="builder-step-badge is-review"><i class="bi bi-send-check me-1"></i>Проверка и отправка</span>
        </div>
        <div class="builder-step-body">
          <label class="form-label small ui-muted mb-1">Заголовок экрана (необязательно)</label>
          <input type="text" class="form-control form-control-sm" data-sk="form_title" value="${escapeAttr(st.form_title)}" placeholder="Например: Проверьте данные" autocomplete="off">
          <input type="hidden" data-sk="id" value="${escapeAttr(st.id || "review")}">
        </div>`;
      return card;
    }

    card.className = "card builder-step-card";
    const murl = mediaPageUrl();
    const mediaLink = murl
      ? `<a href="${escapeAttr(murl)}" target="_blank" rel="noopener">«Файлы»</a>`
      : "«Файлы»";
    card.innerHTML = `
      <div class="builder-step-head">
        <span class="builder-step-grip" data-step-drag title="Перетащить шаг"><i class="bi bi-grip-vertical"></i></span>
        <span class="builder-step-badge"><i class="bi bi-window-stack me-1"></i>Экран ${scrollOrdinal}</span>
        <input type="text" class="form-control form-control-sm builder-step-title" data-sk="form_title"
               value="${escapeAttr(st.form_title)}" placeholder="Заголовок экрана (необязательно)" autocomplete="off">
        <button type="button" class="btn btn-sm builder-step-adv" data-toggle-adv title="Дополнительно"><i class="bi bi-sliders"></i></button>
        <button type="button" class="btn btn-sm btn-icon-danger" data-del-step title="Удалить экран"><i class="bi bi-trash3"></i></button>
      </div>
      <div class="builder-step-adv-box d-none">
        <div class="row g-2">
          <div class="col-md-5">
            <label class="form-label small ui-muted mb-1">Код шага (латиница)</label>
            <input type="text" class="form-control form-control-sm" data-sk="id" value="${escapeAttr(st.id)}" placeholder="form1" autocomplete="off">
          </div>
          <div class="col-md-7">
            <label class="form-label small ui-muted mb-1">Поле ID коровы (для подсказок)</label>
            <input type="text" class="form-control form-control-sm" data-sk="cow_id_field_id" value="${escapeAttr(st.cow_id_field_id)}" placeholder="cow_identifier" autocomplete="off">
          </div>
          <div class="col-12">
            <label class="builder-required-toggle">
              <input class="form-check-input" type="checkbox" data-sk="cow_id_hints" ${st.cow_id_hints ? "checked" : ""}>
              <span>Подсказки из локальной истории по ID коровы</span>
            </label>
          </div>
        </div>
      </div>
      <div class="builder-step-body">
        <div class="builder-fields-section-label small text-white mb-2">
          <i class="bi bi-input-cursor-text me-1"></i><strong>Поля на этом экране</strong>
          <span class="ui-muted fw-normal"> — здесь задаются field_id, подпись, тип и подсказка</span>
        </div>
        <div class="builder-fields-list" data-fields-list></div>
        <div class="builder-empty-hint ${st.fields && st.fields.length ? "d-none" : ""}">
          <i class="bi bi-arrow-down-circle me-1"></i>Пока нет полей — нажмите кнопку типа ниже или перетащите поле с другого экрана.
        </div>
        <div class="builder-palette-label small ui-muted mt-2 mb-1">Добавить поле:</div>
        <div class="builder-palette">
          ${FIELD_TYPES.map(
            (t) =>
              `<button type="button" class="builder-palette-btn" data-add-type="${t.v}" title="${escapeAttr(t.hint)}"><i class="bi ${t.icon} me-1"></i>${escapeHtml(t.label)}</button>`,
          ).join("")}
        </div>
        <input type="hidden" data-sk="id" value="${escapeAttr(st.id)}">
        <p class="small ui-muted mb-0 mt-2 builder-step-foot">Картинки для Markdown — в Git <code>collector/media/</code> (${mediaLink}).</p>
      </div>`;
    // у scroll-карточки два data-sk="id" (в adv-box и hidden) — оставляем один: убираем hidden, если adv есть
    const hidden = card.querySelector('.builder-step-body input[type="hidden"][data-sk="id"]');
    if (hidden) hidden.remove();

    const list = card.querySelector("[data-fields-list]");
    (st.fields || []).forEach((f) => list.appendChild(buildFieldBlock(f)));
    return card;
  }

  let sortableInstances = [];
  function destroySortables() {
    sortableInstances.forEach((s) => {
      try {
        s.destroy();
      } catch (e) {
        /* noop */
      }
    });
    sortableInstances = [];
  }

  function ensureReviewLast() {
    const wrap = document.getElementById("builder-steps");
    if (!wrap) return;
    const review = wrap.querySelector(".builder-step-card.is-review");
    if (review) {
      placeAddStepButton(wrap);
      if (review !== wrap.lastElementChild) wrap.appendChild(review);
    }
  }

  function placeAddStepButton(wrap) {
    if (!wrap) return;
    let slot = wrap.querySelector(".builder-add-step-wrap");
    if (!slot) {
      slot = document.createElement("div");
      slot.className = "builder-add-step-wrap";
      slot.innerHTML =
        '<button type="button" class="btn btn-outline-light btn-sm builder-add-step-btn" id="builder-add-step">' +
        '<i class="bi bi-plus-lg me-1"></i>Добавить экран</button>';
    }
    const review = wrap.querySelector(".builder-step-card.is-review");
    if (review) wrap.insertBefore(slot, review);
    else if (!slot.parentElement) wrap.appendChild(slot);
  }

  function renderSteps(model, onChange) {
    const wrap = document.getElementById("builder-steps");
    if (!wrap) return;
    destroySortables();
    wrap.innerHTML = "";
    let scrollOrdinal = 0;
    model.steps.forEach((st, i) => {
      if (st.kind !== "scroll_form") return;
      scrollOrdinal += 1;
      wrap.appendChild(buildStepCard(st, i, scrollOrdinal));
    });
    placeAddStepButton(wrap);
    model.steps.forEach((st, i) => {
      if (st.kind === "review") wrap.appendChild(buildStepCard(st, i, 0));
    });
    ensureReviewLast();
    initSortables(model, onChange);
  }

  function initSortables(model, onChange) {
    if (typeof window.Sortable === "undefined") return;
    const wrap = document.getElementById("builder-steps");
    // Перетаскивание шагов (review зафиксирован — не draggable и не принимает над собой).
    sortableInstances.push(
      window.Sortable.create(wrap, {
        handle: "[data-step-drag]",
        animation: 150,
        draggable: ".builder-step-card",
        filter: ".is-review",
        onMove: (evt) => !evt.related.classList.contains("is-review"),
        onEnd: () => {
          ensureReviewLast();
          setTimeout(() => onChange(true), 0);
        },
      }),
    );
    // Перетаскивание полей внутри и между scroll-шагами.
    wrap.querySelectorAll("[data-fields-list]").forEach((list) => {
      sortableInstances.push(
        window.Sortable.create(list, {
          group: "builder-fields",
          handle: "[data-drag]",
          animation: 150,
          draggable: ".builder-field-block",
          onEnd: () => setTimeout(() => onChange(true), 0),
        }),
      );
    });
  }

  function renderPreview(model, pid) {
    const el = document.getElementById("builder-preview-steps");
    if (!el) return;
    const steps = model.steps || [];
    el.innerHTML = steps
      .map((st, i) => {
        if (st.kind === "review") {
          return `<div class="preview-step">
            <div class="preview-step-idx"><i class="bi bi-send-check"></i></div>
            <div class="preview-step-body">
              <div class="preview-step-title">${escapeHtml(st.form_title || "Проверка и отправка")}</div>
              <div class="preview-step-fields"><span class="ui-muted small">отправка пакета</span></div>
            </div></div>`;
        }
        const chips = (st.fields || [])
          .map((f) => {
            const tm = typeMeta(f.type);
            const label = f.type === "instruction" ? "инструкция" : f.title || f.field_id || "поле";
            return `<span class="preview-chip"><i class="bi ${tm.icon} me-1"></i>${escapeHtml(label)}</span>`;
          })
          .join(" ");
        return `<div class="preview-step">
          <div class="preview-step-idx">${i + 1}</div>
          <div class="preview-step-body">
            <div class="preview-step-title">${escapeHtml(st.form_title || "Экран " + (i + 1))}</div>
            <div class="preview-step-fields">${chips || '<span class="ui-muted small">нет полей</span>'}</div>
          </div></div>`;
      })
      .join("");
    const ph = document.getElementById("builder-preview-title");
    if (ph) ph.textContent = model.name || pid;
  }

  function syncTextarea(model, pid) {
    const payload = serialize(model, pid);
    const text = JSON.stringify(payload, null, 2);
    const ta = document.getElementById("id_raw_json");
    if (ta) ta.value = text;
    const ro = document.getElementById("builder-json-readonly");
    if (ro) ro.value = text;
  }

  // ——— Init ———

  function init() {
    const app = document.getElementById("builder-app");
    const seed = document.getElementById("builder-initial");
    if (!app || !seed) return;
    const pid = app.getAttribute("data-project-id");
    const validateUrl = app.getAttribute("data-validate-url");

    function showBootError(err) {
      const box = document.getElementById("builder-boot-error");
      if (!box) return;
      box.classList.remove("d-none");
      box.innerHTML =
        '<i class="bi bi-exclamation-triangle me-1"></i><strong>Редактор не инициализировался.</strong> ' +
        escapeHtml(String(err)) +
        " Обновите страницу (Ctrl+F5).";
    }

    let root;
    try {
      root = JSON.parse(seed.textContent);
    } catch (e) {
      console.error(e);
      showBootError("Не удалось прочитать JSON конфига: " + e);
      return;
    }

    function bootEditor(model, refresh) {
      const wrap = document.getElementById("builder-steps");
      const hasSsr = wrap && wrap.querySelector(".builder-step-card");
      if (hasSsr) {
        readModelFromDom(model);
        initSortables(model, refresh);
      } else {
        renderSteps(model, refresh);
      }
      renderPreview(model, pid);
      syncTextarea(model, pid);
    }

    try {
    const model = loadModel(root || {});

    const nameEl = document.getElementById("b-name");
    const verEl = document.getElementById("b-version");
    if (nameEl) nameEl.value = model.name || "";
    if (verEl) verEl.value = model.version || "1";

    let debounceTimer = null;

    /** Прочитать DOM → модель, опционально перерисовать (drag-and-drop, смена типа). */
    function refreshFromDom(structural) {
      readModelFromDom(model);
      if (structural) renderSteps(model, refreshFromDom);
      updateEmptyHints();
      renderPreview(model, pid);
      syncTextarea(model, pid);
    }

    /** Перерисовать из уже изменённой модели (добавление/удаление — DOM ещё старый). */
    function refreshFromModel() {
      renderSteps(model, refreshFromDom);
      updateEmptyHints();
      renderPreview(model, pid);
      syncTextarea(model, pid);
    }

    function updateEmptyHints() {
      document.querySelectorAll(".builder-step-card:not(.is-review)").forEach((card) => {
        const hint = card.querySelector(".builder-empty-hint");
        const count = card.querySelectorAll(".builder-field-block").length;
        if (hint) hint.classList.toggle("d-none", count > 0);
      });
    }
    function refreshDebounced() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        readModelFromDom(model);
        renderPreview(model, pid);
        syncTextarea(model, pid);
      }, 180);
    }

    // Текстовый ввод — без перерисовки (не теряем фокус).
    app.addEventListener("input", (e) => {
      if (e.target.closest("#builder-steps")) refreshDebounced();
    });

    // Смена типа поля и чекбоксы — мгновенно. Тип меняет верстку блока → структурно.
    app.addEventListener("change", (e) => {
      if (e.target.matches('[data-fk="type"]')) {
        refreshFromDom(true);
        return;
      }
      if (e.target.closest("#builder-steps")) {
        readModelFromDom(model);
        renderPreview(model, pid);
        syncTextarea(model, pid);
      }
    });

    // Авто-генерация field_id из подписи, если id ещё не трогали.
    app.addEventListener("input", (e) => {
      if (!e.target.matches('[data-fk="title"]')) return;
      const blk = e.target.closest(".builder-field-block");
      if (!blk) return;
      const idInp = blk.querySelector('[data-fk="field_id"]');
      if (idInp && !idInp.dataset.touched) {
        idInp.value = slugify(e.target.value);
      }
    });
    app.addEventListener("input", (e) => {
      if (e.target.matches('[data-fk="field_id"]')) e.target.dataset.touched = "1";
    });

    // Клики: добавить/удалить поле и шаг, раскрыть «Дополнительно».
    app.addEventListener("click", (e) => {
      const addStepBtn = e.target.closest("#builder-add-step");
      if (addStepBtn) {
        e.preventDefault();
        readModelFromDom(model);
        const n = model.steps.filter((s) => s.kind === "scroll_form").length + 1;
        const review = model.steps.find((s) => s.kind === "review");
        const newStep = { uid: uid(), kind: "scroll_form", id: "form" + n, form_title: "", fields: [] };
        model.steps = model.steps.filter((s) => s.kind !== "review").concat([newStep, review]);
        refreshFromModel();
        document.querySelector(`.builder-step-card[data-uid="${newStep.uid}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      const addType = e.target.closest("[data-add-type]");
      if (addType) {
        e.preventDefault();
        readModelFromDom(model);
        const card = addType.closest(".builder-step-card");
        const st = model.steps.find((s) => s.uid === card.dataset.uid);
        if (st) {
          const t = addType.getAttribute("data-add-type");
          st.fields.push({
            uid: uid(),
            field_id: "",
            type: t,
            title: t === "instruction" ? "" : "Новое поле",
            instructions: "",
            required: false,
            validationExtra: {},
          });
          refreshFromModel();
          const newCard = document.querySelector(`.builder-step-card[data-uid="${st.uid}"]`);
          const last = newCard?.querySelector(".builder-field-block:last-child [data-fk='field_id'], .builder-field-block:last-child [data-fk='instructions']");
          last?.focus();
        }
        return;
      }
      const delF = e.target.closest("[data-del-field]");
      if (delF) {
        e.preventDefault();
        readModelFromDom(model);
        const blk = delF.closest(".builder-field-block");
        const card = delF.closest(".builder-step-card");
        const st = model.steps.find((s) => s.uid === card.dataset.uid);
        if (st) st.fields = st.fields.filter((f) => f.uid !== blk.dataset.uid);
        refreshFromModel();
        return;
      }
      const delS = e.target.closest("[data-del-step]");
      if (delS) {
        e.preventDefault();
        readModelFromDom(model);
        const card = delS.closest(".builder-step-card");
        const scrolls = model.steps.filter((s) => s.kind === "scroll_form");
        if (scrolls.length <= 1) {
          flashError("Нужен хотя бы один экран сбора. Этот удалить нельзя.");
          return;
        }
        model.steps = model.steps.filter((s) => s.uid !== card.dataset.uid);
        refreshFromModel();
        return;
      }
      const adv = e.target.closest("[data-toggle-adv]");
      if (adv) {
        e.preventDefault();
        const box = adv.closest(".builder-step-card")?.querySelector(".builder-step-adv-box");
        box?.classList.toggle("d-none");
        adv.classList.toggle("active");
      }
    });

    ["b-name", "b-version"].forEach((id) => {
      document.getElementById(id)?.addEventListener("input", () => {
        model.name = document.getElementById("b-name")?.value.trim() || "";
        model.version = document.getElementById("b-version")?.value.trim() || "1";
        renderPreview(model, pid);
        syncTextarea(model, pid);
      });
    });

    document.getElementById("builder-btn-validate")?.addEventListener("click", async () => {
      readModelFromDom(model);
      const box = document.getElementById("builder-errors");
      if (!box) return;
      box.innerHTML = '<span class="ui-muted small">Проверка…</span>';
      try {
        const res = await fetch(validateUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") || "" },
          body: JSON.stringify(serialize(model, pid)),
        });
        const data = await res.json();
        if (data.ok) {
          box.innerHTML =
            '<div class="alert alert-success py-2 mb-0"><i class="bi bi-check-circle me-2"></i>Ошибок не найдено — можно сохранять.</div>';
        } else {
          box.innerHTML =
            '<div class="alert alert-danger py-2 mb-0"><strong>Проблемы:</strong><ul class="mb-0 mt-1 small">' +
            (data.errors || ["Неизвестная ошибка"]).map((err) => "<li>" + escapeHtml(err) + "</li>").join("") +
            "</ul></div>";
        }
      } catch (err) {
        box.innerHTML =
          '<div class="alert alert-danger py-2 mb-0">Запрос не удался: ' + escapeHtml(String(err)) + "</div>";
      }
    });

    document.getElementById("builder-form")?.addEventListener("submit", () => {
      clearTimeout(debounceTimer);
      readModelFromDom(model);
      syncTextarea(model, pid);
    });

    function flashError(msg) {
      const box = document.getElementById("builder-errors");
      if (!box) return;
      box.innerHTML = '<div class="alert alert-warning py-2 mb-0"><i class="bi bi-exclamation-triangle me-2"></i>' + escapeHtml(msg) + "</div>";
      setTimeout(() => {
        if (box.querySelector(".alert-warning")) box.innerHTML = "";
      }, 4000);
    }

    bootEditor(model, refreshFromDom);
    } catch (e) {
      console.error(e);
      showBootError(e);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
