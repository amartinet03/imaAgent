import streamlit as st


def apply_theme():
    """
    Aplica el tema visual corporativo de IMA.
    Distingue entre la vista de Login (pantalla completa sin márgenes)
    y el Dashboard autenticado.
    """
    is_auth = st.session_state.get('authenticated', False)

    container_rules = """
        .stApp .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            max-width: 95% !important;
        }
    """ if is_auth else """
        .stApp .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
            width: 100% !important;
        }
    """

    base_css = """
        <style>
        /* Importar fuente Inter */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Ocultar elementos de Streamlit */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header { visibility: hidden; } /* Oculta la barra superior default */
        
        /* Paleta y Fondos */
        :root {
            --sidebar-bg: #1C2E4A; /* Azul corporativo */
            --main-bg: #F8FAFC;    /* Gris muy claro */
            --primary-blue: #2563EB;
            --success-green: #10B981;
            --warning-yellow: #F59E0B;
            --card-border: #E2E8F0;
            --text-main: #0F172A;
            --text-muted: #64748B;
        }
        
        .stApp {
            background-color: var(--main-bg);
        }
    """

    after_css = """
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg);
            color: white;
            border-right: none;
            min-width: 250px !important;
            max-width: 250px !important;
        }
        [data-testid="stSidebar"] * {
            color: #E2E8F0 !important;
        }
        /* Resaltar botones del sidebar para que parezcan menú */
        [data-testid="stSidebar"] .stButton button {
            background-color: transparent !important;
            border: none !important;
            justify-content: flex-start !important;
            padding-left: 20px;
            font-weight: 500;
            border-radius: 8px;
            transition: all 0.2s;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background-color: rgba(255,255,255,0.1) !important;
        }
        /* Título del sidebar imitando logo IMA */
        [data-testid="stSidebar"] h1 {
            color: white !important;
            font-size: 2rem !important;
            font-weight: 800 !important;
            letter-spacing: -1px;
            margin-bottom: 0px;
        }
        [data-testid="stSidebar"] .stCaption {
            color: #94A3B8 !important;
            font-size: 0.75rem !important;
        }

        /* Botones Primarios */
        .stButton button[kind="primary"] {
            background-color: var(--primary-blue) !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 0.5rem 1rem;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
            transition: all 0.2s;
        }
        .stButton button[kind="primary"] * {
            color: white !important;
            font-weight: 600 !important;
        }
        .stButton button[kind="primary"]:hover {
            background-color: #1D4ED8 !important;
            box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
            transform: translateY(-1px);
        }

        /* Tabs (Pestañas) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 30px;
            border-bottom: 1px solid var(--card-border);
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 0;
            gap: 8px;
            padding-top: 10px;
            padding-bottom: 10px;
            font-weight: 600;
            color: var(--text-muted);
        }
        .stTabs [aria-selected="true"] {
            color: var(--primary-blue) !important;
            background-color: transparent !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: var(--primary-blue) !important;
        }
        
        /* Contenedores (Cards) */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column"] > [data-testid="stVerticalBlock"] {
            background-color: white;
            border-radius: 12px;
            border: 1px solid var(--card-border);
            padding: 1.5rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        }

        /* Títulos */
        h1, h2, h3 {
            color: var(--text-main) !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em;
        }
        p {
            color: var(--text-muted);
        }
        
        /* Ajustar alertas (Notification) */
        .stAlert {
            border-radius: 8px;
            border: 1px solid #BFDBFE;
            background-color: #EFF6FF;
            color: #1E3A8A;
        }
        
        /* Chat Input styling */
        .stChatInputContainer {
            border-radius: 12px !important;
            border: 1px solid var(--card-border) !important;
        }

        /* Ocultar instrucciones flotantes en inputs como 'Press Enter to submit form' */
        div[data-testid="InputInstructions"],
        div[data-testid="stFormSubmitInstructions"] {
            display: none !important;
        }
        </style>
    """

    st.markdown(base_css + container_rules + after_css, unsafe_allow_html=True)


def render_metric_card(title, value, subtitle, icon_html, is_online=False):
    """
    Renderiza una tarjeta de métrica usando HTML inyectado.
    """
    online_style = "color: #10B981;" if is_online else "color: #2563EB;"
    st.markdown(f"""
        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); height: 100%;">
            <div style="background: #F1F5F9; width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px;">
                {icon_html}
            </div>
            <div>
                <div style="font-size: 13px; color: #64748B; font-weight: 600; margin-bottom: 2px;">{title}</div>
                <div style="font-size: 24px; font-weight: 700; color: #0F172A; line-height: 1.2;">{value}</div>
                <div style="font-size: 12px; {online_style} font-weight: 500; margin-top: 2px;">{subtitle}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def get_progress_bar_html(percentage, status):
    color = "#10B981" if status == "COMPLETADO" else "#2563EB" if status == "PROCESANDO" else "#EF4444"
    return f"""
        <div style="display: flex; align-items: center; gap: 10px; width: 100%;">
            <div style="flex-grow: 1; height: 6px; background: #E2E8F0; border-radius: 3px; overflow: hidden;">
                <div style="width: {percentage}%; height: 100%; background: {color}; border-radius: 3px;"></div>
            </div>
            <span style="font-size: 12px; font-weight: 600; color: #64748B;">{percentage}%</span>
        </div>
    """


def get_status_badge(status):
    if status == 'COMPLETADO':
        return '<div style="color: #10B981; font-weight: 600; font-size: 13px; margin-bottom: -4px;">● COMPLETADO</div><div style="font-size:11px;color:#94A3B8;">Proceso finalizado</div>'
    elif status == 'PROCESANDO':
        return '<div style="color: #F59E0B; font-weight: 600; font-size: 13px; margin-bottom: -4px;">● EN PROCESO</div><div style="font-size:11px;color:#94A3B8;">Extrayendo datos</div>'
    else:
        return f'<div style="color: #EF4444; font-weight: 600; font-size: 13px;">● {status}</div>'


def render_version_table_header():
    st.markdown("""
        <div style="display: grid; grid-template-columns: 2fr 1.5fr 2fr 1fr; gap: 10px; padding: 10px 15px; border-bottom: 2px solid #E2E8F0; font-size: 12px; font-weight: 600; color: #64748B; margin-top: 10px;">
            <div>Versión</div>
            <div>Estado</div>
            <div>Fecha</div>
            <div style="text-align: right;">Acciones</div>
        </div>
    """, unsafe_allow_html=True)


def render_info_list_item(icon, title, content):
    st.markdown(f"""
        <div style="display: flex; gap: 12px; margin-bottom: 20px;">
            <div style="color: #64748B; font-size: 18px; margin-top: 2px;">{icon}</div>
            <div>
                <div style="font-size: 13px; font-weight: 600; color: #0F172A; margin-bottom: 4px;">{title}</div>
                <div style="font-size: 13px; color: #2563EB;">{content}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
