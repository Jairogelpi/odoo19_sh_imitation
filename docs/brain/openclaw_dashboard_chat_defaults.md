# OpenClaw Dashboard Chat Defaults

## Scope

This note documents the local router behavior for chat-driven dashboard creation when the user delegates configuration choices to OpenClaw.

Relevant code:

- [control-plane/app/mcp_gateway.py](../../control-plane/app/mcp_gateway.py)
- [control-plane/app/tests/test_tool_chat_reply_contract.py](../../control-plane/app/tests/test_tool_chat_reply_contract.py)

## Why this exists

The `openclaw-dashboard-chat` skill requires a proactive discovery flow and explicitly says that when the user says something like "hazlo tu", the system should propose a base configuration and ask for quick confirmation.

That means:

- OpenClaw should not silently invent a dashboard and jump straight to a write action
- but it also should not keep asking for every field again when the user has already delegated the choice and the domain is clear

## Current router behavior

The local dashboard router now uses recent user-message context, not only the last user turn.

Behavior:

1. If the request is still underspecified and there is no explicit delegation, the router asks for the missing dashboard data as before.
2. If the user explicitly delegates configuration and the recent context clearly points to Sales, the router proposes a closed default configuration and waits for confirmation.
3. If the user then confirms with a follow-up like `si`, `hazlo`, or `adelante`, the router generates the normal `odoo_write` action for `dashboard.dashboard`.

## Safe defaults currently supported

Only a narrow Sales default is implemented today.

When recent dashboard context includes an explicit delegation such as:

- `hazlo tu`
- `lo que tu quieras`
- `you choose`

and the domain clearly points to Sales, the router can fill:

- dashboard name: `Ventas - Registros`
- chart type: `bar_chart`
- source model: `sale.order`
- fields: `["state"]`
- representation: `Numero de registros de ventas por estado`

These defaults are not applied for unrelated dashboard domains.

## Confirmation contract

The router only turns those defaults into a suggested action after a confirmation turn such as:

- `si`
- `hazlo`
- `adelante`

Until then, the reply stays informational and `suggested_actions` remains empty.

## Test coverage

Contract tests cover:

- delegated sales dashboard request proposes defaults without action
- confirmation after delegation generates the expected `dashboard.dashboard` create action
- existing strict behavior for incomplete dashboard specs still holds

Current targeted result:

```text
.\.venv\Scripts\python.exe -m pytest control-plane/app/tests/test_tool_chat_reply_contract.py -q
18 passed in 0.71s
```
