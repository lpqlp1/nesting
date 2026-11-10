import streamlit as st
import re
import math
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import matplotlib.patches as patches

st.set_page_config(page_title="Nesting Topográfico - eFe-Design", layout="wide")

def calcular_centroide(vertices):
    cx = sum(x for x, y in vertices) / len(vertices)
    cy = sum(y for x, y in vertices) / len(vertices)
    return cx, cy

def extraer_piezas_con_nombres_desde_bytes(svg_bytes):
    root = ET.fromstring(svg_bytes)
    ns_regex = re.compile(r"\{.*\}")
    contornos = []
    textos = []
    conteo = 1

    for elem in root.iter():
        tag = ns_regex.sub("", elem.tag).lower()
        color_trazo = elem.attrib.get("stroke", "").lower()
        d_attr = elem.attrib.get("d", "").strip()

        es_negro = ("#000000" in color_trazo or "black" in color_trazo or color_trazo == "#000")
        esta_cerrado = d_attr.endswith("Z") or d_attr.endswith("z")

        if tag == "path" and es_negro and esta_cerrado:
            tokens = re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", d_attr)
            coords = []
            for i in range(0, len(tokens) - 1, 2):
                try:
                    coords.append((float(tokens[i]), float(tokens[i+1])))
                except ValueError:
                    pass
            if len(coords) >= 10:
                cx, cy = calcular_centroide(coords)
                contornos.append({
                    "id_temp": f"C{conteo}-P",
                    "vertices": coords,
                    "cx": cx,
                    "cy": cy,
                    "nombre": None
                })
                conteo += 1

        elif tag == "text":
            txt_val = (elem.text or "").strip()
            if txt_val:
                try:
                    tx = float(elem.attrib.get("x", 0))
                    ty = float(elem.attrib.get("y", 0))
                    textos.append({"texto": txt_val, "x": tx, "y": ty})
                except ValueError:
                    pass

    for c in contornos:
        mejor_txt = None
        min_d = float("inf")
        for t in textos:
            d = math.hypot(c["cx"] - t["x"], c["cy"] - t["y"])
            if d < 100.0 and d < min_d:
                min_d = d
                mejor_txt = t["texto"]
        c["nombre"] = mejor_txt if mejor_txt else c["id_temp"]

    return contornos

def rotar_punto(x, y, angulo_deg):
    rad = math.radians(angulo_deg)
    return (x * math.cos(rad) - y * math.sin(rad), x * math.sin(rad) + y * math.cos(rad))

def rotar_poligono(vertices, angulo_deg):
    rad = math.radians(angulo_deg)
    c, s = math.cos(rad), math.sin(rad)
    return [(x * c - y * s, x * s + y * c) for x, y in vertices]

def optimizar_rotacion_1grado(vertices):
    mejor_ang = 0
    menor_h = float("inf")
    ang = 0
    while ang < 180:
        rot = rotar_poligono(vertices, ang)
        h = max(y for x, y in rot) - min(y for x, y in rot)
        if h < menor_h:
            menor_h = h
            mejor_ang = ang
        ang += 1
    return mejor_ang

def calcular_perfiles(vertices, res_x=2.0):
    min_x = min(x for x, y in vertices)
    min_y = min(y for x, y in vertices)
    norm_v = [(x - min_x, y - min_y) for x, y in vertices]
    w = max(x for x, y in norm_v)
    h = max(y for x, y in norm_v)

    n_bins = int(w / res_x) + 1
    p_bot = [float('inf')] * n_bins
    p_top = [0.0] * n_bins

    for i in range(len(norm_v)):
        x1, y1 = norm_v[i]
        x2, y2 = norm_v[(i + 1) % len(norm_v)]
        dist = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(dist / (res_x * 0.25)))
        for j in range(steps + 1):
            tx = x1 + (x2 - x1) * (j / steps)
            ty = y1 + (y2 - y1) * (j / steps)
            b = min(n_bins - 1, int(tx / res_x))
            if ty < p_bot[b]: p_bot[b] = ty
            if ty > p_top[b]: p_top[b] = ty

    for b in range(n_bins):
        if p_bot[b] == float('inf'): p_bot[b] = h / 2.0

    return norm_v, p_bot, p_top, w, h, min_x, min_y

