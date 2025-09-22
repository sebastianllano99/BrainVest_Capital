import os
import streamlit as st
import os
import pandas as pd
import plotly.express as px
import matplotlib.colors as mcolors
import numpy as np
from scipy.optimize import minimize
import plotly.express as px

# -------------------------
# Config

# -------------------------
CAPITAL_TOTAL = 500_000_000  # 500 millones COP (fijo)
DATA_FOLDER = "acciones"     # carpeta donde están los CSV de Yahoo

# color

# -------------------------
# Función para generar paleta monocromática
# -------------------------
def generar_paleta(base_color, n):
    cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["#ffffff", base_color, "#000000"])
    return [mcolors.to_hex(cmap(i)) for i in np.linspace(0.2, 0.8, n)]
# Interfaz de usuario en la pagina, incorporar a los titulos emoticones o diseños que llamen más la atencion en la pagina

st.title(" Mi Portafolio de Inversión")
st.info(f" El monto total disponible para invertir es **${CAPITAL_TOTAL:,.0f} COP** (fijo).")
 
#incorporar emoticones o diseños que llamen más la atencion en la pagina
# -------------------------
# Interfaz
# -------------------------
st.title("📊 Mi Portafolio de Inversión")
st.info(f"💰 El monto total disponible para invertir es **${CAPITAL_TOTAL:,.0f} COP** (fijo).")

st.warning(
    """
**Recuerda**: 
🔔 **Recuerda**:
- El CSV debe contener **dos columnas**: `Ticker` y `Porcentaje`.
- El `Ticker` debe coincidir con los tickers de tus archivos en la carpeta `acciones/`.  
  Ejemplo: si el archivo es `AAPL_2000-01-01_2024-12-31.csv`, el ticker válido es **AAPL**.
- La suma de `Porcentaje` debe ser **100**.
"""
)

# -------------------------
# Detectar tickers disponibles

# -------------------------
available_tickers = set()
if os.path.isdir(DATA_FOLDER):
    for root, _, files in os.walk(DATA_FOLDER):
@@ -44,81 +45,83 @@ def generar_paleta(base_color, n):
                ticker = os.path.basename(f).split("_")[0].upper()
                available_tickers.add(ticker)
else:
    st.info(f"Nota: la carpeta `{DATA_FOLDER}` no se encontró. La validación automática de tickers será omitida.") #incorporar emoticones o diseños que llamen más la atencion en la pagina
    st.info(f"Nota: la carpeta `{DATA_FOLDER}` no se encontró. La validación automática de tickers será omitida.")

# -------------------------
# Botón para descargar CSV ejemplo

# -------------------------
if available_tickers:
    sample_tickers = list(available_tickers)[:4]
else:
    sample_tickers = ["AAPL", "MSFT", "GOOG", "AMZN"]

sample_df = pd.DataFrame({"Ticker": sample_tickers, "Porcentaje": [40, 30, 20, 10]})
st.download_button(
    label="⬇Descargar CSV de ejemplo", #incorporar emoticones o diseños que llamen más la atencion en la pagina
    label="⬇️ Descargar CSV de ejemplo",
    data=sample_df.to_csv(index=False).encode("utf-8"),
    file_name="ejemplo_portafolio.csv",
    mime="text/csv",
)

st.markdown("---")


# Subida del archivo CSV

uploaded = st.file_uploader(" Sube tu archivo CSV (Ticker, Porcentaje)", type=["csv"])#incorporar emoticones o diseños que llamen más la atencion en la pagina
# -------------------------
# Subida del CSV
# -------------------------
uploaded = st.file_uploader("📂 Sube tu archivo CSV (Ticker, Porcentaje)", type=["csv"])

