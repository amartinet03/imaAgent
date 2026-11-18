import re

def get_clean_client_slug(cliente: str, max_length: int = 25) -> str:
    """
    Sanitiza y acorta el nombre del cliente para nombres de archivo limpios.
    Evita nombres de archivo gigantes cuando la IA incluye aclaraciones en el campo cliente.
    Ej: 'DREAN S.A. (grupo Mabe). El pliego también menciona a KRONEN...' -> 'DREAN_S_A'
    """
    if not cliente:
        return "Cliente"
    
    c = str(cliente).split('\n')[0].strip()
    # Remover aclaraciones entre paréntesis
    c_clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', c).strip()
    
    # Cortar en oraciones explicativas posteriores (ej: ". El pliego...")
    parts = c_clean.split('. ')
    first_part = parts[0].strip()
    
    slug = re.sub(r'[^A-Za-z0-9]+', '_', first_part).strip('_')
    final_slug = slug[:max_length].strip('_')
    return final_slug if final_slug else "Cliente"