def generar_variantes(p, res_x=2.0):
    ang_base = optimizar_rotacion_1grado(p["vertices"])
    variantes = []
    for extra_ang in [0, 180]:
        ang_total = (ang_base + extra_ang) % 360
        v_rot = rotar_poligono(p["vertices"], ang_total)
        norm_v, p_bot, p_top, w, h, mx, my = calcular_perfiles(v_rot, res_x)
        cx_rot, cy_rot = rotar_punto(p["cx"], p["cy"], ang_total)
        cx_loc = cx_rot - mx
        cy_loc = cy_rot - my

        variantes.append({
            "angulo": ang_total,
            "vertices": norm_v,
            "ancho": w,
            "alto": h,
            "cx_local": cx_loc,
            "cy_local": cy_loc,
            "p_bot": p_bot,
            "p_top": p_top,
            "n_bins": len(p_bot)
        })
    return variantes

def ejecutar_nesting_topografico(piezas, ancho_mesa=1200.0, alto_mesa=800.0, kerf=5.0):
    res_x = 2.0
    tam_h = int(ancho_mesa / res_x) + 1

    piezas_multi = [{"id": p["nombre"], "variantes": generar_variantes(p, res_x)} for p in piezas]
    piezas_multi.sort(key=lambda item: item["variantes"][0]["ancho"] * item["variantes"][0]["alto"], reverse=True)

    laminas = []
    idx_lamina = 1
    i = 0
    total = len(piezas_multi)

    while i < total:
        piezas_lamina = []
        horizonte = [kerf] * tam_h

        while i < total:
            p_data = piezas_multi[i]
            mejor_y_var = float('inf')
            mejor_x_var = -1
            mejor_var = None

            for var in p_data["variantes"]:
                w = var["ancho"]
                h = var["alto"]
                if w + 2*kerf > ancho_mesa or h + 2*kerf > alto_mesa:
                    continue

                lim_x_bin = int((ancho_mesa - kerf - w) / res_x)
                paso_x_bin = int(4.0 / res_x)

                x_b = int(kerf / res_x)
                while x_b <= lim_x_bin:
                    y_req = 0.0
                    for dx in range(var["n_bins"]):
                        b_mesa = x_b + dx
                        y_shift = horizonte[b_mesa] + kerf - var["p_bot"][dx]
                        if y_shift > y_req:
                            y_req = y_shift

                    if y_req + h <= alto_mesa:
                        score = y_req + (x_b * res_x * 0.02)
                        if score < mejor_y_var:
                            mejor_y_var = score
                            mejor_x_var = x_b * res_x
                            mejor_var = var
                            if y_req < kerf + 2:
                                break
                    x_b += paso_x_bin

            if mejor_var is not None:
                y_final = 0.0
                x_b_final = int(mejor_x_var / res_x)
                for dx in range(mejor_var["n_bins"]):
                    y_shift = horizonte[x_b_final + dx] + kerf - mejor_var["p_bot"][dx]
                    if y_shift > y_final:
                        y_final = y_shift

                p_inst = {
                    "id": p_data["id"],
                    "x": mejor_x_var,
                    "y": y_final,
                    "lamina": idx_lamina,
                    "angulo": mejor_var["angulo"],
                    "vertices": mejor_var["vertices"],
                    "ancho": mejor_var["ancho"],
                    "alto": mejor_var["alto"],
                    "txt_x": mejor_x_var + mejor_var["cx_local"],
                    "txt_y": y_final + mejor_var["cy_local"]
                }
                piezas_lamina.append(p_inst)

                for dx in range(mejor_var["n_bins"]):
                    b_mesa = x_b_final + dx
                    cota = y_final + mejor_var["p_top"][dx]
                    if cota > horizonte[b_mesa]:
                        horizonte[b_mesa] = cota
                i += 1
            else:
                break

        if piezas_lamina:
            alto_usado = min(alto_mesa, max(horizonte))
            laminas.append({
                "numero": idx_lamina,
                "piezas": piezas_lamina,
                "alto_consumido": alto_usado
            })
            idx_lamina += 1
        else:
            i += 1

    return laminas

