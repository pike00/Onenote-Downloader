/**
 * Minimal OneNote InkML → canvas renderer for bake-off path A.
 * Coordinates: himetric → CSS px at 96 DPI (himetric * 96 / 2540).
 */
(function () {
  const HIMETRIC_TO_PX = 96 / 2540;

  function himetricToPx(v) {
    return Number(v) * HIMETRIC_TO_PX;
  }

  function parseBrushes(inkEl) {
    const brushes = {};
    const brushNodes = inkEl.getElementsByTagNameNS("http://www.w3.org/2003/InkML", "brush");
    const list = brushNodes.length
      ? brushNodes
      : inkEl.getElementsByTagName("brush");
    for (const brush of list) {
      const id =
        brush.getAttribute("xml:id") || brush.getAttribute("id") || "";
      const props = {};
      const propNodes = brush.getElementsByTagNameNS(
        "http://www.w3.org/2003/InkML",
        "brushProperty"
      );
      const propsList = propNodes.length
        ? propNodes
        : brush.getElementsByTagName("brushProperty");
      for (const p of propsList) {
        props[p.getAttribute("name")] = p.getAttribute("value");
      }
      const widthH = parseFloat(props.width || "75");
      const transparency = parseFloat(props.transparency || "0");
      brushes[id] = brushes["#" + id] = {
        widthPx: Math.max(1, himetricToPx(widthH)),
        color: props.color || "#000000",
        alpha: Math.max(0, Math.min(1, 1 - transparency)),
        rasterOp: (props.rasterOp || "copyPen").toLowerCase(),
      };
    }
    return brushes;
  }

  function hexToRgba(hex, alpha) {
    const h = (hex || "#000000").replace("#", "");
    const r = parseInt(h.slice(0, 2), 16) || 0;
    const g = parseInt(h.slice(2, 4), 16) || 0;
    const b = parseInt(h.slice(4, 6), 16) || 0;
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function renderInkML(inkmlText, canvas) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(inkmlText, "application/xml");
    const inkEl =
      doc.getElementsByTagNameNS("http://www.w3.org/2003/InkML", "ink")[0] ||
      doc.documentElement;
    const brushes = parseBrushes(inkEl);
    const defaultBrush = {
      widthPx: 2.5,
      color: "#000000",
      alpha: 1,
      rasterOp: "copypen",
    };

    let maxX = 0;
    let maxY = 0;
    const traces = [];
    const traceNodes = inkEl.getElementsByTagNameNS(
      "http://www.w3.org/2003/InkML",
      "trace"
    );
    const tlist = traceNodes.length
      ? traceNodes
      : inkEl.getElementsByTagName("trace");

    for (const t of tlist) {
      const brushRef = t.getAttribute("brushRef") || "";
      const brush = brushes[brushRef] || brushes[brushRef.replace(/^#/, "")] || defaultBrush;
      const raw = (t.textContent || "").trim();
      if (!raw) continue;
      const pts = [];
      for (const point of raw.split(",")) {
        const parts = point.trim().split(/\s+/);
        if (parts.length < 2) continue;
        const x = himetricToPx(parts[0]);
        const y = himetricToPx(parts[1]);
        pts.push([x, y]);
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
      if (pts.length >= 2) traces.push({ pts, brush });
    }

    const cssW = Math.max(
      canvas.width || 0,
      Math.ceil(maxX + 40),
      parseInt(canvas.getAttribute("width") || "0", 10) || 0
    );
    const cssH = Math.max(
      canvas.height || 0,
      Math.ceil(maxY + 40),
      parseInt(canvas.getAttribute("height") || "0", 10) || 0
    );
    canvas.width = cssW;
    canvas.height = cssH;
    canvas.style.width = cssW + "px";
    canvas.style.height = cssH + "px";

    const ctx = canvas.getContext("2d");
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (const { pts, brush } of traces) {
      let a = brush.alpha;
      if (brush.rasterOp === "maskpen") a = Math.min(a, 0.55);
      ctx.strokeStyle = hexToRgba(brush.color, a);
      ctx.lineWidth = brush.widthPx;
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.stroke();
    }
    return { width: cssW, height: cssH, traceCount: traces.length };
  }

  async function boot() {
    const canvas = document.getElementById("ink-canvas");
    if (!canvas) return;
    try {
      let text = "";
      const inline = document.getElementById("inkml-data");
      if (inline && inline.textContent) {
        text = inline.textContent;
      } else {
        const src = canvas.getAttribute("data-inkml-src");
        if (!src) throw new Error("no inkml source");
        const resp = await fetch(src);
        text = await resp.text();
      }
      const result = renderInkML(text, canvas);
      canvas.dataset.traceCount = String(result.traceCount);
    } catch (err) {
      console.error("Ink render failed", err);
      canvas.dataset.inkError = String(err);
    } finally {
      canvas.dataset.inkReady = "1";
    }
  }

  window.OneNoteBakeoffInk = { renderInkML, boot };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
