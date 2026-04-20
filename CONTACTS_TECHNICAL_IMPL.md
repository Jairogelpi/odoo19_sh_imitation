# 👨‍💻 Integración Técnica - Gestión de Contactos en OpenClaw

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    Odoo Chat Interface                           │
│              (http://localhost:8069/odoo/action-303)             │
└────────────────────────────┬────────────────────────────────────┘
                             │

## 🧩 Modelo de Skills Modulares

OpenClaw no debe operar como un bot monolítico. La lógica se divide por dominio y cada dominio vive en su propio skill:

- `openclaw-crm-contacts` para contactos
- `openclaw-crm-opportunities` para CRM y pipeline
- `openclaw-sales` para cotizaciones y pedidos
- `openclaw-inventory` para stock y almacenes
- `openclaw-invoicing` para facturacion y cobranza
- `openclaw-purchase` para compras y proveedores
- `openclaw-hr` para empleados, ausencias y nomina
- `openclaw-reporting` para reportes, dashboards y KPIs
- `openclaw-odoo` para operaciones Odoo genéricas y requests administrativos

Un router de skills decide qué módulo ejecutar según la intención del usuario. Esto mantiene el sistema más seguro, mantenible y alineado con el flujo de OpenClaw.
                    Claude AI with Tools
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
  create_contact      update_contact      delete_contact
  search_contacts     get_contact
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
            OpenClaw Control Plane (HTTP)
            (control-plane:8082/mcp)
                             │
                             ▼
         Odoo XML-RPC Interface (:8069)
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
    res.partner model    Audit system        Permissions
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    PostgreSQL Database
                   (contacts stored safely)
```

---

## 📦 Archivos Implementados

### 1. Modelo Odoo (addon)
**Archivo**: `addons_custom/openclaw/models/contacts.py`

```python
class ResPartner(models.Model):
    """Extensión del modelo Partner con auditoría OpenClaw"""
    _inherit = "res.partner"
    
    # Campos de auditoría
    openclaw_created_by: Many2one  # Usuario creador
    openclaw_last_modified_by: Many2one  # Usuario modificador
    openclaw_request_id: Char  # ID del request OpenClaw

class OpenClawContactsManager(models.AbstractModel):
    """Gestor central de operaciones CRUD"""
    _name = "openclaw.contacts"
    
    + create_contact(name, email, phone, company_name, country)
    + update_contact(contact_id, name, email, phone, country)
    + delete_contact(contact_id)
    + get_contact(contact_id)
    + search_contacts(query, limit)
```

### 2. MCP Tool (Chat Interface)
**Archivo**: `addons_custom/openclaw/tools/contacts_chat.py`

```python
CONTACTS_TOOLS = [
    {
        "name": "create_contact",
        "input_schema": {...}
    },
    {
        "name": "update_contact",
        "input_schema": {...}
    },
    # ... más herramientas
]

class ContactsToolExecutor:
    """Ejecuta las operaciones contra Odoo XML-RPC"""
    + execute_tool(tool_name, tool_input)
    + create_contact(...)
    + update_contact(...)
    + delete_contact(...)
    + get_contact(...)
    + search_contacts(...)

def run_contacts_chat(user_message, odoo_url, odoo_db, odoo_user, odoo_password):
    """Procesa mensaje del usuario y ejecuta herramientas"""
```

### 3. Documentación para Usuario
- `CONTACTS_MANAGEMENT_GUIDE.md` - Guía completa con casos de uso
- `CONTACTS_QUICK_REFERENCE.md` - Cheat sheet con comandos

---

## 🔄 Flujo de Ejecución

### Paso 1: Usuario escribe mensaje
```
Usuario: "Crear contacto Juan García, email juan@ex.com"
```

### Paso 2: Claude procesa con herramientas
```python
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    tools=CONTACTS_TOOLS,  # ← Herramientas disponibles
    messages=[user_message]
)
# Claude iráidentificar que necesita usar "create_contact"
```

### Paso 3: Ejecutor llama a Odoo
```python
executor.execute_tool(
    "create_contact",
    {
        "name": "Juan García",
        "email": "juan@ex.com"
    }
)
```

### Paso 4: XML-RPC a Odoo
```
XML-RPC Call:
  Method: res.partner.create
  Params: [{
    "name": "Juan García",
    "email": "juan@ex.com",
    "openclaw_created_by": uid,
    "openclaw_request_id": request_id
  }]
