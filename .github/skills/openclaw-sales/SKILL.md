---
name: openclaw-sales
description: "Skill especializado para gestionar pedidos de venta, cotizaciones y órdenes de compra. Crea, confirma y rastrea todo el ciclo de sales."
repository: https://github.com/openclaw/odoo19-sales
---

# OpenClaw Sales Skill

Skill para gestión completa de **pedidos de venta, cotizaciones y órdenes**.

## Cuándo Usar Este Skill

✅ Crear cotizaciones (Quotation)  
✅ Crear pedidos de venta (Sale Order)  
✅ Confirmar/validar pedidos  
✅ Facturar pedidos  
✅ Rastrear entregas  
✅ Manejar devoluciones  
✅ Generar reportes de ventas  

## No Usar Para

❌ Gestionar contactos (usar: openclaw-crm-contacts)  
❌ Crear oportunidades (usar: openclaw-crm-opportunities)  
❌ Gestionar inventario (usar: openclaw-inventory)  
❌ Crear facturas directas (usar: openclaw-invoicing)  

---

## Operaciones Disponibles

### 📄 CREATE_QUOTATION
**Crear una cotización**

```
Comando: "Crear cotización para [cliente]: [producto] x [cantidad] @ [precio]"

Entrada:
  - partner_id: int
  - lines: List[{
      product_id: int,
      quantity: float,
      price_unit: float
    }]
  - validity_date: date (opcional, default: +30 días)
  - notes: str (opcional)

Salida:
  - quotation_id: int
  - reference: str (Quotation/2026/001)
  - total: float
  - status: "Draft"
```

### 📦 CREATE_SALE_ORDER
**Crear pedido de venta directamente**

```
Comando: "Crear pedido para [cliente]: [productos]"

Entrada:
  - partner_id: int
  - quotation_id: int (opcional, para convertir)
  - lines: List[OrderLine]
  - delivery_address: int (opcional)
  - payment_terms: str (30 days, COD, etc.)

Salida:
  - order_id: int
  - reference: str (SO/2026/0001)
```

### ✅ CONFIRM_ORDER
**Confirmar pedido de venta**

```
Comando: "Confirmar pedido [REFERENCE]"

Entrada:
  - order_id: int

Salida:
  - status: "Confirmed"
  - message: "Pedido confirmado y disponible para facturar"
```

### 📚 LIST_ORDERS
**Listar pedidos de venta**

```
Comando: "Mostrar pedidos del cliente [cliente]"

Entrada:
  - partner_id: int (opcional, todos si no se especifica)
  - state: str (Draft, Confirmed, Done, Cancelled)
  - date_from: date (opcional)

Salida:
  - total_count: int
  - orders: List[SaleOrder]
```

### 📊 VIEW_ORDER_DETAILS
**Ver detalles completos de un pedido**

```
Comando: "Mostrar detalles pedido SO/2026/0001"

Entrada:
  - order_id: int ou reference: str

Salida:
  - reference: str
  - customer: str
  - total: float
  - lines: List[Line]
  - status: str
  - delivery_date: date
```

---

## Estados de un Pedido

```
Draft (Borrador) - Puede editarse
   ↓
Quotation Sent - Citación enviada (se puede confirmar)
   ↓
Sale Order - Pedido confirmado
   ↓
Delivery - En tránsito/preparando entrega
   ↓
Done - Completado
   ├─→ Cancelled (Cancelado) ❌
```

---

## Líneas de Pedido

Cada línea incluye:
- 📦 Producto (ID, nombre, código)
- 🔢 Cantidad
- 💰 Precio unitario
- 📊 Subtotal (cantidad × precio)
- ✏️ Descripción (opcional)
- 📅 Fecha de entrega

---

## Flujo de Ventas Completo

```
1. Crear Oportunidad (openclaw-crm-opportunities)
   ↓
2. Crear Cotización (CREATE_QUOTATION aquí)
   ↓
3. Gana Oportunidad
   ↓
4. Convertir Cotización → Pedido (CREATE_SALE_ORDER)
   ↓
5. Confirmar Pedido (CONFIRM_ORDER)
   ↓
6. Preparar Envío (openclaw-inventory)
   ↓
7. Facturar (openclaw-invoicing)
   ↓
8. Enviar Factura a Cliente
```

