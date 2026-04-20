# 📇 Gestión de Contactos en OpenClaw - Guía Completa

## ✨ Descripción

Ahora puedes **crear, leer, actualizar y eliminar contactos** en Odoo completamente desde el **chat de OpenClaw** en lenguaje natural.

Los contactos se registran con auditoría automática:
- Quién los creó/modificó
- Cuándo se crearon/modificaron
- ID de solicitud OpenClaw para acceso

---

## 🎯 Operaciones Disponibles

### 1️⃣ CREAR CONTACTO

**Comando en Chat:**
```
Crear un contacto llamado Juan García con email juan@example.com y teléfono +34 123 456 789
```

**Variantes (todas funcionan):**
- "Crear contacto: María López, email: maria@example.com"
- "Nuevo contacto - Acme Corp, country: España"
- "Agregar a Carlos Rivera, empresa XYZ, teléfono: 987654321"

**Campos soportados:**
| Campo | Tipo | Requerido | Ejemplo |
|-------|------|----------|---------|
| nombre | texto | ✅ Sí | "Juan García" |
| email | email | ❌ No | "juan@example.com" |
| teléfono | texto | ❌ No | "+34 123 456 789" |
| empresa | texto | ❌ No | "Acme Corp" |
| país | texto | ❌ No | "España" o "ES" |

**Resultado:**
```
✅ Contacto 'Juan García' creado exitosamente (ID: 42)
```

**Base de datos:**
```
res_partner tabla:
  id: 42
  name: "Juan García"
  email: "juan@example.com"
  phone: "+34 123 456 789"
  is_company: False
  country_id: España
  openclaw_created_by: admin
  openclaw_request_id: "req_xyz123"
```

---

### 2️⃣ BUSCAR CONTACTOS

**Comando en Chat:**
```
Buscar contactos que contengan 'García'
```

**Variantes:**
- "Mostrar todos los contactos"
- "Buscar por email: maria@"
- "Encontrar teléfono de Juan"
- "Listar contactos de empresa" (para empresas)

**Resultado:**
```
✅ Se encontraron 3 contactos:

1. Juan García (ID: 42)
   Email: juan@example.com
   Teléfono: +34 123 456 789
   Tipo: Persona

2. García & Asociados (ID: 43)
   Email: info@garcia.com
   Teléfono: +34 987 654 321
   Tipo: Empresa

3. María García López (ID: 44)
   Email: maria.garcia@example.com
   Teléfono: +34 555 666 777
   Tipo: Persona
```

---

### 3️⃣ VER DETALLES DE CONTACTO

**Comando en Chat:**
```
Mostrar los detalles del contacto 42
```

**Variantes:**
- "Ver información completa del contacto García"
- "Detalles del ID 42"
- "¿Qué información tenemos de Juan?"

**Resultado:**
```
✅ Detalles del Contacto:

ID: 42
Nombre: Juan García
Email: juan@example.com
Teléfono: +34 123 456 789
País: España
Ciudad: Madrid
Es Empresa: No
Creado Por: admin
Fecha de Creación: 2026-04-17 15:30:00
```

---

### 4️⃣ ACTUALIZAR CONTACTO

**Comando en Chat:**
```
Actualizar contacto 42: cambiar teléfono a +34 111 222 333 y email a juan.garcia@example.com
```

**Variantes:**
- "Editar Juan García: agregar ciudad 'Barcelona'"
- "Contacto 42: actualizar país a 'Francia'"
- "Cambiar email del contacto 'Juan García' a: nuevo@example.com"

**Campos que se pueden actualizar:**
- ✏️ Nombre
- ✏️ Email
- ✏️ Teléfono
- ✏️ País
- ✏️ Ciudad

**Resultado:**
```
✅ Contacto actualizado exitosamente

Cambios:
  • Teléfono: +34 123 456 789 → +34 111 222 333
  • Email: juan@example.com → juan.garcia@example.com
  • Modificado por: admin en 2026-04-17 16:45:00
```

---

### 5️⃣ ELIMINAR CONTACTO

**Comando en Chat:**
```
Eliminar contacto 42
```

