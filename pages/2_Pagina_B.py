import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import gdown
import zipfile

# ================================
# CONFIGURACIÓN DE LA PÁGINA
# ================================
st.title("📊 Página 3 — Comparación con Frontera Eficiente")
st.write("""
En esta página se comparará el **portafolio del usuario** con la **frontera eficiente**, 
el portafolio de **mínima varianza (GMVP)** y el de **máxima Sharpe**.
""")

# ================================
# FUENTE 1: ARTEFACTOS PRECOMPUTADOS
# ================================
st.info("📥 Cargando artefactos precomputados...")

ARTIFACTS_FILE_ID = "1cJFHOWURl7DYEYc4r4SWvAvV3Sl7bZCB"  # <-- tu ID real del ZIP de artefactos
ARTIFACTS_ZIP = "artefactos.zip"
ARTIFACTS_FOLDER = "artefactos"

try:
    gdown.download(f"https://drive.google.com/uc?id={ARTIFACTS_FILE_ID}", ARTIFACTS_ZIP, quiet=False)
    with zipfile.ZipFile(ARTIFACTS_ZIP, "r") as zip_ref:
        zip_ref.extractall(ARTIFACTS_FOLDER)
    st.success("✅ Artefactos cargados correctamente")
except Exception as e:
    st.error(f"❌ No se pudieron cargar los artefactos: {e}")

# ================================
# LECTURA DE ARCHIVOS PRECOMPUTADOS
# ================================
frontier, gmvp, maxsharpe, mean_returns, tickers_list = None, None, None, None, None

try:
    frontier = pd.read_csv(os.path.join(ARTIFACTS_FOLDER, "frontier.csv"))
    gmvp = pd.read_csv(os.path.join(ARTIFACTS_FOLDER, "GMVP.csv"))
    maxsharpe = pd.read_csv(os.path.join(ARTIFACTS_FOLDER, "MaxSharpe.csv"))
    mean_returns = pd.read_csv(os.path.join(ARTIFACTS_FOLDER, "mean_returns.csv"))
    tickers_list = pd.read_csv(os.path.join(ARTIFACTS_FOLDER, "tickers.csv"))

    st.success("✅ Archivos precomputados leídos correctamente")
except Exception as e:
    st.error(f"❌ Error leyendo artefactos: {e}")

# ================================
# CARGAR RESULTADOS DEL USUARIO
# ================================
st.subheader("📂 Cargar resultados del Portafolio Usuario")
uploaded_file = st.file_uploader("Sube el archivo CSV generado en Página 2", type="csv")

df_user = None
if uploaded_file is not None:
    try:
        df_user = pd.read_csv(uploaded_file)
        st.success("✅ Archivo del portafolio del usuario cargado")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")

# ================================
# GRAFICAR FRONTERA Y COMPARACIÓN
# ================================
if frontier is not None and gmvp is not None and maxsharpe is not None:
    st.subheader("📈 Frontera Eficiente y Portafolios Óptimos")

    fig = go.Figure()

    # Frontera eficiente
    if "Volatility" in frontier.columns and "Return" in frontier.columns:
        fig.add_trace(go.Scatter(
            x=frontier["Volatility"], y=frontier["Return"],
            mode="lines", name="Frontera Eficiente", line=dict(color="blue")
        ))

    # GMVP
    if "Volatility" in gmvp.columns and "Return" in gmvp.columns:
        fig.add_trace(go.Scatter(
            x=gmvp["Volatility"], y=gmvp["Return"],
            mode="markers", name="GMVP", marker=dict(color="green", size=12, symbol="diamond")
        ))

    # Max Sharpe
    if "Volatility" in maxsharpe.columns and "Return" in maxsharpe.columns:
        fig.add_trace(go.Scatter(
            x=maxsharpe["Volatility"], y=maxsharpe["Return"],
            mode="markers", name="Max Sharpe", marker=dict(color="red", size=12, symbol="star")
        ))

    # Usuario
    if df_user is not None and "Portafolio" in df_user.columns:
        if "Retorno anual esperado" in df_user.columns and "Volatilidad anual esperada" in df_user.columns:
            user_return = df_user["Retorno anual esperado"].iloc[0]
            user_vol = df_user["Volatilidad anual esperada"].iloc[0]

            fig.add_trace(go.Scatter(
                x=[user_vol], y=[user_return],
                mode="markers", name="Usuario",
                marker=dict(color="orange", size=14, symbol="circle")
            ))

    fig.update_layout(
        title="Frontera Eficiente vs Portafolios",
        xaxis_title="Volatilidad (σ)",
        yaxis_title="Retorno esperado (μ)",
        legend=dict(x=0.02, y=0.98)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ No se pudo construir la frontera eficiente por falta de archivos.")
