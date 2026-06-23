# Detection playbooks

How to read an unfamiliar codebase and reconstruct its system model. Four
playbooks (cloud · data · agentic · structure), each: **signals → how to extract → what to emit**.
Patterns are broad/multi-stack; adapt to whatever the repo actually uses.

## The cardinal rule: code is ground truth, docs are hints

READMEs, architecture markdown, `CLAUDE.md`, and even env-var *names* describe
**intent**, which drifts from reality. Always prefer what is **imported and wired at
runtime**. Cross-check prose against code; when they disagree, trust the code and
record the discrepancy in the model's `notes`.

Worked illustration: suppose a `README` and a `REDIS_URL` env var advertise a Redis
cache, but no runtime module imports a redis client and `redis` isn't in the dependency
manifest (it survives only under `scripts/archive/`) — it's vestigial: mark it
`(declared-but-not-wired)`, don't draw it as live. Likewise the docs may claim the
default model is "GPT-4" while `services/llm.py` actually defaults to a cheaper model
with GPT-4 only as a fallback, and an orchestrator may have **9** graph nodes where an
old diagram says 7. A doc-scraper gets all three wrong; a code-reader gets them right
and flags the drift.

Heuristics that operationalize this:
- A datastore named only in markdown / env-var names but **never imported** by runtime code and **absent from the dependency manifest** → mark `(declared-but-not-wired)` in `notes`, don't draw it as live.
- A dependency in the manifest but never imported → likely vestigial.
- Prefer the **entrypoint's transitive imports** (what the running process loads) over file count.

## Add brand icons as you identify products (all views)

