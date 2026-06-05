import os
import streamlit.components.v1 as components


def render_metabase_dashboard(uuid: str, fallback_height: int = 3000) -> None:
    """Embed a public Metabase dashboard with auto height — no internal scrollbar."""
    MB_HOST = os.environ.get("METABASE_HOST", "http://localhost:3000")
    src = f"{MB_HOST}/public/dashboard/{uuid}#theme=night"
    components.html(f"""<!DOCTYPE html>
<html>
<head>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:100%; overflow:hidden; background:transparent; }}
#f {{ width:100%; border:none; display:block; }}
</style>
</head>
<body>
<iframe id="f" src="{src}" scrolling="no"
  sandbox="allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts allow-downloads">
</iframe>
<script>
const f = document.getElementById('f');
let prev = 0;
function sync() {{
  try {{
    const h = f.contentDocument.documentElement.scrollHeight;
    if (h > 100 && h !== prev) {{
      prev = h;
      f.style.height = h + 'px';
      window.parent.postMessage({{type:'streamlit:setFrameHeight', height: h}}, '*');
    }}
  }} catch(e) {{}}
}}
f.onload = function() {{
  sync();
  let n = 0;
  const t = setInterval(function() {{ sync(); if (++n > 40) clearInterval(t); }}, 750);
  try {{
    const obs = new ResizeObserver(sync);
    obs.observe(f.contentDocument.documentElement);
  }} catch(e) {{}}
}};
</script>
</body>
</html>""", height=fallback_height, scrolling=False)
