import base64
import os
import streamlit as st
from src.db.models import verify_user_credentials


def get_base64_image(image_path: str) -> str:
    """Lee una imagen local y la devuelve como cadena base64."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


def clean_html_str(html_multiline: str) -> str:
    """Elimina sangrías y saltos de línea para que Streamlit/Markdown nunca genere bloques de código <pre><code>."""
    return "".join(line.strip() for line in html_multiline.strip().splitlines())


def render_login_page():
    """
    Renderiza la pantalla de inicio de sesión con diseño split-screen parejo,
    con la imagen extendida a la izquierda y el formulario centrado y bajado en la sección blanca.
    """
    hero_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "login_hero.jpg")
    hero_b64 = get_base64_image(hero_path)

    # 1. CSS de estructura precisa, reseteo de márgenes y centrado perfecto
    css_rules = f"""
    <style>
    /* Ocultar barra lateral, cabecera, toolbar y footer */
    [data-testid="stSidebar"] {{
        display: none !important;
    }}
    header, [data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu {{
        display: none !important;
    }}

    /* Reseteo total del viewport */
    html, body, .stApp {{
        background-color: #FFFFFF !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 100vh !important;
        max-height: 100vh !important;
        width: 100vw !important;
        max-width: 100vw !important;
        overflow: hidden !important;
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    }}

    /* Neutralizar contenedores internos de Streamlit para pantalla completa */
    .stApp [data-testid="stAppViewContainer"],
    .stApp section.main,
    .stApp .block-container,
    .stApp [data-testid="stMainBlockContainer"] {{
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100vw !important;
        width: 100vw !important;
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
    }}

    .block-container > [data-testid="stVerticalBlock"] {{
        height: 100vh !important;
        min-height: 100vh !important;
        gap: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }}

    /* Bloque horizontal de dos columnas principales (Hero 38% / Form 62%) */
    .block-container > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {{
        height: 100vh !important;
        min-height: 100vh !important;
        width: 100vw !important;
        max-width: 100vw !important;
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
        align-items: stretch !important;
    }}

    /* --- COLUMNA 1: HERO INDUSTRIAL (38% WIDTH) --- */
    .block-container > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-of-type(1) {{
        flex: 3.8 1 0% !important;
        width: 38vw !important;
        max-width: 38vw !important;
        min-width: 380px !important;
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
        background-color: #081020 !important;
    }}

    .block-container > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-of-type(1) > div,
    .block-container > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-of-type(1) [data-testid="stVerticalBlock"] {{
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
        padding: 0 !important;
        margin: 0 !important;
        gap: 0 !important;
        overflow: hidden !important;
    }}

    /* --- COLUMNA 2: SECCIÓN DERECHA BLANCA (62% WIDTH) --- */
    .block-container > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-of-type(2) {{
        flex: 6.2 1 0% !important;
        width: 62vw !important;
        height: 100vh !important;
        min-height: 100vh !important;
        max-height: 100vh !important;
        padding: 0 !important;
        margin: 0 !important;
        background-color: #FFFFFF !important;
        position: relative !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }}

    /* Formulario nativo limpio sin bordes */
    div[data-testid="stForm"] {{
        border: none !important;
        padding: 0 !important;
        background: transparent !important;
        width: 100% !important;
    }}

    /* Etiquetas de campos */
    div[data-testid="stTextInput"] {{
        margin-bottom: 12px !important;
    }}

    div[data-testid="stTextInput"] label {{
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        margin-bottom: 5px !important;
    }}

    /* Resetear contenedor interno base-input para evitar duplicación de bordes */
    div[data-testid="stTextInput"] div[data-baseweb="base-input"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        height: 100% !important;
    }}

    /* Contenedor exterior ÚNICO con borde, fondo y dimensiones limpias */
    div[data-testid="stTextInput"] div[data-baseweb="input"] {{
        background-color: #F8FAFC !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 8px !important;
        padding: 0 12px !important;
        height: 44px !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }}

    /* Foco en el contenedor único */
    div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {{
        border-color: #0066FF !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.12) !important;
    }}

    /* Elemento <input> interno transparente, sin bordes duplicados ni recortes */
    div[data-testid="stTextInput"] input {{
        background: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        color: #0F172A !important;
        font-size: 0.94rem !important;
        height: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }}

    /* Botón del ojo para mostrar/ocultar contraseña limpio e integrado */
    div[data-testid="stTextInputPasswordToggle"] {{
        background: transparent !important;
    }}
    div[data-testid="stTextInputPasswordToggle"] button {{
        background: transparent !important;
        border: none !important;
        color: #64748B !important;
    }}

    /* Ocultar texto superpuesto "Press Enter to submit form" */
    div[data-testid="InputInstructions"],
    div[data-testid="stTextInput"] div:has(> [data-testid="InputInstructions"]),
    div[data-testid="stFormSubmitInstructions"] {{
        display: none !important;
    }}

    /* Botón azul corporativo vibrante */
    div[data-testid="stForm"] button[kind="primary"] {{
        background: #0066FF !important;
        background: linear-gradient(135deg, #0066FF 0%, #0052CC 100%) !important;
        border-radius: 8px !important;
        border: none !important;
        height: 46px !important;
        width: 100% !important;
        box-shadow: 0 4px 14px rgba(0, 102, 255, 0.28) !important;
        transition: all 0.2s ease !important;
        margin-top: 10px !important;
    }}

    div[data-testid="stForm"] button[kind="primary"] * {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }}

    div[data-testid="stForm"] button[kind="primary"]:hover {{
        background: #0052CC !important;
        box-shadow: 0 6px 20px rgba(0, 102, 255, 0.40) !important;
        transform: translateY(-1px) !important;
    }}
    </style>
    """
    st.markdown(clean_html_str(css_rules), unsafe_allow_html=True)

    # 2. Split Screen: 38% Hero / 62% Formulario
    col_hero, col_form = st.columns([3.8, 6.2], gap="small")

    # --- PANEL IZQUIERDO: HERO CORPORATIVO ---
    with col_hero:
        hero_html = f"""
        <div style="height: 100vh; width: 100%; position: relative; padding: 48px 36px; box-sizing: border-box; overflow: hidden; background: linear-gradient(180deg, rgba(8, 16, 32, 0.90) 0%, rgba(8, 16, 32, 0.35) 42%, rgba(8, 16, 32, 0.90) 100%), url('data:image/jpeg;base64,{hero_b64}') center/cover no-repeat;">
            <div style="position: absolute; left: 0; bottom: 130px; width: 45px; height: 120px; background: #DC2626; clip-path: polygon(0 0, 100% 50%, 0 100%); z-index: 1;"></div>
            <div style="position: absolute; right: 0; bottom: 50px; width: 55px; height: 140px; background: rgba(220, 38, 38, 0.50); clip-path: polygon(100% 0, 0 50%, 100% 100%); z-index: 1;"></div>
            <div style="position: relative; z-index: 3; max-width: 320px;">
                <div style="margin-bottom: 30px;">
                    <div style="font-size: 3rem; font-weight: 900; color: #FFFFFF; letter-spacing: -2px; line-height: 0.9;"><span style="color: #DC2626;">i</span>ma</div>
                    <div style="color: #94A3B8; font-size: 0.88rem; font-weight: 500; margin-top: 5px; letter-spacing: 0.2px;">Servicios Industriales</div>
                </div>
                <div style="color: #FFFFFF; font-size: 1.15rem; font-weight: 600; line-height: 1.45; margin-bottom: 32px; letter-spacing: -0.2px;">
                    Conectamos oportunidades,<br>impulsamos tus proyectos.
                </div>
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div style="display: flex; align-items: center; gap: 10px; color: #CBD5E1; font-size: 0.88rem; font-weight: 500;"><span style="color: #64748B; font-size: 1.05rem; width: 18px;">⚡</span><span>Licitaciones y proyectos</span></div>
                    <div style="display: flex; align-items: center; gap: 10px; color: #CBD5E1; font-size: 0.88rem; font-weight: 500;"><span style="color: #64748B; font-size: 1.05rem; width: 18px;">👥</span><span>Profesionales y empresas</span></div>
                    <div style="display: flex; align-items: center; gap: 10px; color: #CBD5E1; font-size: 0.88rem; font-weight: 500;"><span style="color: #64748B; font-size: 1.05rem; width: 18px;">🛡️</span><span>Servicios industriales</span></div>
                </div>
            </div>
        </div>
        """
        st.markdown(clean_html_str(hero_html), unsafe_allow_html=True)

    # --- PANEL DERECHO: FORMULARIO PERFECTAMENTE CENTRADO Y BAJADO ---
    with col_form:
        # 1. Watermark decorativo en la esquina superior derecha
        watermark_html = """
        <div style="position: absolute; top: 0; right: 0; width: 340px; height: 340px; pointer-events: none; opacity: 0.75; z-index: 0; overflow: hidden;">
            <svg width="340" height="340" viewBox="0 0 340 340">
                <rect x="210" y="-80" width="70" height="340" rx="35" transform="rotate(45 210 -80)" fill="#F1F5F9" />
                <rect x="320" y="-40" width="70" height="340" rx="35" transform="rotate(45 320 -40)" fill="#F1F5F9" />
            </svg>
        </div>
        """
        st.markdown(clean_html_str(watermark_html), unsafe_allow_html=True)

        # 2. Espaciador vertical dedicado para bajar el componente al centro vertical de la pantalla
        st.markdown('<div style="height: 12vh; min-height: 85px; width: 100%;"></div>', unsafe_allow_html=True)

        # 3. Sub-columnas con simetría exacta: 1.2 izquierda, 3.8 centro, 1.2 derecha
        # Esto garantiza que el formulario esté rigurosamente centrado en la sección blanca.
        c_l, c_center, c_r = st.columns([1.2, 3.8, 1.2])

        with c_center:
            # Encabezado corporativo
            header_html = """
            <div style="width: 100%; margin-bottom: 22px;">
                <div style="width: 36px; height: 5px; background: #DC2626; border-radius: 3px; margin-bottom: 22px;"></div>
                <h1 style="font-size: 2.1rem; font-weight: 800; color: #0F172A; margin: 0 0 8px 0; letter-spacing: -0.6px; line-height: 1.15;">Acceso Restringido</h1>
                <p style="font-size: 0.92rem; color: #64748B; line-height: 1.45; margin: 0;">Plataforma de IA para Gestión de Licitaciones -<br>IMA Servicios Industriales</p>
            </div>
            """
            st.markdown(clean_html_str(header_html), unsafe_allow_html=True)

            # Formulario de Acceso
            with st.form("login_form"):
                user = st.text_input("👤 Usuario", placeholder="Ingresá tu usuario", key="input_user")
                password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresá tu contraseña", key="input_pass")
                submit = st.form_submit_button("Ingresar →", type="primary", use_container_width=True)

                if submit:
                    if verify_user_credentials(user.strip(), password):
                        st.session_state['authenticated'] = True
                        st.session_state['current_user'] = user.strip()
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas.")

            # Divisor de ayuda y soporte corporativo limpio
            divider_html = """
            <div style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 22px; margin-bottom: 8px;">
                <span style="flex: 1; height: 1px; background: #E2E8F0;"></span>
                <span style="color: #94A3B8; font-size: 0.82rem; font-weight: 500;">¿Tenés problemas para ingresar?</span>
                <span style="flex: 1; height: 1px; background: #E2E8F0;"></span>
            </div>
            <div style="width: 100%; text-align: center; color: #94A3B8; font-size: 0.76rem; line-height: 1.4;">
                Soporte IT: <strong>soporte.sistemas@ima.com.ar</strong> | Interno 402
            </div>
            """
            st.markdown(clean_html_str(divider_html), unsafe_allow_html=True)
