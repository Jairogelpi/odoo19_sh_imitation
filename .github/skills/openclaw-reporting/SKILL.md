---
name: openclaw-reporting
description: "Skill especializado para reportes, dashboards, metricas y analitica de negocio."
repository: https://github.com/openclaw/odoo19-reporting
---

# OpenClaw Reporting Skill

Skill para reporting y analitica en Odoo.

## Usar para

- Generar reportes operativos y ejecutivos.
- Construir consultas de KPIs.
- Preparar dashboards de negocio.
- Forecasts y analisis de tendencias.

## No usar para

- Ejecucion de ventas operativas: `openclaw-sales`
- Inventario operativo: `openclaw-inventory`
- Flujos CRM de oportunidad: `openclaw-crm-opportunities`
- Creacion guiada de dashboards por chat con preguntas proactivas: `openclaw-dashboard-chat`

## Operaciones objetivo

- GENERATE_REPORT
- KPI_QUERY
- BUILD_DASHBOARD
- FORECAST_SUMMARY
- EXPORT_REPORT

## Integracion en taxonomia

`openclaw-core` -> `openclaw-router` -> `openclaw-reporting`

**Skill**: OpenClaw Reporting  
**Version**: 1.0  
**Status**: READY