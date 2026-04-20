---
name: openclaw-hr
description: "Skill especializado para RRHH: empleados, ausencias, contratos y payroll intents."
repository: https://github.com/openclaw/odoo19-hr
---

# OpenClaw HR Skill

Skill para procesos de recursos humanos en Odoo.

## Usar para

- Alta y actualizacion de empleados.
- Gestion de ausencias y vacaciones.
- Consultas de contratos.
- Flujos de nomina/payroll intents.

## No usar para

- Contactos CRM: `openclaw-crm-contacts`
- Ventas: `openclaw-sales`
- Compras: `openclaw-purchase`

## Operaciones objetivo

- CREATE_EMPLOYEE
- UPDATE_EMPLOYEE
- REQUEST_LEAVE
- APPROVE_LEAVE
- LIST_PAYROLL_ITEMS

## Integracion en taxonomia

`openclaw-core` -> `openclaw-router` -> `openclaw-hr`

**Skill**: OpenClaw HR  
**Version**: 1.0  
**Status**: READY