---
name: openclaw-cif-lookup
description: >
  Skill para enriquecer y guardar empresas españolas en Odoo 19 a partir de
  su CIF. Úsala SIEMPRE que el usuario mencione "buscar empresa por CIF",
  "guardar en Odoo", "crear contacto empresa", "importar empresa",
  "dar de alta proveedor/cliente con CIF", "rellenar res.partner por CIF",
  o cuando pegue un CIF español (letra + 7 dígitos + control) en un
  contexto de Odoo. Orquesta los MCP tools `cif.validate` y `cif.lookup`
  y enruta la escritura a res.partner a través del flujo de aprobación
  de OpenClaw (nunca por XML-RPC directo).
repository: internal
---

# OpenClaw CIF → res.partner

Flujo permisionado para enriquecer y dar de alta una empresa española en
Odoo 19 a partir de su CIF. El lookup externo vive en el servicio MCP
`cif-lookup-mcp` del stack admin; la escritura en `res.partner` se ejecuta
vía una `openclaw.request` con policy/approval, nunca directamente.

## Cuándo usar

- El usuario quiere buscar una empresa por CIF (B12345678, A28015272…).
- El usuario pide dar de alta un nuevo cliente/proveedor empresa con CIF.
- El usuario pega un CIF y pide "rellénalo en Odoo" / "mete esto como contacto".

## Cuándo NO usar

- Contactos personas físicas sin CIF → `openclaw-crm-contacts`.
- Empresas no españolas → `openclaw-crm-contacts` (CIF es específico de ES).
- Editar campos puntuales de un partner existente sin lookup → `openclaw-crm-contacts`.

---

## Principios de interacción (MUY IMPORTANTE)

Este skill es **proactivo** y **conversacional**. NUNCA des de alta una
empresa sin que el usuario haya confirmado explícitamente que los datos
recuperados son los de la empresa que él quiere. En concreto:

1. **Si el usuario no da un CIF** → pídelo primero ("¿Cuál es el CIF de la empresa?"). Si solo da el nombre, explica que los scrapers indexan por CIF y pide el CIF o un identificador equivalente.
2. **Si el CIF devuelve datos** → presenta al usuario **un resumen claro** (razón social, dirección completa, teléfono, web, fuente) y **pregunta explícitamente**: *"¿Es esta la empresa que querías dar de alta? (sí/no)"*. Espera la confirmación antes de escribir en Odoo.
3. **Si el usuario dice que no** → pregunta qué dato no cuadra (¿nombre distinto?, ¿otra empresa del grupo?, ¿CIF mal tecleado?). Itera:
   - Reintenta `cif.lookup` con el CIF corregido si el usuario ofrece uno nuevo.
   - Si parece un CIF válido pero los datos no son los esperados, ofrece reintentarlo por si hubo fallo transitorio del scraper.
   - No inventes una empresa nunca. Si los scrapers no la encuentran y Google Maps tampoco, dilo con claridad.
4. **Si el lookup viene con campos vacíos** (`_campos_no_disponibles`) → menciónalos al usuario antes de pedir confirmación, para que sepa qué se guardará y qué no.
5. **Detectar duplicados antes de crear** → siempre haz el `search_read` por `vat` del paso 3. Si existe, di al usuario *"Ya hay un contacto con este CIF: <nombre> (id <partner_id>). ¿Quieres actualizarlo con los datos nuevos o dejarlo como está?"*.
6. **Cada escritura en Odoo pasa por `openclaw.request`** → el usuario verá la aprobación en la UI como siempre. No intentes bypasar esto.
7. **Idioma**: responde en el idioma del usuario. Los ejemplos de este documento están en español pero el flujo funciona igual en inglés.

## Pipeline

### Paso 1 — Validar el CIF (no llama a red)

```
tool: cif.validate
args: { "cif": "<CIF>" }
```

Si `es_valido=false` → para y pide al usuario que revise el CIF.

### Paso 2 — Lookup + enrichment

```
tool: cif.lookup
args: { "cif": "<CIF>", "include_partner_mapping": true }
```

Qué hace el MCP:

1. Scraping paralelo de `infocif.es`, `infoempresa.com`, `axesor.es` hasta obtener datos.
2. Extracción de CP/municipio desde la dirección si no vienen sueltos.
3. Inferencia de comunidad autónoma desde el CP (primeros dos dígitos).
4. Enrichment opcional de teléfono/web vía Google Maps Places (si `GOOGLE_MAPS_API_KEY` está configurada en el servicio).
5. Con `include_partner_mapping=true`, devuelve también `_res_partner`: un
   dict con `model`, `values`, `state_name`, `country_code` listo para
   enviar a OpenClaw.

