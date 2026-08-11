(function () {
  "use strict";

  var root = document.getElementById("pkgProtocol");
  if (!root) return;

  var protocolInputs = Array.prototype.slice.call(
    root.querySelectorAll("input[data-protocol-field], select[data-protocol-field]"),
  );

  function dataInputFor(fieldId) {
    return document.querySelector(
      '#pkgForm input[data-field="' + fieldId + '"], #pkgForm select[data-field="' + fieldId + '"]',
    );
  }

  function displayValue(el) {
    if (!el) return "";
    if (el.tagName === "SELECT") {
      var opt = el.options[el.selectedIndex];
      if (opt && opt.value) return opt.textContent || opt.value;
      return "";
    }
    return el.value || "";
  }

  function setPreview(fieldId, value, label) {
    var nodes = root.querySelectorAll('[data-preview-for="' + fieldId + '"]');
    var text = label && String(label).trim() !== ""
      ? String(label)
      : (value && String(value).trim() !== "" ? String(value) : "—");
    nodes.forEach(function (n) { n.textContent = text; });
  }

  function syncToData(input) {
    var fid = input.getAttribute("data-sync-field");
    if (!fid) return;
    var target = dataInputFor(fid);
    if (!target) return;
    if (target.value !== input.value) {
      target.value = input.value;
      target.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  function syncFromData(input) {
    var fid = input.getAttribute("data-sync-field");
    if (!fid) return;
    var source = dataInputFor(fid);
    if (!source) return;
    // Если в протоколе пусто, а в данных есть значение — подтянуть
    if ((!input.value || !String(input.value).trim()) && source.value) {
      input.value = source.value;
      setPreview(fid, source.value);
    }
  }

  protocolInputs.forEach(function (input) {
    syncFromData(input);
    setPreview(
      input.getAttribute("data-protocol-field"),
      input.value,
      displayValue(input),
    );
    function onChange() {
      setPreview(
        input.getAttribute("data-protocol-field"),
        input.value,
        displayValue(input),
      );
      syncToData(input);
    }
    input.addEventListener("input", onChange);
    input.addEventListener("change", onChange);
  });

  // Обратная синхронизация: правки на вкладке «Данные»
  document.querySelectorAll("#pkgForm input[data-field], #pkgForm select[data-field]").forEach(function (di) {
    function onDataChange() {
      var fid = di.getAttribute("data-field");
      var pi = root.querySelector(
        'input[data-protocol-field="' + fid + '"], select[data-protocol-field="' + fid + '"]',
      );
      if (!pi) return;
      if (pi.value !== di.value) {
        pi.value = di.value;
        setPreview(fid, di.value, displayValue(pi));
      }
    }
    di.addEventListener("input", onDataChange);
    di.addEventListener("change", onDataChange);
  });

  var fillBtn = document.getElementById("pkgProtocolFillInference");
  if (fillBtn) {
    fillBtn.addEventListener("click", function () {
      var filled = 0;
      protocolInputs.forEach(function (input) {
        var cur = (input.value || "").trim();
        var inf = (input.getAttribute("data-inference") || "").trim();
        if (cur || !inf) return;
        input.value = inf;
        setPreview(input.getAttribute("data-protocol-field"), inf);
        syncToData(input);
        filled++;
      });
      fillBtn.classList.add("btn-outline-success");
      var prev = fillBtn.innerHTML;
      fillBtn.innerHTML =
        '<i class="bi bi-check2 me-1"></i>' +
        (filled ? "Заполнено: " + filled : "Нечего заполнять");
      setTimeout(function () {
        fillBtn.innerHTML = prev;
        fillBtn.classList.remove("btn-outline-success");
      }, 1600);
    });
  }

  var exportBtn = document.getElementById("pkgProtocolExportBtn");
  if (exportBtn) {
    exportBtn.addEventListener("click", function () {
      // Не блокировать уход страницы при скачивании ZIP
      var ws = document.getElementById("pkgWorkspace");
      if (ws) ws.classList.remove("is-dirty");
    });
  }

  // Превью-миниатюры: даунскейл только для отображения
  if (window.PkgDisplayImage) {
    Array.prototype.forEach.call(
      root.querySelectorAll(".pkg-protocol__thumb img"),
      function (img) {
        var orig = img.getAttribute("src");
        if (!orig) return;
        window.PkgDisplayImage.forUrl(orig, { maxEdge: 480 }).then(function (u) {
          if (u && img.getAttribute("src") === orig) img.src = u;
        });
      },
    );
  }
})();
