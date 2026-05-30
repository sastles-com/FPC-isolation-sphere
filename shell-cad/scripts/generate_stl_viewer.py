"""Generate a self-contained HTML STL viewer for any STL file.

Uses Three.js r134 CDN + STLLoader + OrbitControls.
The generated HTML loads the STL from a sibling URL on the same server,
so upload both the .stl and the .html to Lolipop together.

Usage:
    uv run python shell-cad/scripts/generate_stl_viewer.py shell-cad/output/foo.stl
    uv run python shell-cad/scripts/generate_stl_viewer.py shell-cad/output/foo.stl \
        --out web/output/foo_viewer.html \
        --title "Hex Pyramids T=81"
    uv run python shell-cad/scripts/generate_stl_viewer.py shell-cad/output/*.stl  # batch
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #111827; color: #f9fafb; font-family: monospace; overflow: hidden; }}
  #canvas-wrap {{ width: 100vw; height: 100vh; }}
  #hud {{
    position: absolute; top: 12px; left: 14px;
    background: rgba(0,0,0,.55); padding: 8px 12px; border-radius: 6px;
    font-size: 13px; line-height: 1.6; pointer-events: none;
  }}
  #hud .name {{ font-size: 15px; font-weight: bold; color: #60a5fa; }}
  #hud .hint {{ color: #9ca3af; font-size: 11px; margin-top: 4px; }}
  #loading {{
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%,-50%);
    font-size: 14px; color: #9ca3af;
  }}
</style>
</head>
<body>
<div id="canvas-wrap"></div>
<div id="hud">
  <div class="name">{title}</div>
  <div id="stats"></div>
  <div class="hint">Drag: rotate &nbsp;|&nbsp; Scroll: zoom &nbsp;|&nbsp; Right-drag: pan</div>
</div>
<div id="loading">Loading…</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.134.0/examples/js/loaders/STLLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.134.0/examples/js/controls/OrbitControls.js"></script>
<script>
(function () {{
  const STL_URL = "{stl_url}";

  // Scene setup
  const wrap = document.getElementById("canvas-wrap");
  const renderer = new THREE.WebGLRenderer({{ antialias: true }});
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  renderer.shadowMap.enabled = true;
  wrap.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x111827);

  const camera = new THREE.PerspectiveCamera(45, wrap.clientWidth / wrap.clientHeight, 0.1, 2000);
  camera.position.set(0, 0, 200);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;

  // Lights
  scene.add(new THREE.AmbientLight(0xffffff, 0.45));
  const sun = new THREE.DirectionalLight(0xffffff, 0.85);
  sun.position.set(80, 120, 100);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0x8ab4f8, 0.35);
  fill.position.set(-80, -60, -80);
  scene.add(fill);

  // Axis helper (small, bottom-left)
  scene.add(new THREE.AxesHelper(20));

  // Load STL
  const loader = new THREE.STLLoader();
  loader.load(
    STL_URL,
    function (geometry) {{
      document.getElementById("loading").style.display = "none";

      geometry.computeVertexNormals();
      geometry.computeBoundingBox();
      const box = geometry.boundingBox;
      const center = new THREE.Vector3();
      box.getCenter(center);
      geometry.translate(-center.x, -center.y, -center.z);

      const size = new THREE.Vector3();
      box.getSize(size);
      const maxDim = Math.max(size.x, size.y, size.z);
      camera.position.set(0, 0, maxDim * 1.8);
      controls.update();

      const mat = new THREE.MeshPhongMaterial({{
        color: 0x3b82f6, specular: 0x334155, shininess: 60,
        side: THREE.DoubleSide
      }});
      const mesh = new THREE.Mesh(geometry, mat);
      scene.add(mesh);

      const tris = geometry.index
        ? geometry.index.count / 3
        : geometry.attributes.position.count / 3;
      document.getElementById("stats").textContent =
        `${{Math.round(size.x)}}×${{Math.round(size.y)}}×${{Math.round(size.z)}} mm  |  ${{tris.toLocaleString()}} tri`;
    }},
    undefined,
    function (err) {{
      document.getElementById("loading").textContent = "Load error: " + err;
    }}
  );

  // Resize handler
  window.addEventListener("resize", () => {{
    camera.aspect = wrap.clientWidth / wrap.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  }});

  // Render loop
  (function animate() {{
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }})();
}})();
</script>
</body>
</html>
"""


def generate_viewer(stl_path: Path, out_path: Path, title: str | None = None) -> Path:
    """Generate an HTML viewer for *stl_path*, written to *out_path*."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy STL next to the HTML (same directory) so relative URL works
    stl_dest = out_path.parent / stl_path.name
    if stl_dest.resolve() != stl_path.resolve():
        shutil.copy2(stl_path, stl_dest)

    t = title or stl_path.stem.replace("_", " ")
    html = _HTML_TEMPLATE.format(
        title=t,
        stl_url=stl_path.name,  # relative URL — same directory
    )
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stl", nargs="+", type=Path, help="Input STL file(s)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output HTML path (single-file mode). "
                             "Default: web/output/<stem>_viewer.html")
    parser.add_argument("--title", default=None,
                        help="Page title (default: STL filename stem)")
    args = parser.parse_args()

    for stl in args.stl:
        if not stl.exists():
            print(f"  ⚠ not found: {stl}")
            continue
        if args.out and len(args.stl) == 1:
            out = args.out
        else:
            out = Path("web/output") / f"{stl.stem}_viewer.html"

        result = generate_viewer(stl, out, args.title)
        print(f"  → {result}")
        print(f"     upload: shell-cad/scripts/upload_to_lolipop.sh {result}")


if __name__ == "__main__":
    main()
