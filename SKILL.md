---
name: architecture-visualizer
description: Generate interactive, self-contained, zero-egress HTML maps of a codebase's architecture — cloud/infra topology, database schema and connections, or agentic/LLM systems (agents, tools, MCP servers, vector stores, DB/LLM wiring). Diagrams use real product/service logos (inlined Simple Icons) and clean nested boxes (ELK layout), like a cloud-architecture diagram. Use when understanding, mapping, visualizing, diagramming, onboarding to, or auditing a codebase, especially an unfamiliar one. Trigger even when the user just says 'visualize my system', 'map this repo', 'show the database connections', 'diagram the agents', 'draw the architecture', 'with service icons', or 'how does this codebase fit together'. Everything renders locally in the browser; nothing is ever sent to any external site.
---

# Architecture Visualizer

Turn any codebase into an **interactive, self-contained HTML map** you can drag, zoom, click, search, and collapse — covering four lenses: **cloud/infra topology, database schema + connections, agentic/LLM systems, and code structure**. Discovery is intelligent (read the repo, infer the system); rendering is a deterministic local script. The output is a single `.html` that opens by double-click and makes **zero network requests**.

## 1. Privacy first: everything stays local (zero egress)

This skill exists to be safe on sensitive/regulated codebases (PHI, secrets, credentials). The guarantee:

- The diagram renders **100% client-side** in the user's own browser. Everything is **inlined** into the one HTML file: the model describing the code, the Cytoscape library (`assets/cytoscape.min.js`), the ELK layout engine (`assets/elk.bundled.js` + `cytoscape-elk.js`, which runs **in-process — no web worker is fetched**), and every brand icon the diagram uses (base64 `data:` URIs built from `assets/simple-icons.json`). There is **no `<script src>`, no CDN, no `fetch`, no remote image** — opening the file triggers **0 network requests** (verified by audit + a bundled checker).
- A strict Content-Security-Policy (`connect-src 'none'`, `img-src 'self' data:`) is baked into every output as defense-in-depth.
- **Never** swap in a CDN-hosted library, a remote font, a Mermaid `architecture-beta` diagram with remote (iconify) icons, or a Cytoscape `background-image` pointing at an http URL — those are the only ways to introduce egress. Icons are inlined `data:` URIs, never fetched. See `references/zero-egress.md`.
- Acquiring the library itself (already done) is *inbound tool acquisition*, not data egress. Codebase data leaving the machine must always be **zero**.

Always run the verifier (Step 5) and tell the user the file is self-contained.

## 2. When to Use This Skill

Use when the user wants to **understand or visualize the shape of a system**:
- "I just got access to this repo — help me understand the architecture."
- "Map / diagram / visualize this codebase." · "Draw the agent graph." · "Show the database connections / schema." · "What does the cloud setup look like?"
- Onboarding to an unfamiliar codebase, or auditing structure / trust boundaries.

Do **not** use it for: editing code, generating non-architecture docs, or live database introspection.

## 3. Workflow

```
choose view(s) → discover (read CODE, not docs) → build model.json → render → verify + report
```

### Step 1 — Scope the view(s)
Pick one or more of the **four views** (§4). If the user is vague ("understand this codebase"), default to producing the **agentic** view if it's an AI/agent system, else **structure**, and offer the others. One model.json + one HTML per view.

### Step 2 — Discover (read the code, prefer it over docs)
Open `references/detection.md` and run the playbook for the chosen view. **The cardinal rule: source code is ground truth; READMEs / CLAUDE.md / env-var names are only hints — cross-check and prefer what is actually imported and wired at runtime.** When something is deduced rather than declared (an inferred FK, a documented-but-unwired service), mark it and add a line to the model's `notes`. Use Explore/Grep/Read; for agent graphs and table constants prefer an AST pass over a naive regex (see the playbook for why).

