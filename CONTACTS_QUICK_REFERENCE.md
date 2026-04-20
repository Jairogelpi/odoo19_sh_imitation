# 🚀 Cheat Sheet - Gestión de Contactos en OpenClaw

## Abre el chat en Odoo y usa estos comandos:

### ✨ CREAR CONTACTO
```
Crear contacto: [Nombre], email: [email], teléfono: [teléfono], país: [país]

Ejemplos:
  • Crear contacto: Juan García, email: juan@example.com, teléfono: +34 123 456 789
  • Nuevo contacto - María López, país: España
  • Agregar contacto 'Acme Corp', empresa, email: info@acme.com
```

### 🔍 BUSCAR CONTACTOS
```
Buscar contactos [criterio]

Ejemplos:
  • Buscar contactos 'García'
  • Mostrar todos los contactos
  • Buscar por email: maria@
  • ¿Existe un contacto con teléfono 987654321?
```

### 👁️ VER DETALLES
```
Mostrar detalles del contacto [ID o nombre]

Ejemplos:
  • Mostrar detalles del contacto 42
  • Ver información de Juan García
  • Detalles contacto ID 42
```

### ✏️ ACTUALIZAR CONTACTO
```
Actualizar contacto [ID]: [campo]: [nuevo_valor]

Ejemplos:
  • Actualizar contacto 42: email: juan.garcia@example.com
  • Cambiar contacto 42 teléfono a +34 111 222 333
  • Editar contacto 42: país: Francia
  • Contacto 42: actualizar nombre a 'Juan García López'
```

### 🗑️ ELIMINAR CONTACTO
```
Eliminar contacto [ID o nombre]

Ejemplos:
  • Eliminar contacto 42
  • Borrar contacto 'Juan García'
  • Dar de baja contacto ID 42
```

---

## 📝 Campos Disponibles

| Campo | Ejemplo | Notas |
|-------|---------|-------|
| Nombre | Juan García | ⭐ Requerido |
| Email | juan@example.com | Validado automáticamente |
| Teléfono | +34 123 456 789 | Acepta cualquier formato |
| País | España o ES | Código o nombre |
| Ciudad | Madrid | Opcional |
| Empresa | Acme Corp | Marca como contacto empresarial |

---

## 🎯 Respuestas Esperadas

### ✅ Éxito
```
✅ Contacto 'Juan García' creado exitosamente (ID: 42)
✅ Se encontraron 3 contactos
✅ Contacto actualizado exitosamente
✅ Contacto eliminado exitosamente
```

### ❌ Errores Comunes
```
❌ Contacto con ID 99 no encontrado
❌ Nombre requerido
❌ No se puede eliminar: tiene facturas asociadas
❌ Contacto con ID 42 no encontrado
```

---

## 💡 Pro Tips

1. **Búsqueda Flexible**: Buscar funciona con nombres parciales
   ```
   "Buscar: garcía" → Encuentra: Juan García, García & Asociados, etc.
   ```

2. **Actualización Múltiple**: Actualiza varios campos a la vez
   ```
   "Actualizar contacto 42: email: new@ex.com, teléfono: +34 111 222 333"
   ```

3. **Busqueda por Email**: Útil para encontrar contactos rápido
   ```
   "Buscar contactos: info@"
   ```

4. **Duplicados Automáticos**: Busca antes de crear para evitar duplicados
   ```
   "Buscar contactos 'García'" → luego "Crear contacto..."
   ```

---

## 🔐 Información de Seguridad

✅ Todo se registra con auditoría  
✅ Se guarda quién creó/modificó cada contacto  
✅ No puedes eliminar contactos con facturas (protección automática)  
✅ Requiere aprobación OpenClaw para cambios críticos  

---

## 📞 Ejemplos Paso a Paso

### Caso: Registrar nuevo cliente

```
1️⃣ Chat: "Crear contacto: Carlos López"
   Sistema: ✅ Contacto creado (ID: 50)

2️⃣ Chat: "Contacto 50: agregar email carlos@example.com"
   Sistema: ✅ Email agregado

3️⃣ Chat: "Contacto 50: teléfono +34 987 654 321"
   Sistema: ✅ Teléfono agregado

4️⃣ Chat: "Mostrar detalles contacto 50"
   Sistema: Nombre, Email, Teléfono (todo guardado ✅)
```

### Caso: Encontrar y actualizar

```
1️⃣ Chat: "Buscar 'María'"
   Sistema: Se encontraron 2 contactos (ID: 12, 45)

2️⃣ Chat: "Mostrar detalles contacto 45"
   Sistema: María López, email viejo@ex.com, teléfono...

3️⃣ Chat: "Actualizar 45: email nuevo@ex.com"
   Sistema: ✅ Actualizado
```

---

## ⚡ Comandos Rápidos

| Necesidad | Comando |
|-----------|---------|
| Crear rápido | "Nuevo: [nombre]" |
| Ver todo | "Listar contactos" |
| Buscar | "Buscar [texto]" |
| Editar | "Contacto [ID]: [campo]: [valor]" |
| Borrar | "Eliminar [ID]" |

---

## 📲 En el Chat de Odoo

1. Abre **OpenClaw Chat** en Odoo
2. Escribe uno de los comandos arriba
3. El asistente responde automáticamente
4. ¡Listo! Todo se guarda en la base de datos

```
🌐 URL: http://localhost:8069/odoo/action-303
```

---

**¡Ya puedes gestionar contactos! 🎉**

Prueba ahora: `"Crear contacto de prueba: Acme Corp"`
