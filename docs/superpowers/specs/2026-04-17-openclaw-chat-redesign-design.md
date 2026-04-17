# OpenClaw Chat Redesign — Bidirectional Admin Shell

**Date:** 2026-04-17
**Status:** Draft design, pending user review
**Scope:** `addons_custom/openclaw/` (chat client view + request model) and `control-plane/app/mcp_gateway.py` (`tool_chat_reply`)

---

## 1. Goal

Replace the current amber "orphism" chat shell with a sober, light, ChatGPT/Claude-style admin UI that also visualizes agent actions inline. The assistant proposes actions; the user approves or rejects them from the chat; approved actions are materialized as real `openclaw.request` records and executed through the existing state machine.

Two outcomes:

- **Visual**: reuse the `control-plane` design language (Inter + JetBrains Mono, light surfaces, blue accent, chips/badges/panels) inside the Odoo backend, scoped to the chat action.
- **Functional**: bind chat sessions and messages to `openclaw.request` records so the assistant's suggestions flow through the existing approval/execution pipeline — no mock buttons, no parallel state machine.

---

## 2. Non-goals

Deferred to future iterations; explicitly out of this spec:

- Streaming replies (SSE) — chat remains blocking.
- Editing payload before approval — user approves/rejects as proposed; editing is done from the standalone Request form.
- Automatic retry of `failed` requests.
- Shared conversation history across users.
- Markdown or syntax highlighting in message content — plain text only.
- OpenRouter native tool-calling API — suggestions come via structured JSON in the text response.

---

## 3. Architecture

```
┌─ OWL client (openclaw_chat.js) ──────────────────┐
│  state: sessions, activeSession, messages,       │
│         drawerRequestId, sending, approving      │
│  user types      → rpc_send_message              │
│  user approves   → rpc_approve_request           │
│  user rejects    → rpc_reject_request            │
│  user opens card → rpc_get_request_detail        │
└──────────────────────────────────────────────────┘
                    │ ORM/RPC
┌─ Odoo (openclaw.chat.session) ───────────────────┐
│  rpc_send_message(session, content):             │
│    1. create user message                        │
│    2. call gateway chat.reply with policy ctx    │
│    3. persist assistant message (content)        │
│    4. for each suggested_action:                 │
│       validate & create openclaw.request         │
│       in draft state with session_id,            │
│       message_id, origin='chat_suggestion',      │
│       approval_required=True (forced)            │
│    5. return session + messages + requests       │
│                                                  │
│  rpc_approve_request(request_id):                │
│    synchronous: submit → approve → execute →     │
│    mark_executed/failed; return final state      │
└──────────────────────────────────────────────────┘
                    │ httpx
┌─ control-plane (tool_chat_reply) ────────────────┐
│  input: messages + optional policy_context       │
│  output: { reply, suggested_actions[], ... }     │
└──────────────────────────────────────────────────┘
```

Key design points:

- Chat does **not** duplicate the request state machine; it delegates to `action_submit` / `action_approve` / `action_execute` on the existing model.
- The gateway does **not** validate policies. It proposes; Odoo validates and materializes.
- Invalid suggestions (unknown `policy_key`, non-dict payload, unlisted `action_type`) still become `openclaw.request` records in `draft` with `decision_note` explaining the block. UI renders them as `blocked` cards with only a Details button.

---

## 4. Data model changes

### 4.1 `openclaw.request` (extend `addons_custom/openclaw/models/openclaw_request.py`)

```python
session_id = fields.Many2one(
    'openclaw.chat.session',
    string='Chat Session',
    ondelete='set null',
    index=True,
)
message_id = fields.Many2one(
    'openclaw.chat.message',
    string='Originating Message',
    ondelete='set null',
    index=True,
)
origin = fields.Selection(
    [('manual', 'Manual'), ('chat_suggestion', 'Chat Suggestion')],
    default='manual',
    required=True,
)
rationale = fields.Text(string='Agent Rationale', readonly=True)
```

`ondelete='set null'` preserves audit history when sessions or messages are deleted. `origin` distinguishes records created from the classic form from those proposed by the assistant; the existing list view can optionally filter by it.

### 4.2 `openclaw.chat.message` (extend `addons_custom/openclaw/models/openclaw_chat.py`)

```python
request_ids = fields.One2many(
    'openclaw.request',
    'message_id',
    string='Suggested Actions',
)
```

### 4.3 `openclaw.chat.session` (extend same file)