def generar_svg_string(laminas, ancho_mesa=1200.0, alto_mesa=800.0, sep=100.0):
    total = len(laminas)
    alto_svg = total * (alto_mesa + sep)

    lineas = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho_mesa + 50} {alto_svg + 50}" width="{ancho_mesa + 50}mm" height="{alto_svg + 50}mm">',
        '  <style>',
        '    .limite-mesa { fill: none; stroke: #ff0000; stroke-width: 0.5; }',
        '    .capa-corte { fill: none; stroke: #000000; stroke-width: 0.2; }',
        '    .capa-marcado { font-family: Arial, sans-serif; font-size: 7px; fill: #0000ff; text-anchor: middle; dominant-baseline: central; font-weight: bold; }',
        '    .info-lamina { font-family: Arial, sans-serif; font-size: 14px; fill: #ff0000; font-weight: bold; }',
        '  </style>'
    ]

    for lam in laminas:
        num = lam["numero"]
        offset_y = (total - num) * (alto_mesa + sep) + 20
        lineas.append(f'  <g id="LAMINA_{num}">')
        lineas.append(f'    <rect class="limite-mesa" x="20" y="{offset_y}" width="{ancho_mesa}" height="{alto_mesa}" />')
        lineas.append(f'    <text class="info-lamina" x="35" y="{offset_y + 30}">LÁMINA {num} ({int(ancho_mesa)} x {int(alto_mesa)} mm) - {len(lam["piezas"])} PIEZAS</text>')

        lineas.append(f'    <g id="CAPA_00_GRABADO_L{num}">')
        for p in lam["piezas"]:
            tx = p["txt_x"] + 20
            ty = p["txt_y"] + offset_y
            lineas.append(f'      <text class="capa-marcado" x="{tx:.2f}" y="{ty:.2f}" transform="rotate({p["angulo"]}, {tx:.2f}, {ty:.2f})">{p["id"]}</text>')
        lineas.append('    </g>')

        lineas.append(f'    <g id="CAPA_01_CORTE_L{num}">')
        for p in lam["piezas"]:
            xb = p["x"] + 20
            yb = p["y"] + offset_y
            pts_str = " ".join([f"{x + xb:.2f},{y + yb:.2f}" for x, y in p["vertices"]])
            lineas.append(f'      <polygon class="capa-corte" points="{pts_str}" />')
        lineas.append('    </g>')
        lineas.append('  </g>')

    lineas.append('</svg>')
    return "\n".join(lineas)

st.title("🪑 Nesting Topográfico Multi-Lámina (eFe-Design)")
st.markdown("Herramienta de optimización y despiece paramétrico para corte láser y fresado CNC.")

with st.sidebar:
    st.header("⚙️ Parámetros de Mesa")
    ancho_mesa = st.number_input("Ancho Lámina (mm)", min_value=300.0, max_value=3000.0, value=1200.0, step=50.0)
    alto_mesa = st.number_input("Alto Lámina (mm)", min_value=300.0, max_value=3000.0, value=800.0, step=50.0)
    kerf = st.slider("Kerf / Holgura (mm)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)

archivo_subido = st.file_uploader("Cargar archivo SVG de corte (ej. banco_tronco.svg)", type=["svg"])

if archivo_subido is not None:
    contenido = archivo_subido.read()
    piezas = extraer_piezas_con_nombres_desde_bytes(contenido)

    if not piezas:
        st.error("No se detectaron curvas cerradas válidas con trazo negro.")
    else:
        st.success(f"Detectadas {len(piezas)} piezas con identificadores.")

        if st.button("🚀 Ejecutar Nesting Topográfico"):
            with st.spinner("Anidando piezas..."):
                resultado = ejecutar_nesting_topografico(piezas, ancho_mesa, alto_mesa, kerf)

            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Total Láminas", len(resultado))
                for lam in resultado:
                    st.write(f"- Lámina {lam['numero']}: {len(lam['piezas'])} piezas ({lam['alto_consumido']:.1f} mm)")

                svg_str = generar_svg_string(resultado, ancho_mesa, alto_mesa)
                st.download_button(
                    label="📥 Descargar SVG (LightBurn / RDWorks)",
                    data=svg_str,
                    file_name="nesting_optimizado.svg",
                    mime="image/svg+xml"
                )

            with col2:
                total = len(resultado)
                fig, ax = plt.subplots(figsize=(10, min(30, max(5, 2.5 * total))))
                sep = 120.0
                for lam in resultado:
                    num = lam["numero"]
                    offset_y = (num - 1) * (alto_mesa + sep)
                    mesa = patches.Rectangle((0, offset_y), ancho_mesa, alto_mesa, linewidth=1.2, edgecolor="#2d3748", facecolor="#f8fafc")
                    ax.add_patch(mesa)
                    ax.axhline(y=offset_y + lam["alto_consumido"], color="#e53e3e", linestyle="--", linewidth=1.0)
                    for p in lam["piezas"]:
                        xb = p["x"]
                        yb = p["y"] + offset_y
                        pts = [(x + xb, y + yb) for x, y in p["vertices"]]
                        poly = patches.Polygon(pts, closed=True, facecolor="#3182ce", edgecolor="#000", linewidth=0.5, alpha=0.85)
                        ax.add_patch(poly)
                        ax.text(p["txt_x"], p["txt_y"] + offset_y, p["id"], color="white", fontsize=4.5, weight="bold", ha="center", va="center", rotation=p["angulo"])
                ax.set_xlim(-30, ancho_mesa + 30)
                ax.set_ylim(-30, total * (alto_mesa + sep))
                ax.set_aspect("equal")
                plt.axis("off")
                st.pyplot(fig)