**Si `error=true`** → informa al usuario con `mensaje` y los campos que no se pudieron recuperar (`_campos_no_disponibles`). No continúes.

**Si todo va bien** → presenta un resumen (nombre, dirección, CP, municipio, CCAA, fuente) y pide confirmación antes de guardar.

### Paso 3 — Upsert en res.partner vía OpenClaw

Construye una `openclaw.request` con:

```json
{
  "action_type": "odoo_write",
  "instruction": "Dar de alta empresa <razón social> (CIF <vat>) en res.partner",
  "target_model": "res.partner",
  "payload": {
    "model": "res.partner",
    "operation": "create",            // o "write" si ya existe
    "values": { ...values del _res_partner... },
    "state_name": "<comunidad_autonoma>",
    "country_code": "ES"
  }
}
```

**Antes** de la escritura, haz un `search` por `vat` para detectar duplicados:

```json
{
  "action_type": "odoo_read",
  "payload": {
    "model": "res.partner",
    "operation": "search_read",
    "domain": [["vat", "=", "ES<CIF>"], ["is_company", "=", true]],
    "fields": ["id", "name"],
    "limit": 1
  }
}
```

- Si devuelve resultados → usa `operation: "write"` con `ids: [partner_id]` y los `values` no vacíos.
- Si no → usa `operation: "create"` con los `values`.

La `openclaw.request` entra en el flujo estándar: pending → approved → executed. La política aplica como en cualquier escritura Odoo.

### Paso 4 — Confirmar al usuario

Muestra:

- Nombre de la empresa.
- Si se ha **creado** o **actualizado**.
- `partner_id` resultante.
- URL: `http://localhost:8070/odoo/contacts/<partner_id>`.
- Campos que vinieron vacíos del lookup (para que el usuario los rellene a mano si quiere).

---

## Mapeo de campos (resumen)

| Campo lookup          | res.partner      | Notas                                               |
|-----------------------|------------------|-----------------------------------------------------|
| `razon_social`        | `name`           | Obligatorio.                                        |
| `cif` (normalizado)   | `vat`            | Prefijo `ES` se añade automáticamente en el mapping.|
| `direccion`           | `street`         | Solo calle.                                         |
| `codigo_postal`       | `zip`            | 5 dígitos.                                          |
| `municipio`           | `city`           |                                                     |
| `comunidad_autonoma`  | `state_id`       | Se resuelve en Odoo por nombre de CCAA.             |
| `telefono`            | `phone`          | Puede venir vacío; Google Maps puede rellenarlo.    |
| `website`             | `website`        | Google Maps puede rellenarlo.                       |
| `email`               | `email`          | Raramente disponible en datos oficiales españoles.  |
| (siempre)             | `is_company`     | `true`                                              |
| (siempre)             | `company_type`   | `"company"`                                         |
| (siempre)             | `lang`           | `"es_ES"`                                           |
| (fijo)                | `country_id`     | España (resolver por `code="ES"` en `res.country`). |

## Casos especiales

- **CIF ya existe en Odoo** → operación `write`; **no** sobreescribas campos que ya tienen valor en Odoo si el lookup no trae nada nuevo (filtra `values` vacíos antes del write).
- **Faltan teléfono/email** → normal. Informa al usuario que puede añadirlos después desde el formulario del contacto.
- **CCAA no reconocida** → si Odoo no encuentra `state_id` por nombre, crea el partner sin `state_id` y avisa.
- **Dominio de los scrapers caído** → el MCP devuelve `error=true` con `mensaje`; pide al usuario reintentar más tarde.

## Por qué no hay escritura directa desde el MCP

El `server.py` original de referencia incluía un tool `guardar_empresa_en_odoo` que escribía en `res.partner` por XML-RPC directo. **Intencionalmente no se expone** en este stack: toda mutación de datos en Odoo debe pasar por `openclaw.request` para heredar policy, approval y auditoría. Si el MCP escribiera directo, rompería el modelo de permisos de OpenClaw.

## Configuración requerida

Variables de entorno para el control-plane (ya configuradas en `compose.admin.yaml`):

- `OPENCLAW_CIF_LOOKUP_MCP_URL=http://cif-lookup-mcp:8093/mcp`
- `OPENCLAW_CIF_LOOKUP_MCP_TOKEN=<token>`
- `OPENCLAW_CIF_LOOKUP_MCP_TIMEOUT_SECONDS=30`

Para el servicio `cif-lookup-mcp`:

- `MCP_AUTH_TOKEN=<mismo token>`
- `GOOGLE_MAPS_API_KEY=<opcional, mejora teléfono/web>`
