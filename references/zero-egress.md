# Zero-egress: the privacy guarantee in depth

This skill is built so that visualizing a codebase **cannot leak it**. That is the
whole point — it is safe to run on regulated/sensitive repos (PHI, payment
credentials, service keys). This doc explains *why* the guarantee holds, the exact
vectors that are avoided, and how to verify and maintain it.

## Why it holds

1. **Client-side rendering.** Cytoscape parses the model and draws to a `<canvas>`
   entirely inside the browser. The model text (your code's structure) is never
   transmitted; it is read from the same local file the browser already opened.
2. **Everything is inlined.** `render.py` writes a *single* `.html` containing — all
   verbatim, all in `<script>…</script>` with no `src` — the Cytoscape library, the
   ELK layout engine, the model (an inline JS literal), and every brand **icon** the
   diagram uses (each a base64 `data:image/svg+xml` URI built from the local
   `simple-icons.json`). There is no external reference of any kind — no CDN, no font,
   no stylesheet, no **remote** image — so there is nothing to fetch.
   - **ELK runs in-process.** elkjs can run its solver in a Web Worker, which would
     mean loading a worker file. We use `elk.bundled.js` and `new ELK()` with no
     `workerUrl`, so it computes on the main thread — **no worker is ever fetched.**
3. **CSP lockdown (defense in depth).** Every output carries:
   ```
   Content-Security-Policy: default-src 'self' 'unsafe-inline' data:;
       connect-src 'none'; img-src 'self' data:; script-src 'unsafe-inline';
       style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'
   ```
   `connect-src 'none'` makes the browser refuse all `fetch`/`XHR`/`WebSocket`/
   `EventSource` — even if some script tried, it is blocked.
4. **Verified empirically.** Loaded headless under request interception, a rendered
   file makes **0** http/https/ws requests and throws **0** errors. The library source
   was audited: no `fetch`/`XHR`/CDN calls (the `http://…` strings in it are license
   headers and the `http://www.w3.org/2000/svg` XML-namespace literal — not loads).

## The egress vectors — and how they're avoided

Each is an opt-in feature you simply never enable:

1. **Remote icons (Mermaid `architecture-beta`).** That Mermaid diagram type can pull
   icon packs from `api.iconify.design`. **We don't use Mermaid at all** — the engine is
   Cytoscape — so this cannot occur. (If you ever add Mermaid, use `flowchart`/
   `erDiagram`/`classDiagram`, which never touch the network, and never `architecture-beta`.)
2. **Remote `background-image` on a Cytoscape node.** Styling a node's
   `background-image` to an `http(s)` URL makes the browser load that image. We *do* use
   node images (the brand logos) — but every one is an **inlined base64 `data:` URI**,
   never a URL. **Never** put an `http(s)` URL in node styling; embed the icon as a
   `data:` URI (which is exactly what `render.py` does, from the local icon store).
3. **Web-worker layout.** A layout engine that spawns a worker from a URL would fetch
   that file. ELK is loaded as the self-contained `elk.bundled.js` and instantiated
   with no `workerUrl`, so it never fetches a worker (see above).

Everything else (drag, zoom, layouts, search, collapse, PNG export) is pure
computation on the local canvas.

## Verifying any output

Bundled check:
```bash
bash scripts/verify_no_egress.sh path/to/output.html
```
It asserts the CSP `connect-src 'none'` is present and flags any external
`<script src>`, `<link href>`, remote media `src`, or CSS `@import`/`url(http…)`. It
ignores bare URL *literals* (license/namespace strings inside the library) by design,
because those are not resource loads.

Gold-standard manual checks (either one):
- Open the file in a browser, DevTools → **Network** tab → reload → expect **0 requests**.
- Open the file with **Wi-Fi off** → it still works fully.

`render.py` also self-guards: it refuses to write output that contains an external
`<script src>`/`<link href=https>`.

## Acquiring vs leaking — the distinction

Vendoring the library (`assets/cytoscape.min.js`) is **inbound tool acquisition** — the
renderer *arriving* on the machine. That is not egress; no codebase data is involved.
**Codebase data leaving the machine must always be zero.** Keep that line bright: it is
fine to download a tool once; it is never fine to send the model/code to a remote service
(no "render via mermaid.ink/kroki", no "upload to a diagram SaaS", no telemetry).

## Re-vendoring assets offline (only if something in `assets/` goes missing)

All inbound (tools arriving), never outbound — no codebase data is involved.

### Cytoscape (`assets/cytoscape.min.js`)
The pinned version is **Cytoscape 3.34.0** (UMD global build, ~435 KB). To restore it,
fetch the *library* (inbound; carries none of your data):
```bash
# Option 1 — npm (offline-cache friendly)
npm pack cytoscape@3.34.0           # → cytoscape-3.34.0.tgz
tar -xzf cytoscape-3.34.0.tgz
cp package/dist/cytoscape.min.js  assets/cytoscape.min.js

# Option 2 — direct download of just the one file
curl -L https://cdn.jsdelivr.net/npm/cytoscape@3.34.0/dist/cytoscape.min.js \
     -o assets/cytoscape.min.js
```
Then sanity-check: the file should start with the Cytoscape license header and contain
the string `"3.34.0"`. After that, all rendering is offline again.

> Pinning a known version also means the output is reproducible and auditable — a
> reviewer can diff `assets/cytoscape.min.js` against the published 3.34.0 artifact.

### ELK layout engine (`assets/elk.bundled.js` + `assets/cytoscape-elk.js`)
```bash
npm pack elkjs cytoscape-elk            # → elkjs-*.tgz, cytoscape-elk-*.tgz (inbound)
tar -xzf elkjs-*.tgz && tar -xzf cytoscape-elk-*.tgz   # into temp dirs
cp package/lib/elk.bundled.js     assets/elk.bundled.js     # from elkjs
cp package/dist/cytoscape-elk.js  assets/cytoscape-elk.js   # from cytoscape-elk
```
Use **`elk.bundled.js`** (self-contained, runs in-process), *not* `elk-worker.js`.

### Brand icons (`assets/simple-icons.json`)
The icon store is a single consolidated JSON `{ slug: { "p": "<path-d>", "h": "<hex>" } }`
built once from the **Simple Icons** package (CC0). To rebuild it:
```bash
npm pack simple-icons                   # → simple-icons-*.tgz (inbound)
tar -xzf simple-icons-*.tgz             # → package/icons/*.svg + package/data/simple-icons.json
python3 - <<'PY'
import json, re, os
root="package"
meta={i["slug"]: i["hex"] for i in json.load(open(f"{root}/data/simple-icons.json"))}
dpat=re.compile(r'\bd="([^"]+)"'); out={}
for fn in os.listdir(f"{root}/icons"):
    if fn.endswith(".svg"):
        slug=fn[:-4]; paths=dpat.findall(open(f"{root}/icons/{fn}").read())
        if paths: out[slug]={"p":" ".join(paths),"h":meta.get(slug,"555555")}
json.dump(out, open("assets/simple-icons.json","w"), separators=(",",":"))
print(len(out), "icons")
PY
```
If `simple-icons.json` is absent, `render.py` simply renders without logos (category
glyphs only) — icons degrade gracefully, they're never required.
