/* Display-only downscale for package images in the browser.
 * Originals in storage / download links are never modified.
 * The full file is still fetched once; we re-encode a smaller JPEG for <img>.
 */
(function () {
  "use strict";

  var cache = Object.create(null);
  var DEFAULT_MAX_EDGE = 1920;
  var JPEG_Q = 0.82;

  function forUrl(url, opts) {
    opts = opts || {};
    var maxEdge = opts.maxEdge || DEFAULT_MAX_EDGE;
    if (!url) {
      return Promise.resolve(url);
    }
    var key = String(maxEdge) + "|" + url;
    if (cache[key]) return cache[key];

    cache[key] = new Promise(function (resolve) {
      var img = new Image();
      img.decoding = "async";
      img.onload = function () {
        var w = img.naturalWidth || 0;
        var h = img.naturalHeight || 0;
        if (!w || !h || Math.max(w, h) <= maxEdge) {
          resolve(url);
          return;
        }
        var scale = maxEdge / Math.max(w, h);
        var tw = Math.max(1, Math.round(w * scale));
        var th = Math.max(1, Math.round(h * scale));
        var canvas = document.createElement("canvas");
        canvas.width = tw;
        canvas.height = th;
        var ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(url);
          return;
        }
        ctx.drawImage(img, 0, 0, tw, th);
        if (!canvas.toBlob) {
          try {
            resolve(canvas.toDataURL("image/jpeg", JPEG_Q));
          } catch (e) {
            resolve(url);
          }
          return;
        }
        canvas.toBlob(
          function (blob) {
            if (!blob) {
              resolve(url);
              return;
            }
            resolve(URL.createObjectURL(blob));
          },
          "image/jpeg",
          JPEG_Q,
        );
      };
      img.onerror = function () {
        resolve(url);
      };
      img.src = url;
    });

    return cache[key];
  }

  window.PkgDisplayImage = { forUrl: forUrl };
})();
