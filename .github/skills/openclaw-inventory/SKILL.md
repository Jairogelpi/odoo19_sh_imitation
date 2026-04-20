---
name: openclaw-inventory
description: "Skill especializado para gestionar inventario, productos, stock y almacenes. Controla niveles de inventario, movimientos y disponibilidad."
repository: https://github.com/openclaw/odoo19-inventory
---

# OpenClaw Inventory Skill

Skill para gestión completa de **inventario, productos, stock y almacenes** en Odoo.

## Cuándo Usar Este Skill

✅ Crear y gestionar productos  
✅ Ver niveles de stock  
✅ Realizar movimientos de inventario  
✅ Gestionar almacenes y ubicaciones  
✅ Recibir compras en almacén  
✅ Preparar envíos  
✅ Registrar devoluciones  
✅ Ajustar cantidades de stock  
✅ Crear órdenes de transferencia  

## No Usar Para

❌ Crear pedidos de venta (usar: openclaw-sales)  
❌ Gestionar contactos (usar: openclaw-crm-contacts)  
❌ Crear facturas (usar: openclaw-invoicing)  
❌ Gestionar compras (usar: openclaw-procurement)  

---

## Operaciones Disponibles

### 📦 CREATE_PRODUCT
**Crear un nuevo producto**

```
Comando: "Crear producto: [nombre], precio: [precio], tipo: [tipo]"

Entrada:
  - name: str (requerido)
  - product_type: str (consumable, stockable, service)
  - price: float (precio de venta)
  - cost: float (costo de compra)
  - category: str (Electrónica, Ropa, etc.)
  - barcode: str (opcional)
  - description: str (opcional)

Salida:
  - product_id: int
  - name: str
  - reference: str (PROD/0001)
  - initial_stock: int
```

### 🔍 CHECK_STOCK
**Ver niveles de stock**

```
Comando: "¿Cuál es el stock de [producto]?"

Entrada:
  - product_id: int ou name: str
  - warehouse_id: int (opcional, todos si no se especifica)

Salida:
  - product_name: str
  - total_qty: float (total disponible)
  - reserved_qty: float (reservado para pedidos)
  - available_qty: float (realmente disponible)
  - in_transit: float (en camino)
  - locations: {
      "Warehouse A / Shelf 1": 100,
      "Warehouse B / Shelf 3": 50
    }
```

### 📥 RECEIVE_GOODS
**Recibir mercancía en almacén**

```
Comando: "Recibir compra PO/2026/0001"

Entrada:
  - purchase_order_id: int
  - lines: List[{
      product_id: int,
      received_qty: float,
      location: str
    }]
  - reference: str (referencia del proveedor)

Salida:
  - receipt_id: int
  - status: "Done"
  - stock_updated: bool
```

### 📤 PREPARE_SHIPMENT
**Preparar envío desde pedido**

```
Comando: "Preparar envío para pedido SO/2026/0001"

Entrada:
  - sale_order_id: int
  - warehouse_id: int

Salida:
  - delivery_id: int
  - reference: str (Delivery/2026/001)
  - items: List[Item]
  - status: "Ready to Ship"
```

### 🔄 TRANSFER_INVENTORY
**Transferir producto entre almacenes**

```
Comando: "Transferir 50x [producto] de Almacén A a Almacén B"

Entrada:
  - product_id: int
  - quantity: float
  - from_location: str
  - to_location: str
  - reason: str (rebalancing, damaged, etc.)

Salida:
  - transfer_id: int
  - status: "Confirmed"
```

### 📊 INVENTORY_ADJUSTMENT
**Ajustar cantidades de stock**

```
Comando: "Ajustar stock de [producto]: [cantidad]"

Entrada:
  - product_id: int
  - new_quantity: float
  - reason: str (inventory count, damage, loss, etc.)
  - location: str (opcional)

Salida:
  - adjustment_id: int
  - old_qty: float
  - new_qty: float
  - difference: float
```