**Variantes:**
- "Borrar contacto Juan García"
- "Eliminar el contacto ID 42"
- "Dar de baja el contacto 'García'"

**Protecciones automáticas:**
- ✅ No permite eliminar contactos con **facturas asociadas**
- ✅ Sugiere **archivar** en su lugar
- ✅ Requiere **confirmación** del usuario

**Resultado - Si es seguro:**
```
✅ Contacto 'Juan García' eliminado exitosamente
```

**Resultado - Si tiene transacciones:**
```
❌ No se puede eliminar el contacto 'Juan García'
porque tiene 3 facturas asociadas.

Sugerencia: Considera archivarlo en su lugar
Comando: Archivar contacto 42
```

---

## 📋 Casos de Uso Comunes

### Caso 1: Importar Cliente Nuevo

```
Chat: "Crear contacto: Empresa XYZ Corp, email: info@xyzco.com, 
       teléfono: +34 93 123 4567, país: España"

Resultado: ✅ Contacto 'Empresa XYZ Corp' creado (ID: 45)

Base de Datos: se crea registro en res_partner con auditoría
```

### Caso 2: Actualizar Información de Contacto

```
Chat: "Mi contacto Juan García tiene nuevo email.
       Actualizar contacto 42: juan.g@newdomain.com"

Resultado: ✅ Email actualizado
           juan@example.com → juan.g@newdomain.com
```

### Caso 3: Buscar y Validar

```
Chat: "¿Existe un contacto con email maria@example.com?
       Si existe, mostrar su ID y teléfono"

Resultado: ✅ Contacto encontrado
           María López (ID: 46)
           Email: maria@example.com
           Teléfono: +34 666 777 888
```

### Caso 4: Limpiar Contactos Duplicados

```
Chat: "Buscar todos los contactos con nombre que contenga 'García'"

Resultado: 3 contactos encontrados - [lista con IDs]

Chat: "El contacto 47 es duplicado. Eliminar contacto 47"

Sistema: ✅ Contacto eliminado (si no tiene facturas)
```

---

## 🔐 Auditoría y Seguridad

### Registro Automático

Cada acción se registra:

```
res_partner_audit:
  id: 42
  action: "create"
  user: "admin"
  timestamp: 2026-04-17 15:30:00
  request_id: "req_xyz123"
  old_values: {}
  new_values: {
    "name": "Juan García",
    "email": "juan@example.com",
    "phone": "+34 123 456 789"
  }
```

### Permisos

- ✅ **Admin**: Crear, leer, actualizar, eliminar
- ✅ **Sales Manager**: Crear, leer, actualizar (no eliminar)
- ✅ **Sales User**: Leer, actualizar propios contactos
- ❌ **Otros**: Acceso limitado según políticas OpenClaw

### Protecciones

1. **Integridad referencial**: No elimina si tiene facturas
2. **Validación**: Email debe ser válido
3. **Auditoría**: Todo registro queda en logs
4. **Aprobación**: Requiere OpenClaw request approval

---

## 🛠️ Instalación y Configuración

### 1. Activar el Addon

```bash
# En Odoo (Apps > Búscar "openclaw")
# Instalar: OpenClaw - Contacts Manager
```

### 2. Configurar Variables de Entorno

```bash
export ODOO_URL="http://localhost:8069"
export ODOO_DB="odoo"
export ODOO_USER="admin"
export ODOO_PASSWORD="admin"
export ANTHROPIC_API_KEY="sk-..."  # Para Claude AI
```

### 3. Cargar el Addon en Odoo

```bash
# En terminal de Odoo:
cd ~/.local/share/odoo/addons/

# O registrarlo en addon_paths de odoo.conf:
[options]
addons_path = /path/to/addons_custom/openclaw

# Luego reiniciar Odoo
```

### 4. Habilitar en OpenClaw

```yaml
# En openclaw/config.yml
chat_tools:
  - name: "contacts"
    module: "models.contacts"
    tools:
      - create_contact
      - update_contact
      - delete_contact
      - get_contact
      - search_contacts
```

---

## 💬 Ejemplos de Conversaciones Reales

