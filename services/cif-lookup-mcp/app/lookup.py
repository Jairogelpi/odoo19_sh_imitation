"""CIF lookup core: validation + scrapers + enrichment.

Adapted from the standalone stdio MCP server (files (3)/server.py). The
write-to-Odoo path is intentionally omitted: res.partner writes must go
through OpenClaw's policy/approval pipeline, not a direct XML-RPC bypass.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("cif-lookup")

GMAPS_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()

CIF_REGEX = re.compile(r"^[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]$", re.IGNORECASE)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}


def validar_cif(cif: str) -> tuple[bool, str]:
    cif = (cif or "").strip().upper().replace("-", "").replace(" ", "")
    return bool(CIF_REGEX.match(cif)), cif


async def _fetch(url: str, timeout: int = 12) -> httpx.Response | None:
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=timeout) as c:
            r = await c.get(url)
            r.raise_for_status()
            return r
    except Exception as exc:
        logger.warning("fetch %s failed: %s", url, exc)
        return None


async def _scrape_infocif(cif: str) -> dict | None:
    r = await _fetch(f"https://www.infocif.es/buscar?q={cif}")
    if not r:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    link = soup.select_one("a[href*='/ficha-empresa/']")
    if link:
        href = link["href"]
        if not href.startswith("http"):
            href = "https://www.infocif.es" + href
        r2 = await _fetch(href)
        if r2:
            soup = BeautifulSoup(r2.text, "lxml")
    d: dict = {}
    for sel in ["h1.empresa-nombre", "h1[itemprop='name']", "h1"]:
        el = soup.select_one(sel)
        if el and el.text.strip():
            d["razon_social"] = el.text.strip()
            break
    for sel in ["[itemprop='streetAddress']", ".direccion", ".domicilio"]:
        el = soup.select_one(sel)
        if el and el.text.strip():
            d["direccion"] = el.text.strip()
            break
    for sel, key in [
        ("[itemprop='postalCode']", "codigo_postal"),
        ("[itemprop='addressLocality']", "municipio"),
        ("[itemprop='addressRegion']", "comunidad_autonoma"),
        ("[itemprop='telephone']", "telefono"),
    ]:
        el = soup.select_one(sel)
        if el:
            d[key] = el.text.strip()
    el = soup.select_one("[itemprop='email'], a[href^='mailto:']")
    if el:
        d["email"] = el.get("href", el.text).replace("mailto:", "").strip()
    for s in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            ld = json.loads(s.string)
            addr = ld.get("address", {}) if isinstance(ld, dict) else {}
            for src, dst in [
                ("streetAddress", "direccion"),
                ("postalCode", "codigo_postal"),
                ("addressRegion", "comunidad_autonoma"),
                ("addressLocality", "municipio"),
            ]:
                if addr.get(src) and dst not in d:
                    d[dst] = addr[src]
            for src, dst in [("telephone", "telefono"), ("email", "email")]:
                if ld.get(src) and dst not in d:
                    d[dst] = ld[src]
        except Exception:
            pass
    return d if d.get("razon_social") else None


async def _scrape_infoempresa(cif: str) -> dict | None:
    r = await _fetch(f"https://infoempresa.com/es/es/empresa/{cif.lower()}")
    if not r or r.status_code == 404:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    d: dict = {}
    h1 = soup.select_one("h1")
    if h1:
        d["razon_social"] = h1.text.strip()
    s = soup.find("script", {"type": "application/ld+json"})
    if s:
        try:
            ld = json.loads(s.string)
            addr = ld.get("address", {})
            for src, dst in [
                ("streetAddress", "direccion"),
                ("postalCode", "codigo_postal"),
                ("addressRegion", "comunidad_autonoma"),
                ("addressLocality", "municipio"),
            ]:
                if addr.get(src):
                    d[dst] = addr[src]
            if ld.get("telephone"):
                d["telefono"] = ld["telephone"]
            if ld.get("email"):
                d["email"] = ld["email"]
        except Exception:
            pass
    return d if d.get("razon_social") else None


async def _scrape_empresia(cif: str) -> dict | None:
    r = await _fetch(f"https://empresia.es/empresa/{cif}/")
    if not r or r.status_code >= 400:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    d: dict = {}
    h1 = soup.select_one("h1")
    if h1 and h1.text.strip():
        d["razon_social"] = h1.text.strip()
    for s in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            ld = json.loads(s.string or "{}")
        except Exception:
            continue
        if isinstance(ld, list):
            ld = next((x for x in ld if isinstance(x, dict)), {})
        if not isinstance(ld, dict):
            continue
        if ld.get("name") and "razon_social" not in d:
            d["razon_social"] = ld["name"]
        addr = ld.get("address") or {}
        if isinstance(addr, dict):
            for src, dst in [
                ("streetAddress", "direccion"),
                ("postalCode", "codigo_postal"),
                ("addressRegion", "comunidad_autonoma"),
                ("addressLocality", "municipio"),
            ]:
                if addr.get(src) and dst not in d:
                    d[dst] = addr[src]
        if ld.get("telephone") and "telefono" not in d:
            d["telefono"] = ld["telephone"]
        if ld.get("email") and "email" not in d:
            d["email"] = ld["email"]
        if ld.get("url") and "website" not in d:
            d["website"] = ld["url"]
    if "municipio" not in d:
        m = re.search(r"(?i)domicilio en ([A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?:[.<]|Su clasificaci)", r.text)
        if m:
            d["municipio"] = m.group(1).strip()
    return d if d.get("razon_social") else None


async def _scrape_axesor(cif: str) -> dict | None:
    r = await _fetch(f"https://www.axesor.es/Informes-Empresas/Buscar?q={cif}")
    if not r:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    res = soup.select_one(".resultado-empresa a, .company-result a")
    if res:
        href = res.get("href", "")
        if not href.startswith("http"):
            href = "https://www.axesor.es" + href
        r2 = await _fetch(href)
        if r2:
            soup = BeautifulSoup(r2.text, "lxml")
    d: dict = {}
    for s in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            ld = json.loads(s.string)
            if isinstance(ld, list):
                ld = ld[0]
            if ld.get("name") and "razon_social" not in d:
                d["razon_social"] = ld["name"]
            addr = ld.get("address", {})
            for src, dst in [
                ("streetAddress", "direccion"),
                ("postalCode", "codigo_postal"),
                ("addressRegion", "comunidad_autonoma"),
                ("addressLocality", "municipio"),
            ]:
                if addr.get(src) and dst not in d:
                    d[dst] = addr[src]
            for src, dst in [("telephone", "telefono"), ("email", "email")]:
                if ld.get(src) and dst not in d:
                    d[dst] = ld[src]
        except Exception:
            pass
    return d if d.get("razon_social") else None


CP_CCAA = {
    "01": "País Vasco", "02": "Castilla-La Mancha", "03": "Comunidad Valenciana",
    "04": "Andalucía", "05": "Castilla y León", "06": "Extremadura",
    "07": "Islas Baleares", "08": "Cataluña", "09": "Castilla y León",
    "10": "Extremadura", "11": "Andalucía", "12": "Comunidad Valenciana",
    "13": "Castilla-La Mancha", "14": "Andalucía", "15": "Galicia",
    "16": "Castilla-La Mancha", "17": "Cataluña", "18": "Andalucía",
    "19": "Castilla-La Mancha", "20": "País Vasco", "21": "Andalucía",
    "22": "Aragón", "23": "Andalucía", "24": "Castilla y León",
    "25": "Cataluña", "26": "La Rioja", "27": "Galicia",
    "28": "Comunidad de Madrid", "29": "Andalucía", "30": "Región de Murcia",
    "31": "Comunidad Foral de Navarra", "32": "Galicia", "33": "Principado de Asturias",
    "34": "Castilla y León", "35": "Canarias", "36": "Galicia",
    "37": "Castilla y León", "38": "Canarias", "39": "Cantabria",
    "40": "Castilla y León", "41": "Andalucía", "42": "Castilla y León",
    "43": "Cataluña", "44": "Aragón", "45": "Castilla-La Mancha",
    "46": "Comunidad Valenciana", "47": "Castilla y León", "48": "País Vasco",
    "49": "Castilla y León", "50": "Aragón", "51": "Ceuta", "52": "Melilla",
}


def _inferir_ccaa(cp: str) -> str | None:
    return CP_CCAA.get(cp[:2]) if cp and len(cp) >= 2 else None


async def _extraer_cp_municipio(datos: dict) -> dict:
    if "codigo_postal" not in datos and "direccion" in datos:
        m = re.search(r"\b(\d{5})\b", datos["direccion"])
        if m:
            datos["codigo_postal"] = m.group(1)
            post = datos["direccion"][m.end():].strip().lstrip(",").strip()
            if post and "municipio" not in datos:
                datos["municipio"] = post.split(",")[0].strip()
    return datos


async def _gmaps_buscar_place_id(nombre: str, municipio: str) -> str | None:
    if not GMAPS_KEY:
        return None
    query = f"{nombre} {municipio}".strip()
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={"query": query, "language": "es", "region": "es", "key": GMAPS_KEY},
            )
            r.raise_for_status()
            data = r.json()
            if data.get("status") not in {"OK", "ZERO_RESULTS"}:
                logger.warning("GMaps textsearch status=%s msg=%s", data.get("status"), data.get("error_message"))
            results = data.get("results") or []
            return results[0].get("place_id") if results else None
    except Exception as exc:
        logger.warning("GMaps search failed: %s", exc)
        return None


async def _gmaps_details(place_id: str) -> dict:
    if not GMAPS_KEY or not place_id:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={
                    "place_id": place_id,
                    "fields": "name,formatted_address,formatted_phone_number,international_phone_number,website,address_components",
                    "language": "es",
                    "key": GMAPS_KEY,
                },
            )
            r.raise_for_status()
            data = r.json()
            if data.get("status") != "OK":
                logger.warning("GMaps details status=%s msg=%s", data.get("status"), data.get("error_message"))
                return {}
            result = data.get("result") or {}
    except Exception as exc:
        logger.warning("GMaps details failed: %s", exc)
        return {}
    res: dict = {}
    tel = result.get("international_phone_number") or result.get("formatted_phone_number")
    if tel:
        res["telefono"] = tel
    if result.get("website"):
        res["website"] = result["website"]
    for comp in result.get("address_components", []):
        tipos = comp.get("types", [])
        if "postal_code" in tipos:
            res["_gm_cp"] = comp.get("long_name", "")
        if "locality" in tipos:
            res["_gm_municipio"] = comp.get("long_name", "")
        if "administrative_area_level_1" in tipos:
            res["_gm_ccaa"] = comp.get("long_name", "")
        if "route" in tipos or "street_number" in tipos:
            res.setdefault("_gm_street_parts", []).append(comp.get("long_name", ""))
    if result.get("formatted_address"):
        res["_gm_formatted_address"] = result["formatted_address"]
    if result.get("name"):
        res["_gm_name"] = result["name"]
    return res


async def _enriquecer_gmaps(datos: dict) -> dict:
    if not GMAPS_KEY or (datos.get("telefono") and datos.get("website")):
        return datos
    razon = datos.get("razon_social", "")
    if not razon:
        return datos
    place_id = await _gmaps_buscar_place_id(razon, datos.get("municipio", ""))
    if not place_id:
        return datos
    contacto = await _gmaps_details(place_id)
    if contacto:
        datos["_gmaps_place_id"] = place_id
        if "telefono" not in datos and contacto.get("telefono"):
            datos["telefono"] = contacto["telefono"]
        if "website" not in datos and contacto.get("website"):
            datos["website"] = contacto["website"]
        if "codigo_postal" not in datos and contacto.get("_gm_cp"):
            datos["codigo_postal"] = contacto["_gm_cp"]
        if "municipio" not in datos and contacto.get("_gm_municipio"):
            datos["municipio"] = contacto["_gm_municipio"]
        if "comunidad_autonoma" not in datos and contacto.get("_gm_ccaa"):
            datos["comunidad_autonoma"] = contacto["_gm_ccaa"]
        if "direccion" not in datos and contacto.get("_gm_formatted_address"):
            datos["direccion"] = contacto["_gm_formatted_address"]
    return datos


async def _gmaps_buscar_por_cif(cif: str) -> dict | None:
    if not GMAPS_KEY:
        return None
    queries = [f"empresa CIF {cif} España", f"{cif} España"]
    place_id: str | None = None
    top_name: str | None = None
    top_address: str | None = None
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            for q in queries:
                r = await c.get(
                    "https://maps.googleapis.com/maps/api/place/textsearch/json",
                    params={"query": q, "language": "es", "region": "es", "key": GMAPS_KEY},
                )
                r.raise_for_status()
                data = r.json()
                if data.get("status") not in {"OK", "ZERO_RESULTS"}:
                    logger.warning("GMaps CIF search status=%s msg=%s", data.get("status"), data.get("error_message"))
                    continue
                results = data.get("results") or []
                if results:
                    place_id = results[0].get("place_id")
                    top_name = results[0].get("name")
                    top_address = results[0].get("formatted_address")
                    break
    except Exception as exc:
        logger.warning("GMaps CIF search failed: %s", exc)
        return None
    if not place_id:
        return None
    details = await _gmaps_details(place_id)
    d: dict = {"_gmaps_place_id": place_id}
    if details.get("_gm_name") or top_name:
        d["razon_social"] = details.get("_gm_name") or top_name
    if details.get("_gm_formatted_address") or top_address:
        d["direccion"] = details.get("_gm_formatted_address") or top_address
    if details.get("_gm_cp"):
        d["codigo_postal"] = details["_gm_cp"]
    if details.get("_gm_municipio"):
        d["municipio"] = details["_gm_municipio"]
    if details.get("_gm_ccaa"):
        d["comunidad_autonoma"] = details["_gm_ccaa"]
    if details.get("telefono"):
        d["telefono"] = details["telefono"]
    if details.get("website"):
        d["website"] = details["website"]
    return d if d.get("razon_social") else None


async def buscar_empresa(cif: str) -> dict[str, Any]:
    ok, cif_norm = validar_cif(cif)
    if not ok:
        return {"error": True, "mensaje": f"CIF '{cif}' no válido.", "cif": cif}

    resultado: dict[str, Any] = {"cif": cif_norm, "fuente": None, "error": False}

    scrapers = await asyncio.gather(
        _scrape_empresia(cif_norm),
        _scrape_infocif(cif_norm),
        _scrape_infoempresa(cif_norm),
        _scrape_axesor(cif_norm),
        return_exceptions=True,
    )

    datos: dict = {}
    for fuente, d in zip(["empresia.es", "infocif.es", "infoempresa.com", "axesor.es"], scrapers):
        if isinstance(d, dict) and d:
            datos = d
            resultado["fuente"] = fuente
            break

    if not datos:
        gmaps_datos = await _gmaps_buscar_por_cif(cif_norm)
        if gmaps_datos:
            datos = gmaps_datos
            resultado["fuente"] = "google_maps"
        else:
            resultado["error"] = True
            resultado["mensaje"] = f"No se encontraron datos para el CIF {cif_norm}."
            return resultado

    datos = await _extraer_cp_municipio(datos)

    if "comunidad_autonoma" not in datos and "codigo_postal" in datos:
        ccaa = _inferir_ccaa(datos["codigo_postal"])
        if ccaa:
            datos["comunidad_autonoma"] = ccaa
            datos["_ccaa_inferida"] = True

    datos = await _enriquecer_gmaps(datos)
    resultado.update(datos)

    ausentes = [
        c for c in ["razon_social", "direccion", "codigo_postal", "municipio", "comunidad_autonoma", "telefono"]
        if c not in resultado
    ]
    if ausentes:
        resultado["_campos_no_disponibles"] = ausentes
        if "telefono" in ausentes and not GMAPS_KEY:
            resultado["_nota"] = "Define GOOGLE_MAPS_API_KEY para obtener teléfono/web."

    return resultado


def mapear_a_res_partner(datos: dict[str, Any]) -> dict[str, Any]:
    """Translate a buscar_empresa result into a res.partner values dict.

    Caller is responsible for submitting this to Odoo via the OpenClaw
    permission pipeline (openclaw.request with operation='create' or 'write').
    """
    cif = str(datos.get("cif") or "").upper().replace("-", "").replace(" ", "")
    vat = cif if cif.startswith("ES") else f"ES{cif}" if cif else ""

    vals: dict[str, Any] = {
        "is_company": True,
        "company_type": "company",
        "lang": "es_ES",
    }
    if datos.get("razon_social"):
        vals["name"] = datos["razon_social"]
    if vat:
        vals["vat"] = vat
    if datos.get("direccion"):
        vals["street"] = datos["direccion"]
    if datos.get("codigo_postal"):
        vals["zip"] = datos["codigo_postal"]
    if datos.get("municipio"):
        vals["city"] = datos["municipio"]
    if datos.get("telefono"):
        vals["phone"] = datos["telefono"]
    if datos.get("website"):
        vals["website"] = datos["website"]
    if datos.get("email"):
        vals["email"] = datos["email"]

    return {
        "model": "res.partner",
        "values": vals,
        "state_name": datos.get("comunidad_autonoma") or "",
        "country_code": "ES",
    }
