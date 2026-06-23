# Model schema

The model is **engine-agnostic JSON** — a portable description of a system that
`render.py` turns into the interactive HTML. Keep it human-readable; the template
maps it to Cytoscape elements client-side.

## Top-level shape

```jsonc
{
  "title": "Repo Name — agentic view",     // shown in the toolbar + PNG filename
  "view":  "agentic",                       // cloud | data | agentic | structure
  "groups": [ /* collapsible containers */ ],
  "nodes":  [ /* the boxes */ ],
  "edges":  [ /* the arrows */ ],
  "notes":  [ "caveats, inferred items, doc-drift" ]   // surfaced in a banner; optional
}
```

### `groups[]` — collapsible containers (compound nodes)
```jsonc
{ "id": "svc", "label": "services/", "parent": null }   // parent = another group id, for nesting
```
A group renders as a **labelled, zone-tinted box** (VPC / subnet / cluster style); clicking it collapses/expands. Nodes join a group via `node.group`. Nesting (`parent`) is supported and the child box inherits its top-level ancestor's zone color.

### `nodes[]`
```jsonc
{
  "id": "orchestrator",            // unique; referenced by edges and by node.group
  "label": "orchestrator",         // short text under the tile (put detail in meta, not here)
  "type": "router",                // drives accent color + fallback glyph (see taxonomy)
  "group": "app",                  // optional: id of the containing group
  "icon": "googlecloud",           // optional: a Simple Icons slug → real brand logo on the tile.
                                   //   omit to auto-match from the label; "none" forces the
                                   //   neutral category glyph (good for same-vendor services).
  "iconColor": "#4285F4",          // optional: override the icon color (default = brand hex)
  "meta": {                        // optional; all shown in the click panel
    "file": "agents/orchestrator.py",      // rendered as a clickable-looking path
    "desc": "LangGraph router, 9 nodes",   // free text
    "columns": [ /* only for type:"table" — see below */ ]
    // any other key:value pairs are listed in the panel too
  }
}
```

**Icons.** Every node is a white tile showing an image: a **brand logo** when one resolves (explicit `icon` slug, else an auto-match on the label), otherwise a neutral **category glyph** chosen from `type`. Pick slugs from <https://simpleicons.org> (the filename = the slug), e.g. `googlecloud`, `amazonwebservices`, `supabase`, `postgresql`, `redis`, `docker`, `kubernetes`, `whatsapp`, `gitlab`, `stripe`, `openai`. If a slug isn't in the vendored set it silently falls back to the glyph. A few brands have no Simple Icons logo (trademark) — e.g. OpenAI — and will use a glyph.

### `edges[]`
```jsonc
{ "source": "orchestrator", "target": "welcome", "kind": "conditional", "label": "route" }
```
- `source`/`target` must match a node or group `id` (mismatched edges are skipped with a warning).
- `kind` drives the line style (see taxonomy). `label` is optional.

### `table` nodes — columns
For the **data** view, give each table node a `meta.columns` array; it renders as a
typed column list with PK/FK flags in the detail panel:
```jsonc
{ "id": "payments", "label": "payments", "type": "table", "group": "db", "meta": {
    "columns": [
      { "name": "id",       "type": "uuid",    "pk": true },
      { "name": "order_id", "type": "uuid",    "fk": true, "comment": "→ orders.id, nullable (guest)" },
      { "name": "amount",   "type": "numeric" },
      { "name": "gateway",  "type": "text",    "comment": "stripe / paypal" }
    ] } }
```
Represent a foreign key **both** as a column flag (`"fk": true`) **and** as an `edge`
between the two table nodes (`"kind": "data"`), so the relationship is visible on the canvas.

## Type taxonomy (node `type` → accent color + fallback glyph)

Nodes are uniform white tiles; `type` sets the **border accent color** and the
**category glyph** used when no brand logo resolves (a brand `icon` overrides the glyph).