```python
request_ids = fields.One2many(
    'openclaw.request',
    'session_id',
    string='Chat Actions',
)
```

### 4.4 Serialization helper

On `openclaw.request`:

```python
def _chat_card_payload(self):
    self.ensure_one()
    return {
        'id': self.id,
        'state': self.state,
        'action_type': self.action_type,
        'custom_tool_name': self.custom_tool_name,
        'policy_name': self.policy_id.name if self.policy_id else '',
        'policy_key': self.policy_id.key if self.policy_id else '',
        'target_model': self.target_model or '',
        'target_ref': self.target_ref or '',
        'rationale': self.rationale or '',
        'result_summary': self.result_summary or '',
        'error_message': self.error_message or '',
        'decision_note': self.decision_note or '',
        'blocked': bool(self.decision_note) and self.state == 'draft' and not self.policy_id,
    }
```

`_message_payload` in `OpenClawChatSession` adds `'requests': [r._chat_card_payload() for r in message.request_ids]`. The heavy fields (full `payload_json`, `gateway_response_json`, `policy_snapshot_json`) stay off the message payload and are fetched lazily via `rpc_get_request_detail(id)` when the drawer opens.

### 4.5 Access rights

`security/ir.model.access.csv` already grants:

- `base.group_user` → read-only on `openclaw.request`.
- `openclaw.group_openclaw_user` (and above) → read/write/create on `openclaw.request`.

Implication: any internal user can reach the chat action, but only members of the openclaw groups can materialize suggestions as requests. To keep the chat usable for every internal user without silently failing, `_materialize_suggestions` wraps the `.create()` in a check: if the current user lacks create rights on `openclaw.request`, suggestions are logged via `_logger.info("Skipped N chat suggestions for non-openclaw user")` and dropped. The text `reply` still flows through.

No new CSV rows are introduced in this spec. A future iteration can gate the chat menu itself by `openclaw.group_openclaw_user` if the product decides that suggestions are central to the experience.

### 4.6 Migration

Columns are nullable with safe defaults. Pre-existing requests get `origin='manual'` and `session_id=NULL` automatically. No data migration step required; `odoo -u openclaw` is sufficient.

---

## 5. Gateway contract

### 5.1 `tool_chat_reply` input (extended, backward-compatible)

```json
{
  "messages": [...],
  "model": "...",
  "temperature": 0.5,
  "max_tokens": 800,
  "policy_context": {
    "available_policies": [
      {"key": "odoo_read", "name": "Odoo Read",
       "allowed_actions": ["odoo_read", "docs_read", "web_search"]}
    ],
    "user_locale": "es_ES"
  }
}
```

Odoo builds `policy_context` per-request from `openclaw.policy` records accessible to `self.env.user` (via `group_ids`).

### 5.2 `tool_chat_reply` output (extended, backward-compatible)

```json
{
  "kind": "completed",
  "summary": "Generated a chat reply.",
  "reply": "Te propongo actualizar...",
  "model": "...",
  "provider": "openrouter",
  "suggested_actions": [
    {
      "title": "Actualizar contacto ACME",
      "rationale": "El usuario pidió refrescar los datos de ACME.",
      "action_type": "odoo_write",
      "custom_tool_name": null,
      "policy_key": "odoo_write_contacts",
      "payload": {"model": "res.partner", "id": 42, "values": {"phone": "..."}},
      "target_model": "res.partner",
      "target_ref": "42"
    }
  ]
}
```

- `suggested_actions` is optional; absent or empty means no proposal. Full backward compatibility with current callers.
- Validation lives on the Odoo side (see §7).

### 5.3 System prompt extension

`_chat_messages_for_gateway` appends to the existing system message:

```
Available policies for this user: {available_policies_json}.
If the user request fits a policy, include `suggested_actions[]` items with:
title, rationale, action_type, policy_key, payload.
Do NOT invent policies outside the listed set.
When unsure, do not suggest an action.
Always include a human-readable `reply` in text.
```

### 5.4 Tool-calling mechanism

The gateway does **not** use OpenRouter's native tool-calling endpoint. The system prompt instructs the LLM to return a single JSON object as its entire response, matching this schema:

```json
{
  "reply": "<natural-language reply to the user>",
  "suggested_actions": [ /* zero or more action objects, schema per §5.2 */ ]
}
```

The gateway parses this JSON once received. If parsing fails or required keys are missing:

- If the raw text is non-empty, it is used as `reply` and `suggested_actions` defaults to `[]`.
- If the raw text is empty, the fallback "OpenClaw did not receive a usable reply" path runs.

Rationale for this approach: simpler than tool-calling, model-agnostic, works with any chat-completion-capable model, and keeps all validation on the Odoo side where policies live.

### 5.5 Fallback mode

When OpenRouter is unconfigured or fails, the local fallback path returns `suggested_actions: []` unconditionally. The UI works as a plain chat with no agent behavior.

---

## 6. Frontend / UX

### 6.1 Layout (light admin shell)

```
┌──────────────────────────────────────────────────────────────────┐
│ Topbar (sticky)                                                  │
│ ●Odoo19 · OpenClaw    [nueva conversación +]     env · user     │
├────────────────┬─────────────────────────────────────────────────┤
│ Sidebar 260px  │ ChatHeader (sticky): title · · connected · model│
│ session list   │─────────────────────────────────────────────────│
│                │ MessagesScroll                                  │
│                │  user bubble (right)                            │
│                │  assistant bubble (left)                        │
│                │    └ ActionCard(s) inline                       │
│                │─────────────────────────────────────────────────│
│                │ Composer (sticky bottom) · auto-grow · send ↑  │
└────────────────┴─────────────────────────────────────────────────┘
```

### 6.2 OWL component tree

Single file `addons_custom/openclaw/static/src/js/openclaw_chat.js`; templates in `static/src/xml/openclaw_chat.xml`.

- **`OpenClawChatAction`** (root) — state, RPCs, action routing. Extended with `approveRequest(id)`, `rejectRequest(id)`, `openRequestDetail(id)`, `closeDrawer()`. New state: `drawerRequestId`, `approvingRequestId`.
- **`ChatSidebar`** — sessions list + "New chat" button. Extracted sub-template.
- **`ChatMessages`** — scroll area; renders bubbles. Assistant messages render their `message.requests` as inline cards after the text.
- **`ActionCard`** — one request. Props: `request`, `onApprove`, `onReject`, `onViewDetail`.
- **`RequestDrawer`** — slide-in right panel. Opens when `drawerRequestId != null`. Lazily fetches detail via `rpc_get_request_detail(id)`. Closes on Esc or backdrop click.
- **`ChatComposer`** — textarea auto-grow (1–6 rows), circular send button. Enter sends, Shift+Enter newline.

### 6.3 ActionCard state → visual mapping

| `request.state`              | icon | chip          | buttons                       |
|------------------------------|------|---------------|-------------------------------|
| `draft` (normal)             | ○    | "Propuesta"   | Approve / Reject / Details    |
| `draft` with `decision_note` | ⚠    | "Bloqueada"   | Details only                  |
| `pending`                    | ○    | "Pendiente"   | Approve / Reject / Details    |
| `approved` (executing)       | ⟳    | "Ejecutando…" | spinner; Details only         |
| `executed`                   | ✓    | "Ejecutada"   | Details                       |
| `failed`                     | ✕    | "Fallida"     | Details                       |
| `rejected`                   | –    | "Rechazada"   | Details                       |

`blocked` is a UI-only projection of `draft + decision_note + no policy_id`.

### 6.4 Interactions

- **Approve**: RPC `rpc_approve_request(id)` synchronous. UI optimistically renders `approved` with spinner; on return, repaints final state. On RPC error, reverts to `pending` and shows a `notification.add(_, {type:"danger"})`.
- **Reject**: `rpc_reject_request(id)`, no prompt, immediate transition.
- **Details**: sets `drawerRequestId`, opens drawer with skeleton → full detail.
- **Multiple cards per message**: listed vertically; each independent. Approve/Reject on one does not affect the others.
- **Session switch while a card is executing**: the approval continues on the server; returning to the session shows the final state.
- **Scroll**: auto-scroll to bottom on new assistant reply and on user send. No auto-scroll when a card's state changes (user may be reading above).

---

## 7. Visual style

All styles scoped to `.o_openclaw_chat` in `addons_custom/openclaw/static/src/scss/openclaw_chat.scss` to avoid colliding with Odoo backend globals.

### 7.1 Design tokens

