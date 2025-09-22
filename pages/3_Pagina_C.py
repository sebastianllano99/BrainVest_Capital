import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
import zipfile
import requests
import os
import sys

# -----------------------
# Config / IDs
# -----------------------
st.title("📊 Análisis de Portafolios — Página 3 (Frontera)")

# Google Sheets (opcional)
SHEET_ID = "19xIH0ipdUYg0XELl4mHBLcNbmQ5vxQcL"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# ID del ZIP en Google Drive (el que has compartido)
ZIP_FILE_ID = "1Tm2vRpHYbPNUGDVxU4cRbXpYGH_uasW_"

# -----------------------
# Cargar hojas desde Google Sheets (si está disponible)
# -----------------------
df_res = None
df_gmvp = None
df_ms = None

try:
    st.info("📥 Leyendo Google Sheets (Resumen_Portafolios, GMVP, Max_Sharpe)...")
    df_dict = pd.read_excel(url_excel, sheet_name=None, engine="openpyxl")
    df_res = df_dict.get("Resumen_Portafolios")
    df_gmvp = df_dict.get("GMVP")
    df_ms = df_dict.get("Max_Sharpe")
    st.success("✔️ Hoja cargada (Google Sheets).")
except Exception as e:
    st.warning(f"⚠️ No se pudo leer Google Sheets: {e}\nSe procederá con los artefactos en el ZIP (si existen).")

# Formato de 'Ganancia Anual' si existe
def formato_pesos(x):
    try:
        return f"${x:,.0f}"
    except Exception:
        return x

if df_res is not None and "Ganancia Anual" in df_res.columns:
    df_res["Ganancia Anual"] = df_res["Ganancia Anual"].apply(formato_pesos)

# Mostrar resumen si lo tenemos
if df_res is not None:
    st.subheader("📑 Resultados Globales (desde Google Sheets)")
    st.dataframe(df_res)
else:
    st.info("ℹ️ No hay 'Resumen_Portafolios' cargado desde Google Sheets.")

# -----------------------
# Función robusta para descargar ZIP desde Drive
# -----------------------
def fetch_zip_from_drive(file_id, local_name="data.zip"):
    """
    Intenta descargar el ZIP de Drive.
    Primero usa gdown si está disponible; si falla, usa requests con el endpoint de descarga directa.
    Devuelve bytes del ZIP (o None si falla).
    """
    # 1) intentar gdown (si está instalado)
    try:
        import gdown
        url = f"https://drive.google.com/uc?id={file_id}"
        # gdown devuelve 0 en éxito, pero nos limitamos a leer el archivo resultante
        gdown.download(url, local_name, quiet=True)
        if os.path.exists(local_name) and zipfile.is_zipfile(local_name):
            with open(local_name, "rb") as f:
                return f.read()
    except Exception:
        # no fatal — fallback a requests
        pass

    # 2) fallback con requests a la URL de descarga directa
    try:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        content = resp.content
        # validar que sea un zip
        if zipfile.is_zipfile(io.BytesIO(content)):
            return content
        # en algunos casos Google devuelve HTML de confirmación; intentar detectar mensaje
        return None
    except Exception:
        return None

# -----------------------
# Descargar y validar ZIP
# -----------------------
st.write("### 📥 Descargando artefactos precomputados (ZIP) desde Google Drive...")
zip_bytes = fetch_zip_from_drive(ZIP_FILE_ID)

if zip_bytes is None:
    st.error(
        "❌ No se pudo descargar un ZIP válido desde Google Drive. "
        "Asegúrate de usar un link compartido correctamente y que el archivo sea un ZIP. "
        "Prueba a dar acceso público al archivo o a usar `gdown` localmente."
    )
    st.stop()

# -----------------------
# Abrir ZIP en memoria y leer archivos clave
# -----------------------
try:
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
except zipfile.BadZipFile:
    st.error("❌ El archivo descargado no es un ZIP válido (BadZipFile). Verifica el archivo en Drive.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error al abrir el ZIP: {e}")
    st.stop()

namelist = z.namelist()
st.write(f"🗂️ Archivos encontrados en el ZIP: {len(namelist)} (mostrar hasta 20)")
st.write(namelist[:20])

