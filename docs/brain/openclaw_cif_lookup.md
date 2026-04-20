# OpenClaw CIF Lookup

## Purpose

Enrich and upsert Spanish companies into `res.partner` by CIF. Lookup is done
by a dedicated MCP service (`cif-lookup-mcp`). Writes to Odoo are routed
through the OpenClaw permission pipeline (never XML-RPC direct).

## Where it lives

- MCP service: [services/cif-lookup-mcp/](../../services/cif-lookup-mcp/)
- Compose declaration: [compose.admin.yaml](../../compose.admin.yaml) service `cif-lookup-mcp`
- Control-plane wiring: `control-plane/app/config.py` (`openclaw_cif_lookup_mcp_*`) and `control-plane/app/mcp_gateway.py` (tools `cif.validate`, `cif.lookup`, handlers `tool_cif_validate`, `tool_cif_lookup`)
- Skill: [.github/skills/openclaw-cif-lookup/SKILL.md](../../.github/skills/openclaw-cif-lookup/SKILL.md)
- Source of truth for this feature comes from a standalone stdio MCP reference the user supplied (`files (3)/server.py`). Adapted to the HTTP JSON-RPC pattern used by the rest of the stack.

## Exposed tools (via control-plane gateway)

- `cif.validate` — format-only validation. No network.
- `cif.lookup` — scrapes `infocif.es` / `infoempresa.com` / `axesor.es` with fallback chain, extracts CP/municipio/CCAA, and optionally enriches phone/website via Google Maps Places. Returns a ready-to-use `_res_partner` mapping when called with `include_partner_mapping=true`.

## Design decision: no direct Odoo write

The reference server.py shipped a `guardar_empresa_en_odoo` tool that performed a direct XML-RPC upsert on `res.partner`. This was intentionally dropped from the adapted MCP service. Reason:

- OpenClaw's entire value is the policy/approval/audit pipeline on Odoo mutations.
- A separate MCP with Odoo write credentials bypasses that pipeline.
- Instead, `cif.lookup` returns the mapped `res.partner` payload, and the skill instructs the LLM to submit it as an `openclaw.request` (action_type `odoo_write`) which will flow through the normal approval/execution path.

The side benefit is that the CIF service needs no Odoo credentials at all — it only needs `MCP_AUTH_TOKEN` and optionally `GOOGLE_MAPS_API_KEY`.

## Configuration

Required env (`compose.admin.yaml` reads these):

- `OPENCLAW_CIF_LOOKUP_MCP_TOKEN` — shared secret between control-plane and the MCP service.
- `OPENCLAW_CIF_LOOKUP_MCP_URL` — defaults to `http://cif-lookup-mcp:8093/mcp`.
- `OPENCLAW_CIF_LOOKUP_MCP_TIMEOUT_SECONDS` — defaults to 30.
- `GOOGLE_MAPS_API_KEY` — optional, enables phone/website enrichment when scrapers come back empty.

## Bring-up

```bash
docker compose -f compose.yaml -f compose.admin.yaml up -d cif-lookup-mcp control-plane
```

Verify:

```bash
# From inside any container on odoo_net:
curl -s http://cif-lookup-mcp:8093/healthz
# → {"status":"ok","service":"cif-lookup-mcp"}
```

Then a lookup through the gateway:

```bash
curl -s -X POST http://control-plane:8082/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"cif.lookup","arguments":{"cif":"B12345678","include_partner_mapping":true}}}'
```

## Failure modes

- All three scrapers empty → `{"error": true, "mensaje": "No se encontraron datos..."}`. Common for very new or small companies.
- Google Maps not configured → phone/website may be missing; `_nota` flag is set in the response.
- CIF format invalid → short-circuits with `{"error": true, "mensaje": "CIF '<x>' no válido."}`.
- Scraper layout change → a given source returns `None` and the fallback chain tries the next. If all three change at once, the tool returns empty and the skill reports the fields that couldn't be recovered.

## Related

- Skill: `openclaw-crm-contacts` handles contacts that are **not** Spanish companies or don't have a CIF.
- Incident 2026-04-18: see [openclaw_incident_2026-04-18_unlink_became_create.md](openclaw_incident_2026-04-18_unlink_became_create.md) — establishes why all Odoo writes (including the ones this skill triggers) must carry an explicit `operation` field.
