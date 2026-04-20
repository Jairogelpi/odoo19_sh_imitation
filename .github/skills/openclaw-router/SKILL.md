---
name: openclaw-router
description: "Skill orquestador que enruta solicitudes al skill correcto según la taxonomía oficial: openclaw-core + dominios de negocio OpenClaw."
repository: https://github.com/openclaw/openclaw-router
---

# OpenClaw Skill Router

Este skill **no ejecuta la lógica de negocio**. Solo decide **qué skill especializado** debe atender la solicitud.

## Dependencia Oficial

- `openclaw-core` define la taxonomía, políticas y el contexto compartido.
- `openclaw-router` clasifica el mensaje del usuario.
- Los skills de dominio ejecutan la operación real.

## Principio

OpenClaw funciona mejor cuando cada dominio está separado y se apoya en un núcleo común:
- core → `openclaw-core`
- router → `openclaw-router`
- contactos → `openclaw-crm-contacts`
- oportunidades → `openclaw-crm-opportunities`
- ventas → `openclaw-sales`
- inventario → `openclaw-inventory`
- facturacion → `openclaw-invoicing`
- compras → `openclaw-purchase`
- recursos humanos → `openclaw-hr`
- reporting → `openclaw-reporting`
- dashboard chat → `openclaw-dashboard-chat`
- Odoo genérico → `openclaw-odoo`

---

## Reglas de Enrutamiento

### Contactos
Usar `openclaw-crm-contacts` cuando el usuario pida:
- crear contacto
- editar contacto
- borrar contacto
- buscar contactos
- ver detalles de un contacto

### CRM / Pipeline
Usar `openclaw-crm-opportunities` cuando pida:
- crear lead
- calificar lead
- mover oportunidad de etapa
- ver pipeline
- forecast de ventas

### Ventas
Usar `openclaw-sales` cuando pida:
- crear cotización
- crear pedido
- confirmar pedido
- listar pedidos
- ver totales de ventas

### Inventario
Usar `openclaw-inventory` cuando pida:
- crear producto
- ver stock
- recibir mercancía
- transferir stock
- ajustar inventario

### Odoo Genérico
Usar `openclaw-odoo` cuando pida:
- configuración de Odoo
- permisos
- requests OpenClaw
- acciones ORM generales que no encajan en un dominio específico

### Facturación
Usar `openclaw-invoicing` cuando pida:
- crear factura
- registrar cobro/pago
- consultar cuentas por cobrar
- revisar estado de factura

### Compras
Usar `openclaw-purchase` cuando pida:
- crear orden de compra
- gestionar proveedor
- recibir compra
- flujo de procurement

### Recursos Humanos
Usar `openclaw-hr` cuando pida:
- alta o edición de empleado
- vacaciones, ausencias o permisos
- nómina/payroll
- contratos y procesos de RRHH

### Reporting
Usar `openclaw-reporting` cuando pida:
- reportes o informes
- dashboards
- métricas/KPIs
- análisis y forecast

### Dashboard por chat
Usar `openclaw-dashboard-chat` cuando pida:
- crear un dashboard desde chat
- definir KPIs, filtros y widgets conversando
- editar o clonar un dashboard existente
- publicar/compartir dashboard por roles
- asistente proactivo que pregunte datos faltantes

---

## Ejemplos de Ruteo

### Ejemplo 1
```
Usuario: "Crear contacto Juan García"
Router -> openclaw-crm-contacts
```

### Ejemplo 2
```
Usuario: "Mover Acme Corp a Qualified"
Router -> openclaw-crm-opportunities
```

### Ejemplo 3
```
Usuario: "Crear cotización para Acme Corp"
Router -> openclaw-sales
```

### Ejemplo 4
```
Usuario: "¿Cuánto stock hay de Widget A?"
Router -> openclaw-inventory
```

### Ejemplo 5
```
Usuario: "Revisar política de aprobación de OpenClaw"
Router -> openclaw-odoo
```

---

## Formato de Decisión

```json
{
  "selected_skill": "openclaw-crm-contacts",
  "reason": "El usuario pide crear/editar/borrar un contacto",
  "confidence": 0.98,
  "fallback": "openclaw-odoo"
}
```

---

## Prioridad de Resolución

1. Dominio explícito del usuario
2. Entidad principal mencionada
3. Acción pedida
4. Skill más específico
5. Fallback a `openclaw-odoo`

---

## Ambigüedades Comunes

### "Crear cliente"
Puede significar:
- `openclaw-crm-contacts` si es alta de contacto
- `openclaw-sales` si es una cotización/pedido

### "Actualizar pedido del cliente"
Puede significar:
- `openclaw-sales` si es un pedido
- `openclaw-crm-contacts` si es solo información del contacto

### "Ver estado del cliente"
Puede significar:
- `openclaw-crm-contacts` si es ficha de contacto
- `openclaw-crm-opportunities` si es estado comercial

---

## Recomendación de Uso

No mezclar lógica de negocio entre skills. Si una nueva capacidad pertenece a un dominio distinto, crear un skill nuevo en lugar de ampliar uno existente.

---

## Checklist del Router

- [x] Contactos → skill de contactos
- [x] CRM pipeline → skill de oportunidades
- [x] Ventas → skill de sales
- [x] Inventario → skill de inventory
- [x] Facturación → skill de invoicing
- [x] Compras → skill de purchase
- [x] RRHH → skill de hr
- [x] Reporting → skill de reporting
- [x] Dashboard por chat → skill de dashboard chat
- [x] Fallback genérico → openclaw-odoo

---

**Skill**: OpenClaw Router  
**Versión**: 1.0  
**Status**: ✅ READY