| `type` | accent / glyph | use for |
|--------|----------------|---------|
| `external` | orange · globe | third-party systems / anything across the trust boundary (APIs, payment, webhooks) |
| `datastore` | green · cylinder | databases, caches, object storage |
| `vectorstore` | teal · cylinder+dots | vector / embedding stores (Pinecone, Chroma, pgvector) |
| `router` | blue · branch | orchestrators, dispatchers, graph entry points |
| `agent` | purple · robot | LLM agents / autonomous workers |
| `tool` | amber · wrench | callable tools / function-calling endpoints |
| `mcp` | indigo · plug | MCP servers |
| `table` | slate · grid | individual DB tables (with `meta.columns`) |
| `service` | slate · cube | internal services / modules |
| `queue` | brown · layers | queues, topics, pub/sub, schedulers |
| `config` | gray · gear | config files, data files, embeddings on disk |
| `component` | gray · box | anything else / generic component |

Unknown types fall back to `component`. Keep the set small — legibility beats precision.

## Edge taxonomy (`kind` → line style)

| `kind` | style | use for |
|--------|-------|---------|
| `primary` | solid gray | the main call/control flow |
| `conditional` | dashed blue | conditional routing / branch |
| `data` | dotted green | reads/writes, data flow, FK relationships |
| `external` | thick orange | edge that crosses the trust boundary (egress/ingress) |
| `async` | dashed purple | async / event / fire-and-forget |

## Worked example (abbreviated — agentic view)

```jsonc
{
  "title": "Sample Shop Bot — agentic view",
  "view": "agentic",
  "groups": [
    { "id": "app",    "label": "app/ (FastAPI)" },
    { "id": "agents", "label": "agents/" },
    { "id": "svc",    "label": "services/" },
    { "id": "ext",    "label": "external" }
  ],
  "nodes": [
    { "id": "webhook", "label": "POST /webhook", "type": "service", "group": "app",
      "meta": { "file": "app/routers/webhook.py", "desc": "chat ingress" } },
    { "id": "orch", "label": "orchestrator", "type": "router", "group": "agents",
      "meta": { "file": "agents/orchestrator.py", "desc": "LangGraph StateGraph, 9 nodes; conditional routing" } },
    { "id": "sales", "label": "sales_agent", "type": "agent", "group": "agents", "meta": { "file": "agents/sales_agent.py" } },
    { "id": "support", "label": "support_agent", "type": "agent", "group": "agents", "meta": { "file": "agents/support_agent.py" } },
    { "id": "lookup_order", "label": "lookup_order", "type": "tool", "group": "agents", "meta": { "file": "agents/support_tools.py", "desc": "@tool" } },
    { "id": "llm", "label": "get_llm()", "type": "service", "group": "svc", "meta": { "file": "services/llm.py", "desc": "OpenAI primary, Anthropic fallback" } },
    { "id": "db", "label": "Postgres", "type": "datastore", "group": "ext", "icon": "postgresql", "meta": { "desc": "orders, payments, users" } },
    { "id": "openai", "label": "OpenAI", "type": "external", "group": "ext", "icon": "none" },
    { "id": "anthropic", "label": "Anthropic", "type": "external", "group": "ext", "icon": "anthropic" }
  ],
  "edges": [
    { "source": "webhook",  "target": "orch",    "kind": "primary" },
    { "source": "orch",     "target": "sales",   "kind": "conditional", "label": "route" },
    { "source": "orch",     "target": "support", "kind": "conditional", "label": "route" },
    { "source": "support",  "target": "lookup_order", "kind": "primary", "label": "tool" },
    { "source": "lookup_order", "target": "db",  "kind": "data" },
    { "source": "sales",    "target": "llm",     "kind": "primary" },
    { "source": "llm",      "target": "openai",  "kind": "external" },
    { "source": "llm",      "target": "anthropic", "kind": "external", "label": "fallback" }
  ],
  "notes": [
    "LLM default is OpenAI (services/llm.py), with Anthropic as fallback.",
    "No MCP servers found in this repo."
  ]
}
```

This renders to a graph with three internal group boxes and an `external` cluster,
conditional routing edges from the orchestrator, a tool wired to both its agent and
the database, and the LLM provider fanning out to two external providers — with the
two caveats shown in the notes banner.