---

## Ejemplos de Uso

### Ejemplo 1: Crear Cotización
```
Chat: "Crear cotización para Acme Corp:
       - 10x Widget A @ $50 cada una
       - 5x Widget B @ $75 cada una
       Válida por 30 días"

Skill: openclaw-sales
Action: CREATE_QUOTATION
Resultado:
✅ Cotización creada (Quotation/2026/0001)
   Cliente: Acme Corp
   Línea 1: 10x Widget A = $500
   Línea 2: 5x Widget B = $375
   Total: $875
   Válida hasta: 2026-05-17
```

### Ejemplo 2: Convertir a Pedido
```
Chat: "El cliente Acme aceptó la cotización.
       Convertir Quotation/2026/0001 a pedido de venta"

Skill: openclaw-sales
Action: CREATE_SALE_ORDER
Resultado:
✅ Pedido creado (SO/2026/0001)
   Total: $875
   Estado: Sale Order (listo para facturar)
```

### Ejemplo 3: Confirmar Pedido
```
Chat: "Confirmar pedido SO/2026/0001"

Skill: openclaw-sales
Action: CONFIRM_ORDER
Resultado:
✅ Pedido confirmado
   Referencias: SO/2026/0001
   Estado: Confirmed
   Próximo paso: Preparar entrega o crear factura
```

---

## Descuentos y Promociones

### Aplicar Descuel

```
Línea:
  - Producto: Widget A
  - Cantidad: 10
  - Precio unitario: $50
  - Descuento: 10%
  - Precio final: $45
  - Subtotal: $450 (en lugar de $500)
```

### Descuentos Disponibles
- % Descuento por línea
- % Descuento total
- Monto fijo
- Código promocional

---

## Impuestos y Envío

### Cálculo Automático
```
Subtotal:          $875
Descuel:           -$87.50
Impuesto (21%):    $165.45
Envío:             +$20
─────────────────────────
Total Final:       $973
```

---

## Términos de Pago

Soportados:
- 💳 Pago a la entrega (COD)
- 📅 Neto 30 días
- 📅 Neto 60 días
- 💰 Prepago
- 🏦 Transferencia bancaria

---

## Auditoría OpenClaw

```python
{
    "action": "create_quotation|confirm|cancel",
    "user": "sales_user",
    "timestamp": "2026-04-17T15:30:00Z",
    "order_id": 1,
    "order_reference": "SO/2026/0001",
    "total": 875.00,
    "request_id": "req_so123"
}
```

---

## Validaciones

- ✅ Cliente (partner) debe existir
- ✅ Producto debe existir
- ✅ Cantidad > 0
- ✅ Precio > 0
- ✅ Fecha validez > hoy

---

## Reportes

### Sales Report
```
Período: Enero - Diciembre 2026
Total Ventas: $50,000
Pedidos: 25
Ticket Promedio: $2,000
Top Cliente: Acme Corp ($15,000)
```

### Fulfillment Report
```
Pedidos Confirmados: 25
Entregados: 23
En Tránsito: 1
Retrasados: 1
On-Time Delivery: 92%
```

---

## Integraciones

```
openclaw-sales
    ↓
    ├── ← openclaw-crm-opportunities (pedidos desde oportunidades)
    ├── ← openclaw-crm-contacts (cliente del pedido)
    ├── ← openclaw-inventory (disponibilidad de productos)
    ├── → openclaw-invoicing (crear factura desde pedido)
    └── → openclaw-shipping (integraciones de envío)
```

---

## Limitaciones

| Limitación | Workaround |
|-----------|-----------|
| Sin firmas digitales | Adicionar integración e-firma |
| Entregas parciales limitadas | Crear pedidos separados |
| Sin multi-moneda nativa | Usar conversión manual |

---

## Próximas Mejoras

- 🔜 Presupuestos (budgeting)
- 🔜 Reservas de inventario
- 🔜 Firmas digitales
- 🔜 Multi-moneda
- 🔜 Pagos en línea

---

**Skill**: OpenClaw Sales  
**Versión**: 1.0  
**Especialidad**: Sale Orders & Quotations  
**Dependencias**: openclaw-crm-contacts, sale.order, product  
**Status**: ✅ PRODUCTION READY
