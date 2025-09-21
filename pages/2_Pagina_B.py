import streamlit as st
import pandas as pd
import numpy as np
import os, zipfile, gdown
import matplotlib.pyplot as plt
from scipy.optimize import minimize

# =========================
# CONFIGURACIÓN DE DATOS
# =========================
ZIP_FILE_ID = "19R9zQNq5vmNuP3l2BMvN0V7rmNvegGas"
CARPETA_DATOS = "acciones"
ZIP_NAME = "acciones.zip"

def download_and_unzip():
    url = f"https://drive.google.com/uc?export=download&id={ZIP_FILE_ID}"
    st.info("Descargando base de datos desde Google Drive, por favor espera...")
    gdown.download(url, ZIP_NAME, quiet=False)
    with zipfile.ZipFile(ZIP_NAME, "r") as zf:
        zf.extractall(CARPETA_DATOS)

if not os.path.exists(CARPETA_DATOS) or len(os.listdir(CARPETA_DATOS)) == 0:
    download_and_unzip()

# Buscar CSV en la carpeta de históricos
archivos = []
for root, _, files in os.walk(CARPETA_DATOS):
    for f in files:
        if f.endswith(".csv"):
            archivos.append(os.path.join(root, f))

archivos = sorted(archivos)

if not archivos:
    st.error("No se encontraron archivos CSV en la carpeta de históricos.")
    st.stop()

# Diccionario {ticker: ruta al csv}
tickers = {os.path.basename(f).split("_")[0]: f for f in archivos}

# =========================
# INTERFAZ DE PÁGINA 2
# =========================
st.title("📊 Simulación de Portafolios con Markowitz")

st.write("Sube el archivo CSV con la selección de tu equipo. El sistema calculará el portafolio óptimo usando los datos históricos.")

# -------------------------
# CSV de guía para descargar
# -------------------------
st.markdown("### 📥 Descarga un CSV de ejemplo con la estructura correcta")
sample_df = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "GOOG", "AMZN"],
    "Porcentaje": [40, 30, 20, 10]
})
st.download_button(
    label="⬇️ Descargar CSV de ejemplo",
    data=sample_df.to_csv(index=False).encode("utf-8"),
    file_name="ejemplo_portafolio.csv",
    mime="text/csv",
)
st.info("El CSV debe contener las columnas **Ticker** y **Porcentaje**, y la suma de porcentajes debe ser 100%.")

# -------------------------
# Subida del CSV del equipo
# -------------------------
uploaded_file = st.file_uploader("📂 Sube tu archivo CSV de tu equipo", type=["csv"])

