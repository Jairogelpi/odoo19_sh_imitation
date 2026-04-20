---
name: openclaw-core
description: "Skill núcleo de OpenClaw para políticas, permisos, taxonomía oficial, enrutamiento y orquestación entre dominios."
repository: https://github.com/openclaw/openclaw-core
---

# OpenClaw Core

Este es el skill **núcleo** de OpenClaw. No resuelve dominios de negocio concretos. Define el marco común que usan el router y los skills de dominio.

## Responsabilidades

- Definir la taxonomía oficial de skills.
- Mantener políticas, permisos y aprobaciones.
- Coordinar el routing entre dominios.
- Normalizar el contexto compartido entre skills.
- Servir como fallback para tareas Odoo genéricas.

## Taxonomía Oficial

### 1. Core
- `openclaw-core`

### 2. Router
- `openclaw-router`

### 3. Skills de Dominio
- `openclaw-crm-contacts`
- `openclaw-crm-opportunities`
- `openclaw-sales`
- `openclaw-inventory`
- `openclaw-invoicing`
- `openclaw-purchase`
- `openclaw-hr`
- `openclaw-reporting`
- `openclaw-odoo`

## Cuándo Usar Este Skill

Usar `openclaw-core` cuando la tarea sea de:
- políticas
- permisos
- approvals
- routing entre skills
- arquitectura OpenClaw
- normalización del contexto compartido

## No Usar Para

- Crear o editar contactos: usar `openclaw-crm-contacts`
- Pipeline CRM: usar `openclaw-crm-opportunities`
- Cotizaciones y pedidos: usar `openclaw-sales`
- Stock e inventario: usar `openclaw-inventory`
- Operaciones Odoo genéricas: usar `openclaw-odoo`

## Formato de Contexto

```json
{
  "core": "openclaw-core",
  "router": "openclaw-router",
  "domains": [
    "openclaw-crm-contacts",
    "openclaw-crm-opportunities",
    "openclaw-sales",
    "openclaw-inventory",
    "openclaw-invoicing",
    "openclaw-purchase",
    "openclaw-hr",
    "openclaw-reporting",
    "openclaw-odoo"
  ]
}
```

## Regla Principal

Primero se identifica el dominio, luego se ejecuta el skill correcto. Si el dominio no es claro, el router pide más contexto o deriva a `openclaw-odoo`.

**Skill**: OpenClaw Core  
**Versión**: 1.0  
**Status**: ✅ OFFICIAL TAXONOMY CORE