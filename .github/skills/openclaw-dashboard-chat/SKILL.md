---
name: openclaw-dashboard-chat
description: "Usar cuando el usuario pida crear, editar, clonar, publicar o compartir dashboards por chat en OpenClaw. Activa flujo proactivo de descubrimiento para pedir toda la informacion necesaria antes de construir el dashboard."
repository: https://github.com/openclaw/openclaw-dashboard-chat
---

# OpenClaw Dashboard Chat Skill

Skill especializado para crear dashboards desde chat de forma guiada, proactiva y segura.

## Usar para

- Crear dashboards desde lenguaje natural.
- Refinar dashboards existentes (filtros, metricas, visualizaciones).
- Clonar dashboard y adaptarlo a otro equipo o periodo.
- Publicar dashboards para grupos/usuarios en Odoo.
- Entregar resumen final por chat con el resultado y siguientes pasos.

## No usar para

- Operaciones de ventas directas: `openclaw-sales`
- CRUD de contactos: `openclaw-crm-contacts`
- Ajustes de seguridad global no ligados al dashboard: `openclaw-odoo`
- Reportes puntuales sin persistencia en dashboard: `openclaw-reporting`

## Operaciones objetivo

- DASHBOARD_DISCOVERY
- DASHBOARD_CREATE
- DASHBOARD_EDIT
- DASHBOARD_CLONE
- DASHBOARD_PUBLISH
- DASHBOARD_VALIDATE
- DASHBOARD_EXPLAIN

## Integracion en taxonomia

`openclaw-core` -> `openclaw-router` -> `openclaw-dashboard-chat`

## Contrato conversacional (proactivo)

Antes de crear el dashboard, el skill debe preguntar lo necesario. No asumir datos faltantes.

### Preguntas minimas obligatorias

1. Objetivo de negocio:
- Que decision debe habilitar este dashboard?

2. Audiencia:
- Quien lo va a usar (rol, equipo, frecuencia)?

3. Alcance temporal:
- Dia, semana, mes, trimestre o rango personalizado?

4. Fuente de datos:
- Modulos/modelos Odoo implicados (CRM, Sales, Facturacion, Inventario, etc.)?

5. KPIs prioritarios:
- Cuales 3 a 7 metricas son imprescindibles?

6. Segmentacion/filtros:
- Por comercial, territorio, producto, cliente, etapa, compania?

7. Visualizacion preferida:
- Tabla, barra, linea, embudo, donut, KPI cards?

8. Umbrales/alertas:
- Existe objetivo minimo, maximo o semaforo?

9. Permisos:
- Quien puede ver/editar?

10. Entrega:
- Solo en pantalla, exportable, o compartir por chat/email?

### Modo proactivo

- Si detecta ambiguedad, hace una pregunta cerrada con opciones.
- Si el usuario pide "hazlo tu", propone una configuracion base y pide confirmacion rapida.
- Si faltan datos criticos, bloquea la ejecucion y explica exactamente que falta.

## Formato de salida por chat

Siempre responder con estructura clara:

1. Resumen de lo entendido.
2. Datos faltantes (si aplica).
3. Propuesta de dashboard (bloques, KPIs, filtros, visualizaciones).
4. Estado de ejecucion (creado/actualizado/publicado).
5. Siguientes acciones recomendadas.

## Definicion minima de dashboard (payload)

```json
{
  "name": "Ventas Semanal",
  "goal": "Monitorear conversion y facturacion semanal",
  "kpis": ["opportunities_won", "quote_to_order_rate", "invoiced_amount"],
  "filters": {"date_range": "last_30_days", "team": "Sales ES"},
  "widgets": [
    {"type": "kpi", "metric": "invoiced_amount"},
    {"type": "funnel", "metric": "pipeline_stages"},
    {"type": "bar", "metric": "top_products"}
  ],
  "permissions": {"read_groups": ["sales_manager"], "edit_groups": ["bi_admin"]}
}
```

## Checklist de calidad

- [x] Objetivo de negocio definido
- [x] KPIs y filtros validados con el usuario
- [x] Visualizaciones alineadas al caso de uso
- [x] Permisos aplicados
- [x] Dashboard probado con datos reales
- [x] Resumen final enviado por chat

**Skill**: OpenClaw Dashboard Chat  
**Version**: 1.0  
**Status**: READY
