---
name: openclaw-crm-contacts
description: "Skill especializado para gestionar contactos (partners) en Odoo. Crea, lee, actualiza y elimina contactos con auditoría OpenClaw y restricciones de seguridad."
repository: https://github.com/openclaw/odoo19-crm-contacts
---

# OpenClaw CRM Contacts Skill

Skill especializado para gestión completa de **contactos (res.partner)** en Odoo con control de OpenClaw.

## Cuándo Usar Este Skill

✅ Crear nuevos contactos (personas o empresas)  
✅ Editar información de contactos existentes  
✅ Buscar y filtrar contactos  
✅ Ver detalles completos de un contacto  
✅ Eliminar contactos (con protecciones)  
✅ Registrar auditoría de cambios  

## No Usar Para

❌ Gestionar oportunidades (usar: openclaw-crm-opportunities)  
❌ Crear facturas (usar: openclaw-invoicing)  
❌ Gestionar inventario (usar: openclaw-inventory)  
❌ Crear pedidos de venta (usar: openclaw-sales)  

---

## Operaciones Disponibles

### ✨ CREATE_CONTACT
**Crear un nuevo contacto**

```
Comando: "Crear contacto: [nombre], email: [email], teléfono: [teléfono]"

Entrada:
  - name: str (requerido)
  - email: str (opcional)
  - phone: str (opcional)
  - country: str (opcional)
  - is_company: bool (opcional)

Salida:
  - id: int (ID del contacto creado)
  - name: str
  - status: "success" | "error"
```

### 🔍 SEARCH_CONTACTS
**Buscar contactos por criterios**

```
Comando: "Buscar contactos [criterio]"

Entrada:
  - query: str (nombre, email, teléfono)
  - limit: int (default: 20)
  - filters: dict (country, is_company, etc.)

Salida:
  - total: int (número de resultados)
  - contacts: List[Contact]
  - status: "success" | "error"
```

### 👁️ GET_CONTACT
**Obtener detalles completos de un contacto**

```
Comando: "Mostrar detalles contacto [ID]"

Entrada:
  - contact_id: int

Salida:
  - id: int
  - name: str
  - email: str
  - phone: str
  - country: str
  - city: str
  - is_company: bool
  - created_at: datetime
  - openclaw_created_by: str (auditoría)
```

### ✏️ UPDATE_CONTACT
**Actualizar información de un contacto**

```
Comando: "Actualizar contacto [ID]: [campo]: [valor]"

Entrada:
  - contact_id: int
  - name: str (opcional)
  - email: str (opcional)
  - phone: str (opcional)
  - country: str (opcional)
  - city: str (opcional)

Salida:
  - id: int
  - status: "success" | "error"
  - changes: dict (qué cambió)
```

### 🗑️ DELETE_CONTACT
**Eliminar un contacto**

```
Comando: "Eliminar contacto [ID]"

Entrada:
  - contact_id: int
  - reason: str (opcional)

Salida:
  - status: "success" | "protected" | "error"
  - message: str
```

---

## Validaciones y Protecciones

### Validaciones de Entrada
- ✅ Nombre requerido
- ✅ Email debe ser válido (si se proporciona)
- ✅ Teléfono puede tener varios formatos
- ✅ País validado contra res.country

### Protecciones de Seguridad
- ✅ **No permite eliminar contactos con facturas** (account.invoice)
- ✅ **No permite eliminar contactos con pedidos** (sale.order)
- ✅ **No permite eliminar contactos con compras** (purchase.order)
- ✅ **Suggiere archivar en lugar de eliminar**
- ✅ **Auditoría completa de cada cambio**

### Restricciones por Rol
- 👑 **Admin**: Crear, leer, actualizar, eliminar
- 👤 **Sales Manager**: Crear, leer, actualizar (no eliminar)
- 👨‍💼 **Sales User**: Leer, actualizar propios contactos
- 🚫 **Otros**: Acceso limitado según permisos OpenClaw

---

## Campos Soportados

| Campo | Tipo | Requerido | Validación | Ejemplo |
|-------|------|----------|-----------|---------|
| name | str | ✅ | 1-255 chars | "Juan García" |
| email | email | ❌ | RFC 5322 | "juan@example.com" |
| phone | str | ❌ | Any format | "+34 123 456 789" |
| country_id | str/id | ❌ | res.country | "ES" o "España" |
| city | str | ❌ | 0-255 chars | "Madrid" |
| is_company | bool | ❌ | true/false | true |
| street | str | ❌ | Address | "Calle Principal 123" |
| zip | str | ❌ | Postal code | "28001" |

---

## Auditoría OpenClaw

Cada operación registra:

```python
{
    "action": "create|update|delete",
    "user": "admin",
    "timestamp": "2026-04-17T15:30:00Z",
    "contact_id": 42,
    "request_id": "req_xyz123",
    "old_values": {...},
    "new_values": {...},
    "status": "success|error"
}
```

---

## Integración con OpenClaw Request System

```
Usuario escribe comando
    ↓
Skill identifica operación (CREATE/READ/UPDATE/DELETE)
    ↓
¿Requiere aprobación? (según política)
    ↓
Si SÍ: Crea OpenClaw Request (pendiente aprobación)
Si NO: Ejecuta directamente
    ↓
Operación se ejecuta en Odoo (XML-RPC)
    ↓
Resultado devuelto al usuario
```

---

## Ejemplos de Uso