### Step 3 — Build the model
Write a model JSON following `references/model-schema.md` (engine-agnostic: `groups`, `nodes`, `edges`, `notes`). Put `meta.file` on nodes (clickable in the panel), `meta.columns` on `table` nodes, and honest caveats in `notes`. For nodes that are a recognisable **product/brand**, add `"icon": "<slug>"` (a [Simple Icons](https://simpleicons.org) slug, e.g. `googlecloud`, `supabase`, `postgresql`, `whatsapp`, `gitlab`, `docker`) so the node shows its real logo. The renderer also auto-matches obvious brands from the label, so this is optional — but explicit slugs are reliable. Use `"icon": "none"` to force a neutral category glyph instead of a logo (handy to tell several same-vendor services apart, e.g. distinct GCP datastores). Save the model next to where the HTML will go (a scratch dir, or the repo's `docs/architecture/`).

### Step 4 — Render
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/architecture-visualizer}/scripts/render.py" \
  --model /path/to/model.json \
  --out   /path/to/output.html \
  --title "Repo Name — agentic view"
```
`render.py` is stdlib-only and self-locates its template, library, icons, and layout engine. It prints warnings for any edge with a missing endpoint (usually a model typo). Options: `--light` skips the ELK engine for a much smaller file (~450 KB vs ~2 MB; falls back to the built-in `cose` layout); `--no-icons` renders plain shapes with no logos. (If the skill lives elsewhere, adjust the path; the script still finds its own `assets/`.)

### Step 5 — Verify zero-egress & report
```bash
bash "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/architecture-visualizer}/scripts/verify_no_egress.sh" /path/to/output.html
```
Expect `PASS`. Then tell the user the path, that it's **self-contained / safe to open offline**, and that they can **double-click to open**. Mention the in-browser **⤓ PNG** button if they want a flat image. Gold-standard manual check: open with DevTools → Network → 0 requests (or just open with Wi-Fi off).

## 4. The Four Views

| View | Answers | Typical node types |
|------|---------|--------------------|
| **cloud** | How/where does it deploy? What does it talk to? | `external`, `service`, `datastore`, `queue`, `config` |
| **data** | What tables exist and how do they relate? | `table` (with `meta.columns`), `datastore` |
| **agentic** | How do agents, tools, MCP servers, LLMs, and stores connect? | `router`, `agent`, `tool`, `mcp`, `vectorstore`, `datastore`, `external` |
| **structure** | How is the code organized and what calls what? | `service`, `component`, `config`, grouped by directory |

Each node is a clean white **tile** showing its product **logo** (or a neutral role glyph) with the label beneath; each group is a **labelled, tinted box** (VPC / subnet / cluster style). A `node.type` drives its accent color + fallback glyph; an `edge.kind` (`primary`/`conditional`/`data`/`external`/`async`) drives the line style. `external` nodes/edges are the **trust-boundary / egress** points — useful for the security lens.

## 5. Interactivity (what the HTML gives the user)

- Clean **nested boxes with directional flow** by default (ELK layout); **layout switcher** also offers boxes / organic / layered / concentric / grid / circle.
- **Drag / zoom / pan** the graph; recognisable **brand logos** mark known products.
- **Click a node** → detail panel: type, description, **file path**, and for tables the full **column list** (PK/FK flagged), plus its connections.
- **Click a group** → collapse/expand it, with edges re-routed to the group box (declutter big graphs); or **⊟ Collapse all**.
- **Search** box highlights matching nodes and fits to them.
- **Neighborhood highlight**: clicking a node dims everything except its neighbors (answers "what touches X?").
- **⤓ PNG** export (rendered on the local canvas — still zero egress) and **⤢ Fit**.
- A **legend** (only the types/kinds actually present) and a **notes/caveats** banner surfacing inferred items and doc-drift.

## 6. Tips for a good map

- **Group by the thing that aids comprehension** — directory (`services/`, `agents/`), layer (ingress / app / external), or subsystem. Groups become collapsible boxes.
- **Keep labels short**; put detail in `meta` (it shows in the panel, not on the canvas).
- **Be honest**: mark inferred relationships and documented-but-unwired components in `notes`; don't invent an MCP server or a database that the code doesn't actually use.
- **One view per file** keeps each map legible. Produce several and tell the user which is which.
- **Add `icon` slugs** for known products (logos aid recognition); use `icon: "none"` on same-vendor services so they don't all show one identical logo. Internal modules/tables don't need logos — their role glyphs are clearer.
- The default ELK build is ~2 MB (mostly the layout engine). If a user wants small files, render with `--light` (~450 KB, organic layout).
- For large repos, dispatch the discovery per-view to subagents (Explore) in parallel, then assemble each model.

## 7. Additional Resources

- `references/detection.md` — the four discovery playbooks (broad multi-stack: Python/Node/Go/Java, GCP/AWS/Azure, SQL/NoSQL, LangGraph/LangChain/CrewAI/AutoGen + MCP), plus the "code > docs" meta-rule and worked examples.
- `references/model-schema.md` — the full model JSON schema, the type/kind taxonomy, and a complete worked example.
- `references/zero-egress.md` — the privacy guarantee in depth: the audited egress vectors, the CSP, the verifier, and how to re-vendor the library / icons / layout engine offline if ever needed.
- `scripts/render.py` — model JSON → self-contained HTML. `scripts/verify_no_egress.sh` — egress audit.
- `assets/template.html` — the Cytoscape UI shell. `assets/cytoscape.min.js` — the vendored, inlined engine (v3.34.0). `assets/elk.bundled.js` + `cytoscape-elk.js` — the ELK box-layout engine (in-process). `assets/simple-icons.json` — the consolidated brand-icon store (3,446 logos, CC0; `simple-icons-LICENSE.md`).
