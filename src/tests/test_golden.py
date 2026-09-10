import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.outputs.query_generator import QueryGenerator
from langchain_core.documents import Document

def test_extract_json_golden_dataset():
    # Simulamos un Pliego Dorado (Golden Dataset) con ambigüedades insertadas a propósito
    golden_text = """
    --- [Página 1] ---
    PLIEGO DE BASES Y CONDICIONES
    Cliente: Empresa X S.A.
    Proceso: Licitación 2026-001
    Moneda: USD

    1. El contratista deberá proveer andamios.
    2. La multa por atraso es del 1% diario.
    3. El cliente proveerá el agua, pero la electricidad corre por cuenta del contratista.
    """
    
    docs = [Document(page_content=golden_text, metadata={"source": "Pliego_Golden.pdf"})]
    
    gen = QueryGenerator()
    parsed_data = gen.extract_json_with_llm(docs)
    
    assert "error" not in parsed_data
    assert "metadata" in parsed_data
    
    meta = parsed_data["metadata"]
    assert "Empresa X S.A." in meta.get("cliente", "")
    assert "USD" in meta.get("moneda", "")
    
    # Validamos que se detecten consultas/inconsistencias
    assert "consultas_generales" in parsed_data
    assert "inconsistencias" in parsed_data
    
    # Verificamos estructura y trazabilidad (Citation Tracking)
    if parsed_data["consultas_generales"]:
        c = parsed_data["consultas_generales"][0]
        assert "categoria" in c
        assert "archivo_origen" in c
        assert "pagina_origen" in c
        assert "cita_textual" in c
        
    if parsed_data["inconsistencias"]:
        i = parsed_data["inconsistencias"][0]
        assert "tipo" in i
        assert "documentos_conflicto" in i
        assert "pagina_origen" in i
        assert "cita_textual" in i
