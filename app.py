"""
App Streamlit - Cálculo de IVA / Impuesto a Pagar
Procesa los CSV de Resumen de Compras y Ventas del SII (Chile)
y genera un detalle de impuestos con el formato del cliente.
"""

import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ------------------------- Configuración de página -------------------------
st.set_page_config(
    page_title="Cálculo de IVA - Detalle de Impuesto",
    page_icon="🧾",
    layout="centered",
)


# ------------------------- Utilidades -------------------------
def fmt(n):
    """Formato chileno: punto como separador de miles, sin decimales."""
    try:
        n = int(round(float(n)))
    except (TypeError, ValueError):
        return "0"
    return f"{n:,}".replace(",", ".")


def leer_csv_sii(file):
    """Lee un CSV del SII probando separadores y encodings comunes."""
    if file is None:
        return None
    raw = file.read()
    if isinstance(raw, str):
        raw = raw.encode("utf-8")

    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        for sep in (";", ","):
            try:
                df = pd.read_csv(io.BytesIO(raw), sep=sep, encoding=enc)
                if df.shape[1] >= 3:
                    df.columns = [c.strip() for c in df.columns]
                    return df
            except Exception:
                continue
    return None


def num(v):
    """Convierte un valor a número entero, tolerando NaN, vacíos y strings con puntos."""
    if pd.isna(v):
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().replace(".", "").replace(",", "")
    if s == "" or s.lower() == "nan":
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def buscar_fila(df, claves):
    """Busca en la primera columna una fila cuyo texto contenga alguna de las claves."""
    if df is None or df.empty:
        return None
    col = df.iloc[:, 0].astype(str).str.lower()
    for clave in claves:
        mask = col.str.contains(clave.lower(), na=False, regex=False)
        if mask.any():
            return df[mask].iloc[0]
    return None


def extraer_ventas(df):
    """Extrae los montos de ventas desde el CSV del SII."""
    resultado = {
        "facturas_neto": 0, "facturas_iva": 0,
        "boletas_neto": 0, "boletas_iva": 0,
        "nc_neto": 0, "nc_iva": 0,
        "cpe_neto": 0, "cpe_iva": 0,
    }
    if df is None:
        return resultado

    f = buscar_fila(df, ["Factura Electrónica(33)", "Factura Electronica(33)", "factura electr"])
    if f is not None:
        resultado["facturas_neto"] = num(f.get("Monto Neto", 0))
        resultado["facturas_iva"] = num(f.get("Monto IVA", 0))

    b = buscar_fila(df, ["Boleta Electr", "boleta(39)", "boleta electr"])
    if b is not None:
        resultado["boletas_neto"] = num(b.get("Monto Neto", 0))
        resultado["boletas_iva"] = num(b.get("Monto IVA", 0))

    nc = buscar_fila(df, ["Nota de Crédito", "Nota de Credito", "nota de cr"])
    if nc is not None:
        resultado["nc_neto"] = num(nc.get("Monto Neto", 0))
        resultado["nc_iva"] = num(nc.get("Monto IVA", 0))

    cpe = buscar_fila(df, ["Comprobantes Pago Electrónico", "Comprobante Pago Electronico",
                            "comprobante pago", "Pago Electr"])
    if cpe is not None:
        resultado["cpe_neto"] = num(cpe.get("Monto Neto", 0))
        resultado["cpe_iva"] = num(cpe.get("Monto IVA", 0))

    return resultado


def extraer_compras(df):
    """Extrae los montos de compras desde el CSV del SII."""
    resultado = {
        "facturas_neto": 0, "facturas_iva": 0,
        "nc_neto": 0, "nc_iva": 0,
    }
    if df is None:
        return resultado

    # IVA en compras puede venir en distintas columnas: IVA Recuperable, Monto IVA, etc.
    def iva_de(fila):
        for c in ("IVA Recuperable", "Monto IVA", "IVA Uso Comun", "IVA Uso Común"):
            if c in fila.index:
                v = num(fila.get(c, 0))
                if v:
                    return v
        return 0

    f = buscar_fila(df, ["Factura Electrónica(33)", "Factura Electronica(33)", "factura electr"])
    if f is not None:
        resultado["facturas_neto"] = num(f.get("Monto Neto", 0))
        resultado["facturas_iva"] = iva_de(f)

    nc = buscar_fila(df, ["Nota de Crédito", "Nota de Credito", "nota de cr"])
    if nc is not None:
        resultado["nc_neto"] = num(nc.get("Monto Neto", 0))
        resultado["nc_iva"] = iva_de(nc)

    return resultado


