---
name: openclaw-lead-mining
description: >
  Skill para captación gratuita de leads B2B en Odoo 19 a partir de
  OpenStreetMap. Úsala SIEMPRE que el usuario pida "buscar leads",
  "generar leads", "prospectar negocios", "conseguir empresas de una zona",
  "buscar restaurantes/hoteles/tiendas en X ciudad", "necesito contactos
  de Y sector en Z provincia" o cualquier caso de prospección por zona
  geográfica + sector sin pagar créditos de Odoo IAP. Orquesta los MCP
  tools `lead.categories` y `lead.search` contra `lead-mining-mcp` y
  crea `crm.lead` (opcionalmente también `res.partner` empresa) a través
  del wizard `openclaw.lead.mining.wizard`. No llama XML-RPC directo.
repository: internal
---

# OpenClaw Lead Mining → crm.lead

Pipeline gratuito de lead mining basado en OpenStreetMap. Sustituye a
`crm_iap_mine` (que cuesta ~0,20 €/crédito, 2 créditos por lead enriquecido,
≈ 400 €/1000 leads) por un flujo autohospedado con coste variable cero.

La búsqueda externa vive en el MCP `lead-mining-mcp` (puerto 8094). La
escritura en Odoo se hace a través del wizard del addon
`openclaw_lead_mining` — nunca por XML-RPC directo.

## Cuándo usar

- El usuario pide captar leads nuevos por zona + sector (p.ej. "búscame
  30 restaurantes en Valencia con web y teléfono").
- Quiere replicar el Lead Mining de Odoo sin comprar créditos IAP.
- Necesita alimentar el pipeline de CRM en bulk desde cero.

## Cuándo NO usar

- Enriquecer una empresa concreta de la que ya tienes el CIF → usar
  `openclaw-cif-lookup`.
- Gestionar oportunidades ya existentes o moverlas por el pipeline →
  `openclaw-crm-opportunities`.
- Crear una empresa suelta a mano → `openclaw-crm-contacts`.

---

## Principios de interacción

Este skill es **conversacional** y **permisionado**. Nunca crea leads sin
confirmación explícita del usuario sobre qué subconjunto de resultados
persistir:

1. **Si el usuario no da zona o sector** → pídelos. Ejemplo: "¿En qué
   ciudad o provincia? ¿Qué sector (restaurante, hotel, despacho…)?".
2. **Antes de buscar**, si no estás seguro del nombre exacto de la
   categoría OSM, llama a `lead.categories` y ofrece la lista.
3. **Después de `lead.search`**, presenta un resumen (total encontrados,
   % con web/teléfono/email, ciudades más frecuentes) y los **5-10
   primeros** como muestra. Pregunta: "¿Creo estos N leads en CRM o
   afinamos los filtros?".
4. **Si el usuario dice afinar** → repite `lead.search` con más/menos
   filtros (`require_website`, `require_phone`, `limit`, otra
   `area_name`).
5. **Creación**: siempre a través del wizard `openclaw.lead.mining.wizard`
   (pasa por policy/approval de openclaw). No construyas `crm.lead`
   directamente.
6. **Opcional — crear partner empresa**: si el usuario quiere además
   contactos empresa (`res.partner` con logo), activa `create_partner=True`
   y explica que el botón "Buscar CIF" del partner queda listo para
   rellenar fiscales cuando se sepa el CIF.
7. **Idioma**: responde en el idioma del usuario.

## Pipeline

### Paso 1 — Listar categorías (solo si hay duda)

```
tool: lead.categories
args: {}
→ { "categories": ["accountant","bar","cafe","car","clothes",...] }
```

### Paso 2 — Buscar en OSM

```
tool: lead.search
args: {
  "category": "restaurant",
  "area_name": "Madrid",
  "require_website": true,
  "require_phone": true,
  "limit": 30
}
```

Respuesta normalizada:
```json
{
  "error": false,
  "count": 30,
  "source": "openstreetmap",
  "category": "restaurant",
  "leads": [
    {
      "osm_id": "node/123",
      "name": "Café Comercial",
      "phone": "+34 910 88 25 25",
      "website": "http://cafecomercialmadrid.com/",
      "email": "info@cafecomercialmadrid.com",
      "street": "Glorieta de Bilbao 7",
      "zip": "28004",
      "city": "Madrid",
      "country_code": "ES",
      "category_hint": "spanish",
      "lat": 40.427,
      "lon": -3.702
    }
  ]
}
```

### Paso 3 — Confirmar y crear vía wizard

El flujo UI equivalente: **CRM → OpenClaw Lead Mining**. Desde skill se
invoca el wizard vía `openclaw.execute_request` con un request que
represente los filtros aprobados; el wizard ejecuta internamente
`action_search` + `action_create_leads`.

No escribas en `crm.lead` por XML-RPC directo. El skill se limita a:
- Recomendar filtros al usuario.
- Presentar resultados de `lead.search`.
- Delegar la persistencia al wizard (pasa por policy).

## Cobertura real (medida en Madrid, categoría restaurant)

| Campo | Cobertura |
|---|---|
| `name` | 100 % |
| `phone` | ~100 % con `require_phone=true` |
| `website` | ~100 % con `require_website=true` |
| `email` directo | ~20-30 % |
| `email` tras scrape del home | ~50-70 % |
| `street` + `zip` | 85-95 % |
| `category_hint` (cocina/tipo) | ~75 % |

## Comparativa vs Odoo IAP

| 1.000 leads | Odoo IAP | openclaw-lead-mining |
|---|---|---|
| Créditos | 2.000 × 0,20 € = 400 € | 0 € |
| Infra | 0 € | ~0 € (reusa stack admin) |
| Email verificado | Sí (Clearbit) | Scrape del home (~50-70%) |
| Contactos nominales | Sí | No (OSM no los tiene) |

## Límites honestos

- **OSM no trae CIF/VAT.** Si el usuario necesita datos fiscales, tras
  crear el lead/partner deberá ejecutar `openclaw-cif-lookup` con el CIF
  (cuando lo consiga). El wizard deja el partner listo para ese botón.
- **OSM no trae contactos personales** (CEO, decision maker). Para eso
  haría falta otro proveedor (Apollo, Hunter, Lusha), no cubierto por
  este skill.
- **Overpass es best-effort**: los endpoints públicos se saturan. El MCP
  hace fallback automático entre `private.coffee`, `kumi.systems`,
  `osm.ch`, `overpass-api.de`, `openstreetmap.fr`. Si todos fallan,
  `lead.search` devuelve `{error: true, mensaje: "…no respondieron"}`;
  reintentar en 1-2 minutos.
