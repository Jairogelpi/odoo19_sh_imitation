---
name: openclaw-crm-opportunities
description: "Skill especializado para gestionar oportunidades y pipeline de ventas en CRM. Crea oportunidades, mueve por fases, califica leads y rastrea probabilidades."
repository: https://github.com/openclaw/odoo19-crm-opportunities
---

# OpenClaw CRM Opportunities Skill

Skill para gestión completa de **oportunidades, leads y pipeline** de ventas en Odoo.

## Cuándo Usar Este Skill

✅ Crear nuevos leads y oportunidades  
✅ Mover oportunidades entre etapas del pipeline  
✅ Calificar leads (lead → opportunity)  
✅ Rastrear probabilidades de conversion  
✅ Asignar oportunidades a vendedores  
✅ Ver pipeline de ventas con pronósticos  
✅ Generar reportes de oportunidades  

## No Usar Para

❌ Gestionar contactos específicamente (usar: openclaw-crm-contacts)  
❌ Crear facturas (usar: openclaw-invoicing)  
❌ Crear pedidos directo (usar: openclaw-sales)  
❌ Gestionar inventario (usar: openclaw-inventory)  

---

## Operaciones Disponibles

### 💡 CREATE_LEAD
**Crear un nuevo lead**

```
Comando: "Crear lead para [contacto], valor estimado: [monto], industria: [industria]"

Entrada:
  - partner_id: int (contacto existente)
  - name: str (nombre del lead)
  - expected_revenue: float (valor en USD)
  - industry: str (sector)
  - contact_name: str (si es lead sin contacto)
  - email: str (si es lead sin contacto)

Salida:
  - id: int (ID del lead)
  - name: str
  - stage: "New" | "Contacted" | "Qualified" | "Negotiation"
  - status: "success" | "error"
```

### 🎯 CREATE_OPPORTUNITY
**Crear oportunidad directamente**

```
Comando: "Crear oportunidad para [contacto], fase: Propuesta, valor: [monto]"

Entrada:
  - partner_id: int
  - opportunity_name: str
  - stage_id: str (New, Contacted, Qualified, Negotiation, Won, Lost)
  - expected_revenue: float
  - probability: int (0-100, %)
  - user_id: int (vendedor asignado)

Salida:
  - id: int
  - name: str
  - expected_revenue: float
  - probability: int
```

### 📊 VIEW_PIPELINE
**Ver pipeline de ventas completo**

```
Comando: "Mostrar pipeline de ventas"

Entrada:
  - filters: dict (usuario, período, segmento)
  - group_by: str (stage, salesman, expected_date)

Salida:
  - stages: {
      "New": [opp1, opp2, ...],
      "Contacted": [...],
      "Qualified": [...],
      ...
    }
  - total_revenue: float
  - weighted_forecast: float (revenue * probability)
```

### 🔄 MOVE_OPPORTUNITY
**Mover oportunidad entre fases**

```
Comando: "Mover oportunidad [ID] a fase: [fase]"

Entrada:
  - opportunity_id: int
  - new_stage: str (New, Contacted, Qualified, Negotiation, Won, Lost)
  - reason: str (opcional)

Salida:
  - id: int
  - old_stage: str
  - new_stage: str
  - timestamp: datetime
```

### ✅ QUALIFY_LEAD
**Calificar un lead como oportunidad**

```
Comando: "Calificar lead [ID]"

Entrada:
  - lead_id: int
  - expected_revenue: float
  - partner_id: int (si aplica)

Salida:
  - opportunity_id: int (nuevo ID de oportunidad)
  - status: "success" | "error"
```

### 🏆 WIN_OPPORTUNITY
**Marcar oportunidad como ganada**

```
Comando: "Marcar oportunidad [ID] como ganada"

Entrada:
  - opportunity_id: int
  - final_revenue: float (opcional)

Salida:
  - status: "success"
  - message: "Oportunidad [nombre] ganada por [monto]"
  - next_step: "Crear OrderVenta" | "Crear Factura"
```

### ❌ LOSE_OPPORTUNITY
**Marcar oportunidad como perdida**

```
Comando: "Marcar oportunidad [ID] como perdida, razón: [razón]"

Entrada:
  - opportunity_id: int
  - lost_reason: str (budget, competition, timing, etc.)

Salida:
  - status: "success"
```

---

## Etapas del Pipeline

### Estándar Odoo
```
New (Nuevo)
  ↓
Contacted (Contactado)
  ↓
Qualified (Calificado)
  ↓
Negotiation (Negociación)
  ↓
Won (Ganado) ✅  o  Lost (Perdido) ❌
```

### Cada Etapa Incluye
- 📅 Duración estimada
- 📊 Probabilidad de conversión
- 👤 Asignado a quien
- 💰 Ingresos esperados
- 📝 Notas y actividades

---

## Pronósticos y Análisis

### Métrica: Expected Revenue por Etapa
```
New:           $50,000 × 10% = $5,000
Contacted:     $75,000 × 25% = $18,750
Qualified:     $100,000 × 50% = $50,000
Negotiation:   $80,000 × 75% = $60,000
                                _________
Total Forecast:                 $133,750
```

### Métricas Disponibles
- **Win Rate**: % oportunidades ganadas
- **Sales Cycle**: Días promedio desde lead a ganado
- **Average Deal Size**: Valor promedio por oportunidad
- **Forecast**: Ingresos esperados (ponderado por probabilidad)

