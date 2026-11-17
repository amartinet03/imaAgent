import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.analyzer import analyze_full_tender
from langchain_core.documents import Document

def test_extract_json_golden_dataset():
    # Simulamos un Pliego Dorado (Golden Dataset)
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
    
    mock_response = MagicMock()
    mock_response.content = '''```json
    {
        "metadata": {
            "cliente": "Empresa X S.A.",
            "moneda": "USD",
            "proceso": "Licitación 2026-001",
            "nombre_pliego": "Servicios de Mantenimiento"
        },
        "consultas_generales": [
            {
                "categoria": "Operativa",
                "archivo_origen": "Pliego_Golden.pdf",
                "pagina_origen": "1",
                "cita_textual": "proveer andamios",
                "consulta": "Se consulta tipo de andamio"
            }
        ],
        "inconsistencias": [
            {
                "tipo": "Contradicción",
                "documentos_conflicto": ["Pliego_Golden.pdf"],
                "pagina_origen": "1",
                "cita_textual": "proveer andamios",
                "descripcion_pregunta": "Aclarar alcance"
            }
        ],
        "tecnicos": {
            "alcance_general": "Provisión de andamios y servicios"
        },
        "costos": {
            "plazo_contrato_meses": 12
        }
    }
    ```'''
    
    with patch("src.core.analyzer.invoke_with_retry", return_value=mock_response):
        parsed_data = analyze_full_tender(docs)
        
        assert isinstance(parsed_data, dict)
        assert "error" not in parsed_data
        assert "metadata" in parsed_data
        
        meta = parsed_data["metadata"]
        assert "Empresa X S.A." in meta.get("cliente", "")
        assert "USD" in meta.get("moneda", "")
        
        # Validamos consultas e inconsistencias
        assert "consultas_generales" in parsed_data
        assert "inconsistencias" in parsed_data
        
        c = parsed_data["consultas_generales"][0]
        assert "categoria" in c
        assert "archivo_origen" in c
        assert "pagina_origen" in c
        assert "cita_textual" in c
        
        i = parsed_data["inconsistencias"][0]
        assert "tipo" in i
        assert "documentos_conflicto" in i
        assert "pagina_origen" in i
        assert "cita_textual" in i