```scss
.o_openclaw_chat {
  --openclaw-font: "Inter", ui-sans-serif, system-ui, -apple-system,
                   "Segoe UI", Roboto, sans-serif;
  --openclaw-mono: "JetBrains Mono", ui-monospace, SFMono-Regular,
                   Menlo, monospace;

  --openclaw-bg: #f7f8fa;
  --openclaw-bg-gradient:
    radial-gradient(1200px 600px at 10% -10%, #eef2f7 0%, transparent 60%),
    radial-gradient(900px 500px at 90% 0%, #e8eef7 0%, transparent 55%),
    linear-gradient(180deg, #f7f8fa 0%, #eef1f6 100%);

  --openclaw-surface: rgba(255, 255, 255, 0.82);
  --openclaw-surface-strong: rgba(255, 255, 255, 0.95);
  --openclaw-border: rgba(15, 23, 42, 0.08);
  --openclaw-border-strong: rgba(15, 23, 42, 0.14);

  --openclaw-text: #0f172a;
  --openclaw-text-muted: #475569;
  --openclaw-text-subtle: #64748b;

  --openclaw-accent: #2563eb;
  --openclaw-accent-soft: rgba(37, 99, 235, 0.08);
  --openclaw-accent-strong: #1d4ed8;

  --openclaw-success: #10b981;
  --openclaw-success-soft: rgba(16, 185, 129, 0.1);
  --openclaw-warning: #f59e0b;
  --openclaw-warning-soft: rgba(245, 158, 11, 0.12);
  --openclaw-danger: #ef4444;
  --openclaw-danger-soft: rgba(239, 68, 68, 0.1);

  --openclaw-radius: 14px;
  --openclaw-radius-sm: 10px;
  --openclaw-radius-xs: 6px;

  --openclaw-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04),
                       0 1px 3px rgba(15, 23, 42, 0.04);
  --openclaw-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
                    0 8px 24px rgba(15, 23, 42, 0.06);
}
```

### 7.2 Typography

- Body: Inter 0.92rem / line-height 1.55.
- Kicker/meta labels: 0.72rem, `letter-spacing: 0.08em`, uppercase, `text-subtle`.
- Payload JSON in drawer: JetBrains Mono 0.82rem over dark background (`#0f172a` / `#e2e8f0`), matching `.recipe` in control-plane.
- No large h1/h2 in the shell; titles are 1rem weight 600. Admin density, not marketing.

### 7.3 Component styling

| Component         | Style rules                                                             |
|-------------------|-------------------------------------------------------------------------|
| Sidebar           | `surface` + `border` + `radius`, 260px, padding 16px                    |
| Session item      | transparent; hover `accent-soft`; active `accent` bg + white text       |
| Topbar / header   | sticky, `surface`, `backdrop-filter: blur(16px)`, 1px border-bottom     |
| User bubble       | `accent-soft` bg, `accent-strong` text, right-aligned, max-width 72ch   |
| Assistant bubble  | `surface` bg, no border, left-aligned, max-width 72ch                   |
| Avatar            | none — author shown as 0.72rem uppercase kicker above bubble            |
| ActionCard        | `surface-strong` bg, `border-strong`, `radius-sm`, padding 12px 14px    |
| Card chip         | reuse `.chip`/`.badge-*` classes: `badge-success`=executed, `badge-failure`=failed, `badge-running`=approved, `badge-cancelled`=rejected, `chip` with `warning-soft`=pending, `chip` with `warning-soft` + ⚠ icon=blocked |
| Card buttons      | compact 7px 12px: `btn-primary` Approve, `btn-ghost` Reject, `btn-ghost` underlined Details |
| Composer          | sticky bottom, `surface-strong` + border-top, borderless textarea, circular 36px `accent` send button |
| Drawer            | 420px wide, `surface-strong`, border-left, `shadow-lg`, 200ms slide-in  |
| Empty state       | `border: 1px dashed`, 40px padding, centered muted text                 |

### 7.4 Density rules

- Gap between messages: 12px.
- Bubble padding: 10px 14px.
- Bubble and card radius: 10px (down from 20/24).
- `backdrop-filter` only on topbar; bubbles and cards are opaque for legibility.
- No amber radial glow; background is the subtle blue/gray gradient from control-plane.

### 7.5 Font loading

`@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap")` in the SCSS. Falls back to system-ui in offline installations.

### 7.6 Responsive

- `<1024px`: sidebar collapses to overlay triggered by hamburger icon in topbar.
- `<768px`: detail drawer expands to 100% width.
- `<480px`: sidebar hidden by default; session switcher exposed via dropdown in the header.

### 7.7 Accessibility

