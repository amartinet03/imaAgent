import os
import streamlit as st
from src.db.models import (
    get_monitored_portals,
    add_monitored_portal,
    delete_monitored_portal,
    toggle_monitored_portal,
    get_monitored_keywords,
    add_monitored_keyword,
    delete_monitored_keyword,
    get_all_opportunities,
    update_opportunity_status,
    create_tender,
    verify_user_credentials,
    update_user_password
)
from src.core.web_scanner import WebTenderScanner


def render_view_configuracion(launch_worker_callback=None):
    """
    Pantalla de Configuración y Gestión del Radar de Licitaciones Web.
    Permite administrar los sitios web monitoreados, palabras clave de interés,
    forzar escaneos y revisar el historial de oportunidades detectadas.
    """
    st.markdown("<h1>⚙️ Configuración y Radar de Licitaciones</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color: #64748B; font-size: 1.05rem; margin-top: -10px; margin-bottom: 25px;'>"
        "Monitoreo proactivo de portales públicos de compras y licitaciones sin aviso de clientes.</p>",
        unsafe_allow_html=True
    )

    tab_portales, tab_keywords, tab_radar, tab_password = st.tabs([
        "🌐 Páginas Web Monitoreadas",
        "🏷️ Palabras Clave de Filtrado",
        "📡 Radar y Oportunidades Detectadas",
        "🔒 Cambiar Contraseña"
    ])

    # =========================================================================
    # TAB 1: PÁGINAS WEB MONITOREADAS
    # =========================================================================
    with tab_portales:
        st.markdown("### 📋 Listado de Sitios Web para Extracción")
        st.markdown("La aplicación revisa periódicamente estas páginas en busca de nuevos pliegos y llamados a licitación.")

        # Formulario para agregar nuevo portal
        with st.expander("➕ Agregar Nueva Página Web al Radar", expanded=False):
            with st.form("form_add_portal"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    p_name = st.text_input("Nombre de la Entidad / Portal *", placeholder="Ej: AySA / Enarsa / YPF")
                    p_freq = st.selectbox("Frecuencia de Chequeo", ["Diaria", "Cada 12 Horas", "Semanal"])
                with c2:
                    p_url = st.text_input("URL de Licitaciones Vigentes *", placeholder="https://www.entidad.gob.ar/licitaciones")

                submit_portal = st.form_submit_button("Guardar Portal en el Radar ✨", type="primary", use_container_width=True)
                if submit_portal:
                    if p_name.strip() and p_url.strip().startswith("http"):
                        add_monitored_portal(p_name, p_url, p_freq)
                        st.success(f"✅ Portal '{p_name}' agregado correctamente al radar.")
                        st.rerun()
                    else:
                        st.warning("Por favor ingresa un nombre y una URL válida que comience con http:// o https://")

        portals = get_monitored_portals()
        if not portals:
            st.info("No hay portales configurados. Agrega uno arriba.")
        else:
            for p in portals:
                with st.container():
                    col_info, col_status, col_del = st.columns([3, 1, 0.8])
                    with col_info:
                        active_icon = "🟢" if p.get("active", 1) else "⚪"
                        st.markdown(f"**{active_icon} {p['name']}**")
                        st.markdown(f"<span style='font-size: 0.85rem; color: #2563EB;'>[{p['url']}]({p['url']})</span>", unsafe_allow_html=True)
                        last_scanned = p.get("last_scanned") or "Aún no escaneado"
                        st.caption(f"Frecuencia: {p.get('frequency', 'Diaria')} | Último escaneo: {last_scanned}")
                    with col_status:
                        is_active = bool(p.get("active", 1))
                        new_state = st.toggle("Activo", value=is_active, key=f"toggle_portal_{p['id']}")
                        if new_state != is_active:
                            toggle_monitored_portal(p['id'], 1 if new_state else 0)
                            st.rerun()
                    with col_del:
                        if st.button("🗑️", key=f"del_portal_{p['id']}", help="Eliminar portal del monitoreo"):
                            delete_monitored_portal(p['id'])
                            st.rerun()
                    st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: PALABRAS CLAVE DE FILTRADO (KEYWORDS)
    # =========================================================================
    with tab_keywords:
        st.markdown("### 🎯 Palabras Clave de Interés para el Negocio")
        st.markdown("Solo se notificarán y destacarán las licitaciones públicas cuyo título o descripción contenga al menos una de estas palabras clave.")

        col_kw_input, col_kw_btn = st.columns([3, 1])
        with col_kw_input:
            new_kw = st.text_input("Nueva palabra clave", placeholder="Ej: generadores, transformadores, instrumentación...", label_visibility="collapsed")
        with col_kw_btn:
            if st.button("➕ Agregar", use_container_width=True, type="primary"):
                if new_kw.strip():
                    add_monitored_keyword(new_kw.strip())
                    st.success(f"Palabra clave '{new_kw.strip()}' agregada.")
                    st.rerun()

        st.markdown("#### Palabras clave activas:")
        keywords = get_monitored_keywords()
        if not keywords:
            st.warning("No hay palabras clave configuradas. El radar no filtrará ninguna licitación.")
        else:
            # Mostrar en una cuadrícula moderna de badges
            kw_cols = st.columns(3)
            for i, kw in enumerate(keywords):
                with kw_cols[i % 3]:
                    st.markdown(
                        f"""
                        <div style="background-color: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600; color: #1E293B;">🏷️ {kw['keyword']}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button(f"Quitar '{kw['keyword']}'", key=f"del_kw_{kw['id']}", help="Eliminar palabra clave"):
                        delete_monitored_keyword(kw['id'])
                        st.rerun()

    # =========================================================================
    # TAB 3: RADAR EN VIVO & OPORTUNIDADES
    # =========================================================================
    with tab_radar:
        col_r_head, col_r_btn = st.columns([2.5, 1.5])
        with col_r_head:
            st.markdown("### 📡 Radar de Licitaciones Detectadas")
            st.markdown("Historial de llamados encontrados por el radar automático en los portales oficiales.")
        with col_r_btn:
            if st.button("🔍 Escanear Portales Ahora", type="primary", use_container_width=True):
                with st.spinner("Rastreando portales web oficiales (NA-SA, ARSAT, etc.)..."):
                    scanner = WebTenderScanner()
                    result = scanner.scan_all_portals()
                    st.success(
                        f"🎉 Escaneo completado: {result['total_portals_scanned']} portales rastreados. "
                        f"{result['total_found']} oportunidades coincidentes encontradas ({result['new_detected_count']} nuevas)."
                    )
                    st.rerun()

        opportunities = get_all_opportunities()
        if not opportunities:
            st.info("No hay oportunidades detectadas aún. Haz clic en 'Escanear Portales Ahora' para iniciar el rastreo.")
        else:
            for opp in opportunities:
                status = opp.get("status", "PENDIENTE")
                status_color = "#F59E0B" if status == "PENDIENTE" else ("#10B981" if status == "APROBADA" else "#94A3B8")
                status_text = "⏳ PENDIENTE DE REVISIÓN" if status == "PENDIENTE" else ("✅ APROBADA (EN PROCESO)" if status == "APROBADA" else "❌ DESCARTADA")

                with st.container():
                    st.markdown(
                        f"""
                        <div style="background-color: #FFFFFF; border: 1.5px solid #E2E8F0; border-radius: 12px; padding: 18px 22px; margin-bottom: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                <span style="font-weight: 700; color: #2563EB; font-size: 0.9rem; text-transform: uppercase;">🏢 {opp.get('portal_name', 'Portal')}</span>
                                <span style="font-size: 0.8rem; font-weight: 700; background-color: {status_color}22; color: {status_color}; padding: 4px 10px; border-radius: 6px;">{status_text}</span>
                            </div>
                            <h4 style="margin: 0 0 8px 0; color: #0F172A;">{opp.get('title')}</h4>
                            <p style="color: #64748B; font-size: 0.9rem; margin: 0 0 10px 0;">{opp.get('snippet', '')}</p>
                            <div style="display: flex; gap: 8px; align-items: center; font-size: 0.85rem; color: #475569;">
                                <span>🎯 Palabras Clave:</span>
                                <span style="background-color: #EFF6FF; color: #1D4ED8; font-weight: 600; padding: 2px 8px; border-radius: 4px;">{opp.get('matched_keywords')}</span>
                                <span style="margin-left: auto;">📅 Detectado: {opp.get('created_at', '')[:16]}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    c_act1, c_act2, c_act3 = st.columns([1.5, 1.2, 3])
                    with c_act1:
                        if opp.get("url"):
                            st.link_button("🌐 Ver en Portal Oficial", opp["url"], use_container_width=True)
                    with c_act2:
                        if status == "PENDIENTE":
                            if st.button("🚀 Iniciar Show (Analizar)", key=f"start_show_{opp['id']}", type="primary", use_container_width=True):
                                # Crear licitación automáticamente
                                tender_name = f"{opp.get('portal_name', 'Web')}: {opp.get('title', 'Licitación Web')[:80]}"
                                tender_id = create_tender(tender_name)

                                # Crear un documento resumen preliminar en data/tenders/{tender_id}/docs
                                tender_dir = os.path.join(os.getcwd(), "data", "tenders", str(tender_id), "docs")
                                os.makedirs(tender_dir, exist_ok=True)
                                brief_path = os.path.join(tender_dir, "Aviso_Licitacion_Web.txt")
                                with open(brief_path, "w", encoding="utf-8") as f:
                                    f.write(f"PUBLICACIÓN OFICIAL DE LICITACIÓN\n")
                                    f.write(f"Entidad: {opp.get('portal_name')}\n")
                                    f.write(f"Título: {opp.get('title')}\n")
                                    f.write(f"URL Oficial: {opp.get('url')}\n")
                                    f.write(f"Detalle / Snippet: {opp.get('snippet')}\n")
                                    f.write(f"Palabras clave coincidentes: {opp.get('matched_keywords')}\n")

                                # Actualizar estado en oportunidades
                                update_opportunity_status(opp['id'], "APROBADA", tender_id=tender_id)

                                # Lanzar el análisis de fondo si se proveyó callback
                                if launch_worker_callback:
                                    launch_worker_callback(tender_id)

                                st.session_state['current_tender_id'] = tender_id
                                st.session_state['current_view'] = 'detalle'
                                st.success("🎉 ¡Licitación creada! ¡Empieza el show!")
                                st.rerun()

                    with c_act3:
                        if status == "PENDIENTE":
                            if st.button("❌ Descartar", key=f"discard_opp_{opp['id']}", help="Marcar como no de interés"):
                                update_opportunity_status(opp['id'], "DESCARTADA")
                                st.rerun()

    # =========================================================================
    # TAB 4: SEGURIDAD Y CAMBIO DE CONTRASEÑA
    # =========================================================================
    with tab_password:
        st.markdown("### 🔒 Seguridad de la Cuenta y Cambio de Contraseña")
        st.markdown("Actualizá la clave de acceso de tu usuario para mantener protegida la plataforma.")

        col_form, col_info = st.columns([1.4, 1], gap="large")

        current_user = st.session_state.get("current_user", "admin")

        with col_form:
            with st.form("form_change_password", clear_on_submit=True):
                st.markdown(
                    f"""
                    <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 1.4rem;">👤</span>
                        <div>
                            <div style="font-size: 0.75rem; color: #64748B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Usuario de Sesión</div>
                            <div style="font-size: 1rem; color: #0F172A; font-weight: 700;">{current_user}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                curr_pass = st.text_input("Contraseña Actual *", type="password", placeholder="Ingresá tu contraseña actual")
                new_pass = st.text_input("Nueva Contraseña *", type="password", placeholder="Mínimo 6 caracteres")
                confirm_pass = st.text_input("Confirmar Nueva Contraseña *", type="password", placeholder="Repetí la nueva contraseña")

                submit_btn = st.form_submit_button("Actualizar Contraseña ✨", type="primary", use_container_width=True)

                if submit_btn:
                    if not curr_pass or not new_pass or not confirm_pass:
                        st.warning("⚠️ Por favor completá todos los campos requeridos.")
                    elif not verify_user_credentials(current_user, curr_pass):
                        st.error("❌ La contraseña actual ingresada es incorrecta.")
                    elif len(new_pass) < 6:
                        st.error("❌ La nueva contraseña debe tener al menos 6 caracteres.")
                    elif new_pass != confirm_pass:
                        st.error("❌ La nueva contraseña y su confirmación no coinciden.")
                    elif new_pass == curr_pass:
                        st.warning("⚠️ La nueva contraseña no puede ser idéntica a la actual.")
                    else:
                        success = update_user_password(current_user, new_pass)
                        if success:
                            st.success("✅ ¡Contraseña actualizada exitosamente! Utilizala en tu próximo inicio de sesión.")
                        else:
                            st.error("❌ Ocurrió un error al actualizar la contraseña en la base de datos.")

        with col_info:
            st.markdown(
                """
                <div style="background-color: #F8FAFC; border: 1.5px solid #E2E8F0; border-radius: 12px; padding: 22px 24px;">
                    <h4 style="margin: 0 0 14px 0; color: #1E293B; font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
                        🛡️ Recomendaciones de Seguridad
                    </h4>
                    <ul style="color: #475569; font-size: 0.88rem; line-height: 1.65; margin: 0; padding-left: 18px;">
                        <li>Utilizá al menos <strong>6 caracteres</strong> (recomendado 8 o más).</li>
                        <li>Combiná letras mayúsculas, minúsculas, números y símbolos.</li>
                        <li>No utilices información personal predecible ni claves compartidas.</li>
                        <li>El cambio se aplica <strong>inmediatamente</strong> en el sistema.</li>
                    </ul>
                    <div style="margin-top: 20px; padding-top: 14px; border-top: 1px solid #E2E8F0; font-size: 0.82rem; color: #64748B; line-height: 1.4;">
                        ℹ️ Si necesitás restablecer la clave por olvido, contactá al administrador de soporte interno.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