```

### Paso 5: Odoo crea registro
```sql
INSERT INTO res_partner (
  name, email, openclaw_created_by, openclaw_request_id, create_date
) VALUES (
  'Juan García', 'juan@ex.com', 2, 'req_xyz123', NOW()
);
```

### Paso 6: Respuesta al usuario
```
Claude responde:
"✅ Contacto 'Juan García' creado exitosamente (ID: 42)"
```

---

## 🛠️ Instalación Técnica

### 1. Registro del Addon

**Archivo**: `addons_custom/openclaw/__manifest__.py`

```python
{
    'name': 'OpenClaw',
    'version': '19.0.1.0',
    'category': 'Tools',
    'depends': ['base', 'crm'],
    'data': [
        'data/groups.xml',
    ],
    'external_dependencies': {
        'python': ['anthropic'],
    },
    'installable': True,
}
```

### 2. Cargar el Addon en Odoo

```bash
# En Docker
docker compose exec odoo odoo --addons-path=/mnt/addons_custom -u openclaw

# O en terminal local
cd /path/to/odoo
./odoo-bin --addons-path=addons_custom -u openclaw
```

### 3. Configurar Variables de Entorno

```bash
# En .env o compose.yaml
ODOO_URL=http://odoo:8069
ODOO_DB=odoo
ODOO_USER=admin
ODOO_PASSWORD=${ADMIN_PASSWORD}
ANTHROPIC_API_KEY=sk-...
```

### 4. Registrar en OpenClaw

**Archivo**: `addons_custom/openclaw/config.yaml`

```yaml
chat_tools:
  - id: "contacts"
    name: "Gestión de Contactos"
    description: "Crear, editar, eliminar contactos"
    module: "models.contacts"
    tools:
      - create_contact
      - update_contact
      - delete_contact
      - get_contact
      - search_contacts
    enabled: true
    timeout: 30
```

---

## 🔗 Integración con OpenClaw Request System

### Request Workflow

```
1. Chat User escribe comando
   ↓
2. Claude identifica acción (tool use)
   ↓
3. Crea OpenClaw Request (si requiere aprobación)
   {
     "type": "odoo.contact.create",
     "action": "create_contact",
     "params": {...},
     "requester": "admin",
     "status": "pending"
   }
   ↓
4. Sistema verifica permisos
   - ¿Usuario tiene permiso?
   - ¿Requiere aprobación?
   ↓
5. Si requiere aprobación: espera confirmación
   Si no: ejecuta directamente
   ↓
6. Contacto se crea en Odoo
   with audit trail
   ↓
7. Respuesta al usuario con confirmación
```

---

## 📊 Esquema de Base de Datos

### Tabla: res_partner (extendida)
```sql
CREATE TABLE res_partner (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    is_company BOOLEAN DEFAULT FALSE,
    country_id INTEGER REFERENCES res_country(id),
    city VARCHAR(255),
    
    -- Campos de auditoría OpenClaw
    openclaw_created_by INTEGER REFERENCES res_users(id),
    openclaw_last_modified_by INTEGER REFERENCES res_users(id),
    openclaw_request_id VARCHAR(255),
    
    -- Timestamp estándar Odoo
    create_date TIMESTAMP DEFAULT NOW(),
    write_date TIMESTAMP DEFAULT NOW(),
    create_uid INTEGER REFERENCES res_users(id),
    write_uid INTEGER REFERENCES res_users(id)
);

CREATE INDEX idx_partner_email ON res_partner(email);
CREATE INDEX idx_partner_name ON res_partner(name);
CREATE INDEX idx_openclaw_request_id ON res_partner(openclaw_request_id);
```

### Tabla: res_partner_audit (nueva - opcional)
```sql
CREATE TABLE res_partner_audit (
    id SERIAL PRIMARY KEY,
    partner_id INTEGER REFERENCES res_partner(id),
    action VARCHAR(50),  -- create, write, unlink
    user_id INTEGER REFERENCES res_users(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    old_values JSONB,
    new_values JSONB,
    request_id VARCHAR(255),
    
    CREATE INDEX idx_audit_partner_id ON res_partner_audit(partner_id)
);
```

---

## 🔐 Permisos y ACL

### Definición en Odoo
**Archivo**: `addons_custom/openclaw/data/groups.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Grupos de acceso -->
    <record id="group_contact_admin" model="res.groups">
        <field name="name">Contact Management / Admin</field>
        <field name="comment">Has full access to all contact operations</field>
    </record>
    
    <record id="group_contact_manager" model="res.groups">
        <field name="name">Contact Management / Manager</field>
        <field name="comment">Can create, read, update contacts</field>
    </record>
    
    <record id="group_contact_user" model="res.groups">
        <field name="name">Contact Management / User</field>
        <field name="comment">Can read and update own contacts</field>
    </record>
    
    <!-- Reglas de acceso -->
    <record model="ir.rule" id="contact_admin_rule">
        <field name="name">Contact Admin Full Access</field>
        <field name="model_id" ref="model_res_partner"/>
        <field name="groups" eval="[(4, ref('group_contact_admin'))]"/>
        <field name="perm_read" eval="True"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_create" eval="True"/>
        <field name="perm_unlink" eval="True"/>
    </record>
</odoo>
```

---

## 🧪 Testing

### Unit Tests
**Archivo**: `addons_custom/openclaw/tests/test_contacts.py`

```python
from odoo.tests import TransactionCase

class TestContacts(TransactionCase):
    
    def test_create_contact(self):
        """Test crear contacto"""
        contact = self.env['openclaw.contacts'].create_contact(
            name="Test User",
            email="test@ex.com"
        )
        self.assertEqual(contact['status'], 'success')
        self.assertIsNotNone(contact['id'])
    
    def test_search_contacts(self):
        """Test buscar contactos"""
        result = self.env['openclaw.contacts'].search_contacts(
            query="Test"
        )
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['total'], 0)
    
    def test_update_contact(self):
        """Test actualizar contacto"""
        # ... crear contacto primero
        result = self.env['openclaw.contacts'].update_contact(
            contact_id=42,
            email="new@ex.com"
        )
        self.assertEqual(result['status'], 'success')
    
    def test_delete_protection(self):
        """Test protección contra eliminar con facturas"""
        # ... crear contacto con factura
        result = self.env['openclaw.contacts'].delete_contact(
            contact_id=42
        )
        self.assertEqual(result['status'], 'error')
        self.assertIn("facturas", result['message'])
