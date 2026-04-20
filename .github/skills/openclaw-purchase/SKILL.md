---
name: openclaw-purchase
description: "Skill especializado para compras, proveedores y procurement en Odoo."
repository: https://github.com/openclaw/odoo19-purchase
---

# OpenClaw Purchase Skill

Skill para ciclo de compras y proveedores en Odoo.

## Usar para

- Crear y gestionar ordenes de compra.
- Gestionar proveedores.
- Revisar recepciones de compra.
- Flujos de procurement y reabastecimiento.

## No usar para

- Ventas: `openclaw-sales`
- Inventario operativo: `openclaw-inventory`
- Facturacion cliente: `openclaw-invoicing`

## Operaciones objetivo

- CREATE_PURCHASE_ORDER
- LIST_PURCHASE_ORDERS
- GET_VENDOR
- RECEIVE_PURCHASE
- TRACK_PROCUREMENT

## Integracion en taxonomia

`openclaw-core` -> `openclaw-router` -> `openclaw-purchase`

**Skill**: OpenClaw Purchase  
**Version**: 1.0  
**Status**: READY