# ------------------------- HTML del informe -------------------------
def render_informe(nombre, v, c, ppm_pct, retencion, remanente_anterior):
    iva_ventas = v["facturas_iva"] + v["boletas_iva"] + v["cpe_iva"] - v["nc_iva"]
    neto_ventas = v["facturas_neto"] + v["boletas_neto"] + v["cpe_neto"] - v["nc_neto"]

    iva_compras = c["facturas_iva"] - c["nc_iva"] + remanente_anterior
    neto_compras = c["facturas_neto"] - c["nc_neto"]

    impuesto_det = iva_ventas - iva_compras
    if impuesto_det < 0:
        remanente_prox = abs(impuesto_det)
        impuesto_det_mostrar = 0
    else:
        remanente_prox = 0
        impuesto_det_mostrar = impuesto_det

    ppm_monto = int(round(neto_ventas * (ppm_pct / 100)))
    total_pagar = impuesto_det_mostrar + ppm_monto + retencion

    html = f"""
    <div id="informe-iva" style="
        font-family: Arial, sans-serif;
        background: white;
        color: black;
        padding: 28px 36px;
        border: 1px solid #000;
        max-width: 720px;
        margin: 0 auto;
        font-size: 14px;
    ">
        <div style="text-align:center; margin-bottom: 4px;">
            <span style="font-size:18px; font-weight:bold; text-decoration:underline;">
                DETALLE DE IMPUESTO
            </span>
        </div>
        <div style="text-align:center; font-size:16px; font-weight:bold; margin-bottom:14px;">
            {nombre}
        </div>

        <table style="width:100%; border-collapse: collapse;">
            <tr>
                <td style="width:55%;"></td>
                <td style="text-align:right; width:22%;">$ Netos</td>
                <td style="width:6%;"></td>
                <td style="text-align:right; width:17%;">$ IVA</td>
            </tr>

            <tr><td colspan="4" style="padding-top:10px;">
                <b><u>Ventas del mes</u></b>
            </td></tr>
            <tr>
                <td>Facturas</td>
                <td style="text-align:right;">{fmt(v['facturas_neto'])}</td>
                <td></td>
                <td style="text-align:right;">{fmt(v['facturas_iva'])}</td>
            </tr>
            <tr>
                <td>Boletas</td>
                <td style="text-align:right;">{fmt(v['boletas_neto'])}</td>
                <td></td>
                <td style="text-align:right;">{fmt(v['boletas_iva'])}</td>
            </tr>
            <tr>
                <td style="color:#c00;">Notas de Créditos</td>
                <td style="text-align:right; color:#c00;">{fmt(v['nc_neto'])}</td>
                <td></td>
                <td style="text-align:right; color:#c00;">{fmt(v['nc_iva'])}</td>
            </tr>
            <tr>
                <td>Comprobantes Pago Electrónico</td>
                <td style="text-align:right; border-bottom:1px solid #000;">{fmt(v['cpe_neto'])}</td>
                <td></td>
                <td style="text-align:right; border-bottom:1px solid #000;">{fmt(v['cpe_iva'])}</td>
            </tr>
            <tr>
                <td></td>
                <td style="text-align:right; font-weight:bold;">{fmt(neto_ventas)}</td>
                <td style="text-align:center;">(+)</td>
                <td style="text-align:right; font-weight:bold;">{fmt(iva_ventas)}</td>
            </tr>

            <tr><td colspan="4" style="padding-top:10px;">
                <b><u>Compras del Mes</u></b>
            </td></tr>
            <tr>
                <td>Facturas</td>
                <td style="text-align:right;">{fmt(c['facturas_neto'])}</td>
                <td></td>
                <td style="text-align:right;">{fmt(c['facturas_iva'])}</td>
            </tr>
            <tr>
                <td style="color:#c00;">Notas de Créditos</td>
                <td style="text-align:right; color:#c00;">{fmt(c['nc_neto'])}</td>
                <td></td>
                <td style="text-align:right; color:#c00;">{fmt(c['nc_iva'])}</td>
            </tr>
            <tr>
                <td>Remanente mes Anterior</td>
                <td style="text-align:right; border-bottom:1px solid #000;">&nbsp;</td>
                <td></td>
                <td style="text-align:right; border-bottom:1px solid #000;">{fmt(remanente_anterior)}</td>
            </tr>
            <tr>
                <td></td>
                <td style="text-align:right; font-weight:bold;">{fmt(neto_compras)}</td>
                <td style="text-align:center;">(-)</td>
                <td style="text-align:right; font-weight:bold;">{fmt(iva_compras)}</td>
            </tr>

            <tr><td colspan="4" style="height:14px;"></td></tr>

            <tr>
                <td><b>IMPUESTO DETERMINADO</b></td>
                <td></td>
                <td style="text-align:center;">(=)</td>
                <td style="text-align:right; font-weight:bold; border:1px solid #000; padding:2px 6px;">
                    {fmt(impuesto_det_mostrar)}
                </td>
            </tr>
            <tr>
                <td>Remanente para proximo mes</td>
                <td></td>
                <td></td>
                <td style="text-align:right; font-weight:bold; border:1px solid #000; padding:2px 6px;">
                    {fmt(remanente_prox)}
                </td>
            </tr>

            <tr><td colspan="4" style="height:10px;"></td></tr>

            <tr>
                <td>PPM</td>
                <td></td>
                <td style="text-align:center;">(+)</td>
                <td style="text-align:right; border:1px solid #000; padding:2px 6px;">
                    {fmt(ppm_monto)}
                </td>
            </tr>

            <tr><td colspan="4" style="height:6px;"></td></tr>

            <tr>
                <td>RETENCION</td>
                <td></td>
                <td style="text-align:center;">(+)</td>
                <td style="text-align:right; border:1px solid #000; padding:2px 6px;">
                    {fmt(retencion) if retencion else ''}
                </td>
            </tr>

            <tr><td colspan="4" style="height:10px;"></td></tr>

            <tr style="border-top:2px solid #000;">
                <td style="border-top:2px solid #000; border-bottom:2px solid #000; padding:6px 0;">
                    <b>TOTAL A PAGAR</b>
                </td>
                <td style="border-top:2px solid #000; border-bottom:2px solid #000;"></td>
                <td style="border-top:2px solid #000; border-bottom:2px solid #000; text-align:center;">
                    <b>(=)</b>
                </td>
                <td style="border-top:2px solid #000; border-bottom:2px solid #000;
                           text-align:right; font-weight:bold; padding:6px 6px;">
                    {fmt(total_pagar)}
                </td>
            </tr>
        </table>
    </div>
    """
    return html, {
        "iva_ventas": iva_ventas,
        "iva_compras": iva_compras,
        "neto_ventas": neto_ventas,
        "impuesto_determinado": impuesto_det_mostrar,
        "remanente_proximo": remanente_prox,
        "ppm": ppm_monto,
        "retencion": retencion,
        "total_pagar": total_pagar,
    }


