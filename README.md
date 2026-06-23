# architecture-visualizer

A [Claude Code](https://claude.com/claude-code) skill that turns **any codebase** into an
**interactive, self-contained HTML map** of its architecture — across four lenses:

- **cloud / infra** — services, datastores, queues, secrets, ingress/egress, trust boundaries
- **data** — tables with typed columns (PK/FK) and their relationships
- **agentic** — agents, tools, MCP servers, vector stores, and LLM/DB wiring
- **structure** — packages, routers/routes, and what calls what

The output looks like a real cloud-architecture diagram: **product/service logos** on clean
white tiles, inside **labelled, nested boxes** with directional flow — and it's a single
`.html` file you open by double-click.

## Privacy first — zero egress

This skill is built to be safe on **sensitive/regulated** codebases. Everything renders
**100% client-side** in your browser. The renderer inlines *everything* into the one HTML
file — the [Cytoscape](https://js.cytoscape.org) engine, the [ELK](https://eclipse.dev/elk/)
box layout (run **in-process**, no web worker fetched), the model of your code, and every
brand icon (as base64 `data:` URIs). There is **no `<script src>`, no CDN, no `fetch`, no
remote image** — opening the file makes **zero network requests** (enforced by a strict
`Content-Security-Policy: connect-src 'none'` and verifiable with a bundled checker).

> Nothing about your codebase is ever sent anywhere. The libraries travel *to* you (a
> one-time download); your code never leaves the machine. See
> [`references/zero-egress.md`](references/zero-egress.md).

## Install

### Option A — as a plugin (recommended)

This repo is its own Claude Code plugin marketplace. In Claude Code:

```text
/plugin marketplace add BenjaSchindler/architecture-visualizer
/plugin install architecture-visualizer@benja-skills
```

Then just ask Claude to *"map this repo's architecture"* (or invoke
`/architecture-visualizer` explicitly). If you installed mid-session, run
`/reload-plugins` first.

### Option B — as a personal skill (manual)

```bash
git clone https://github.com/BenjaSchindler/architecture-visualizer /tmp/av
cp -r /tmp/av ~/.claude/skills/architecture-visualizer
```

Either way it needs only `python3` (standard library — no `pip install`).

## Use

In Claude Code, just ask:

> "Map this repo's architecture." · "Diagram the agents." · "Show the database connections."
> "Visualize the cloud setup." · "How does this codebase fit together?"

The skill reads the code (preferring what's actually imported/wired over what docs claim),
builds a small model JSON, and renders it. Or drive the renderer directly:

```bash
python3 scripts/render.py --model my-model.json --out arch.html --title "My System — cloud"
bash   scripts/verify_no_egress.sh arch.html      # → PASS
```

Useful flags: `--light` (skip the ELK engine for a ~450 KB file instead of ~2 MB),
`--no-icons` (plain shapes, no logos). The model schema (including the optional `icon`
field — a [Simple Icons](https://simpleicons.org) slug) is documented in
[`references/model-schema.md`](references/model-schema.md); discovery playbooks for each
view are in [`references/detection.md`](references/detection.md).

## What's in here

| Path | What |
|------|------|
| `SKILL.md` | The skill instructions Claude follows |
| `references/` | Model schema · detection playbooks · the zero-egress deep-dive |
| `scripts/render.py` | Model JSON → one self-contained HTML (stdlib only) |
| `scripts/verify_no_egress.sh` | Audits an output for any egress vector |
| `assets/template.html` | The interactive Cytoscape UI shell |
| `assets/cytoscape.min.js` · `elk.bundled.js` · `cytoscape-elk.js` | Inlined render + layout engines |
| `assets/simple-icons.json` | Consolidated brand-icon store (3,446 logos) |

## Licensing

This skill's own code (`SKILL.md`, `scripts/`, `references/`, `assets/template.html`) is
released under the **MIT License** (see [`LICENSE`](LICENSE)). It bundles third-party
components under their own permissive licenses — see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Brand logos are trademarks of their
respective owners and are used only as identifying icons.

## A note on outputs

The diagrams this skill generates describe **your** system. The skill itself contains no
project data — but the `.html` / `.model.json` files you generate do. Don't commit those to
a public repo unless you mean to. (This repo intentionally ships **no** generated diagrams.)