### Conversación 1: Crear y Buscar

```
📱 Usuario: "Necesito registrar un nuevo cliente"

🤖 OpenClaw: "Claro, te ayudo. ¿Cuál es el nombre del cliente?"

📱 Usuario: "Carlos López, email carlos@example.com"

🤖 OpenClaw: "✅ Contacto 'Carlos López' creado exitosamente (ID: 48)
             Email: carlos@example.com
             ¿Necesitas agregar más información?"

📱 Usuario: "Sí, agregar teléfono +34 123 456 789"

🤖 OpenClaw: "✅ Teléfono agregado: +34 123 456 789
             ¿Algo más?"

📱 Usuario: "Listo, gracias"

🤖 OpenClaw: "✅ Contacto completamente registrado:
             • ID: 48
             • Nombre: Carlos López
             • Email: carlos@example.com
             • Teléfono: +34 123 456 789"
```

### Conversación 2: Buscar y Actualizar

```
📱 Usuario: "Busca contactos de García"

🤖 OpenClaw: "✅ Se encontraron 3 contactos:
             1. Juan García (ID: 42)
             2. García & Asociados (ID: 43)
             3. María García López (ID: 44)"

📱 Usuario: "Actualizar Juan García: nuevo email juan.g@company.com"

🤖 OpenClaw: "✅ Email actualizado para Juan García
             Antiguo: juan@example.com
             Nuevo: juan.g@company.com"
```

---

## ⚠️ Limitaciones y Consideraciones

| Situación | Comportamiento |
|-----------|-----------------|
| Crear sin nombre | ❌ Error: "Nombre requerido" |
| Email inválido | ⚠️ Advertencia pero permite guardar |
| Eliminar con facturas | ❌ Error: Sugiere archivar |
| Actualizar no existente | ❌ Error: "Contacto no encontrado" |
| Buscar sin resultados | ✅ Mensaje: "No se encontraron contactos" |

---

## 📞 Soporte y Ayuda

### Comandos de Ayuda

```
"¿Qué puedo hacer con contactos?"
"¿Cómo creo un contacto empresarial?"
"¿Puedo eliminar un contacto con facturas?"
"Muestra ejemplos de búsqueda de contactos"
```

### Errores Comunes

| Error | Solución |
|-------|----------|
| "Contacto no encontrado" | Verifica el ID o busca por nombre |
| "Email inválido" | Ej: usuario@dominio.com |
| "No se puede eliminar" | El contacto tiene facturas, archívalo |
| "Acceso denegado" | Verifica permisos OpenClaw |

---

## 📊 Estadísticas y Reportes

```
Chat: "¿Cuántos contactos tenemos en total?"

Resultado: "Se encontraron 150 contactos registrados
           • Personas: 98
           • Empresas: 52
           • Últimos 7 días: 15 nuevos"
```

---

## 🚀 Próximas Funcionalidades

- ✅ Crear contactos
- ✅ Editar contactos
- ✅ Eliminar contactos
- ✅ Buscar contactos
- 🔜 Exportar a Excel
- 🔜 Importar CSV
- 🔜 Duplicar contactos
- 🔜 Fusionar contactos duplicados
- 🔜 Generar reportes de contactos

---

## 📝 Resumen Rápido

| Acción | Comando Ejemplo |
|--------|-----------------|
| 🆕 Crear | "Crear contacto Juan García, email juan@ex.com" |
| 🔍 Buscar | "Buscar contactos 'García'" |
| 👁️ Ver Detalles | "Mostrar detalles contacto 42" |
| ✏️ Actualizar | "Actualizar contacto 42: teléfono +34 123 4567" |
| 🗑️ Eliminar | "Eliminar contacto 42" |

---

**✨ ¡Ya estás listo para gestionar contactos desde OpenClaw Chat!**

Para empezar, abre el chat y escribe:
```
"Crear un nuevo contacto"
```

¡El asistente te guiará en cada paso!

---

**Documento**: Guía de Gestión de Contactos  
**Versión**: 1.0  
**Fecha**: 2026-04-17  
**Estado**: ✅ LISTO PARA USAR