- Visible focus outlines (3px `accent-soft`).
- `aria-label` on bubbles ("tu mensaje" / "mensaje de OpenClaw").
- Cards wrapped in `role="group"` with `aria-label="Acción propuesta: …"`.
- Drawer uses `role="dialog"`, focus trap, Esc to close.

---

## 8. States and error handling

### 8.1 UI states

| State            | Condition                              | UI behavior                                                             |
|------------------|----------------------------------------|-------------------------------------------------------------------------|
| `loading`        | Initial session fetch                  | "Cargando…" empty state, sidebar hidden                                 |
| `empty_sessions` | User has no sessions                   | Auto-creates one (existing behavior)                                    |
| `empty_messages` | Open session, no messages              | Centered empty state with tip                                           |
| `idle`           | Normal operation                       | Standard UI                                                             |
| `sending`        | `rpc_send_message` in flight           | Composer disabled; ghost bubble "OpenClaw está pensando…" on left      |
| `approving`      | `rpc_approve_request` in flight        | Target card shows spinner; **other cards' Approve disabled**; Reject still allowed |
| `rejecting`      | `rpc_reject_request` in flight         | Card fades to 60% opacity briefly                                       |
| `drawer_loading` | Drawer open, fetching detail           | Skeleton placeholders                                                   |

### 8.2 Error paths

- **Gateway URL not configured**: `ValidationError` in `_generate_reply` → UI restores draft and shows danger notification.
- **Gateway timeout / 5xx**: existing `OpenClawGatewayError` path returns a text-only assistant message ("OpenClaw no pudo contactar…"); `suggested_actions=[]`. No change in behavior from today.
- **Invalid suggested_action** (unknown `policy_key`, non-dict payload, unlisted `action_type`): request is still created in `draft` with `decision_note` set to the specific reason and `policy_id` left empty. UI renders as `blocked`, Details-only.
- **`_execute_one` raises on Approve**: request becomes `failed` with `error_message` populated. Card repaints as `failed`. Notification: "No se pudo ejecutar la acción". User opens Details for `error_message` + `gateway_response_json`.
- **Policy revoked between propose and approve**: `_execute_one` re-validates permissions; if missing, raises `AccessError` → caught and set to `failed` with `error_message="Permiso revocado"`.
- **Session or message deleted with live requests**: FK `ondelete='set null'` preserves the request. It disappears from chat (no session) but remains in the OpenClaw Requests list with full history.
- **Empty LLM reply** (`kind='rejected'` or missing `reply`): existing behavior — shows "OpenClaw did not receive a usable reply"; ignores `suggested_actions`.

### 8.3 Degraded mode (local fallback)

Fallback provider emits `suggested_actions=[]` always. UI is functional as plain chat. No user-visible indicator of fallback; the information is logged server-side only.

### 8.4 Anti-abuse rules (in scope)

- **Rate limit**: max 5 suggested_actions per assistant reply. Extras are dropped on the Odoo side with `_logger.warning`; not persisted as requests.
- **Forced approval**: chat-originated requests set `approval_required=True` regardless of the policy's `require_human_approval`. The user's explicit click is the minimum consent for LLM-proposed actions. Manual requests keep respecting the policy flag.
- **No parallel execution in the same session**: while one card is `approving`, Approve on other cards is disabled until it resolves. Reject remains available (local state transition, no gateway call).

### 8.5 Audit / logging

- `approved_by` / `approved_at` already set by the existing state transitions — no extra work.
- `_logger.info` line on each materialization: `"Chat session %s materialized action %s as request %s"`.
- `message.response_json` (full gateway response retained on the message) is **not** added now; if needed for forensic use, can be a future column.

---

## 9. Testing

### 9.1 New test files in `addons_custom/openclaw/tests/`

Directory does not exist yet; create `tests/__init__.py` and the files below.

**`test_openclaw_chat_suggestions.py`** (TransactionCase):
- `test_send_message_materializes_actions` — stub gateway returns 2 valid actions; assert 2 `openclaw.request` with `origin='chat_suggestion'`, `session_id`, `message_id`, `state='draft'`, `approval_required=True`.
- `test_invalid_policy_key_creates_blocked_card` — stub returns unknown `policy_key`; request is `draft` with `decision_note` set, `policy_id` empty.
- `test_truncation_to_five_actions` — stub returns 7 actions; 5 persisted.
- `test_payload_not_dict_is_blocked` — payload is a list; request blocked with decision_note.
- `test_fallback_local_emits_no_actions` — fallback provider path yields no requests.

