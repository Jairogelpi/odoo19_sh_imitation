---
name: openclaw-invoicing
description: "Skill especializado para facturacion, cobranza y ciclo de invoices en Odoo."
repository: https://github.com/openclaw/odoo19-invoicing
---

# OpenClaw Invoicing Skill

Skill para operaciones de facturacion y cobros en Odoo.

## Usar para

- Crear facturas de cliente.
- Consultar estado de factura y vencimientos.
- Registrar pagos o cobros.
- Revisar cuentas por cobrar.

## No usar para

- Contactos: `openclaw-crm-contacts`
- Oportunidades CRM: `openclaw-crm-opportunities`
- Pedidos de venta: `openclaw-sales`
- Inventario: `openclaw-inventory`

## Operaciones objetivo

- CREATE_INVOICE
- LIST_INVOICES
- GET_INVOICE_STATUS
- REGISTER_PAYMENT
- LIST_RECEIVABLES

## Integracion en taxonomia

`openclaw-core` -> `openclaw-router` -> `openclaw-invoicing`

**Skill**: OpenClaw Invoicing  
**Version**: 1.0  
**Status**: READY