### Ejemplo 1: Crear Contacto
```
Chat: "Crear contacto: Carlos López, email: carlos@example.com, teléfono: +34 987 654 321"

Skill: openclaw-crm-contacts
Action: CREATE_CONTACT
Params: {
  "name": "Carlos López",
  "email": "carlos@example.com",
  "phone": "+34 987 654 321"
}

Resultado:
✅ Contacto 'Carlos López' creado (ID: 48)
   Email: carlos@example.com
   Teléfono: +34 987 654 321
   Creado por: admin en 2026-04-17 15:30:00
```

### Ejemplo 2: Buscar Contactos
```
Chat: "Buscar contactos 'García'"

Skill: openclaw-crm-contacts
Action: SEARCH_CONTACTS
Params: {
  "query": "García",
  "limit": 20
}

Resultado:
✅ Se encontraron 3 contactos:
   1. Juan García (ID: 42)
   2. García & Asociados (ID: 43)
   3. María García López (ID: 44)
```

### Ejemplo 3: Actualizar Contacto
```
Chat: "Actualizar contacto 42: teléfono +34 111 222 333"

Skill: openclaw-crm-contacts
Action: UPDATE_CONTACT
Params: {
  "contact_id": 42,
  "phone": "+34 111 222 333"
}

Resultado:
✅ Contacto actualizado
   Campo: phone
   Antiguo: +34 123 456 789
   Nuevo: +34 111 222 333
```

---

## Manejo de Errores

### Error: Contacto No Encontrado
```
Status: error
Message: "Contacto con ID 999 no encontrado"
Action: Buscar contacto primero
```

### Error: Email Inválido
```
Status: error
Message: "Email inválido: 'notanemail'"
Sugerencia: "Formato: usuario@dominio.com"
```

### Error: No Se Puede Eliminar
```
Status: protected
Message: "No se puede eliminar contacto con 3 facturas"
Sugerencia: "Considere archivar el contacto en su lugar"
Action: Archivar contacto [ID]
```

---

## Integración con Otros Skills

```
openclaw-crm-contacts (ESTE SKILL)
    ↓
    ├── → openclaw-crm-opportunities (crear oportunidad para contacto)
    ├── → openclaw-sales (crear pedido para contacto)
    └── → openclaw-invoicing (crear factura para contacto)
```

**Flujo**: Crear contacto → Crear oportunidad → Crear pedido → Crear factura

---

## Configuración

### Habilitar en OpenClaw

**Archivo**: `.github/copilot-instructions.md`

```yaml
skills:
  - name: "openclaw-crm-contacts"
    enabled: true
    require_approval:
      - delete_contact  # Requiere aprobación
    timeout: 30
```

### Variables de Entorno

```bash
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=admin
ODOO_PASSWORD=admin
OPENCLAW_VAULT_URL=http://vault:8200
```

---

## APIs Disponibles

### XML-RPC (Directo a Odoo)
```python
import xmlrpc.client

models = xmlrpc.client.ServerProxy('http://odoo:8069/xmlrpc/2/object')

# Crear
partner_id = models.execute_kw(
    'odoo', uid, password,
    'res.partner', 'create', [{'name': 'Juan', 'email': 'juan@ex.com'}]
)

# Buscar
ids = models.execute_kw(
    'odoo', uid, password,
    'res.partner', 'search', [[('name', 'ilike', 'García')]]
)

# Actualizar
models.execute_kw(
    'odoo', uid, password,
    'res.partner', 'write', [[42], {'phone': '+34 123'}]
)

# Eliminar
models.execute_kw(
    'odoo', uid, password,
    'res.partner', 'unlink', [[42]]
)
```

### OpenClaw MCP Tool
```python
from openclaw.tools.contacts_chat import ContactsToolExecutor

executor = ContactsToolExecutor(url, db, user, password)
result = executor.execute_tool("create_contact", {
    "name": "Juan García",
    "email": "juan@example.com"
})
```

---

## Limitaciones Conocidas

| Limitación | Descrición | Workaround |
|-----------|----------|-----------|
| Duplicados | No detecta automaticamente duplicados | Buscar primero |
| Importación | No importa múltiples contactos | Script de importación |
| Deduplicación | No fusiona contactos | Hacerlo manual |
| Sincronización | No sincroniza desde otras fuentes | Integraciones externas |

---

## Roadmap Futuro

- 🔜 Detectar duplicados automáticamente
- 🔜 Fusionar contactos duplicados
- 🔜 Importar desde CSV/Excel
- 🔜 Exportar a Excel/PDF
- 🔜 Validación de email en tiempo real
- 🔜 Sincronización con Google Contacts
- 🔜 Geocodificación de direcciones
- 🔜 Análisis de contactos (segmentación)

---

## Soporte y Ayuda

📖 Documentación: [CONTACTS_MANAGEMENT_GUIDE.md](../../CONTACTS_MANAGEMENT_GUIDE.md)  
📖 Quick Reference: [CONTACTS_QUICK_REFERENCE.md](../../CONTACTS_QUICK_REFERENCE.md)  
👨‍💻 Técnico: [CONTACTS_TECHNICAL_IMPL.md](../../CONTACTS_TECHNICAL_IMPL.md)  

---

## Métricas y Monitoreo

```bash
# Ver logs de skill
docker logs odoo19_openclaw_1 | grep "openclaw-crm-contacts"

# Monitorear auditoría
SELECT * FROM res_partner_audit WHERE action='create'
  AND timestamp > NOW() - INTERVAL '1 day'
```

---

**Skill**: OpenClaw CRM Contacts  
**Versión**: 1.0  
**Especialidad**: Gestión de Contactos  
**Dependencias**: openclaw-odoo, res.partner model  
**Status**: ✅ PRODUCTION READY