# Buscar frontier.csv (case-insensitive, puede estar en una subcarpeta)
def find_file_in_zip(z, target_basename_lower):
    names = z.namelist()
    for n in names:
        if n.lower().endswith(target_basename_lower):
            return n
    return None

frontier_name = find_file_in_zip(z, "frontier.csv")
gmvp_name = find_file_in_zip(z, "gmvp.csv") or find_file_in_zip(z, "gmv.csv")
ms_name = find_file_in_zip(z, "maxsharpe.csv") or find_file_in_zip(z, "markshare.csv") or find_file_in_zip(z, "max_sharpe.csv")

if frontier_name is None:
    st.error("❌ No se encontró 'frontier.csv' dentro del ZIP. Imposible graficar la frontera.")
    st.stop()

# leer frontier
with z.open(frontier_name) as f:
    df_frontier = pd.read_csv(f)

# detectar columnas de retorno & volatilidad (case-insensitive)
cols_lower = [c.lower() for c in df_frontier.columns]
ret_col = None
vol_col = None
for c, cl in zip(df_frontier.columns, cols_lower):
    if any(key in cl for key in ["retorno", "return", "mean", "r_"]):
        # prefer names containing 'diario' if present; but assign if likely
        ret_col = c
    if any(key in cl for key in ["volatil", "volatility", "vol", "sigma"]):
        vol_col = c

# buscar más específicos si hay varios
# Priorizar exactos 'retorno_diario' / 'volatilidad_diaria'
for c in df_frontier.columns:
    if c.lower() in ("retorno_diario", "retorno diario", "retorno_diario "):
        ret_col = c
    if c.lower() in ("volatilidad_diaria", "volatilidad diaria", "volatilidad_diaria "):
        vol_col = c

if ret_col is None or vol_col is None:
    st.error(
        "❌ No se pudieron identificar en 'frontier.csv' las columnas de retorno y volatilidad. "
        f"Columnas detectadas: {df_frontier.columns.tolist()}"
    )
    st.stop()

# asegurarse numéricos
df_frontier[ret_col] = pd.to_numeric(df_frontier[ret_col], errors="coerce")
df_frontier[vol_col] = pd.to_numeric(df_frontier[vol_col], errors="coerce")
df_frontier = df_frontier.dropna(subset=[ret_col, vol_col])

# Asumimos que frontier contiene retornos y volatilidad diarios (como en tu generator). Si no,
# el usuario podrá ajustar. Aquí anualizamos:
df_frontier["Retorno_Anual_%"] = df_frontier[ret_col] * 252 * 100
df_frontier["Riesgo_Anual_%"] = df_frontier[vol_col] * (252 ** 0.5) * 100

# -----------------------
# Preparar df_res (si no viene de Google Sheets)
# -----------------------
if df_res is None:
    st.warning("⚠️ 'Resumen_Portafolios' no cargado desde Google Sheets. Usando valores de ejemplo.")
    # ejemplo: reemplazar por tus reales si los tienes en el ZIP
    df_res = pd.DataFrame({
        "Portafolio": ["GMVP", "Max Sharpe"],
        "Riesgo Anual": [0.1304, 0.1651],   # fracciones (13.04% -> 0.1304)
        "Retorno Anual": [0.0929, 0.1883],  # fracciones
        "Ganancia Anual": [0, 0]
    })

# -----------------------
# Intentar leer GMVP/MaxSharpe desde ZIP si no están en Google Sheets
# -----------------------
df_gmvp_zip = None
df_ms_zip = None
if gmvp_name is not None:
    try:
        with z.open(gmvp_name) as f:
            df_gmvp_zip = pd.read_csv(f)
    except Exception:
        df_gmvp_zip = None

if ms_name is not None:
    try:
        with z.open(ms_name) as f:
            df_ms_zip = pd.read_csv(f)
    except Exception:
        df_ms_zip = None

# -----------------------
# Mostrar tabla de resumen
# -----------------------
st.subheader("📑 Resumen de Portafolios")
st.dataframe(df_res)

# -----------------------
# Graficar Comparación y Frontera
# -----------------------
st.write("### 🌐 Comparación entre portafolios y Frontera Eficiente")

fig = go.Figure()

