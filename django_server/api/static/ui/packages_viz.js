/* Packages visualisation tab — lazy init via window.PkgViz.ensure(). */
(function () {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";

  var PALETTE = {
    gt: { box: "#22c55e", boxFill: "rgba(34,197,94,0.08)", point: "#f59e0b", segment: "#c084fc", label: "GT" },
    inference: { box: "#06b6d4", boxFill: "rgba(6,182,212,0.08)", point: "#3b82f6", segment: "#8b5cf6", label: "Inference" },
  };

  // ── Depth colormap (port of depth-colormap.ts) ────────────────────────────
  var DEPTH_SENTINEL = 126.72;
  var INVALID_HIGH = 120;
  function isValidDepth(v) {
    return isFinite(v) && v < INVALID_HIGH && Math.abs(v - DEPTH_SENTINEL) >= 0.05;
  }
  function clamp01(x) { return Math.min(1, Math.max(0, x)); }
  function lerp(a, b, t) {
    return [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)];
  }
  function depthToRgb(t) {
    var x = clamp01(t);
    if (x < 0.33) return lerp([46, 91, 255], [0, 201, 201], x / 0.33);
    if (x < 0.66) return lerp([0, 201, 201], [245, 213, 71], (x - 0.33) / 0.33);
    return lerp([245, 213, 71], [240, 78, 78], (x - 0.66) / 0.34);
  }
  function depthRange(values) {
    var sample = [], step = Math.max(1, Math.floor(values.length / 16000));
    for (var i = 0; i < values.length; i += step) if (isValidDepth(values[i])) sample.push(values[i]);
    if (!sample.length) return { min: 0, max: 1 };
    sample.sort(function (a, b) { return a - b; });
    var lo = sample[Math.floor(sample.length * 0.05)] || sample[0];
    var hi = sample[Math.floor(sample.length * 0.95)] || sample[sample.length - 1];
    return hi <= lo ? { min: lo, max: lo + 0.01 } : { min: lo, max: hi };
  }

  // ── Minimal NPY parser (float32/float64, 2D) ──────────────────────────────
  function parseNpy(buf) {
    var bytes = new Uint8Array(buf);
    if (bytes[0] !== 0x93) throw new Error("not a npy file");
    var major = bytes[6];
    var headerLen, offset;
    var dv = new DataView(buf);
    if (major <= 1) { headerLen = dv.getUint16(8, true); offset = 10 + headerLen; }
    else { headerLen = dv.getUint32(8, true); offset = 12 + headerLen; }
    var headerStart = major <= 1 ? 10 : 12;
    var header = new TextDecoder("latin1").decode(bytes.subarray(headerStart, headerStart + headerLen));
    var descrM = header.match(/'descr':\s*'([^']+)'/);
    var shapeM = header.match(/'shape':\s*\(([^)]*)\)/);
    var descr = descrM ? descrM[1] : "<f4";
    var shape = shapeM ? shapeM[1].split(",").map(function (s) { return parseInt(s.trim(), 10); }).filter(function (n) { return !isNaN(n); }) : [];
    var count = shape.reduce(function (a, b) { return a * b; }, 1);
    var data;
    if (descr.indexOf("f4") !== -1) data = new Float32Array(buf, offset, count);
    else if (descr.indexOf("f8") !== -1) {
      var f8 = new Float64Array(buf, offset, count);
      data = new Float32Array(count);
      for (var i = 0; i < count; i++) data[i] = f8[i];
    } else throw new Error("unsupported dtype " + descr);
    var gh, gw;
    if (shape.length === 2) { gh = shape[0]; gw = shape[1]; }
    else if (shape.length === 3 && shape[2] === 1) { gh = shape[0]; gw = shape[1]; }
    else throw new Error("unsupported shape " + shape.join("x"));
    var valid = 0, sampled = 0, step = Math.max(1, Math.floor(data.length / 8000));
    for (var vi = 0; vi < data.length; vi += step) {
      sampled++;
      if (isValidDepth(data[vi])) valid++;
    }
    return {
      values: data,
      gridWidth: gw,
      gridHeight: gh,
      range: depthRange(data),
      validPixelRatio: sampled ? valid / sampled : 0,
    };
  }
  var depthCache = {};
  function loadDepth(url) {
    if (depthCache[url]) return depthCache[url];
    var p = fetch(url, { credentials: "include" })
      .then(function (r) { if (!r.ok) throw new Error("depth " + r.status); return r.arrayBuffer(); })
      .then(parseNpy);
    depthCache[url] = p;
    return p;
  }
  function sampleDepth(d, x, y) {
    if (x < 0 || y < 0 || x >= d.gridWidth || y >= d.gridHeight) return null;
    var v = d.values[y * d.gridWidth + x];
    return isValidDepth(v) ? v : null;
  }
  function sampleDepthAtImage(d, ix, iy, iw, ih) {
    var gx = Math.round(ix / iw * d.gridWidth);
    var gy = Math.round(iy / ih * d.gridHeight);
    return sampleDepth(d, gx, gy);
  }
  function formatDepthMeters(m) {
    if (!isFinite(m)) return "—";
    if (m >= 10) return m.toFixed(1) + " м";
    if (m >= 1) return m.toFixed(2) + " м";
    return (m * 100).toFixed(0) + " см";
  }
  function formatDepthRange(min, max) {
    return formatDepthMeters(min) + " – " + formatDepthMeters(max);
  }
  function clientToImageCoords(cx, cy, rect, iw, ih) {
    var scale = Math.min(rect.width / iw, rect.height / ih);
    var dw = iw * scale, dh = ih * scale;
    var ox = (rect.width - dw) / 2, oy = (rect.height - dh) / 2;
    var lx = cx - rect.left - ox, ly = cy - rect.top - oy;
    if (lx < 0 || ly < 0 || lx > dw || ly > dh) return null;
    return {
      x: Math.min(iw - 1, Math.max(0, Math.round((lx / dw) * iw))),
      y: Math.min(ih - 1, Math.max(0, Math.round((ly / dh) * ih))),
    };
  }

  // ── Label geometry (port of annotation-label-layout.ts) ───────────────────
  var FONT = 13, PADX = 6, PADY = 4;
  function textW(text, fs) {
    var w = 0;
    for (var i = 0; i < text.length; i++) {
      var c = text.charCodeAt(i);
      w += text[i] === " " ? fs * 0.3 : fs * (c > 127 ? 0.56 : 0.5);
    }
    return w;
  }
  function segLabelText(label, valueCm) {
    return (valueCm != null && isFinite(valueCm)) ? label + " — " + valueCm.toFixed(1) + " см" : label;
  }
  function layoutSegments(segments) {
    var placed = [], out = [];
    function aabb(mx, my, bw, bh, ang, off) {
      var rad = ang * Math.PI / 180;
      var cx = mx + (-Math.sin(rad)) * off, cy = my + Math.cos(rad) * off;
      var hw = bw / 2 + 4, hh = bh / 2 + 4;
      var c = Math.abs(Math.cos(rad)), s = Math.abs(Math.sin(rad));
      var ew = hw * c + hh * s, eh = hw * s + hh * c;
      return { x0: cx - ew, y0: cy - eh, x1: cx + ew, y1: cy + eh };
    }
    function overlap(a, b) {
      var g = 6;
      return !(a.x1 + g < b.x0 || b.x1 + g < a.x0 || a.y1 + g < b.y0 || b.y1 + g < a.y0);
    }
    segments.forEach(function (seg, idx) {
      var dx = seg.x2 - seg.x1, dy = seg.y2 - seg.y1;
      var ang = Math.atan2(dy, dx) * 180 / Math.PI;
      if (ang > 90) ang -= 180; if (ang < -90) ang += 180;
      var text = segLabelText(seg.label, seg.value_cm);
      var fs = text.length > 32 ? 11 : FONT;
      var bw = textW(text, fs) + PADX * 2, bh = fs + PADY * 2;
      var mx = (seg.x1 + seg.x2) / 2, my = (seg.y1 + seg.y2) / 2;
      var offs = [0, 16, -16, 28, -28, 40, -40];
      if (idx % 2 === 1) offs.reverse();
      var off = 0;
      for (var k = 0; k < offs.length; k++) {
        var box = aabb(mx, my, bw, bh, ang, offs[k]);
        var hit = placed.some(function (p) { return overlap(p, box); });
        if (!hit) { off = offs[k]; placed.push(box); break; }
      }
      out.push({ midX: mx, midY: my, angleDeg: ang, normalOffset: off, text: text, boxW: bw, boxH: bh, fs: fs });
    });
    return out;
  }
  function pointAnchor(px, py, idx, iw, ih) {
    var m = 48, nr = px > iw - m, nl = px < m, nt = py < m, nb = py > ih - m;
    if (nr && nt) return { dx: -10, dy: 14, anchor: "end" };
    if (nr) return { dx: -10, dy: -6, anchor: "end" };
    if (nl && nb) return { dx: 10, dy: -14, anchor: "start" };
    if (nl) return { dx: 10, dy: -6, anchor: "start" };
    if (nt) return { dx: 6, dy: 14, anchor: "start" };
    if (nb) return { dx: 6, dy: -14, anchor: "start" };
    var corners = [{ dx: 11, dy: -7, anchor: "start" }, { dx: -11, dy: -7, anchor: "end" }, { dx: 11, dy: 10, anchor: "start" }, { dx: -11, dy: 10, anchor: "end" }];
    return corners[idx % 4];
  }
  function gtLabelColor(label) {
    var h = 0;
    for (var i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) >>> 0;
    return "hsl(" + (h % 360) + " 70% 52%)";
  }

  // ── SVG helpers ───────────────────────────────────────────────────────────
  function svgEl(name, attrs) {
    var e = document.createElementNS(SVG_NS, name);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) e.setAttribute(k, attrs[k]);
    return e;
  }
  function yoloLabel(g, x, y, text, color, anchor, valign) {
    if (!text) return;
    var fs = text.length > 32 ? 11 : FONT;
    var bw = textW(text, fs) + PADX * 2, bh = fs + PADY * 2;
    var bx = x;
    if (anchor === "middle") bx = x - bw / 2; else if (anchor === "end") bx = x - bw;
    var by = y - bh;
    if (valign === "on") by = y - bh / 2; else if (valign === "below") by = y;
    var tx = anchor === "middle" ? x : anchor === "end" ? bx + bw - PADX : bx + PADX;
    g.appendChild(svgEl("rect", { x: bx, y: by, width: bw, height: bh, rx: 2, ry: 2, fill: color, "fill-opacity": 0.92 }));
    var t = svgEl("text", { x: tx, y: by + bh / 2, fill: "#fff", "font-size": fs, "font-weight": 600, "text-anchor": anchor, "dominant-baseline": "central" });
    t.textContent = text;
    g.appendChild(t);
  }

  // ── Main controller ───────────────────────────────────────────────────────
  var root, blobMap, slides = [], inited = false, loading = false;
  var depthBaseUrl = "/ui/packages/depth/";

  function resolveDepthBase() {
    var el = document.getElementById("pkgViz") || document.getElementById("pkgWorkspace");
    var base = (el && el.getAttribute("data-depth-base")) || depthBaseUrl;
    if (!base) base = "/ui/packages/depth/";
    if (base.charAt(base.length - 1) !== "/") base += "/";
    return base;
  }

  function depthNpyUrl(filename) {
    return resolveDepthBase() + filename;
  }
  var state = {
    index: 0, showGt: false, showInference: true, showBoxes: false, showLabels: false,
    showDepth: false, depthMode: "split", depthOpacity: 0.5, selected: null, probe: null,
    depthData: null, depthLoading: false, depthError: null,
  };
  var depthResizeObs = [];

  function currentSlide() { return slides[state.index] || null; }

  function depthUrlFor(slide) {
    if (!slide || !slide.inference) return null;
    var inf = slide.inference;
    var dm = inf.depth_map;
    if (dm && dm.depth_url) return dm.depth_url;
    var asset = dm && dm.asset_path;
    if (asset) {
      if (asset.charAt(0) === "/") return asset;
      return depthNpyUrl(asset.split("/").pop());
    }
    if (inf.source_export) return depthNpyUrl(inf.source_export.replace(/\.json$/i, "") + ".npy");
    return null;
  }

  function buildLayers(slide) {
    var layers = [];
    if (slide.gt) {
      var a = slide.gt.annotation || {};
      layers.push({ id: "gt", palette: "gt", visible: state.showGt, boxes: a.boxes || [], points: a.points || [], segments: [] });
    }
    if (slide.inference) {
      var ia = (slide.inference.inference && slide.inference.inference.annotation) || {};
      layers.push({ id: "inf", palette: "inference", visible: state.showInference, boxes: ia.boxes || [], points: ia.keypoints || [], segments: ia.segments || [] });
    }
    return layers;
  }

  function imageSize(slide) {
    var sz = (slide.gt && slide.gt.image_size) || (slide.inference && slide.inference.image_size) || { width: 1024, height: 640 };
    return { w: sz.width || 1024, h: sz.height || 640 };
  }

  // Build SVG overlay into a given <svg> element.
  function renderOverlay(svg, slide) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var sz = imageSize(slide);
    var layers = buildLayers(slide).filter(function (l) { return l.visible; });
    var active = state.selected;

    layers.forEach(function (layer) {
      var p = PALETTE[layer.palette];
      var g = svgEl("g", {});

      if (state.showBoxes) {
        layer.boxes.forEach(function (box) {
          var w = Math.max(0, box.xbr - box.xtl), h = Math.max(0, box.ybr - box.ytl);
          g.appendChild(svgEl("rect", { x: box.xtl, y: box.ytl, width: w, height: h, fill: p.boxFill, stroke: p.box, "stroke-width": 2, "vector-effect": "non-scaling-stroke" }));
          if (state.showLabels) yoloLabel(g, box.xtl, box.ytl, box.label || p.label, p.box, "start", "above");
        });
      }

      if (layer.segments && layer.segments.length) {
        var layout = layoutSegments(layer.segments);
        layer.segments.forEach(function (seg, idx) {
          g.appendChild(svgEl("line", { x1: seg.x1, y1: seg.y1, x2: seg.x2, y2: seg.y2, stroke: p.segment, "stroke-width": 2.5, "stroke-dasharray": "8 5", "vector-effect": "non-scaling-stroke", opacity: 0.9 }));
          if (state.showLabels) {
            var L = layout[idx];
            var lg = svgEl("g", { transform: "translate(" + L.midX + "," + L.midY + ") rotate(" + L.angleDeg + ")" });
            var ig = svgEl("g", { transform: "translate(0," + L.normalOffset + ")" });
            ig.appendChild(svgEl("rect", { x: -L.boxW / 2, y: -L.boxH / 2, width: L.boxW, height: L.boxH, rx: 2, ry: 2, fill: p.segment, "fill-opacity": 0.93 }));
            var tt = svgEl("text", { x: 0, y: 0, fill: "#fff", "font-size": L.fs, "font-weight": 600, "text-anchor": "middle", "dominant-baseline": "central" });
            tt.textContent = L.text; ig.appendChild(tt); lg.appendChild(ig); g.appendChild(lg);
          }
        });
      }

      layer.points.forEach(function (pt, idx) {
        var isActive = active && active.layerId === layer.id && active.index === idx;
        var dimmed = state.selected && !(state.selected.layerId === layer.id && state.selected.index === idx);
        var color = layer.palette === "gt" ? gtLabelColor(pt.label) : p.point;
        var pg = svgEl("g", { class: "annotation-keypoint", opacity: dimmed && !isActive ? 0.35 : 1 });
        pg.appendChild(svgEl("circle", { cx: pt.x, cy: pt.y, r: 14, fill: "transparent" }));
        pg.appendChild(svgEl("circle", { cx: pt.x, cy: pt.y, r: isActive ? 8 : 6, fill: "rgba(15,17,23,0.8)", stroke: color, "stroke-width": isActive ? 2.5 : 2, "vector-effect": "non-scaling-stroke" }));
        pg.appendChild(svgEl("circle", { cx: pt.x, cy: pt.y, r: isActive ? 3 : 2.5, fill: color }));
        if (state.showLabels || isActive) {
          var an = pointAnchor(pt.x, pt.y, idx, sz.w, sz.h);
          yoloLabel(pg, pt.x + an.dx, pt.y + an.dy, pt.label, color, an.anchor, "on");
        }
        pg.addEventListener("click", function (e) {
          e.stopPropagation();
          var same = state.selected && state.selected.layerId === layer.id && state.selected.index === idx;
          state.selected = same ? null : { layerId: layer.id, index: idx };
          rerenderDynamic();
        });
        g.appendChild(pg);
      });

      svg.appendChild(g);
    });
  }

  // Rebuild only overlay + side lists (cheap), keep image/depth.
  var refs = {};
  function rerenderDynamic() {
    var slide = currentSlide();
    if (!slide) return;
    renderOverlay(refs.svg, slide);
    renderSide(slide);
    syncToggles();
    if (state.showDepth && state.depthData) {
      var sz = imageSize(slide);
      renderPhotoProbe(sz.w, sz.h);
      repaintDepthViews();
    }
  }

  function renderSide(slide) {
    var box = refs.side;
    box.innerHTML = "";
    var layers = buildLayers(slide);

    layers.forEach(function (layer) {
      if (!layer.visible || !layer.points.length) return;
      var p = PALETTE[layer.palette];
      var card = document.createElement("div");
      card.className = "pkg-viz__card";
      var title = document.createElement("div");
      title.className = "pkg-viz__card-title";
      title.textContent = (layer.palette === "gt" ? "GT точки" : "Inference точки") + " (" + layer.points.length + ")";
      card.appendChild(title);
      var ul = document.createElement("ul");
      ul.className = "pkg-kp-list";
      layer.points.forEach(function (pt, idx) {
        var li = document.createElement("li");
        li.className = "pkg-kp";
        var sel = state.selected;
        if (sel && sel.layerId === layer.id && sel.index === idx) li.classList.add("active");
        var color = layer.palette === "gt" ? gtLabelColor(pt.label) : p.point;
        var conf = pt.confidence != null ? '<span class="pkg-kp__conf">' + Math.round(pt.confidence * 100) + "%</span>" : "";
        li.innerHTML = '<span class="pkg-kp__label"><span class="pkg-kp__dot" style="background:' + color + '"></span><span class="text">' + escapeHtml(pt.label) + "</span></span>" + conf;
        li.addEventListener("click", function () {
          var same = state.selected && state.selected.layerId === layer.id && state.selected.index === idx;
          state.selected = same ? null : { layerId: layer.id, index: idx };
          rerenderDynamic();
        });
        ul.appendChild(li);
      });
      card.appendChild(ul);
      box.appendChild(card);
    });

    // Metrics (distances) from inference.
    var inf = slide.inference && slide.inference.inference;
    if (state.showInference && inf && inf.distances && Object.keys(inf.distances).length) {
      var mcard = document.createElement("div");
      mcard.className = "pkg-viz__card";
      var mt = document.createElement("div");
      mt.className = "pkg-viz__card-title";
      mt.textContent = "Метрики (см)";
      mcard.appendChild(mt);
      Object.keys(inf.distances).forEach(function (k) {
        var row = document.createElement("div");
        row.className = "pkg-metric";
        row.innerHTML = "<span>" + escapeHtml(k) + '</span><span class="pkg-metric__val">' + Number(inf.distances[k]).toFixed(1) + "</span>";
        mcard.appendChild(row);
      });
      box.appendChild(mcard);
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function syncToggles() {
    Object.keys(refs.toggles || {}).forEach(function (key) {
      var btn = refs.toggles[key];
      if (btn) btn.classList.toggle("on", !!state[key]);
    });
  }

  // ── Depth rendering (port DepthMapViewer) ─────────────────────────────────
  function rasterDepthBitmap(d, mode, vmin, vmax) {
    var cacheKey = mode + "|" + vmin + "|" + vmax;
    if (d._bitmap && d._bitmapKey === cacheKey) return d._bitmap;
    var img = new ImageData(d.gridWidth, d.gridHeight), data = img.data;
    for (var y = 0; y < d.gridHeight; y++) {
      for (var x = 0; x < d.gridWidth; x++) {
        var v = d.values[y * d.gridWidth + x], i = (y * d.gridWidth + x) * 4;
        if (!isValidDepth(v)) {
          if (mode === "overlay") { data[i + 3] = 0; }
          else {
            var ch = ((x >> 2) ^ (y >> 2)) & 1;
            data[i] = ch ? 22 : 16; data[i + 1] = ch ? 26 : 19; data[i + 2] = ch ? 36 : 28; data[i + 3] = 255;
          }
          continue;
        }
        var t = clamp01((v - vmin) / (vmax - vmin)), rgb = depthToRgb(t);
        data[i] = rgb[0]; data[i + 1] = rgb[1]; data[i + 2] = rgb[2]; data[i + 3] = 255;
      }
    }
    d._bitmap = img;
    d._bitmapKey = cacheKey;
    return img;
  }

  function paintDepthToDisplay(canvas, frame, d, iw, ih, mode, opacity, probe) {
    if (!canvas || !frame || !d) return;
    var w = Math.max(1, Math.round(frame.clientWidth));
    var h = Math.max(1, Math.round(frame.clientHeight));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    var off = document.createElement("canvas");
    off.width = d.gridWidth;
    off.height = d.gridHeight;
    var offCtx = off.getContext("2d");
    var vmin = d.range.min, vmax = d.range.max;
    var rasterMode = mode === "overlay" ? "overlay" : "opaque";
    offCtx.putImageData(rasterDepthBitmap(d, rasterMode, vmin, vmax), 0, 0);
    ctx.clearRect(0, 0, w, h);
    if (mode === "split") {
      var g = ctx.createLinearGradient(0, 0, 0, h);
      g.addColorStop(0, "#0c0e14");
      g.addColorStop(1, "#080a0f");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);
    }
    var scale = Math.min(w / iw, h / ih);
    var drawW = iw * scale, drawH = ih * scale;
    var ox = (w - drawW) / 2, oy = (h - drawH) / 2;
    ctx.imageSmoothingEnabled = true;
    ctx.globalAlpha = mode === "overlay" ? opacity : 1;
    ctx.drawImage(off, 0, 0, d.gridWidth, d.gridHeight, ox, oy, drawW, drawH);
    ctx.globalAlpha = 1;
    if (mode === "split") {
      ctx.strokeStyle = "rgba(251, 146, 60, 0.15)";
      ctx.lineWidth = 1;
      ctx.strokeRect(ox + 0.5, oy + 0.5, drawW - 1, drawH - 1);
    }
    if (probe) {
      var px = ox + (probe.x / iw) * drawW;
      var py = oy + (probe.y / ih) * drawH;
      ctx.beginPath();
      ctx.arc(px, py, 11, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(15, 17, 23, 0.55)";
      ctx.fill();
      ctx.strokeStyle = "rgba(255, 255, 255, 0.92)";
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.strokeStyle = "rgba(251, 146, 60, 0.95)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(px - 16, py);
      ctx.lineTo(px + 16, py);
      ctx.moveTo(px, py - 16);
      ctx.lineTo(px, py + 16);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#fb923c";
      ctx.fill();
    }
  }

  function repaintDepthViews() {
    var slide = currentSlide();
    if (!slide || !state.depthData) return;
    var sz = imageSize(slide);
    var probe = state.probe;
    if (state.depthMode === "split" && refs.depthSplit) {
      paintDepthToDisplay(refs.depthSplit.canvas, refs.depthSplit.frame, state.depthData, sz.w, sz.h, "split", 1, probe);
      positionDepthTooltip(refs.depthSplit, sz.w, sz.h, probe);
    }
    if (state.depthMode === "overlay" && refs.depthOverlay) {
      paintDepthToDisplay(refs.depthOverlay.canvas, refs.depthOverlay.frame, state.depthData, sz.w, sz.h, "overlay", state.depthOpacity, probe);
      positionDepthTooltip(refs.depthOverlay, sz.w, sz.h, probe);
    }
    renderPhotoProbe(sz.w, sz.h);
  }

  function positionDepthTooltip(view, iw, ih, probe) {
    if (!view || !view.tooltip) return;
    if (!probe) {
      view.tooltip.style.display = "none";
      return;
    }
    view.tooltip.style.display = "";
    view.tooltip.style.left = (probe.x / iw) * 100 + "%";
    view.tooltip.style.top = (probe.y / ih) * 100 + "%";
    if (view.tooltipValue) view.tooltipValue.textContent = formatDepthMeters(probe.depthM);
  }

  function renderPhotoProbe(iw, ih) {
    if (!refs.probeSvg) return;
    while (refs.probeSvg.firstChild) refs.probeSvg.removeChild(refs.probeSvg.firstChild);
    var probe = state.probe;
    if (!probe || !state.showDepth) {
      refs.probeSvg.style.display = "none";
      return;
    }
    refs.probeSvg.style.display = "";
    var g = svgEl("g", { transform: "translate(" + probe.x + "," + probe.y + ")" });
    g.appendChild(svgEl("circle", { cx: 0, cy: 0, r: 11, fill: "rgba(15,17,23,0.55)", stroke: "rgba(255,255,255,0.92)", "stroke-width": 2, "vector-effect": "non-scaling-stroke" }));
    g.appendChild(svgEl("line", { x1: -16, y1: 0, x2: 16, y2: 0, stroke: "rgba(251,146,60,0.95)", "stroke-width": 1.5, "vector-effect": "non-scaling-stroke" }));
    g.appendChild(svgEl("line", { x1: 0, y1: -16, x2: 0, y2: 16, stroke: "rgba(251,146,60,0.95)", "stroke-width": 1.5, "vector-effect": "non-scaling-stroke" }));
    g.appendChild(svgEl("circle", { cx: 0, cy: 0, r: 3, fill: "#fb923c" }));
    refs.probeSvg.appendChild(g);
    refs.probeSvg.style.display = "";
  }

  function updateDepthLegend(d) {
    if (!refs.depthSplit) return;
    if (refs.depthSplit.chip) {
      refs.depthSplit.chip.textContent = "~" + Math.round((d.validPixelRatio || 0) * 100) + "% кадра";
    }
    if (refs.depthSplit.rangeEl) {
      refs.depthSplit.rangeEl.textContent = formatDepthRange(d.range.min, d.range.max);
    }
  }

  function updateProbeBar() {
    if (!refs.probeBar) return;
    var readout = refs.probeBar.readout;
    readout.innerHTML = "";
    if (state.depthLoading) {
      var s = document.createElement("span");
      s.className = "depth-probe-bar__status depth-probe-bar__status--loading";
      s.textContent = "Загрузка карты…";
      readout.appendChild(s);
      return;
    }
    if (state.depthError) {
      var e = document.createElement("span");
      e.className = "depth-probe-bar__status depth-probe-bar__status--error";
      e.textContent = state.depthError;
      readout.appendChild(e);
      return;
    }
    if (state.probe) {
      var m = document.createElement("div");
      m.className = "depth-probe-bar__measure";
      m.innerHTML =
        '<span class="depth-probe-bar__measure-label">Расстояние</span>' +
        '<span class="depth-probe-bar__depth">' + formatDepthMeters(state.probe.depthM) + "</span>" +
        '<span class="depth-probe-bar__coords">(' + state.probe.x + ", " + state.probe.y + ")</span>";
      readout.appendChild(m);
      return;
    }
    var idle = document.createElement("span");
    idle.className = "depth-probe-bar__status";
    idle.textContent = "Наведите на фото или карту глубины";
    readout.appendChild(idle);
  }

  function setProbe(probe) {
    state.probe = probe;
    updateProbeBar();
    repaintDepthViews();
  }

  function layoutDepthUI() {
    var depthUrl = depthUrlFor(currentSlide());
    var active = state.showDepth && depthUrl;
    if (refs.probeBar) refs.probeBar.root.classList.toggle("is-visible", !!active);
    if (refs.vizDual) refs.vizDual.classList.toggle("viz-dual--single", !active || state.depthMode === "overlay");
    if (refs.depthCol) refs.depthCol.classList.toggle("is-visible", !!active && state.depthMode === "split");
    if (refs.annotationStage) refs.annotationStage.classList.toggle("annotation-stage--depth", !!active);
    if (refs.depthOverlay && refs.depthOverlay.root) {
      refs.depthOverlay.root.style.display = active && state.depthMode === "overlay" ? "" : "none";
    }
    if (refs.probeBar && refs.probeBar.opacityWrap) {
      refs.probeBar.opacityWrap.classList.toggle("is-visible", active && state.depthMode === "overlay");
    }
    if (refs.probeBar && refs.probeBar.splitBtn && refs.probeBar.overlayBtn) {
      refs.probeBar.splitBtn.classList.toggle("depth-mode-btn--on", state.depthMode === "split");
      refs.probeBar.overlayBtn.classList.toggle("depth-mode-btn--on", state.depthMode === "overlay");
    }
  }

  function observeDepthFrame(frame) {
    if (typeof ResizeObserver === "undefined" || !frame) return;
    var ro = new ResizeObserver(function () { repaintDepthViews(); });
    ro.observe(frame);
    depthResizeObs.push(ro);
  }

  function buildDepthView(compact) {
    var view = document.createElement("div");
    view.className = "depth-view" + (compact ? " depth-view--compact" : "");
    var out = { root: view, frame: null, canvas: null, tooltip: null, tooltipValue: null, chip: null, rangeEl: null };
    if (!compact) {
      var head = document.createElement("div");
      head.className = "depth-view__head";
      head.innerHTML =
        '<div class="depth-view__head-text">' +
        '<span class="depth-view__badge">Z</span>' +
        '<div><span class="depth-view__title">Карта глубины</span>' +
        '<span class="depth-view__subtitle">расстояние до камеры · метры</span></div></div>';
      out.chip = document.createElement("span");
      out.chip.className = "depth-view__chip";
      out.chip.textContent = "~0% кадра";
      head.appendChild(out.chip);
      view.appendChild(head);
    }
    out.frame = document.createElement("div");
    out.frame.className = "depth-view__frame" + (compact ? " depth-view__frame--overlay" : " depth-view__frame--split");
    out.canvas = document.createElement("canvas");
    out.canvas.className = "depth-view__canvas";
    out.tooltip = document.createElement("div");
    out.tooltip.className = "depth-view__tooltip";
    out.tooltip.style.display = "none";
    out.tooltipValue = document.createElement("span");
    out.tooltipValue.className = "depth-view__tooltip-value";
    out.tooltip.appendChild(out.tooltipValue);
    out.frame.appendChild(out.canvas);
    out.frame.appendChild(out.tooltip);
    view.appendChild(out.frame);
    if (!compact) {
      var footer = document.createElement("div");
      footer.className = "depth-view__footer";
      var wrap = document.createElement("div");
      wrap.className = "depth-view__legend-wrap";
      var leg = document.createElement("div");
      leg.className = "depth-view__legend";
      leg.setAttribute("aria-hidden", "true");
      var nearWord = document.createElement("span");
      nearWord.className = "depth-view__legend-word";
      nearWord.textContent = "ближе";
      leg.appendChild(nearWord);
      var bar = document.createElement("div");
      bar.className = "depth-view__legend-bar";
      for (var i = 0; i < 32; i++) {
        var rgb = depthToRgb(i / 31);
        var step = document.createElement("span");
        step.className = "depth-view__legend-step";
        step.style.background = "rgb(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ")";
        bar.appendChild(step);
      }
      leg.appendChild(bar);
      var farWord = document.createElement("span");
      farWord.className = "depth-view__legend-word";
      farWord.textContent = "дальше";
      leg.appendChild(farWord);
      wrap.appendChild(leg);
      out.rangeEl = document.createElement("p");
      out.rangeEl.className = "depth-view__range";
      wrap.appendChild(out.rangeEl);
      footer.appendChild(wrap);
      var hint = document.createElement("p");
      hint.className = "depth-view__hint";
      hint.textContent = "Шахматный фон — нет данных. Наведите на цветную область коровы.";
      footer.appendChild(hint);
      view.appendChild(footer);
    }
    return out;
  }

  function buildDepthProbeBar() {
    var bar = document.createElement("div");
    bar.className = "depth-probe-bar";
    var left = document.createElement("div");
    left.className = "depth-probe-bar__left";
    left.innerHTML = '<span class="depth-probe-bar__label">Глубина</span>';
    var modes = document.createElement("div");
    modes.className = "depth-probe-bar__modes";
    modes.setAttribute("role", "group");
    modes.setAttribute("aria-label", "Режим отображения");
    var splitBtn = document.createElement("button");
    splitBtn.type = "button";
    splitBtn.className = "depth-mode-btn depth-mode-btn--on";
    splitBtn.textContent = "Рядом";
    var overlayBtn = document.createElement("button");
    overlayBtn.type = "button";
    overlayBtn.className = "depth-mode-btn";
    overlayBtn.textContent = "Наложение";
    modes.appendChild(splitBtn);
    modes.appendChild(overlayBtn);
    left.appendChild(modes);
    var opacityWrap = document.createElement("label");
    opacityWrap.className = "depth-probe-bar__opacity";
    var op = document.createElement("input");
    op.type = "range";
    op.min = 15;
    op.max = 85;
    op.value = 50;
    op.className = "depth-range";
    op.title = "Прозрачность";
    var opVal = document.createElement("span");
    opVal.className = "depth-probe-bar__opacity-val";
    opVal.textContent = "50%";
    opacityWrap.appendChild(op);
    opacityWrap.appendChild(opVal);
    left.appendChild(opacityWrap);
    bar.appendChild(left);
    var readout = document.createElement("div");
    readout.className = "depth-probe-bar__readout";
    bar.appendChild(readout);
    splitBtn.addEventListener("click", function () {
      state.depthMode = "split";
      layoutDepthUI();
      if (state.showDepth) renderSlideKeepDepth();
    });
    overlayBtn.addEventListener("click", function () {
      state.depthMode = "overlay";
      layoutDepthUI();
      if (state.showDepth) renderSlideKeepDepth();
    });
    op.addEventListener("input", function () {
      state.depthOpacity = op.value / 100;
      opVal.textContent = Math.round(state.depthOpacity * 100) + "%";
      repaintDepthViews();
    });
    return { root: bar, readout: readout, splitBtn: splitBtn, overlayBtn: overlayBtn, opacityWrap: opacityWrap, op: op, opVal: opVal };
  }

  function handleProbePointer(e, frameEl) {
    if (!state.showDepth || !state.depthData) return;
    var slide = currentSlide();
    if (!slide) return;
    var sz = imageSize(slide);
    var c = clientToImageCoords(e.clientX, e.clientY, frameEl.getBoundingClientRect(), sz.w, sz.h);
    if (!c) { setProbe(null); return; }
    var depthM = sampleDepthAtImage(state.depthData, c.x, c.y, sz.w, sz.h);
    if (depthM == null) { setProbe(null); return; }
    setProbe({ x: c.x, y: c.y, depthM: depthM });
  }

  // ── Full render of current slide ──────────────────────────────────────────
  function renderSlide() {
    var slide = currentSlide();
    if (!slide) return;
    var sz = imageSize(slide);

    refs.title.innerHTML = "Кадр <strong>" + escapeHtml(slide.key.split("/").pop()) + "</strong> · " + (state.index + 1) + " / " + slides.length;

    // Stage image
    refs.img.src = slide.url;
    refs.svg.setAttribute("viewBox", "0 0 " + sz.w + " " + sz.h);
    if (refs.probeSvg) refs.probeSvg.setAttribute("viewBox", "0 0 " + sz.w + " " + sz.h);

    // CVAT link
    var cvat = slide.gt && slide.gt.cvat_link;
    refs.cvat.style.display = cvat ? "" : "none";
    if (cvat) refs.cvat.href = cvat;

    // Depth availability
    var depthUrl = depthUrlFor(slide);
    refs.depthToggle.disabled = !depthUrl;
    state.depthData = null;
    state.depthLoading = false;
    state.depthError = null;
    setProbe(null);
    layoutDepthUI();
    updateProbeBar();

    renderOverlay(refs.svg, slide);
    renderSide(slide);
    renderFilmstrip();
    syncToggles();

    if (state.showDepth && depthUrl) applyDepth(depthUrl);
    else renderPhotoProbe(sz.w, sz.h);
  }

  function applyDepth(depthTarget) {
    if (!depthTarget) return;
    var url = depthTarget.charAt(0) === "/" ? depthTarget : depthNpyUrl(depthTarget);
    state.depthLoading = true;
    state.depthError = null;
    state.depthData = null;
    updateProbeBar();
    layoutDepthUI();
    loadDepth(url).then(function (d) {
      state.depthLoading = false;
      if (!state.showDepth || depthUrlFor(currentSlide()) !== depthTarget) return;
      delete d._bitmap;
      delete d._bitmapKey;
      state.depthData = d;
      updateDepthLegend(d);
      layoutDepthUI();
      updateProbeBar();
      repaintDepthViews();
    }).catch(function (err) {
      console.warn("Depth map load failed:", url, err);
      state.depthLoading = false;
      state.depthError = "Не удалось загрузить карту";
      state.depthData = null;
      if (depthUrlFor(currentSlide()) === depthTarget) {
        refs.depthToggle.disabled = true;
        state.showDepth = false;
        syncToggles();
      }
      layoutDepthUI();
      updateProbeBar();
    });
  }

  function renderFilmstrip() {
    var strip = refs.strip;
    if (slides.length <= 1) { strip.style.display = "none"; return; }
    strip.style.display = "";
    strip.innerHTML = "";
    slides.forEach(function (s, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "pkg-filmstrip__item" + (i === state.index ? " active" : "");
      b.innerHTML = '<img src="' + s.url + '" alt=""><span class="pkg-filmstrip__num">' + (i + 1) + "</span>";
      b.addEventListener("click", function () { goTo(i); });
      strip.appendChild(b);
    });
  }

  function goTo(i) {
    state.index = (i + slides.length) % slides.length;
    state.selected = null;
    state.probe = null;
    renderSlide();
  }

  // ── Export ─────────────────────────────────────────────────────────────────
  function downloadBlob(blob, name) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = name; document.body.appendChild(a); a.click();
    a.remove(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function exportJson() {
    var slide = currentSlide();
    if (!slide) return;
    var doc = {
      format_version: 1,
      exported_at: new Date().toISOString(),
      image_file: slide.key.split("/").pop(),
      manifest_blob: slide.key,
      cow_keypoint_annotation: slide.gt || null,
      cow_inference_result: slide.inference || null,
    };
    downloadBlob(new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" }), (doc.image_file || "frame") + ".annotation.json");
  }

  function exportPng() {
    var slide = currentSlide();
    if (!slide) return;
    var sz = imageSize(slide);
    var img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = function () {
      var canvas = document.createElement("canvas");
      canvas.width = sz.w; canvas.height = sz.h;
      var ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, sz.w, sz.h);
      if (state.showDepth && state.depthData) {
        var dc = document.createElement("canvas");
        dc.width = state.depthData.gridWidth; dc.height = state.depthData.gridHeight;
        var vmin = state.depthData.range.min, vmax = state.depthData.range.max;
        var mode = state.depthMode === "overlay" ? "overlay" : "opaque";
        dc.getContext("2d").putImageData(rasterDepthBitmap(state.depthData, mode, vmin, vmax), 0, 0);
        if (state.depthMode === "overlay") { ctx.globalAlpha = state.depthOpacity; ctx.drawImage(dc, 0, 0, sz.w, sz.h); ctx.globalAlpha = 1; }
      }
      // Draw SVG overlay on top by serializing it.
      var svgStr = new XMLSerializer().serializeToString(refs.svg);
      var svgImg = new Image();
      svgImg.onload = function () {
        ctx.drawImage(svgImg, 0, 0, sz.w, sz.h);
        canvas.toBlob(function (blob) { if (blob) downloadBlob(blob, slide.key.split("/").pop().replace(/\.[^.]+$/, "") + ".viz.png"); });
      };
      svgImg.onerror = function () {
        canvas.toBlob(function (blob) { if (blob) downloadBlob(blob, slide.key.split("/").pop().replace(/\.[^.]+$/, "") + ".viz.png"); });
      };
      var clone = refs.svg.cloneNode(true);
      clone.setAttribute("xmlns", SVG_NS);
      clone.setAttribute("width", sz.w); clone.setAttribute("height", sz.h);
      svgImg.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(new XMLSerializer().serializeToString(clone))));
    };
    img.onerror = function () { alert("Не удалось загрузить изображение для экспорта."); };
    img.src = slide.url;
  }

  // ── DOM skeleton ────────────────────────────────────────────────────────────
  function makeToggle(key, label, dotColor) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pkg-toggle";
    btn.innerHTML = (dotColor ? '<span class="pkg-toggle__dot" style="background:' + dotColor + '"></span>' : "") + label;
    btn.addEventListener("click", function () {
      if (btn.disabled) return;
      state[key] = !state[key];
      if (key === "showDepth") renderSlide(); else rerenderDynamic();
      if (key === "showDepth" && state.showDepth) {
        var u = depthUrlFor(currentSlide());
        if (u) applyDepth(u);
      }
      if (key === "showDepth" && !state.showDepth) {
        state.depthData = null;
        state.depthLoading = false;
        state.depthError = null;
        setProbe(null);
        layoutDepthUI();
        updateProbeBar();
      }
    });
    refs.toggles[key] = btn;
    return btn;
  }

  function buildSkeleton() {
    refs.toggles = {};
    root.innerHTML = "";

    // Toolbar
    var tb = document.createElement("div");
    tb.className = "pkg-viz__toolbar";
    refs.title = document.createElement("div");
    refs.title.className = "pkg-viz__title";
    tb.appendChild(refs.title);

    tb.appendChild(makeToggle("showGt", "GT", PALETTE.gt.point));
    tb.appendChild(makeToggle("showInference", "Inference", PALETTE.inference.point));
    var sep1 = document.createElement("div"); sep1.className = "pkg-viz__toolbar-sep"; tb.appendChild(sep1);
    tb.appendChild(makeToggle("showBoxes", "BBox"));
    tb.appendChild(makeToggle("showLabels", "Подписи"));
    refs.depthToggle = makeToggle("showDepth", "Глубина"); tb.appendChild(refs.depthToggle);

    var sep2 = document.createElement("div"); sep2.className = "pkg-viz__toolbar-sep"; tb.appendChild(sep2);

    refs.cvat = document.createElement("a");
    refs.cvat.className = "pkg-toggle"; refs.cvat.target = "_blank"; refs.cvat.rel = "noopener";
    refs.cvat.innerHTML = '<i class="bi bi-box-arrow-up-right"></i> CVAT';
    tb.appendChild(refs.cvat);

    // Export menu
    var exp = document.createElement("div"); exp.className = "pkg-export";
    var expBtn = document.createElement("button");
    expBtn.type = "button"; expBtn.className = "pkg-toggle";
    expBtn.innerHTML = '<i class="bi bi-download"></i> Экспорт';
    var menu = document.createElement("div"); menu.className = "pkg-export__menu";
    var pngItem = document.createElement("button"); pngItem.type = "button"; pngItem.className = "pkg-export__item"; pngItem.textContent = "PNG (с разметкой)";
    var jsonItem = document.createElement("button"); jsonItem.type = "button"; jsonItem.className = "pkg-export__item"; jsonItem.textContent = "Аннотация (JSON)";
    pngItem.addEventListener("click", function () { menu.classList.remove("open"); exportPng(); });
    jsonItem.addEventListener("click", function () { menu.classList.remove("open"); exportJson(); });
    menu.appendChild(pngItem); menu.appendChild(jsonItem);
    expBtn.addEventListener("click", function (e) { e.stopPropagation(); menu.classList.toggle("open"); });
    document.addEventListener("click", function () { menu.classList.remove("open"); });
    exp.appendChild(expBtn); exp.appendChild(menu); tb.appendChild(exp);

    var sep3 = document.createElement("div"); sep3.className = "pkg-viz__toolbar-sep"; tb.appendChild(sep3);
    var prev = document.createElement("button"); prev.type = "button"; prev.className = "pkg-toggle"; prev.textContent = "‹";
    var next = document.createElement("button"); next.type = "button"; next.className = "pkg-toggle"; next.textContent = "›";
    prev.addEventListener("click", function () { goTo(state.index - 1); });
    next.addEventListener("click", function () { goTo(state.index + 1); });
    tb.appendChild(prev); tb.appendChild(next);
    root.appendChild(tb);

    refs.body = document.createElement("div");
    refs.body.className = "pkg-viz__body";

    refs.canvasCol = document.createElement("div");
    refs.canvasCol.className = "pkg-viz__canvas-col";

    refs.probeBar = buildDepthProbeBar();
    refs.canvasCol.appendChild(refs.probeBar.root);

    refs.vizDual = document.createElement("div");
    refs.vizDual.className = "viz-dual viz-dual--single";

    refs.photoCol = document.createElement("div");
    refs.photoCol.className = "viz-dual__photo";

    refs.annotationStage = document.createElement("div");
    refs.annotationStage.className = "annotation-stage";

    var stage = document.createElement("div");
    stage.className = "pkg-stage";
    refs.stageFrame = document.createElement("div");
    refs.stageFrame.className = "pkg-stage__frame";
    refs.img = document.createElement("img");
    refs.img.className = "pkg-stage__img";
    refs.img.alt = "";
    refs.img.addEventListener("load", function () { repaintDepthViews(); });
    refs.depthOverlay = buildDepthView(true);
    refs.depthOverlay.root.style.display = "none";
    refs.svg = svgEl("svg", { class: "pkg-stage__svg", preserveAspectRatio: "xMidYMid meet" });
    refs.probeSvg = svgEl("svg", { class: "annotation-stage__probe-svg", preserveAspectRatio: "xMidYMid meet" });
    refs.stageFrame.appendChild(refs.img);
    refs.stageFrame.appendChild(refs.svg);
    refs.stageFrame.appendChild(refs.depthOverlay.root);
    refs.stageFrame.appendChild(refs.probeSvg);
    stage.appendChild(refs.stageFrame);
    var legend = document.createElement("div");
    legend.className = "pkg-stage__legend";
    legend.innerHTML =
      '<span><span class="dot" style="background:' + PALETTE.gt.point + '"></span>GT</span>' +
      '<span><span class="dot" style="background:' + PALETTE.inference.point + '"></span>Inference</span>';
    stage.appendChild(legend);
    refs.annotationStage.appendChild(stage);
    refs.photoCol.appendChild(refs.annotationStage);

    refs.depthCol = document.createElement("div");
    refs.depthCol.className = "viz-dual__depth";
    refs.depthSplit = buildDepthView(false);
    refs.depthCol.appendChild(refs.depthSplit.root);
    refs.vizDual.appendChild(refs.photoCol);
    refs.vizDual.appendChild(refs.depthCol);
    refs.canvasCol.appendChild(refs.vizDual);

    refs.side = document.createElement("div");
    refs.side.className = "pkg-viz__side";
    refs.body.appendChild(refs.canvasCol);
    refs.body.appendChild(refs.side);
    root.appendChild(refs.body);

    refs.strip = document.createElement("div");
    refs.strip.className = "pkg-filmstrip";
    refs.canvasCol.appendChild(refs.strip);

    function bindProbe(frame) {
      frame.addEventListener("pointermove", function (e) { handleProbePointer(e, frame); });
      frame.addEventListener("pointerleave", function () { setProbe(null); });
    }
    bindProbe(refs.stageFrame);
    bindProbe(refs.depthSplit.frame);
    bindProbe(refs.depthOverlay.frame);
    observeDepthFrame(refs.depthSplit.frame);
    observeDepthFrame(refs.depthOverlay.frame);
    observeDepthFrame(refs.stageFrame);

    updateProbeBar();

    // Keyboard nav
    document.addEventListener("keydown", function (e) {
      var panel = root.closest(".pkg-panel");
      if (!panel || !panel.classList.contains("active")) return;
      if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
      if (e.key === "ArrowLeft") goTo(state.index - 1);
      else if (e.key === "ArrowRight") goTo(state.index + 1);
      else if (e.key === "Escape" && state.selected) { state.selected = null; rerenderDynamic(); }
    });
  }

  function renderSlideKeepDepth() {
    setProbe(null);
    layoutDepthUI();
    var u = depthUrlFor(currentSlide());
    if (u) applyDepth(u);
  }

  function buildSlides(data) {
    var byKey = {}, order = [];
    (data.gt || []).forEach(function (r) {
      var k = r.manifest_blob_key;
      if (!byKey[k]) { byKey[k] = {}; order.push(k); }
      byKey[k].gt = r;
    });
    (data.inference || []).forEach(function (r) {
      var k = r.manifest_blob_key;
      if (!byKey[k]) { byKey[k] = {}; order.push(k); }
      byKey[k].inference = r;
    });
    return order
      .filter(function (k) { return blobMap[k]; })
      .map(function (k) { return { key: k, url: blobMap[k], gt: byKey[k].gt || null, inference: byKey[k].inference || null }; });
  }

  function init() {
    if (inited || loading) return;
    loading = true;
    root = document.getElementById("pkgViz");
    if (!root) { loading = false; return; }
    depthBaseUrl = resolveDepthBase();
    try {
      blobMap = JSON.parse(document.getElementById("pkgBlobMap").textContent || "{}");
    } catch (e) { blobMap = {}; }
    var url = document.getElementById("pkgWorkspace").getAttribute("data-viz-url");
    fetch(url, { credentials: "include" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        slides = buildSlides(data);
        if (!slides.length) {
          root.innerHTML = '<div class="ui-muted p-5 text-center">Нет кадров с разметкой для этого пакета.</div>';
          inited = true; loading = false; return;
        }
        buildSkeleton();
        renderSlide();
        inited = true; loading = false;
      })
      .catch(function () {
        root.innerHTML = '<div class="ui-muted p-5 text-center">Не удалось загрузить визуализацию.</div>';
        loading = false;
      });
  }

  window.PkgViz = { ensure: init };
})();