### 📋 LIST_LOW_STOCK
**Ver productos con stock bajo**

```
Comando: "Mostrar productos con stock bajo"

Entrada:
  - threshold: int (default: reorder point)
  - category: str (opcional)

Salida:
  - count: int
  - products: List[{
      name: str,
      current_qty: float,
      reorder_point: float,
      status: "Critical" | "Low"
    }]
```

### 📈 SET_REORDER_POINT
**Establecer punto de reorden**

```
Comando: "Establecer stock mínimo de [producto]: [cantidad]"

Entrada:
  - product_id: int
  - reorder_qty: int
  - reorder_point: int

Salida:
  - product_id: int
  - reorder_point: int
  - message: "Reorden automático si stock < [cantidad]"
```

---

## Tipos de Productos

### Consumible
```
- Se usa pero no rastrea cantidad
- Ejemplos: Bolígrafos, papel, café
- No requiere stock en almacén
```

### Stockable (Almacenable)
```
- Se rastrea cantidad en tiempo real
- Genera movimientos de inventario
- Ejemplos: Widgets, dispositivos, componentes
- Requiere gestión de almacén
```

### Servicio
```
- No tiene stock
- Se vende pero no se almacena
- Ejemplos: Consultoría, mantenimiento, diseño
```

---

## Ubicaciones y Almacenes

### Estructura
```
Company (Empresa)
    └─ Warehouse A (Almacén)
        ├─ Stock (Ubicación)
        │   ├─ Shelf 1
        │   ├─ Shelf 2
        │   └─ Shelf 3
        ├─ Damaged
        └─ Quality Control
    └─ Warehouse B (Almacén)
        ├─ Stock
        └─ Returns
```

### Operaciones por Ubicación
```
Stock → Quality Control → Stock (si pasa control)
Stock → Quality Control → Damaged (si falla)
      → Damaged → Returns (devolución)
```

---

## Ciclo de Inventario Típico

```
1. Recibir compra de proveedor
   CREATE_PURCHASE → RECEIVE_GOODS
   ↓
2. Inspeccionar mercancía
   Stock → Quality Control (TRANSFER_INVENTORY)
   ↓
3. Aceptar o rechazar
   ✅ QC → Stock
   ❌ QC → Damaged → Returns
   ↓
4. Preparar envío a cliente
   Stock → [Warehouse Out] (PREPARE_SHIPMENT)
   ↓
5. Enviar al cliente
   [Warehouse Out] → Customer
   ↓
6. Si devolución:
   Customer → Returns → [Reinspeccionar]
```

---

## Ejemplos de Uso

### Ejemplo 1: Crear Producto
```
Chat: "Crear producto: Widget A Pro, precio: $99.99, costo: $35, tipo: stockable"

Skill: openclaw-inventory
Action: CREATE_PRODUCT
Resultado:
✅ Producto creado (PROD/0001)
   Nombre: Widget A Pro
   Precio: $99.99
   Costo: $35
   Margen: 65%
   Tipo: Stockable
```

### Ejemplo 2: Ver Stock
```
Chat: "¿Cuántos Widget A tenemos en stock?"

Skill: openclaw-inventory
Action: CHECK_STOCK
Resultado:
✅ Stock de Widget A Pro:
   Total: 250 unidades
   Reservado: 30 (para pedidos pendientes)
   Disponible: 220
   
   Por Almacén:
   • Warehouse A: 150 unidades
   • Warehouse B: 100 unidades
```

### Ejemplo 3: Ajustar Stock
```
Chat: "Contamos 245 Widget A en inventario (50 menos).
       Ajustar stock - razón: pérdida en tránsito"

Skill: openclaw-inventory
Action: INVENTORY_ADJUSTMENT
Resultado:
✅ Stock ajustado:
   Producto: Widget A Pro
   Stock anterior: 250
   Stock actual: 245
   Diferencia: -5 unidades
   Razón: pérdida en tránsito
```

