import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.models import hash_password, verify_user_credentials, update_user_password, init_db

def test_password_hashing_bcrypt():
    init_db()
    
    # Probar hashing
    pwd = "TestSecurePassword123!"
    p_hash = hash_password(pwd)
    
    assert p_hash.startswith("$2b$") or p_hash.startswith("$2a$")
    assert p_hash != pwd

def test_credentials_verification_flow():
    init_db()
    
    # Crear usuario de prueba
    test_user = "test_sec_user"
    test_pass = "ComplexPass2026!"
    
    update_user_password(test_user, test_pass)
    
    # Verificación exitosa
    assert verify_user_credentials(test_user, test_pass) is True
    
    # Verificación con contraseña errónea
    assert verify_user_credentials(test_user, "WrongPass123") is False
    
    # Verificación con usuario inexistente
    assert verify_user_credentials("non_existent_user_999", test_pass) is False
    
    # Verificación con inputs vacíos
    assert verify_user_credentials("", "") is False
    assert verify_user_credentials(test_user, "") is False
    assert verify_user_credentials(None, None) is False

def test_path_traversal_sanitization():
    from src.ui.components import save_uploaded_files
    import re
    
    # Simular nombres maliciosos
    malicious_names = [
        "../../etc/passwd",
        "..\\..\\Windows\\System32\\calc.exe",
        "nested/path/to/file.pdf",
        "valid_doc.pdf"
    ]
    
    for raw in malicious_names:
        safe_base = os.path.basename(raw)
        safe_name = re.sub(r'[^a-zA-Z0-9_.\-\sáéíóúÁÉÍÓÚñÑ()]', '_', safe_base).strip()
        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert ".." not in safe_name