if uploaded_file is not None:
    df_equipo = pd.read_csv(uploaded_file)
    st.success("✅ Archivo cargado correctamente.")
    st.write("Vista previa de tu selección:")
    st.dataframe(df_equipo.head())

    # Validación básica
    if "Ticker" not in df_equipo.columns or "Porcentaje" not in df_equipo.columns:
        st.error("El CSV debe contener las columnas `Ticker` y `Porcentaje`.")
        st.stop()

    if abs(df_equipo["Porcentaje"].sum() - 100) > 0.01:
        st.error("❌ La suma de los porcentajes debe ser 100%.")
        st.stop()

    tickers_equipo = df_equipo["Ticker"].unique().tolist()
    st.info(f"Tu equipo seleccionó los siguientes activos: {', '.join(tickers_equipo)}")

    # =====================
    # BOTÓN PARA SIMULACIÓN
    # =====================
    if st.button("🚀 Iniciar Simulación"):

        # ------------------------
        # Cálculo de frontera eficiente real (toda la base de datos)
        # ------------------------
        precios_all = pd.DataFrame()
        for t in tickers.keys():
            df_hist = pd.read_csv(tickers[t], parse_dates=["Date"], index_col="Date")
            precios_all[t] = df_hist["Adj Close"]

        returns_all = np.log(precios_all / precios_all.shift(1)).dropna()
        pBar_all = returns_all.mean()
        Sigma_all = returns_all.cov()
        n_assets_all = len(pBar_all)

        def portfolio_return(weights, pBar=pBar_all):
            return np.sum(pBar * weights)

        def portfolio_volatility(weights, Sigma=Sigma_all):
            return np.sqrt(np.dot(weights.T, np.dot(Sigma, weights)))

        def minimize_volatility_all(target_return):
            w0 = np.ones(n_assets_all)/n_assets_all
            bounds = [(0,1)]*n_assets_all
            constraints = (
                {'type':'eq','fun': lambda w: portfolio_return(w)-target_return},
                {'type':'eq','fun': lambda w: np.sum(w)-1}
            )
            return minimize(portfolio_volatility, w0, method="SLSQP", bounds=bounds, constraints=constraints)

        frontier_volatility_all, frontier_returns_all = [], []
        target_returns_all = np.linspace(pBar_all.min(), pBar_all.max(), 30)
        for r in target_returns_all:
            opt = minimize_volatility_all(r)
            if opt.success:
                frontier_volatility_all.append(portfolio_volatility(opt.x))
                frontier_returns_all.append(portfolio_return(opt.x))

        # ------------------------
        # Cálculo del portafolio del jugador
        # ------------------------
        precios_player = pd.DataFrame()
        for t in tickers_equipo:
            if t in tickers:
                df_hist = pd.read_csv(tickers[t], parse_dates=["Date"], index_col="Date")
                precios_player[t] = df_hist["Adj Close"]
            else:
                st.warning(f"No se encontró histórico para {t}")

        if precios_player.empty:
            st.error("No se encontraron datos históricos para los tickers seleccionados.")
            st.stop()

        returns_player = np.log(precios_player / precios_player.shift(1)).dropna()
        pBar_player = returns_player.mean()
        Sigma_player = returns_player.cov()
        n_assets_player = len(pBar_player)

        # Funciones
        def portfolio_return_player(weights):
            return np.sum(pBar_player * weights)

        def portfolio_volatility_player(weights):
            return np.sqrt(np.dot(weights.T, np.dot(Sigma_player, weights)))

        # GMVP jugador
        def global_min_variance_player():
            w0 = np.ones(n_assets_player)/n_assets_player
            bounds = [(0,1)]*n_assets_player
            constraints = ({'type':'eq','fun': lambda w: np.sum(w)-1})
            return minimize(portfolio_volatility_player, w0, method="SLSQP", bounds=bounds, constraints=constraints)

        gmv_player = global_min_variance_player()

        # Max Sharpe jugador
        risk_free = 0.0
        def negative_sharpe_player(weights):
            ret = portfolio_return_player(weights)
            vol = portfolio_volatility_player(weights)
            return -(ret-risk_free)/vol

        def max_sharpe_player():
            w0 = np.ones(n_assets_player)/n_assets_player
            bounds = [(0,1)]*n_assets_player
            constraints = ({'type':'eq','fun': lambda w: np.sum(w)-1})
            return minimize(negative_sharpe_player, w0, method="SLSQP", bounds=bounds, constraints=constraints)

        ms_player = max_sharpe_player()

        # =====================
        # Mostrar resultados
        # =====================
        st.subheader("📈 Resultados del Portafolio del Jugador (Anualizados)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**GMVP Jugador**")
            st.write("Pesos:", dict(zip(pBar_player.index, np.round(gmv_player.x, 3))))
            st.write("Retorno esperado anual:", round(portfolio_return_player(gmv_player.x)*252*100,2), "%")
            st.write("Volatilidad anual:", round(portfolio_volatility_player(gmv_player.x)*np.sqrt(252)*100,2), "%")

        with col2:
            st.markdown("**Max Sharpe Jugador**")
            st.write("Pesos:", dict(zip(pBar_player.index, np.round(ms_player.x, 3))))
            st.write("Retorno esperado anual:", round(portfolio_return_player(ms_player.x)*252*100,2), "%")
            st.write("Volatilidad anual:", round(portfolio_volatility_player(ms_player.x)*np.sqrt(252)*100,2), "%")

        # =====================
        # Gráfico comparativo
        # =====================
        st.subheader("📊 Comparativa con Frontera Eficiente Real")
        fig, ax = plt.subplots(figsize=(8,5))

        # Frontera eficiente real
        ax.plot(np.array(frontier_volatility_all)*np.sqrt(252), np.array(frontier_returns_all)*252, 
                'b--', label="Frontera Eficiente Real")

        # GMVP jugador
        ax.scatter(portfolio_volatility_player(gmv_player.x)*np.sqrt(252), 
                   portfolio_return_player(gmv_player.x)*252, 
                   c="red", marker="o", s=80, label="GMVP Jugador")

        # Max Sharpe jugador
        ax.scatter(portfolio_volatility_player(ms_player.x)*np.sqrt(252), 
                   portfolio_return_player(ms_player.x)*252, 
                   c="green", marker="*", s=120, label="Max Sharpe Jugador")

        ax.set_xlabel("Volatilidad Anual")
        ax.set_ylabel("Retorno Anual Esperado")
        ax.legend()
        st.pyplot(fig)

        # =====================
        # Botón para avanzar
        # =====================
        if st.button("✅ Finalizar Simulación y continuar a Página 3"):
            st.session_state["simulacion_finalizada"] = True
            st.success("Simulación finalizada. Ahora puedes ir a la Página 3.")