**`test_openclaw_chat_approval.py`** (TransactionCase):
- `test_rpc_approve_full_flow` — session + message + draft request; approve with mocked `_execute_one` success; state `executed`.
- `test_rpc_approve_policy_revoked` — user loses group between propose and approve; request ends `failed` with `error_message`.
- `test_rpc_reject_transitions` — pending → rejected.
- `test_rpc_approve_blocked_card_raises` — card with `decision_note` and no `policy_id`; approve raises `ValidationError`.

**`test_openclaw_request_origin.py`** (TransactionCase):
- `test_manual_request_still_works` — create request via form flow without `session_id`; `origin='manual'`; full existing flow intact.
- `test_session_deletion_preserves_request` — delete session with linked requests; requests survive with `session_id=NULL`.

### 9.2 Gateway tests (`control-plane/app/tests/test_tool_chat_reply_contract.py`, pytest)

- Mock OpenRouter returning JSON with parseable `suggested_actions`; assert output shape.
- Response with no `suggested_actions`; output defaults to `[]`.
- Malformed JSON in the LLM response; fallback to `suggested_actions=[]` without raising.

### 9.3 Manual verification checklist

1. `docker compose up` → open Odoo → OpenClaw menu.
2. Golden path: new session → prompt matching a policy → assistant replies + 1 card.
3. Approve → spinner → executed → Details shows payload and gateway response.
4. Trigger a failing action (e.g. revoke policy manually) → card shows `failed`.
5. Rapid send of 3 messages → composer correctly blocks; no overlap.
6. Responsive: resize to 1000px (sidebar visible), 700px (sidebar overlay), 400px (drawer 100%).
7. Dark-mode Odoo toggle (if enabled): chat remains light (scoped); contrast remains legible.

---

## 10. Rollout

1. Merge branch → `docker compose restart odoo`.
2. `odoo -u openclaw` to apply new columns on `openclaw.request`. Existing rows get `origin='manual'` and `session_id=NULL` automatically. No data migration needed.
3. `docker compose restart control-plane` to reload `tool_chat_reply`.
4. No config changes required; `policy_context` is derived from existing records.
5. Smoke test: send "hola" — must reply and not fail even with empty `suggested_actions`.

## 11. Rollback

- Revert Odoo addon commits → `odoo -u openclaw`. New columns persist but are ignored.
- Revert `mcp_gateway.py` → `docker compose restart control-plane`.
- No data loss: chat-originated requests become orphans visible from the Requests form.

---

## 12. File-level change summary

New:
- `addons_custom/openclaw/tests/__init__.py`
- `addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py`
- `addons_custom/openclaw/tests/test_openclaw_chat_approval.py`
- `addons_custom/openclaw/tests/test_openclaw_request_origin.py`
- `control-plane/app/tests/test_tool_chat_reply_contract.py`

Modified:
- `addons_custom/openclaw/__manifest__.py` — register `tests/` if needed; no asset changes beyond existing SCSS/JS/XML.
- `addons_custom/openclaw/models/openclaw_request.py` — add `session_id`, `message_id`, `origin`, `rationale`, `_chat_card_payload()`.
- `addons_custom/openclaw/models/openclaw_chat.py` — add `request_ids` on session and message; extend `_message_payload` to include `requests`; extend `_generate_reply` to return `(reply, suggested_actions)`; add `_materialize_suggestions`, `rpc_approve_request`, `rpc_reject_request`, `rpc_get_request_detail`; build `policy_context` in `_chat_messages_for_gateway` or an adjacent helper.
- `addons_custom/openclaw/static/src/js/openclaw_chat.js` — split into root + sub-components; add approve/reject/drawer logic.
- `addons_custom/openclaw/static/src/xml/openclaw_chat.xml` — new templates for `ChatSidebar`, `ChatMessages`, `ActionCard`, `RequestDrawer`, `ChatComposer`.
- `addons_custom/openclaw/static/src/scss/openclaw_chat.scss` — full replacement of the amber/orphism theme with the light control-plane-derived tokens and component styles.
- `control-plane/app/mcp_gateway.py` — extend `tool_chat_reply` input (`policy_context`) and output (`suggested_actions`); extend system prompt generation.

Unchanged:
- `openclaw.policy` model and form.
- `openclaw.request` state machine (`action_submit`, `action_approve`, `action_execute`, `_execute_one`).
- Gateway transport (JSON-RPC).
- Security groups.
