#!/usr/bin/env python3
"""
render.py — turn a portable architecture model (JSON) into ONE self-contained,
interactive, zero-egress HTML file.

The output inlines the Cytoscape library, the compound-layout engine (fcose), the
brand icons it needs (as base64 data: URIs), and the model itself — so opening it
in a browser makes ZERO network requests. Nothing about the codebase ever leaves
the machine. Standard library only — no pip install, runs against any repo.

Usage:
    python render.py --model model.json --out arch.html [--title "My System"]
                     [--no-icons] [--lib cytoscape.min.js] [--template template.html]

Brand icons: each node may carry an "icon" field (a Simple Icons slug, e.g.
"googlecloud", "supabase", "postgresql"). render.py also auto-matches common
brands from the label. Anything without a brand logo gets a neutral category
glyph keyed off its "type", so every node looks deliberate. See
../references/model-schema.md.
"""
import argparse
import base64
import html as _html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
ASSETS = SKILL / "assets"
DEFAULT_TEMPLATE = ASSETS / "template.html"
DEFAULT_LIB = ASSETS / "cytoscape.min.js"
DEFAULT_ICONS = ASSETS / "simple-icons.json"
# Hierarchical compound-layout engine (ELK), in dependency order: elk.bundled.js
# exposes the global ELK (runs in-process, no web-worker fetch), then
# cytoscape-elk.js consumes it. This is what gives the clean, non-overlapping
# nested "boxes" look. Skipped entirely under --light (built-in 'cose' is used).
LAYOUT_LIBS = ["elk.bundled.js", "cytoscape-elk.js"]

VALID_VIEWS = {"cloud", "data", "agentic", "structure", "system"}
TOKEN_RE = re.compile(r"(__TITLE__|__CYTOSCAPE_LIB__|__LAYOUT_LIBS__|__ICONS_JSON__|__MODEL_JSON__)")

# type -> accent colour (mirrors the template's TYPES borders); used to tint the
# fallback category glyphs so an icon-less node still reads by role.
TYPE_COLORS = {
    "external": "#c2410c", "datastore": "#15803d", "vectorstore": "#0e7490",
    "router": "#1d4ed8", "agent": "#6d28d9", "tool": "#a16207", "mcp": "#4338ca",
    "table": "#334155", "service": "#475569", "queue": "#92400e",
    "config": "#6b7280", "component": "#64748b",
}

# Neutral, house-style line glyphs (24x24, stroke = {C}). One per node type, so
# anything without a brand logo is still a clean, intentional tile.
_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{C}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">')
FALLBACK_GLYPHS = {
    "datastore":   _SVG + '<ellipse cx="12" cy="5" rx="7.5" ry="3"/><path d="M4.5 5v14c0 1.7 3.36 3 7.5 3s7.5-1.3 7.5-3V5"/><path d="M4.5 12c0 1.7 3.36 3 7.5 3s7.5-1.3 7.5-3"/></svg>',
    "vectorstore": _SVG + '<ellipse cx="12" cy="5" rx="7.5" ry="3"/><path d="M4.5 5v14c0 1.7 3.36 3 7.5 3s7.5-1.3 7.5-3V5"/><path d="M4.5 12c0 1.7 3.36 3 7.5 3s7.5-1.3 7.5-3"/><circle cx="9" cy="18" r=".6"/><circle cx="12" cy="19" r=".6"/><circle cx="15" cy="18" r=".6"/></svg>',
    "external":    _SVG + '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z"/></svg>',
    "router":      _SVG + '<circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="12" cy="18" r="2"/><path d="M5 8v2.5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8M12 13v3"/></svg>',
    "agent":       _SVG + '<rect x="4.5" y="8" width="15" height="11" rx="2.5"/><path d="M12 8V4.6"/><circle cx="12" cy="3.4" r="1.2"/><path d="M9 13h.01M15 13h.01"/></svg>',
    "tool":        _SVG + '<path d="M14.6 6.2a3.8 3.8 0 0 0-5.1 5.1L3.5 17.3l3.2 3.2 6-6a3.8 3.8 0 0 0 5.1-5.1l-2.3 2.3-2.2-.6-.6-2.2z"/></svg>',
    "mcp":         _SVG + '<path d="M9 3v5M15 3v5"/><path d="M7.5 8h9v2.5a4.5 4.5 0 0 1-9 0z"/><path d="M12 15.5V21"/></svg>',
    "table":       _SVG + '<rect x="3.5" y="4" width="17" height="16" rx="2"/><path d="M3.5 9.5h17M3.5 15h17M9.5 4v16"/></svg>',
    "service":     _SVG + '<path d="M12 2.5l8.5 4.75v9.5L12 21.5 3.5 16.75v-9.5z"/><path d="M3.7 7.2 12 12l8.3-4.8M12 12v9.3"/></svg>',
    "queue":       _SVG + '<path d="M12 2.8l8.5 4.6L12 12 3.5 7.4z"/><path d="M3.5 12 12 16.6 20.5 12M3.5 16.6 12 21.2l8.5-4.6"/></svg>',
    "config":      _SVG + '<circle cx="12" cy="12" r="2.6"/><path d="M12 3v2.4M12 18.6V21M4.2 7.5l2.1 1.2M17.7 15.3l2.1 1.2M19.8 7.5l-2.1 1.2M6.3 15.3l-2.1 1.2"/></svg>',
    "component":   _SVG + '<rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M9 4v16"/></svg>',
}

