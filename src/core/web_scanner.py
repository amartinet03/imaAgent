import re
import urllib3
import requests
from src.db.models import (
    get_monitored_portals,
    get_monitored_keywords,
    save_radar_opportunity,
    update_portal_scanned_time
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8'
}


class WebTenderScanner:
    """
    Motor de rastreo y extracción proactiva de licitaciones públicas en portales oficiales.
    """
    def __init__(self):
        self.headers = DEFAULT_HEADERS

    def _fetch_page(self, url: str) -> str:
        try:
            response = requests.get(url, headers=self.headers, timeout=15, verify=False)
            if response.status_code == 200:
                return response.text
            return ""
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def _check_keywords(self, text: str, keywords: list) -> list:
        text_lower = text.lower()
        matched = []
        for kw in keywords:
            kw_clean = kw.strip().lower()
            if kw_clean and kw_clean in text_lower:
                matched.append(kw_clean)
        return list(set(matched))

    def scan_nasa(self, portal_info: dict, keywords: list) -> list:
        url = portal_info.get("url", "https://www.na-sa.com.ar/proveedores/home/licitaciones/vigentes")
        portal_name = portal_info.get("name", "NA-SA")
        html = self._fetch_page(url)
        if not html:
            return []

        opportunities = []
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
        for row in rows:
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)]
            if len(cells) >= 4:
                expediente = cells[0]
                descripcion = cells[1]
                tipo = cells[2]
                apertura = cells[3]

                full_text = f"{descripcion} {tipo}"
                matched = self._check_keywords(full_text, keywords)
                if matched:
                    title = f"{tipo}: {descripcion} (Exp. {expediente})"
                    snippet = f"Apertura: {apertura} | Expediente: {expediente} | Tipo: {tipo}"
                    opportunities.append({
                        "portal_name": portal_name,
                        "title": title,
                        "url": url,
                        "matched_keywords": ", ".join(matched),
                        "snippet": snippet
                    })
        return opportunities

    def scan_arsat(self, portal_info: dict, keywords: list) -> list:
        url = portal_info.get("url", "https://www.arsat.com.ar/acerca-de-arsat/transparencia-activa/compras-y-contrataciones/")
        portal_name = portal_info.get("name", "ARSAT")
        html = self._fetch_page(url)
        if not html:
            return []

        opportunities = []
        # Buscar bloques o encabezados con llamados a licitación
        links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        
        current_tender_title = None
        current_docs = []

        for href, text in links:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if not clean_text:
                continue

            # Detectar título de licitación
            if any(k in clean_text.lower() for k in ["licitación", "licitacion", "concurso", "contratación", "contratacion"]):
                matched = self._check_keywords(clean_text, keywords)
                if matched:
                    current_tender_title = clean_text
                    target_url = href if href.startswith("http") else url
                    snippet = f"Detectado en ARSAT Compras. Publicación oficial: {target_url}"
                    opportunities.append({
                        "portal_name": portal_name,
                        "title": current_tender_title,
                        "url": target_url,
                        "matched_keywords": ", ".join(matched),
                        "snippet": snippet
                    })

        return opportunities

    def scan_generic(self, portal_info: dict, keywords: list) -> list:
        url = portal_info.get("url", "")
        portal_name = portal_info.get("name", "Portal Web")
        html = self._fetch_page(url)
        if not html:
            return []

        opportunities = []
        # Buscar en enlaces y textos
        links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        for href, text in links:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if len(clean_text) > 15:
                matched = self._check_keywords(clean_text, keywords)
                if matched:
                    full_url = href if href.startswith("http") else f"{url.rstrip('/')}/{href.lstrip('/')}"
                    opportunities.append({
                        "portal_name": portal_name,
                        "title": clean_text[:180],
                        "url": full_url,
                        "matched_keywords": ", ".join(matched),
                        "snippet": f"Detectado mediante rastreo web en {portal_name}"
                    })

        return opportunities

    def scan_all_portals(self) -> dict:
        """
        Ejecuta el escaneo en todos los portales activos configurados,
        evalúa contra las palabras clave y guarda las nuevas oportunidades.
        """
        portals = [p for p in get_monitored_portals() if p.get("active", 1)]
        keywords = [k["keyword"] for k in get_monitored_keywords()]

        total_scanned = len(portals)
        new_detected_count = 0
        all_found = []

        for portal in portals:
            p_name = portal.get("name", "").upper()
            p_url = portal.get("url", "")

            if "NA-SA" in p_name or "NUCLEO" in p_name:
                found = self.scan_nasa(portal, keywords)
            elif "ARSAT" in p_name:
                found = self.scan_arsat(portal, keywords)
            else:
                found = self.scan_generic(portal, keywords)

            for opp in found:
                opp_id = save_radar_opportunity(
                    portal_name=opp["portal_name"],
                    title=opp["title"],
                    url=opp["url"],
                    matched_keywords=opp["matched_keywords"],
                    snippet=opp.get("snippet", "")
                )
                if opp_id:
                    new_detected_count += 1
                all_found.append(opp)

            update_portal_scanned_time(portal["id"])

        return {
            "total_portals_scanned": total_scanned,
            "new_detected_count": new_detected_count,
            "total_found": len(all_found),
            "items": all_found
        }