Whenever a node is a recognisable **product/service**, set `node.icon` to its
[Simple Icons](https://simpleicons.org) slug — the resulting logo makes the map read at a
glance. The slug is the icon's filename without `.svg` (lowercase, no spaces): `googlecloud`,
`amazonwebservices`, `microsoftazure`, `postgresql`, `mysql`, `mongodb`, `redis`, `supabase`,
`firebase`, `docker`, `kubernetes`, `nginx`, `gitlab`, `github`, `stripe`, `whatsapp`,
`googlegemini`, `anthropic`, `langchain`, `fastapi`, `python`, `nodedotjs`, `react`, etc.
Guidance: brand logos for **third-party / external** products; for several services from the
**same vendor** (e.g. multiple GCP datastores) set `icon: "none"` on the data services so they
show distinct role glyphs instead of one repeated logo. Internal modules, tables, agents, and
tools usually need no `icon` — their category glyph is clearer. A handful of brands have no
Simple Icons logo (trademark, e.g. OpenAI, or some regional/niche vendors) → leave them to
the glyph. Unknown slugs degrade silently to the glyph, so guessing is safe.

---

## Playbook A — Cloud / infra topology

**Signals (by ecosystem):**
- **Containers:** `Dockerfile` (base image = runtime; `COPY` lines reveal the *real* source packages; `CMD`/`ENTRYPOINT` = the process), `docker-compose.yml` (service graph + linked DBs/queues).
- **CI/CD deploy specs (richest signal):** `.gitlab-ci.yml`, `.github/workflows/*.yml`, `cloudbuild.yaml`, `Jenkinsfile`. Parse the deploy command flags.
- **IaC:** `*.tf` (Terraform `resource`/`module`), `serverless.yml`, AWS SAM/`template.yaml`, CDK, k8s manifests (`kind: Deployment/Service/Ingress`), `app.yaml` (App Engine), `Procfile`, `vercel.json`/`netlify.toml`.
- **Cloud SDK calls in code:** `google.cloud.*`, `boto3`/`aws-sdk`, `azure.*`.
- **Dependency manifest** as a tech fingerprint: `pyproject.toml`/`requirements.txt`, `package.json`, `go.mod`, `pom.xml`, `Gemfile`.
- **Env files** for variable *names* (never values): `.env.example`, `.env.*`.

**How to extract:**
- From a `gcloud run deploy …` (or `aws ecs`/`kubectl apply`) block, read flags: region, CPU/memory, min/max instances, concurrency, timeout, `--allow-unauthenticated` (public ingress), `--add-cloudsql-instances` (attached DB), `--port`.
- The **secrets/integration map** is the best external-dependency list: `--set-secrets="OPENAI_API_KEY=...:latest,SUPABASE_URL=...,BREVO_API_KEY=..."` (GCP) or GH Actions `secrets.*` / k8s `secretKeyRef`. Each secret name names an external integration → emit an `external` node per provider family.
- `--set-env-vars` plaintext gives base URLs/hostnames (the live service endpoints) and mode flags.
- Health/readiness endpoints in CI test stages confirm probe routes.

**Emit:** `service` nodes for each deployed service (label with region/sizing in `meta`);
`datastore`/`queue`/`external` nodes for attached DBs, buses, and third-party APIs;
`config` for secret groups. Edges: ingress (`external → service`, `kind:external`),
service→datastore (`data`), service→third-party (`external`). Group by environment
(prod/dev) or by tier (ingress / compute / external). Note absent-but-documented infra.

**Worked example:** a CI deploy spec defines two Cloud Run–style services (`shop-api`,
`shop-api-staging`) in `us-central1`, images in a registry tagged by commit SHA, and a
`--set-secrets` list (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `STRIPE_API_KEY`,
`DATABASE_URL`, …) = the external-integration map; the `Dockerfile` runs
`uvicorn app.main:app` on `python:3.11-slim`. No Terraform/k8s → deploy is CI-driven,
not "no cloud".

---

## Playbook B — Database / data model

**Signals:**
- **DDL / migrations:** `*.sql`, `migrations/`, `alembic/`, Prisma `schema.prisma`, Django/SQLAlchemy models, `db/schema.rb`, Drizzle/TypeORM entity files. `CREATE TABLE` / `ALTER TABLE ADD COLUMN` / `REFERENCES` are authoritative for columns + FKs.
- **Query call-sites (when no central schema):**
  - Supabase/PostgREST: `.table("name")` / `.from_("name")`.
  - SQLAlchemy: `class X(Base): __tablename__ = "..."`; Django: `class X(models.Model)` + `ForeignKey`.
  - Raw SQL: `FROM <t>` / `JOIN <t>` / `INSERT INTO <t>` in query strings.
  - ORMs (JS): Prisma `prisma.<model>`, Drizzle `db.select().from(<t>)`, Knex `knex("<t>")`, Mongoose `mongoose.model("X", schema)` / collections.
- **Connection identity:** connection strings / client init (`createClient(SUPABASE_URL …)`, `psycopg`, `mongoose.connect`), and the secret names from Playbook A.

**How to extract (two patterns you must combine):**
1. **Inline literals:** regex `\.table\(["']([a-z_]+)["']\)` (and `\.from_`/`FROM\s+([a-z_]+)`), tallied with frequencies → the table set.
2. **Constant indirection (regex-only misses these):** module constants like
   `ORDERS_TABLE = "orders"` then `.table(ORDERS_TABLE)`. **Resolve the
   constant** (AST: assignment whose name matches `*TABLE*` and value is a string),
   then attribute `.table(<CONST>)` call-sites to it. A pure literal grep silently
   drops every constant-addressed table.
- **Columns + FKs** from: DDL `REFERENCES`; `.insert({...})`/`.update({...})` dict keys
  (enumerate columns without DDL); `.eq("<fk_col>", …)` and join/flatten helpers
  (e.g. a `{"products": {...}}` nested select ⇒ FK `order_items.product_id → products.id`).
- **Detect multi-DB splits:** group tables by which client/connection touches them;
  migration filename prefixes often encode it (`billing_00N_*.sql` vs bare-numeric).

**Emit:** one `table` node per table with `meta.columns` (typed, PK/FK flagged); a `data`
edge per relationship (label the FK column); mark code-inferred (non-DDL) relationships
`(inferred)` in the column comment and/or `notes`. Group tables by datastore. For a
higher-level data-flow view, use `datastore` nodes instead of per-table.

**Worked example:** a Postgres store; a `.table()`/`FROM` tally → `users`(42),
`orders`(26), `order_items`, `payments`, `coupons`, `sessions`, … plus a
constant-addressed table (`ORDERS_TABLE = "orders"`) resolved from
`services/order_service.py`. FKs largely inferred from `.eq()`/joins + the
`migrations/*.sql` DDL (e.g. `payments.order_id → orders.id`). A `REDIS_URL` cache named
in docs but never imported = declared-but-not-wired.

---

## Playbook C — Agentic / LLM systems

**Signals:**
- **Graph frameworks:** LangGraph (`from langgraph.graph import StateGraph, END`), LangChain (`AgentExecutor`, `Runnable`), CrewAI (`Crew`, `Agent`, `Task`), AutoGen (`AssistantAgent`, `GroupChat`), LlamaIndex, OpenAI Assistants/Swarm. The import is the cheapest "this is agentic" tell.
- **Tools:** `@tool` decorator (LangChain), `tools=[...]` / `bind_tools([...])`, OpenAI `tools=[{type:"function", function:{name,…}}]`, JSON-schema tool defs, a central tool registry dict.
- **MCP servers:** `mcpServers` keys in `mcp.json` / `.mcp.json` / `claude_desktop_config.json` / `.cursor/mcp.json`; `from mcp …` / `modelcontextprotocol` imports; `mcp__<server>__<tool>` tool names.
- **Vector stores / RAG:** `pinecone`, `chromadb`, `weaviate`, `qdrant`, `faiss`, `pgvector`, embeddings files; `.similarity_search` / `.as_retriever`.
- **LLM providers:** `ChatOpenAI`, `ChatGoogleGenerativeAI`/`google.genai`, `ChatAnthropic`, `boto3 bedrock`, Ollama. Find the **single provider chokepoint** if one exists (e.g. a `get_llm()` factory) and read its model constants + fallback order.

**How to extract a LangGraph graph (AST, not regex):**
- Find `StateGraph(<StateType>)`; the state `TypedDict` gives the channel shape.
- Collect `.add_node("name", fn)`, `.set_entry_point("name")`, `.add_edge(src, dst)`.
- `.add_conditional_edges(src, router_fn, { "label": "dst", … })` — the **literal
  label→target dict** is fully enumerable statically; also read the router's
  `-> Literal["a","b",…]` return type as an independent source of the labels.
- **AST-walk** so you catch edges emitted inside a `for` loop over node names and inside
  **nested per-agent `_build_graph()`** subgraphs — a regex over literal args misses both.
- Map tools→agent via each agent's `bind_tools([...])` / `tools=[...]` list and any
  central `tool_registry`. For MCP, if none found, **say so** — don't invent one.

**Emit:** `router` for orchestrators/graph entry; `agent` per agent; `tool` per tool
(name + signature/docstring in `meta`); `mcp` per server; `vectorstore`/`datastore` for
stores; `external` per LLM provider; `service` for the provider factory. Edges:
orchestrator→agents (`conditional` for routed handoffs), agent→tool (`primary`),
tool/agent→store (`data`), provider→external LLM (`external`). Group by `agents/` vs
`services/` vs external. Other frameworks: CrewAI → crew=`router`, agents=`agent`,
tasks as edges; AutoGen → group chat=`router`, participants=`agent`.

**Worked example:** `agents/orchestrator.py` `StateGraph` with **9** nodes; entry
`route_message`; conditional routers (`_route_intent`, `_should_handoff` — some edges
emitted in a `for` loop) → 3 agent nodes + `tools_node`. Agents: sales / support /
returns. Tools across `sales_tools` / `support_tools`. Provider chokepoint
`services/llm.py` = OpenAI primary / Anthropic fallback. **MCP: none found → say so.**

---

## Playbook D — Code structure

**Signals:** entrypoints (`app/main.py`, `main.go`, `index.ts`, `Application.java`);
package/dir layout (and which dirs the `Dockerfile` actually `COPY`s = runtime vs
support); web routes (`APIRouter(prefix=…)` + `@router.<verb>("…")` joined with
`include_router`; Express `app.use`/`router.get`; Flask `@app.route`; Spring
`@RestController`/`@RequestMapping`); the dependency manifest; per-directory `CLAUDE.md`/
`README` as human-written hints (verify against code).

**How to extract:** build the top-level component graph from directories that contain
runtime code; map each web route to its handler/feature; optionally an import/dependency
graph between internal packages.

**Emit:** `service`/`component` nodes grouped by directory or layer; `config` for
config/data dirs; edges for route→handler and module→module imports. Keep it
high-level — one box per module/package, not per file.

**Worked example:** runtime dirs `agents/ app/ core/ services/ config/` (the
`Dockerfile` `COPY` set); entry `app/main.py` includes routers
`health · webhook · orders · payments · admin`; support dirs `tests/ scripts/ docs/`
(present in the repo but not copied into the image).

---

## Cross-cutting tips
- Discover **per view in parallel** (one Explore subagent each) on large repos, then assemble.
- Prefer a small Python AST script (stdlib `ast`) for graph/table-constant extraction over brittle regex; fall back to `grep` for a first pass.
- Always populate `notes` with what you **inferred** vs **read**, and any doc/code drift — honesty is a feature of the output (it shows in a banner).
