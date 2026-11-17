import re
import datetime
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

CLOSED_WORDS = [
    "cerrada", "cerrado", "adjudicada", "adjudicado", "desierta", "desierto",
    "cancelada", "cancelado", "finalizada", "finalizado", "preadjudicada", "preadjudicado",
    "pre-adjudicada", "pre-adjudicado", "suspendida", "suspendido", "vencida", "vencido",
    "archivada", "archivado", "anulada", "anulado", "sin efecto", "dejar sin efecto",
    "dada de baja", "baja", "histórico", "historico", "histórica", "historica"
]


class WebTenderScanner:
    """
    Motor inteligente de rastreo y extracción proactiva de licitaciones públicas en portales oficiales.
    """
    def __init__(self):
        self.headers = DEFAULT_HEADERS

    def _fetch_page(self, url: str) -> str:
        try:
            response = requests.get(url, headers=self.headers, timeout=20, verify=False)
            if response.status_code == 200:
                return response.text
            return ""
        except Exception as e:
            print(f"[Radar Error] Error accediendo a {url}: {e}")
            return ""

    def _is_valid_tender(self, text: str, url: str = "") -> bool:
        if not text:
            return False

        current_year = datetime.datetime.now().year
        text_lower = text.lower()
        combo = f"{text_lower} {url.lower()}"

        # 1. Excluir licitaciones cerradas, desiertas, canceladas o adjudicadas
        for cw in CLOSED_WORDS:
            if re.search(r'\b' + re.escape(cw) + r's?\b', text_lower):
                return False

        # 2. Análisis del año (4 dígitos)
        years_found = [int(y) for y in re.findall(r'\b(20[1-3][0-9])\b', combo)]
        if years_found:
            if all(y < current_year for y in years_found) and current_year not in years_found:
                return False
            if any(y >= current_year for y in years_found):
                return True

        # 3. Análisis de años cortos en expedientes (ej. /20, /21, /24, /25 vs /26)
        short_past_pattern = r'[/–-](1[5-9]|2[0-5])\b'
        current_short = str(current_year)[2:]
        if re.search(short_past_pattern, text):
            if not re.search(r'[/–-]' + current_short + r'\b', text):
                return False

        # 4. Si el portal o texto especifica fecha DD/MM/AAAA
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-](20\d{2})\b', text)
        if dates:
            date_years = [int(dy) for dy in dates]
            if all(dy < current_year for dy in date_years):
                return False
            if any(dy >= current_year for dy in date_years):
                return True

        return current_year in years_found or str(current_year) in text

    def _matches_keyword(self, kw: str, text: str) -> bool:
        kw = kw.strip().lower()
        if not kw:
            return False
        pattern = r'\b' + re.escape(kw) + r'(?:s|es)?\b'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _check_keywords(self, text: str, keywords: list, url: str = "") -> list:
        if not self._is_valid_tender(text, url):
            return []

        matched = []
        for kw in keywords:
            if self._matches_keyword(kw, text):
                matched.append(kw.strip().lower())
        return sorted(list(set(matched)))

    def scan_nasa(self, portal_info: dict, keywords: list) -> list:
        url = portal_info.get("url", "https://www.na-sa.com.ar/proveedores/home/licitaciones/vigentes")
        portal_name = portal_info.get("name", "NA-SA")
        html = self._fetch_page(url)
        if not html:
            return []

        opportunities = []
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
        for row in rows:
            cells = [re.sub(r'<[^>]+>', ' ', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)]
            if len(cells) >= 4:
                expediente = ' '.join(cells[0].split())
                descripcion = ' '.join(cells[1].split())
                tipo = ' '.join(cells[2].split())
                apertura = ' '.join(cells[3].split())

                full_text = f"{tipo} {descripcion} Expediente {expediente} Apertura {apertura}"
                matched = self._check_keywords(full_text, keywords, url)
                if matched:
                    title = f"{tipo}: {descripcion} (Exp. {expediente})"
                    snippet = f"Apertura: {apertura} | Expediente: {expediente} | Tipo: {tipo}"
                    opportunities.append({
                        "portal_name": portal_name,
                        "title": title[:200],
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
        seen_titles = set()

        headings = re.findall(r'<h[2-5][^>]*>(.*?)</h[2-5]>', html, re.DOTALL | re.IGNORECASE)
        for h in headings:
            clean_title = re.sub(r'<[^>]+>', ' ', h).strip()
            clean_title = ' '.join(clean_title.split())
            if not clean_title or clean_title.lower() in seen_titles:
                continue

            if any(k in clean_title.lower() for k in ["licitación", "licitacion", "concurso", "contratación", "contratacion"]):
                matched = self._check_keywords(clean_title, keywords, url)
                if matched:
                    seen_titles.add(clean_title.lower())
                    opportunities.append({
                        "portal_name": portal_name,
                        "title": clean_title[:200],
                        "url": url,
                        "matched_keywords": ", ".join(matched),
                        "snippet": f"Publicación en ARSAT Compras: {clean_title}"
                    })

        links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        for href, text in links:
            clean_text = re.sub(r'<[^>]+>', ' ', text).strip()
            clean_text = ' '.join(clean_text.split())
            if not clean_text or clean_text.lower() in seen_titles:
                continue

            if any(k in clean_text.lower() for k in ["licitación", "licitacion", "concurso", "contratación", "contratacion"]):
                matched = self._check_keywords(clean_text, keywords, href)
                if matched:
                    seen_titles.add(clean_text.lower())
                    target_url = href if href.startswith("http") else url
                    opportunities.append({
                        "portal_name": portal_name,
                        "title": clean_text[:200],
                        "url": target_url,
                        "matched_keywords": ", ".join(matched),
                        "snippet": f"Detectado en ARSAT Transparencia Activa: {clean_text}"
                    })

        return opportunities

    def scan_generic(self, portal_info: dict, keywords: list) -> list:
        url = portal_info.get("url", "")
        portal_name = portal_info.get("name", "Portal Web")
        html = self._fetch_page(url)
        if not html:
            return []

        opportunities = []
        seen_titles = set()

        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
        for row in rows:
            clean_row = re.sub(r'<[^>]+>', ' ', row).strip()
            clean_row = ' '.join(clean_row.split())
            if len(clean_row) > 20:
                matched = self._check_keywords(clean_row, keywords, url)
                if matched:
                    title_candidate = clean_row[:180]
                    if title_candidate.lower() not in seen_titles:
                        seen_titles.add(title_candidate.lower())
                        opportunities.append({
                            "portal_name": portal_name,
                            "title": title_candidate,
                            "url": url,
                            "matched_keywords": ", ".join(matched),
                            "snippet": f"Detectado mediante rastreo en tabla de {portal_name}: {clean_row[:120]}..."
                        })

        links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        for href, text in links:
            clean_text = re.sub(r'<[^>]+>', ' ', text).strip()
            clean_text = ' '.join(clean_text.split())
            if len(clean_text) > 15 and clean_text.lower() not in seen_titles:
                matched = self._check_keywords(clean_text, keywords, href)
                if matched:
                    seen_titles.add(clean_text.lower())
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
        all_portals = get_monitored_portals()
        portals = [
            p for p in all_portals
            if str(p.get("active", 1)).lower() in ("1", "true")
        ]

        raw_keywords = get_monitored_keywords()
        keywords = [k["keyword"].strip() for k in raw_keywords if k.get("keyword", "").strip()]

        if not keywords:
            print("[Radar Web] No hay palabras clave activas configuradas. Escaneo cancelado.")
            return {
                "total_portals_scanned": 0,
                "new_detected_count": 0,
                "total_found": 0,
                "items": []
            }

        total_scanned = len(portals)
        new_detected_count = 0
        all_found = []

        for portal in portals:
            p_name = portal.get("name", "").upper()
            p_url = portal.get("url", "")

            try:
                if "NA-SA" in p_name or "NUCLEO" in p_name:
                    found = self.scan_nasa(portal, keywords)
                elif "ARSAT" in p_name:
                    found = self.scan_arsat(portal, keywords)
                else:
                    found = self.scan_generic(portal, keywords)
            except Exception as e:
                print(f"[Radar Error] Error escaneando portal {p_name} ({p_url}): {e}")
                found = []

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