# Curated label->slug hints so even un-annotated models pick up obvious brands.
# Ordered (specific first); only entries whose slug exists in the vendored set are
# kept (see _alias_table). The primary path is an explicit node["icon"].
_ALIAS_RAW = [
    ("supabase", "supabase"), ("postgres", "postgresql"), ("mysql", "mysql"),
    ("mariadb", "mariadb"), ("sqlite", "sqlite"), ("mongo", "mongodb"),
    ("redis", "redis"), ("elasticsearch", "elasticsearch"), ("snowflake", "snowflake"),
    ("bigquery", "googlecloud"), ("cloud run", "googlecloud"), ("cloud storage", "googlecloud"),
    ("cloud sql", "googlecloud"), ("cloud scheduler", "googlecloud"), ("secret manager", "googlecloud"),
    ("pub/sub", "googlecloud"), ("firestore", "firebase"), ("firebase", "firebase"),
    ("google cloud", "googlecloud"), ("gcr", "googlecloud"), ("vertex", "googlecloud"),
    ("gemini", "googlegemini"), ("anthropic", "claude"), ("claude", "claude"),
    ("hugging", "huggingface"), ("cohere", "cohere"), ("mistral", "mistralai"),
    ("whatsapp", "whatsapp"), ("telegram", "telegram"), ("twilio", "twilio"),
    ("discord", "discord"), ("slack", "slack"), ("meta flow", "meta"),
    ("messenger", "messenger"), ("instagram", "instagram"),
    ("brevo", "brevo"), ("sendinblue", "brevo"), ("sendgrid", "sendgrid"),
    ("mailgun", "mailgun"), ("mercado", "mercadopago"), ("stripe", "stripe"),
    ("paypal", "paypal"), ("gitlab", "gitlab"), ("github", "github"),
    ("bitbucket", "bitbucket"), ("docker", "docker"), ("kubernetes", "kubernetes"),
    ("k8s", "kubernetes"), ("terraform", "terraform"), ("nginx", "nginx"),
    ("langchain", "langchain"), ("langgraph", "langchain"), ("llamaindex", "llamaindex"),
    ("openai", "openai"), ("fastapi", "fastapi"), ("django", "django"),
    ("flask", "flask"), ("express", "express"), ("nestjs", "nestjs"),
    ("next.js", "nextdotjs"), ("nextjs", "nextdotjs"), ("react", "react"),
    ("node", "nodedotjs"), ("python", "python"), ("typescript", "typescript"),
    ("vercel", "vercel"), ("netlify", "netlify"), ("cloudflare", "cloudflare"),
    ("kafka", "apachekafka"), ("rabbitmq", "rabbitmq"), ("celery", "celery"),
    ("supabase", "supabase"), ("auth0", "auth0"), ("okta", "okta"),
    ("amazon", "amazonwebservices"), ("aws", "amazonwebservices"),
    ("azure", "microsoftazure"), ("openrouter", "openrouter"),
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _alias_table(si: dict):
    """Keep only hints whose target slug is actually vendored."""
    seen, out = set(), []
    for sub, slug in _ALIAS_RAW:
        if slug in si and (sub, slug) not in seen:
            out.append((sub, slug)); seen.add((sub, slug))
    return out


def _pick_color(hexv: str) -> str:
    """Brand hex, but never near-white (would vanish on the white tile)."""
    h = (hexv or "").lstrip("#")
    if len(h) != 6:
        return "#475569"
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return "#475569"
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    return "#374151" if lum > 0.82 else "#" + h.lower()


def _data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


_FORCE_GLYPH = {"", "none", "fallback", "glyph", "default"}


def _resolve_slug(node: dict, si: dict, aliases) -> str:
    """Return a vendored Simple Icons slug for this node, or '' if none fits.

    An explicit node["icon"] wins; the sentinel values in _FORCE_GLYPH (e.g.
    "none") force the neutral category glyph — handy to tell same-vendor
    services apart (e.g. several GCP datastores) instead of repeating one logo.
    """
    ic = node.get("icon")
    if ic is not None:
        s = _norm(ic)
        if s in _FORCE_GLYPH:
            return ""                 # author asked for the category glyph
        return s if s in si else ""   # explicit-but-unknown -> fall back to glyph
    label = (node.get("label") or node.get("id") or "").lower()
    for sub, slug in aliases:
        if sub in label:
            return slug
    cand = _norm(label)
    return cand if cand in si else ""


def build_icons(model: dict, si: dict) -> dict:
    """Map each node id -> a base64 data: URI (brand logo, else category glyph)."""
    icons, aliases = {}, _alias_table(si)
    for n in (model.get("nodes") or []):
        nid = n.get("id")
        if not nid:
            continue
        slug = _resolve_slug(n, si, aliases)
        if slug:
            entry = si[slug]
            color = n.get("iconColor") or _pick_color(entry.get("h"))
            color = color if str(color).startswith("#") else "#" + str(color)
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%s">'
                   '<path d="%s"/></svg>' % (color, entry.get("p", "")))
        else:
            t = n.get("type") if n.get("type") in FALLBACK_GLYPHS else "component"
            color = n.get("iconColor") or TYPE_COLORS.get(t, "#64748b")
            svg = FALLBACK_GLYPHS[t].replace("{C}", color)
        icons[nid] = _data_uri(svg)
    return icons