# ------------------------- UI -------------------------
st.title("🧾 Cálculo de IVA / Impuesto a Pagar")
st.caption("Sube los resúmenes del SII y obtén el detalle listo para enviar al cliente.")

with st.sidebar:
    st.header("⚙️ Parámetros")
    nombre = st.text_input("Nombre del contribuyente", value="", placeholder="Nombre de la empresa")
    ppm_pct = st.number_input("PPM (%)", min_value=0.0, max_value=100.0,
                              value=2.0, step=0.125, format="%.3f",
                              help="Se aplica sobre el Neto total de ventas.")
    aplica_retencion = st.checkbox("Aplica Retención de Honorarios", value=False)
    retencion = 0
    if aplica_retencion:
        retencion = st.number_input("Monto Retención Honorarios ($)",
                                    min_value=0, value=0, step=1000)
    remanente_anterior = st.number_input("Remanente mes Anterior ($)",
                                         min_value=0, value=0, step=1000)

col1, col2 = st.columns(2)
with col1:
    archivo_ventas = st.file_uploader("📤 Resumen de **Ventas** (CSV del SII)",
                                      type=["csv"], key="ventas")
with col2:
    archivo_compras = st.file_uploader("📥 Resumen de **Compras** (CSV del SII)",
                                       type=["csv"], key="compras")

if archivo_ventas and archivo_compras:
    df_v = leer_csv_sii(archivo_ventas)
    df_c = leer_csv_sii(archivo_compras)

    if df_v is None or df_c is None:
        st.error("No pude leer alguno de los CSV. Revisa el formato (separador ; y encoding UTF-8).")
    else:
        with st.expander("👁️ Vista previa de los datos cargados"):
            st.write("**Ventas**")
            st.dataframe(df_v, use_container_width=True)
            st.write("**Compras**")
            st.dataframe(df_c, use_container_width=True)

        ventas = extraer_ventas(df_v)
        compras = extraer_compras(df_c)

        html, totales = render_informe(
            nombre, ventas, compras, ppm_pct, retencion, remanente_anterior
        )

        st.markdown("### 📄 Detalle de Impuesto")
        components.html(html, height=620, scrolling=False)

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Impuesto Determinado", f"${fmt(totales['impuesto_determinado'])}")
        m2.metric("PPM", f"${fmt(totales['ppm'])}")
        m3.metric("TOTAL A PAGAR", f"${fmt(totales['total_pagar'])}")

        st.info("💡 Toma una captura de pantalla del recuadro superior para enviársela al cliente.")
else:
    st.warning("⬆️ Sube ambos archivos (ventas y compras) para generar el detalle.")
    st.markdown("""
    **Formato esperado del CSV del SII:**
    - Separador: `;`
    - Columnas de ventas: `Tipo Documento; Total Documentos; Monto Exento; Monto Neto; Monto IVA; Monto Total`
    - Columnas de compras: `Tipo Documento; Total Documentos; Monto Exento; Monto Neto; IVA Recuperable; ...`
    """)