# Frontera (anualizada) — eje X: Riesgo (%), eje Y: Retorno (%)
fig.add_trace(go.Scatter(
    x=df_frontier["Riesgo_Anual_%"],
    y=df_frontier["Retorno_Anual_%"],
    mode="lines",
    line=dict(color="#00CFFF", width=2),
    name="Frontera Eficiente"
))

# Puntos: todos los portafolios de df_res (si existen columnas)
if ("Riesgo Anual" in df_res.columns) and ("Retorno Anual" in df_res.columns):
    # df_res tiene fracciones (0.13 => 13%). Convertimos a % en eje Y
    fig.add_trace(go.Scatter(
        x=(df_res["Riesgo Anual"] * 100),
        y=(df_res["Retorno Anual"] * 100),
        mode="markers",
        marker=dict(size=10, color="#00CFFF"),
        name="Portafolios (Resumen)"
    ))

# Añadir GMVP y Max Sharpe destacados desde df_res si existen
if df_res is not None:
    if "GMVP" in df_res["Portafolio"].values:
        m = df_res[df_res["Portafolio"] == "GMVP"].iloc[0]
        fig.add_trace(go.Scatter(
            x=[m["Riesgo Anual"] * 100],
            y=[m["Retorno Anual"] * 100],
            mode="markers+text",
            marker=dict(color="#FF4B4B", size=16, symbol="star"),
            text=["GMVP"], textposition="top right",
            name="GMVP"
        ))
    if "Max Sharpe" in df_res["Portafolio"].values:
        m = df_res[df_res["Portafolio"] == "Max Sharpe"].iloc[0]
        fig.add_trace(go.Scatter(
            x=[m["Riesgo Anual"] * 100],
            y=[m["Retorno Anual"] * 100],
            mode="markers+text",
            marker=dict(color="#00FF9D", size=16, symbol="star"),
            text=["Max Sharpe"], textposition="top right",
            name="Max Sharpe"
        ))

# Si no vienen en df_res, intentar extraer un punto representativo desde GMVP.csv / MaxSharpe.csv en el ZIP
def try_add_point_from_weights(df_weights, mean_returns=None, cov_matrix=None, label=""):
    """
    df_weights: DataFrame con columnas ['Ticker','Peso'] o index=ticker, columns weight-like.
    mean_returns, cov_matrix: si están disponibles (no en este script por defecto), permitir calcular.
    """
    try:
        # buscar columna numérica que represente peso
        weight_col = None
        for c in df_weights.columns:
            if "peso" in c.lower() or "weight" in c.lower() or "peso %" in c.lower():
                weight_col = c
                break
        if weight_col is None:
            # intentar segunda columna
            if df_weights.shape[1] >= 2:
                weight_col = df_weights.columns[1]
            else:
                return False
        # si tiene ticker columna
        if "ticker" in [c.lower() for c in df_weights.columns]:
            tick_col = [c for c in df_weights.columns if c.lower() == "ticker"][0]
            series_weights = pd.Series(df_weights[weight_col].values, index=df_weights[tick_col].astype(str))
        else:
            # si el df está indexado
            series_weights = pd.Series(df_weights[weight_col].values, index=df_weights.index.astype(str))
        # Si mean_returns y cov_matrix no están disponibles, no calculamos, devolvemos False
        return False
    except Exception:
        return False

# Layout and styling
fig.update_layout(
    template="plotly_dark",
    plot_bgcolor="#0E1117",
    paper_bgcolor="#0E1117",
    font=dict(color="white"),
    xaxis_title="Riesgo (Volatilidad Anual %)",
    yaxis_title="Retorno Anual (%)",
    title="Frontera Eficiente - Markowitz"
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------
# Información adicional y diagnóstico
# -----------------------
st.markdown("---")
st.write("### ℹ️ Notas y diagnóstico")
st.write("- El ZIP fue descargado y listado. Si no ves 'frontier.csv' revisa el contenido del ZIP mostrado arriba.")
st.write("- Si deseas que los puntos GMVP/MaxSharpe se tomen del ZIP (pesos), sube los archivos `GMVP.csv` y `MaxSharpe.csv` dentro del ZIP con formato `Ticker,Peso` o indícamelo y te preparo el cálculo automático (se requiere mean_returns y cov_matrix).")