```

### Integration Tests
```bash
# Ejecutar tests
python -m pytest addons_custom/openclaw/tests/test_contacts.py -v

# Con coverage
pytest --cov=addons_custom/openclaw addons_custom/openclaw/tests/
```

---

## 📈 Performance

### Optimizaciones Implementadas

1. **Índices en BD**
   ```sql
   CREATE INDEX idx_partner_email ON res_partner(email);
   CREATE INDEX idx_partner_name ON res_partner(name);
   ```

2. **Caching de búsquedas**
   - Claude cache los resultados de búsquedas recientes
   - Limit por defecto: 20 contactos (configurable)

3. **Paginación**
   ```python
   search_contacts(query, limit=20)  # Devuelve máx 20
   ```

4. **Lazy loading**
   - Solo cargar campos necesarios en búsquedas
   - Detalles completos solo cuando se soliciten

---

## 🚀 Deployment

### Docker Compose
```yaml
services:
  odoo:
    image: odoo:19
    environment:
      ODOO_ADDONS_PATH: /mnt/addons_custom
    volumes:
      - ./addons_custom:/mnt/addons_custom  # ← Contacts addon aquí
```

### Kubernetes (Si aplica)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: odoo-addons
data:
  contacts.py: |
    # ... contenido del addon
```

---

## 🔧 Debugging

### Ver logs
```bash
# Logs de Odoo
docker logs odoo19_odoo_1 | grep openclaw

# Logs de ContactsManager
docker logs odoo19_odoo_1 | grep "CREATE_CONTACT\|UPDATE_CONTACT"
```

### Comandos útiles
```python
# En consola de Odoo
partners = env['res.partner'].search([('openclaw_request_id', '!=', False)])
for p in partners:
    print(f"{p.name} - Created: {p.openclaw_created_by.name}")
```

---

## 📞 API XML-RPC

Si necesitas usar directamente (sin Chat):

```python
import xmlrpc.client

# Conectar
common = xmlrpc.client.ServerProxy('http://odoo:8069/xmlrpc/2/common')
uid = common.authenticate('odoo', 'admin', 'admin', {})
models = xmlrpc.client.ServerProxy('http://odoo:8069/xmlrpc/2/object')

# Crear contacto
partner_id = models.execute_kw(
    'odoo', uid, 'admin',
    'res.partner', 'create', [{
        'name': 'Juan García',
        'email': 'juan@ex.com'
    }]
)

# Buscar
partner_ids = models.execute_kw(
    'odoo', uid, 'admin',
    'res.partner', 'search',
    [[('name', 'ilike', 'García')]]
)

# Actualizar
models.execute_kw(
    'odoo',uid, 'admin',
    'res.partner', 'write',
    [[partner_id], {'phone': '+34 123 4567'}]
)

# Eliminar
models.execute_kw(
    'odoo', uid, 'admin',
    'res.partner', 'unlink',
    [[partner_id]]
)
```

---

## 📚 Referencias

- **Odoo API**: https://www.odoo.com/documentation/19.0/developer/misc/api/odoo.html
- **Anthropic Tools**: https://docs.anthropic.com/claude/reference/messages
- **OpenClaw**: http://localhost:8069/odoo/view/openclaw.request

---

**Documento**: Integración Técnica - Contactos  
**Versión**: 1.0  
**Fecha**: 2026-04-17  
**Mantenido por**: DevOps / OpenClaw Team