### Ejemplo 4: Preparar Envío
```
Chat: "Preparar envío para pedido SO/2026/0001"

Skill: openclaw-inventory
Action: PREPARE_SHIPMENT
Resultado:
✅ Envío preparado (Delivery/2026/0001)
   
   Artículos:
   • 10x Widget A Pro (ubicación: Warehouse A / Shelf 1)
   • 5x Widget B Standard (ubicación: Warehouse A / Shelf 2)
   
   Stock actualizado automáticamente:
   • Widget A: 250 → 240
   • Widget B: 150 → 145
```

---

## Auditoría OpenClaw

```python
{
    "action": "create_product|receive|transfer|adjust",
    "user": "warehouse_manager",
    "timestamp": "2026-04-17T15:30:00Z",
    "product_id": 1,
    "quantity_change": 50,  # movimiento neto
    "location_from": "Warehouse A",
    "location_to": "Warehouse B",
    "reason": "rebalancing",
    "request_id": "req_inv123"
}
```

---

## Validaciones

- ✅ Nombre de producto requerido
- ✅ Cantidad ≥ 0
- ✅ Precio > 0
- ✅ Ubicaciones válidas
- ✅ No sobrevender (cantidad > disponible)

---

## Restricciones de Seguridad

- 👑 **Admin**: Control total
- 👤 **Warehouse Manager**: Recibir, transferir, ajustar, ver todo
- 👨‍💼 **Sales User**: Ver disponibilidad (no crear/modificar)
- 📊 **Contador**: Ver solo para auditoría

---

## Reportes

### Stock Report
```
Producto | Qty Stock | Qty Reserved | Qty Disponible | Reorder Pnt | Status
Widget A | 250       | 30           | 220            | 50          | ✅ OK
Widget B | 15        | 5            | 10             | 30          | ⚠️  LOW
Widget C | 2         | 1            | 1              | 20          | 🔴 CRITICAL
```

### Inventory Movement Report
```
Período: Abril 2026
Total Entradas: 500 unidades
Total Salidas: 350 unidades
Neto: +150 unidades
Transferencias: 75 unidades
Ajustes: 12 unidades
```

---

## Integración con Otros Skills

```
openclaw-inventory
    ↓
    ├── ← openclaw-sales (reservas de stock para pedidos)
    ├── ← openclaw-procurement (recibir compras)
    ├── ← openclaw-suppliers (compras a proveedores)
    └── → openclaw-accounting (valuación de inventario)
```

---

## Automatizaciones

### Alertas Automáticas
- 🔔 Stock bajo (< reorder point)
- 🔔 Stock vencido
- 🔔 Discrepancias de inventario
- 🔔 Compras que esperan recepción

### Órdenes de Compra Automáticas
```
Si stock < reorder point:
  1. Crear PO automáticamente
  2. Enviar a proveedor preferido
  3. Notificar a gerente de compras
```

---

## Limitaciones y Consideraciones

| Limitación | Impacto | Workaround |
|-----------|--------|-----------|
| Sin lotes | No rastrea lotes específicos | Crear ubicaciones por lote |
| Sin series | No rastrea números de serie | Usar ubicación/código |
| Sin fechas vencimiento | No alerta stock vencido | Integración calendario |
| Multi-almacén básico | Interface complicada | Filtros y reportes |

---

## Roadmap Futuro

- 🔜 Lotes y series
- 🔜 Fechas de vencimiento
- 🔜 Códigos de barras avanzados
- 🔜 Radiofrecuencia (RFID)
- 🔜 Predicción de demanda (ML)
- 🔜 Optimización de almacén
- 🔜 Integración con WMS externo

---

**Skill**: OpenClaw Inventory  
**Versión**: 1.0  
**Especialidad**: Stock & Warehouse Management  
**Dependencias**: openclaw-sales, stock.move, product  
**Status**: ✅ PRODUCTION READY