---

## Integración con Contactos

### Flujo Completo
```
1. Crear Contacto (openclaw-crm-contacts)
   ↓
2. Crear Lead para contacto
   ↓
3. Calificar Lead → Oportunidad
   ↓
4. Mover por Pipeline
   ↓
5. Ganar/Perder
   ↓
6. Si Ganado → Crear Pedido (openclaw-sales)
           → Crear Factura (openclaw-invoicing)
```

---

## Ejemplos de Uso

### Ejemplo 1: Crear Lead y Oportunidad
```
Chat: "Crear lead para Acme Corp, valor $50,000, contacto: John Smith"

Skill: openclaw-crm-opportunities
Action: CREATE_LEAD
Resultado:
✅ Lead creado (ID: 15)
   Nombre: Acme Corp - $50,000
   Etapa: New
   Probabilidad: 10%
   Próximo paso: Contactar a John Smith

Chat: "Calificar lead 15 como oportunidad"
✅ Lead calificado → Oportunidad (ID: 42)
```

### Ejemplo 2: Ver Pipeline de Ventas
```
Chat: "Mostrar pipeline del mes"

Skill: openclaw-crm-opportunities
Action: VIEW_PIPELINE
Resultado:
✅ Pipeline de Ventas - Abril 2026:

New (Nuevos)
  • Prospecto A: $25,000 × 10% = $2,500
  • Prospecto B: $15,000 × 10% = $1,500
  Subtotal: $4,000

Contacted (Contactados)
  • Cliente X: $50,000 × 25% = $12,500
  • Cliente Y: $40,000 × 25% = $10,000
  Subtotal: $22,500

Qualified (Calificados)
  • Empresa Z: $100,000 × 50% = $50,000
  Subtotal: $50,000

Negotiation (Negociación)
  • Gran Cliente: $150,000 × 75% = $112,500
  Subtotal: $112,500

TOTAL FORECAST: $189,500
```

### Ejemplo 3: Mover por Pipeline
```
Chat: "Acme Corp pasó a fase Qualified"

Skill: openclaw-crm-opportunities
Action: MOVE_OPPORTUNITY
Params: {
  "opportunity_id": 42,
  "new_stage": "Qualified"
}

Resultado:
✅ Oportunidad movida:
   Acme Corp: New → Qualified
   Probabilidad: 10% → 50%
   Ingresos esperados: $5,000 → $25,000
```

---

## Notificaciones Automáticas

El skill puede enviar automáticamente:
- 🔔 Lead asignado a vendedor
- 🔔 Actividad vencida
- 🔔 Próxima acción debida
- 🔔 Oportunidad ganada/perdida

---

## Reportes Disponibles

### Sales Pipeline Report
```
Período: Abril 2026
Vendedor: Todos
Forecast Total: $189,500
Win Rate: 65%
Sales Cycle Promedio: 45 días
```

### Lead Conversion Report
```
Nuevos Leads: 25
Leads Calificados: 12 (48%)
Oportunidades Ganadas: 8 (32%)
Pipeline Cerrado: $250,000
```

---

## Validaciones

- ✅ Contacto debe existir (si opportunity con partner)
- ✅ Monto debe ser positivo
- ✅ Probabilidad: 0-100%
- ✅ Etapa debe ser válida
- ✅ Vendedor debe estar activo

---

## Auditoría OpenClaw

```python
{
    "action": "create_lead|move_stage|qualify|win",
    "user": "sales_manager",
    "timestamp": "2026-04-17T15:30:00Z",
    "opportunity_id": 42,
    "details": {
        "old_stage": "New",
        "new_stage": "Qualified",
        "revenue_impact": 20000  # Cambio en forecast
    },
    "request_id": "req_opp123"
}
```

---

## Permisos por Rol

- 👑 **Sales Manager**: Ver todo, crear, mover, marcar ganado/perdido
- 👤 **Sales User**: Ver propios, crear, mover
- 🔍 **Manager**: Ver todo (lectura)
- 📊 **Analista**: Ver reportes

---

## Integración con Otros Skills

```
openclaw-crm-opportunities
    ↓
    ├── ← openclaw-crm-contacts (crear lead para contacto)
    ├── → openclaw-sales (crear pedido cuando se gana)
    ├── → openclaw-invoicing (crear factura)
    └── → openclaw-reporting (métricas y análisis)
```

---

## Limitaciones Conocidas

| Limitación | Descripción | Workaround |
|-----------|-----------|-----------|
| Multi-etapa | No soporta etapas custom | Usar etapas estándar |
| Probabilidad | No se actualiza automáticamente | Actualizar manual |
| Pronóstico | No incluye pipeline histórico | Ver reportes |
| Notificaciones | Básicas (email, en-app) | Integraciones SMS/Slack |

---

## Roadmap

- 🔜 Etapas customizables
- 🔜 Probabilidades automáticas basadas en IA
- 🔜 Análisis predictivo de ganancia
- 🔜 Integración con calendario/actividades
- 🔜 Alertas de riesgo
- 🔜 Scorecard de vendedor
- 🔜 Integración Salesforce/LinkedIn

---

**Skill**: OpenClaw CRM Opportunities  
**Versión**: 1.0  
**Especialidad**: Sales Pipeline & Lead Management  
**Dependencias**: openclaw-crm-contacts, crm.lead, crm.opportunity  
**Status**: ✅ PRODUCTION READY