def safe_json(obj) -> str:
    """JSON-encode for safe embedding inside a <script> tag.

    ensure_ascii=True escapes all non-ASCII (incl. U+2028/U+2029 which are valid
    JSON but illegal in JS string literals). We additionally neutralise <, >, &
    so a string like "</script>" in the data cannot break out of the tag.
    """
    s = json.dumps(obj, ensure_ascii=True)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def validate_model(model: dict) -> list:
    """Return a list of human-readable warnings (never raises on soft issues)."""
    warns = []
    if not isinstance(model, dict):
        raise SystemExit("error: model must be a JSON object")
    view = model.get("view")
    if view and view not in VALID_VIEWS:
        warns.append(f"unknown view '{view}' (expected one of {sorted(VALID_VIEWS)})")
    nodes = model.get("nodes") or []
    edges = model.get("edges") or []
    if not nodes:
        warns.append("model has no nodes")
    ids = {}
    for n in nodes:
        nid = n.get("id")
        if not nid:
            warns.append(f"node without id: {n}")
            continue
        if nid in ids:
            warns.append(f"duplicate node id: {nid}")
        ids[nid] = True
    for g in (model.get("groups") or []):
        if g.get("id"):
            ids[g["id"]] = True
    for e in edges:
        if e.get("source") not in ids:
            warns.append(f"edge source not found: {e.get('source')} -> {e.get('target')}")
        if e.get("target") not in ids:
            warns.append(f"edge target not found: {e.get('source')} -> {e.get('target')}")
    return warns


