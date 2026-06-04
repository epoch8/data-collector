(function () {
  "use strict";
  var form = document.getElementById("pkgFilters");
  if (form) {
    var projectSel = document.getElementById("fProject");

    form.addEventListener("change", function (e) {
      var t = e.target;
      if (!t.hasAttribute("data-autosubmit")) return;
      // Смена проекта сбрасывает поле/запрос/дату — у другого проекта другие поля.
      if (t === projectSel) {
        ["field", "q", "date"].forEach(function (name) {
          var el = form.elements[name];
          if (el) el.value = "";
        });
      }
      form.submit();
    });

    // Debounce для текстового поиска.
    var q = form.querySelector('input[name="q"]');
    if (q) {
      var timer = null;
      q.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(function () {
          form.submit();
        }, 450);
      });
    }

    // Чипы статуса.
    var phaseInput = document.getElementById("fPhase");
    form.querySelectorAll(".pkg-chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        if (phaseInput) phaseInput.value = chip.getAttribute("data-phase");
        form.submit();
      });
    });
  }

  // Копировать package_id.
  document.querySelectorAll(".pkg-copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var id = btn.getAttribute("data-copy");
      if (!navigator.clipboard) return;
      navigator.clipboard.writeText(id).then(function () {
        var icon = btn.querySelector("i");
        if (!icon) return;
        var prev = icon.className;
        icon.className = "bi bi-check-lg";
        setTimeout(function () {
          icon.className = prev;
        }, 1200);
      });
    });
  });
})();
