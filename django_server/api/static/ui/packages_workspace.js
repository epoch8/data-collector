(function () {
  "use strict";

  var ws = document.getElementById("pkgWorkspace");
  if (!ws) return;
  var editable = ws.getAttribute("data-editable") === "1";
  var form = document.getElementById("pkgForm");
  var saveBtn = document.getElementById("pkgSaveBtn");
  var revertBtn = document.getElementById("pkgRevertBtn");

  // ── Tabs ──────────────────────────────────────────────────────────────────
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".pkg-tab"));
  var panels = Array.prototype.slice.call(document.querySelectorAll(".pkg-panel"));
  function activate(name) {
    tabs.forEach(function (t) { t.classList.toggle("active", t.getAttribute("data-tab") === name); });
    panels.forEach(function (p) { p.classList.toggle("active", p.getAttribute("data-panel") === name); });
    if (name === "viz" && window.PkgViz) window.PkgViz.ensure();
  }
  tabs.forEach(function (t) {
    t.addEventListener("click", function () { activate(t.getAttribute("data-tab")); });
  });

  // ── Datetime read-only localized display ───────────────────────────────────
  document.querySelectorAll("[data-datetime]").forEach(function (el) {
    var raw = el.getAttribute("data-datetime");
    if (!raw) return;
    var d = new Date(raw);
    if (isNaN(d.getTime())) return;
    el.innerHTML =
      d.toLocaleString("ru-RU", {
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit",
      }) + '<span class="pkg-field__ro-sub d-block">' + raw + "</span>";
  });

  // ── Dirty tracking ──────────────────────────────────────────────────────────
  var inputs = Array.prototype.slice.call(document.querySelectorAll("input[data-field]"));
  function changedFields() {
    return inputs.filter(function (i) { return i.value !== (i.getAttribute("data-initial") || ""); });
  }
  function refreshDirty() {
    var dirty = editable && changedFields().length > 0;
    ws.classList.toggle("is-dirty", dirty);
    if (saveBtn && !saveBtn.hasAttribute("data-locked")) saveBtn.disabled = !dirty;
    if (revertBtn) revertBtn.disabled = !dirty;
    return dirty;
  }
  inputs.forEach(function (i) {
    i.addEventListener("input", refreshDirty);
  });

  window.addEventListener("beforeunload", function (e) {
    if (ws.classList.contains("is-dirty")) {
      e.preventDefault();
      e.returnValue = "";
    }
  });

  // ── Revert ────────────────────────────────────────────────────────────────
  if (revertBtn) {
    revertBtn.addEventListener("click", function () {
      if (!changedFields().length) return;
      inputs.forEach(function (i) { i.value = i.getAttribute("data-initial") || ""; });
      refreshDirty();
    });
  }

  // ── Save modal ──────────────────────────────────────────────────────────────
  var reasonInput = document.getElementById("pkgReasonInput");
  var customBox = document.getElementById("pkgReasonCustom");
  var changeCount = document.getElementById("pkgChangeCount");
  var modalEl = document.getElementById("pkgReasonModal");
  if (modalEl && modalEl.parentElement && modalEl.parentElement !== document.body) {
    document.body.appendChild(modalEl);
  }
  var modal = modalEl && window.bootstrap ? new window.bootstrap.Modal(modalEl, { focus: true }) : null;

  document.querySelectorAll('input[name="reasonPreset"]').forEach(function (r) {
    r.addEventListener("change", function () {
      var checked = document.querySelector('input[name="reasonPreset"]:checked');
      if (!checked) return;
      var custom = checked.value === "__custom__";
      if (customBox) customBox.classList.toggle("d-none", !custom);
      if (custom && customBox) customBox.focus();
    });
  });

  if (saveBtn) {
    saveBtn.addEventListener("click", function () {
      if (saveBtn.disabled) return;
      if (changeCount) changeCount.textContent = String(changedFields().length);
      if (modal) modal.show();
    });
  }

  var confirmBtn = document.getElementById("pkgConfirmSave");
  if (confirmBtn && form && reasonInput) {
    confirmBtn.addEventListener("click", function () {
      var sel = document.querySelector('input[name="reasonPreset"]:checked');
      var reason = sel ? sel.value : "";
      if (reason === "__custom__") reason = customBox ? customBox.value.trim() : "";
      if (!reason) {
        if (customBox) {
          customBox.classList.remove("d-none");
          customBox.focus();
        }
        return;
      }
      reasonInput.value = reason;
      ws.classList.remove("is-dirty");
      if (modal) modal.hide();
      confirmBtn.disabled = true;
      form.submit();
    });
  }

  // ── Sidebar search ──────────────────────────────────────────────────────────
  var sideSearch = document.getElementById("pkgSidebarSearch");
  var sideItems = Array.prototype.slice.call(document.querySelectorAll("#pkgSidebarList .pkg-sidebar__item"));
  var sideCount = document.getElementById("pkgSidebarCount");
  if (sideSearch) {
    sideSearch.addEventListener("input", function () {
      var q = sideSearch.value.trim().toLowerCase();
      var shown = 0;
      sideItems.forEach(function (it) {
        var match = !q || (it.getAttribute("data-search") || "").indexOf(q) !== -1;
        it.style.display = match ? "" : "none";
        if (match) shown++;
      });
      if (sideCount) sideCount.textContent = String(shown);
    });
  }
  // Scroll active package into view.
  var active = document.querySelector(".pkg-sidebar__item--active");
  if (active && active.scrollIntoView) active.scrollIntoView({ block: "center" });

  // ── Lightbox + display-only downscale (оригиналы в storage не трогаем) ─────
  var thumbs = Array.prototype.slice.call(document.querySelectorAll("[data-lightbox]"));
  var displayImage = window.PkgDisplayImage;

  // Превью в галерее Media: даунскейл только для <img>, download остаётся оригиналом.
  if (displayImage) {
    Array.prototype.forEach.call(
      document.querySelectorAll(".pkg-shot__frame--img img"),
      function (img) {
        var orig = img.getAttribute("src");
        if (!orig) return;
        displayImage.forUrl(orig, { maxEdge: 720 }).then(function (u) {
          if (u && img.getAttribute("src") === orig) img.src = u;
        });
      },
    );
  }

  if (thumbs.length) {
    var lb = document.createElement("div");
    lb.className = "pkg-lightbox";
    lb.innerHTML =
      '<div class="pkg-lightbox__bar"><span class="pkg-lightbox__name"></span>' +
      '<button type="button" class="btn btn-sm btn-outline-light" data-close>Закрыть ✕</button></div>' +
      '<div class="pkg-lightbox__stage">' +
      '<button type="button" class="pkg-lightbox__nav" data-prev>‹</button>' +
      '<img alt="">' +
      '<button type="button" class="pkg-lightbox__nav" data-next>›</button></div>';
    document.body.appendChild(lb);
    var lbImg = lb.querySelector("img");
    var lbName = lb.querySelector(".pkg-lightbox__name");
    var idx = 0;
    var lbGen = 0;
    function show(i) {
      idx = (i + thumbs.length) % thumbs.length;
      var t = thumbs[idx];
      var url = t.getAttribute("data-lightbox");
      lbName.textContent = t.getAttribute("data-name") || "";
      var gen = ++lbGen;
      if (!displayImage) {
        lbImg.src = url;
        return;
      }
      displayImage.forUrl(url, { maxEdge: 1920 }).then(function (u) {
        if (gen !== lbGen) return;
        lbImg.src = u || url;
      });
    }
    function open(i) { show(i); lb.classList.add("open"); }
    function close() { lb.classList.remove("open"); lbImg.src = ""; }
    thumbs.forEach(function (t, i) {
      t.addEventListener("click", function () { open(i); });
    });
    lb.querySelector("[data-close]").addEventListener("click", close);
    lb.querySelector("[data-prev]").addEventListener("click", function () { show(idx - 1); });
    lb.querySelector("[data-next]").addEventListener("click", function () { show(idx + 1); });
    lb.addEventListener("click", function (e) { if (e.target === lb) close(); });
    document.addEventListener("keydown", function (e) {
      if (!lb.classList.contains("open")) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowLeft") show(idx - 1);
      else if (e.key === "ArrowRight") show(idx + 1);
    });
  }

  refreshDirty();

  // ── JSON copy ─────────────────────────────────────────────────────────────
  var jsonPre = document.getElementById("pkgJsonPre");
  var jsonCopyBtn = document.getElementById("pkgJsonCopyBtn");
  if (jsonCopyBtn && jsonPre) {
    jsonCopyBtn.addEventListener("click", function () {
      var text = jsonPre.textContent || "";
      if (!text) return;
      function done() {
        var prev = jsonCopyBtn.innerHTML;
        jsonCopyBtn.innerHTML = '<i class="bi bi-check2 me-1"></i>Скопировано';
        setTimeout(function () { jsonCopyBtn.innerHTML = prev; }, 1600);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () {
          window.prompt("Скопируйте JSON:", text);
        });
      } else {
        window.prompt("Скопируйте JSON:", text);
        done();
      }
    });
  }

  // ── Delete modal ──────────────────────────────────────────────────────────
  var deleteBtn = document.getElementById("pkgDeleteBtn");
  var deleteAck = document.getElementById("pkgDeleteAck");
  var deleteSubmit = document.getElementById("pkgDeleteSubmit");
  var deleteModalEl = document.getElementById("pkgDeleteModal");
  if (deleteModalEl && deleteModalEl.parentElement && deleteModalEl.parentElement !== document.body) {
    document.body.appendChild(deleteModalEl);
  }
  var deleteModal = deleteModalEl && window.bootstrap
    ? new window.bootstrap.Modal(deleteModalEl, { focus: true })
    : null;
  function refreshDeleteAck() {
    if (deleteSubmit && deleteAck) deleteSubmit.disabled = !deleteAck.checked;
  }
  if (deleteAck) {
    deleteAck.addEventListener("change", refreshDeleteAck);
  }
  if (deleteBtn && deleteModal) {
    deleteBtn.addEventListener("click", function () {
      if (deleteAck) deleteAck.checked = false;
      refreshDeleteAck();
      deleteModal.show();
    });
  }
  if (deleteModalEl) {
    deleteModalEl.addEventListener("hidden.bs.modal", function () {
      if (deleteAck) deleteAck.checked = false;
      refreshDeleteAck();
    });
  }
})();
