"""Thin wrapper over the public OpenStreetMap Overpass API.

We only use free, public endpoints; no API key required. Results are normalised
into a stable shape the Odoo wizard can consume without knowing OSM internals.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Iterable

import httpx

logger = logging.getLogger("lead-mining-mcp.overpass")

_DEFAULT_OVERPASS_ENDPOINTS = (
    "https://overpass.private.coffee/api/interpreter,"
    "https://overpass.kumi.systems/api/interpreter,"
    "https://overpass.osm.ch/api/interpreter,"
    "https://overpass-api.de/api/interpreter,"
    "https://overpass.openstreetmap.fr/api/interpreter"
)
OVERPASS_ENDPOINTS = [
    url.strip() for url in (os.getenv("OVERPASS_ENDPOINTS") or _DEFAULT_OVERPASS_ENDPOINTS).split(",")
    if url.strip()
]

SUPPORTED_CATEGORIES: dict[str, dict[str, str]] = {
    # alias -> OSM key=value
    "restaurant": {"amenity": "restaurant"},
    "cafe": {"amenity": "cafe"},
    "bar": {"amenity": "bar"},
    "hotel": {"tourism": "hotel"},
    "office": {"office": "*"},
    "lawyer": {"office": "lawyer"},
    "accountant": {"office": "accountant"},
    "company": {"office": "company"},
    "retail": {"shop": "*"},
    "supermarket": {"shop": "supermarket"},
    "clothes": {"shop": "clothes"},
    "car": {"shop": "car"},
    "industrial": {"landuse": "industrial"},
    "healthcare": {"amenity": "clinic"},
    "dentist": {"amenity": "dentist"},
    "gym": {"leisure": "fitness_centre"},
    "school": {"amenity": "school"},
    "real_estate": {"office": "estate_agent"},
}


def _build_query(
    *,
    bbox: tuple[float, float, float, float] | None,
    area_name: str | None,
    category: str,
    require_website: bool,
    require_phone: bool,
    limit: int,
) -> str:
    filters = SUPPORTED_CATEGORIES.get(category)
    if not filters:
        raise ValueError(f"Unsupported category: {category}")

    tag_clauses: list[str] = []
    for key, value in filters.items():
        if value == "*":
            tag_clauses.append(f'["{key}"]')
        else:
            tag_clauses.append(f'["{key}"="{value}"]')
    if require_website:
        tag_clauses.append('["website"]')
    if require_phone:
        tag_clauses.append('["phone"]')

    scope = ""
    area_block = ""
    if bbox:
        south, west, north, east = bbox
        scope = f"({south},{west},{north},{east})"
    elif area_name:
        area_block = (
            f'area["name"="{area_name}"]["boundary"="administrative"]->.a;\n'
        )
        scope = "(area.a)"
    else:
        raise ValueError("bbox or area_name is required")

    tag_str = "".join(tag_clauses)
    capped = max(1, min(int(limit), 500))
    query = (
        f"[out:json][timeout:60];\n"
        f"{area_block}"
        f"nwr{tag_str}{scope};\n"
        f"out center {capped};"
    )
    return query


async def _post_query(query: str, timeout: float) -> dict | None:
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(endpoint, data={"data": query})
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
                return resp.json()
            logger.info("overpass %s returned %s", endpoint, resp.status_code)
        except httpx.HTTPError as exc:
            logger.info("overpass %s failed: %s", endpoint, exc)
    return None


def _normalise(element: dict[str, Any]) -> dict[str, Any]:
    tags = element.get("tags") or {}

    def _t(*names: str) -> str:
        for n in names:
            v = tags.get(n)
            if v:
                return str(v).strip()
        return ""

    street = _t("addr:street")
    housenum = _t("addr:housenumber")
    full_street = (f"{street} {housenum}".strip()) if street else ""

    geom = element.get("center") or {"lat": element.get("lat"), "lon": element.get("lon")}
    lat = geom.get("lat")
    lon = geom.get("lon")

    return {
        "osm_id": f"{element.get('type')}/{element.get('id')}",
        "name": _t("name"),
        "phone": _t("phone", "contact:phone"),
        "website": _t("website", "contact:website"),
        "email": _t("email", "contact:email"),
        "street": full_street,
        "zip": _t("addr:postcode"),
        "city": _t("addr:city"),
        "country_code": (_t("addr:country") or "").upper(),
        "opening_hours": _t("opening_hours"),
        "category_hint": (
            _t("cuisine")
            or _t("shop")
            or _t("office")
            or _t("amenity")
            or _t("tourism")
        ),
        "lat": lat,
        "lon": lon,
    }


async def search_leads(
    *,
    category: str,
    area_name: str | None = None,
    bbox: Iterable[float] | None = None,
    require_website: bool = True,
    require_phone: bool = True,
    limit: int = 50,
    timeout: float = 90.0,
) -> dict[str, Any]:
    bbox_t = tuple(bbox) if bbox else None
    if bbox_t is not None and len(bbox_t) != 4:
        return {"error": True, "mensaje": "bbox debe tener 4 valores [sur,oeste,norte,este]"}

    try:
        query = _build_query(
            bbox=bbox_t,
            area_name=area_name,
            category=category,
            require_website=require_website,
            require_phone=require_phone,
            limit=limit,
        )
    except ValueError as exc:
        return {"error": True, "mensaje": str(exc)}

    data = await _post_query(query, timeout=timeout)
    if data is None:
        return {
            "error": True,
            "mensaje": "Los servidores Overpass públicos no respondieron. Vuelve a intentarlo.",
        }

    elements = data.get("elements") or []
    leads = [_normalise(e) for e in elements if (e.get("tags") or {}).get("name")]
    return {
        "error": False,
        "count": len(leads),
        "source": "openstreetmap",
        "category": category,
        "leads": leads,
    }