if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)

        # normalizar nombres de columnas
        cols_map = {c.lower().strip(): c for c in df.columns}
        if "ticker" not in cols_map or "porcentaje" not in cols_map:
            st.error("El CSV debe contener las columnas `Ticker` y `Porcentaje`.")#incorporar emoticones o diseños que llamen más la atencion en la pagina
            st.error("❌ El CSV debe contener las columnas `Ticker` y `Porcentaje`.")
        else:
            df = df.rename(columns={cols_map["ticker"]: "Ticker", cols_map["porcentaje"]: "Porcentaje"})
            df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
            df["Porcentaje"] = pd.to_numeric(df["Porcentaje"], errors="coerce")

            if df["Porcentaje"].isnull().any():
                st.error(" Hay valores no numéricos en la columna `Porcentaje`.")#incorporar emoticones o diseños que llamen más la atencion en la pagina
                st.error("❌ Hay valores no numéricos en la columna `Porcentaje`.")
            else:
                suma_pct = df["Porcentaje"].sum()
                if abs(suma_pct - 100) > 0.01:
                    st.error(f" Los porcentajes deben sumar 100. Actualmente suman {suma_pct:.6f}.")#incorporar emoticones o diseños que llamen más la atencion en la pagina
                    st.error(f"❌ Los porcentajes deben sumar 100. Actualmente suman {suma_pct:.6f}.")
                else:
                    if available_tickers:
                        missing = [t for t in df["Ticker"] if t not in available_tickers]
                        if missing:
                            st.error(
                                " Algunos tickers del CSV no se encontraron en la carpeta 'acciones':\n\n"
                                "❌ Algunos tickers del CSV no se encontraron en la carpeta 'acciones':\n\n"
                                + ", ".join(missing)
                            )
                            st.stop()
#incorporar emoticones o diseños que llamen más la atencion en la pagina

                    # calcular montos
                    df["Inversion (COP)"] = (df["Porcentaje"] / 100.0 * CAPITAL_TOTAL).round(0).astype(int)

                    st.subheader(" Distribución del Portafolio")
                    st.subheader("📋 Distribución del Portafolio")
                    st.dataframe(df, use_container_width=True)

                    total_invertido = int(df["Inversion (COP)"].sum())
                    st.success(f"Portafolio válido. Total invertido: {total_invertido:,.0f} COP")

                    st.success(f"✅ Portafolio válido. Total invertido: {total_invertido:,.0f} COP")

                    # -------------------------
                    # Selector de gráfico
                 #incorporar emoticones o diseños que llamen más la atencion en la pagina
                    chart_type = st.radio(" Selecciona el tipo de gráfico:", ["Torta", "Barras"])
                    # -------------------------
                    chart_type = st.radio("📊 Selecciona el tipo de gráfico:", ["Torta", "Barras"])

                    # paleta color
                    # generar paleta monocromática (ejemplo: azul corporativo #1f77b4)
                    palette = generar_paleta("#1f77b4", len(df))

                    if chart_type == "Torta":
                        fig = px.pie(
                            df,
                            names="Ticker",
                            values="Porcentaje",
                            title="Distribución del Portafolio (%)",#incorporar emoticones o diseños que llamen más la atencion en la pagina
                            title="Distribución del Portafolio (%)",
                            hole=0.3,
                            color="Ticker",
                            color_discrete_sequence=palette
@@ -131,17 +134,17 @@ def generar_paleta(base_color, n):
                            y="Ticker",
                            orientation="h",
                            text="Porcentaje",
                            title="Distribución del Portafolio (%)",#incorporar emoticones o diseños que llamen más la atencion en la pagina
                            title="Distribución del Portafolio (%)",
                            color="Ticker",
                            color_discrete_sequence=palette
                        )
                        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
                        fig.update_layout(yaxis=dict(categoryorder="total ascending"))

                    # Fondo 
                    # Fondo oscuro elegante
                    fig.update_layout(
                        title_font=dict(size=22, color="white"),
                        legend_title="Acciones", #incorporar emoticones o diseños que llamen más la atencion en la pagina
                        legend_title="Acciones",
                        legend=dict(font=dict(size=12, color="white")),
                        plot_bgcolor="#1e1e2f",   # gris oscuro
                        paper_bgcolor="#1e1e2f",  # gris oscuro
@@ -150,7 +153,6 @@ def generar_paleta(base_color, n):
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        st.error(f"⚠️ Error al procesar el archivo: {e}")
else:
    st.info("Sube un CSV para ver la distribución.")
#incorporar emoticones o diseños que llamen más la atencion en la pagina
    st.info("📥 Sube un CSV para ver la distribución.")