def _load_layout_libs() -> str:
    """Concatenate the vendored ELK UMD bundles, statement-safe (';' between each
    so adjacent IIFEs can't merge into a call). Empty string if any are missing —
    the template then falls back to the built-in 'cose' layout."""
    parts = []
    for name in LAYOUT_LIBS:
        p = ASSETS / name
        if not p.exists():
            return ""
        parts.append(p.read_text(encoding="utf-8").strip())
    return "\n;\n".join(parts)


def render(model, template, lib, layout_libs, icons, title) -> str:
    repl = {
        "__TITLE__": _html.escape(title or model.get("title") or "Architecture"),
        "__CYTOSCAPE_LIB__": lib,
        "__LAYOUT_LIBS__": layout_libs,
        "__ICONS_JSON__": safe_json(icons),
        "__MODEL_JSON__": safe_json(model),
    }
    # Single pass over the ORIGINAL template: each placeholder is replaced by its
    # value, and inserted values are never re-scanned — so library/model content
    # containing a token-like string can never corrupt the output.
    return "".join(repl.get(part, part) for part in TOKEN_RE.split(template))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a portable architecture model to self-contained HTML.")
    ap.add_argument("--model", required=True, help="path to the model JSON")
    ap.add_argument("--out", required=True, help="path to write the .html")
    ap.add_argument("--title", default=None, help="override the document title")
    ap.add_argument("--lib", default=str(DEFAULT_LIB), help="path to cytoscape.min.js (default: bundled)")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="path to template.html (default: bundled)")
    ap.add_argument("--icons-file", default=str(DEFAULT_ICONS), help="path to simple-icons.json (default: bundled)")
    ap.add_argument("--no-icons", action="store_true", help="skip brand icons (plain shapes only)")
    ap.add_argument("--light", action="store_true",
                    help="skip the ELK layout engine (~1.6 MB) for a much smaller file; uses the built-in 'cose' layout")
    args = ap.parse_args(argv)

    model_path, lib_path, tpl_path = Path(args.model), Path(args.lib), Path(args.template)
    for p, what in [(model_path, "model"), (lib_path, "cytoscape library"), (tpl_path, "template")]:
        if not p.exists():
            raise SystemExit(f"error: {what} not found: {p}")

    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"error: model is not valid JSON ({e})")

    warns = validate_model(model)
    for w in warns:
        print(f"  warning: {w}", file=sys.stderr)

    # Icons (graceful: a missing/empty store just disables them).
    icons = {}
    if not args.no_icons:
        ip = Path(args.icons_file)
        if ip.exists():
            try:
                si = json.loads(ip.read_text(encoding="utf-8"))
                icons = build_icons(model, si)
            except json.JSONDecodeError as e:
                print(f"  warning: icon store is not valid JSON ({e}); rendering without icons", file=sys.stderr)
        else:
            print(f"  warning: icon store not found ({ip}); rendering without icons", file=sys.stderr)

    layout_libs = "" if args.light else _load_layout_libs()
    if not layout_libs and not args.light:
        print("  warning: ELK layout libs not found in assets/; falling back to built-in 'cose'", file=sys.stderr)

    lib = lib_path.read_text(encoding="utf-8")
    template = tpl_path.read_text(encoding="utf-8")
    out_html = render(model, template, lib, layout_libs, icons, args.title)

    # Hard guard: the rendered file must not contain a live external script/style ref.
    if re.search(r"<script[^>]+\bsrc\s*=", out_html, re.I) or re.search(r"<link[^>]+href\s*=\s*['\"]https?:", out_html, re.I):
        raise SystemExit("error: output unexpectedly contains an external <script src>/<link href> — refusing to write")

    out_path = Path(args.out)
    out_path.write_text(out_html, encoding="utf-8")
    n_nodes = len(model.get("nodes") or [])
    n_edges = len(model.get("edges") or [])
    n_groups = len(model.get("groups") or [])
    n_icons = len(icons)
    size_kb = out_path.stat().st_size / 1024
    print(f"✓ wrote {out_path}  ({n_nodes} nodes, {n_edges} edges, {n_groups} groups, "
          f"{n_icons} icons, {size_kb:.0f} KB, self-contained)")
    print(f"  open it: file://{out_path.resolve()}")
    if warns:
        print(f"  ({len(warns)} warning(s) above — usually fine; check missing-endpoint edges)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
