import docx
import os
import shutil

source_path = "OT_1341_RAIZEN_MTO_Metalurgico_REV00.docx"
target_path = "templates/OT_template.docx"

if not os.path.exists("templates"):
    os.makedirs("templates")

# Copy the original first to preserve everything
shutil.copy2(source_path, target_path)

doc = docx.Document(target_path)

# Variables to replace based on the structure of the doc:
# 1341 — RAIZEN ARGENTINA S.A.U. -> {{CLIENTE_NOMBRE_CORTO}}
# Depósito Santa Fe -> {{PLANTA}}
# Licitante Raizen Argentina S.A.U. -> {{CLIENTE}}
# 1341 — MTO Metalúrgico, Mecánico y Eléctrico AR -> {{PROCESO}}
# Dique 2, Puerto de Santa Fe de la Vera Cruz, Santa Fe -> {{UBICACION_COMPLETA}}
# Los servicios se ejecutarán en las instalaciones de RAIZEN Argentina S.A.U., Depósito Santa Fe, ubicado en Dique 2, Puerto de Santa Fe de la Vera Cruz, Provincia de Santa Fe. -> {{TEXTO_LUGAR_PRESTACION}}
# Horario Normal: Lunes a Jueves de 7:00 a 16:00 hs... -> {{TEXTO_HORARIOS}}
# Repuestos y materiales de proceso para las tareas definidas... -> {{TEXTO_MATERIALES_CLIENTE}}
# Herramientas y equipos básicos... -> {{TEXTO_MATERIALES_IMA}}

replacements = {
    "1341 — RAIZEN ARGENTINA S.A.U.": "{{CLIENTE}}",
    "Depósito Santa Fe": "{{PLANTA}}",
    "Raizen Argentina S.A.U. — Depósito Santa Fe": "{{CLIENTE}} - {{PLANTA}}",
    "1341 — MTO Metalúrgico, Mecánico y Eléctrico AR": "{{PROCESO}}",
    "1341": "{{NUMERO_LICITACION}}",
    "Junio 2026": "{{FECHA_EMISION}}",
    "RAIZEN ARGENTINA S.A.U.": "{{CLIENTE}}",
    "RAIZEN": "{{CLIENTE_CORTO}}",
    "Los servicios se ejecutarán en las instalaciones de RAIZEN Argentina S.A.U., Depósito Santa Fe, ubicado en Dique 2, Puerto de Santa Fe de la Vera Cruz, Provincia de Santa Fe.": "{{TEXTO_LUGAR_PRESTACION}}",
    "Horario Normal: Lunes a Jueves de 7:00 a 16:00 hs. Viernes de 7:00 a 15:00 hs.": "{{TEXTO_HORARIOS}}",
    "Horario Extra Tipo A: Lunes a Viernes de 16:00 a 19:00 hs, y Sábados de 7:00 a 13:00 hs.": "",
    "Horario Extra Tipo B: Sábados de 13:00 a 19:00 hs, Domingos y feriados de 7:00 a 19:00 hs.": "",
    "Repuestos y materiales de proceso para las tareas definidas (IMA coordina solicitud con antelación suficiente)": "{{TEXTO_MATERIALES_CLIENTE}}",
    "Energía eléctrica y agua para la realización de los trabajos": "",
    "Grúas de más de 8 toneladas (IMA coordina y programa con supervisión RAIZEN)": "",
    "Espacio para taller asignado por RAIZEN dentro del predio del Depósito Santa Fe": "",
    "Herramientas y equipos básicos: amoladoras angulares 115 mm y 175 mm con discos, roto-perforadora 700 W con mechas, soldadora eléctrica, herramientas de mano, niveles, escuadras, cintas métricas, escaleras hasta 3,00 m, multímetro hasta 400 V CA/CC, tablero eléctrico de obra": "{{TEXTO_MATERIALES_IMA}}",
    "Consumibles de soldadura: electrodos recubiertos, varillas TIG, gases industriales": "",
    "Consumibles de corte: discos abrasivos, gases industriales, hojas de sierra": "",
    "EPP completo para todo el personal (ver sección 8)": "",
    "Matafuegos, mangueras y accesorios para conexión a red de incendios en trabajos en caliente": "",
    "Tapas de cámara de drenajes según requerimiento de permisos de trabajo": "",
    "Combustibles y lubricantes para máquinas y herramientas propias": "",
    "El alcance de la prestación comprende tres especialidades de mantenimiento, cotizadas por hora hombre según categoría, conforme al Anexo C del pliego — Licitación N° 1341:": "{{TEXTO_ALCANCE_GENERAL}}",
    "Para las tareas definidas, RAIZEN entregará los equipos desvinculados de la operación y IMA los devolverá listos para operar una vez obtenido el Permiso de Trabajo. El plazo de entrega comenzará a correr desde la obtención del permiso. IMA coordinará con suficiente antelación la obtención de materiales, permisos, grúas y andamios para aprovechar al máximo el tiempo de parada del equipo.": "{{TEXTO_TAREAS_DEFINIDAS}}",
    "Los repuestos y materiales serán provistos por RAIZEN. IMA coordinará su solicitud con antelación suficiente.": "",
}

for p in doc.paragraphs:
    for k, v in replacements.items():
        if k in p.text:
            p.text = p.text.replace(k, v)

# Handling tables might be too risky (breaking formats), we'll do our best with paragraphs.
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for k, v in replacements.items():
                    if k in p.text:
                        p.text = p.text.replace(k, v)

doc.save(target_path)
print(f"Template created at {target_path}")
