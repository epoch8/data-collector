(function () {
  document.querySelectorAll(".ui-copy-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var id = btn.getAttribute("data-copy-target");
      var el = id ? document.getElementById(id) : null;
      var text = el ? (el.textContent || "").trim() : (btn.getAttribute("data-copy-text") || "").trim();
      if (!text || !navigator.clipboard) return;
      navigator.clipboard.writeText(text).then(function () {
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
